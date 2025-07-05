import cyal, cyal.efx, cyal.hrtf, cyal.exceptions
import contextlib
import os
import weakref
import math
import pyogg
import requests
from .audio.soundgroup import SoundGroup
from .audio.sound import Sound
from . import options
from . import path_utils
from . import consts

class AudioManager():
    def __init__(self):
        device = options.get("audio_device", cyal.util.get_default_all_device_specifier())
        if device == "system default": device = cyal.util.get_default_all_device_specifier()
        self.context = cyal.Context(
            cyal.Device(name=device),
            make_current=True,
            mono_sources=1024,
            stereo_sources=1024,
            max_auxiliary_sends=64,
        )
        self.silent_buf = bytearray(96*options.get("jitter_buffer", 60))
        self.hrtf = cyal.hrtf.HrtfExtension(self.context.device)
        self.hrtf.use(options.get("hrtf_model", "Built-In HRTF"))
        self.muted=False
        self.max_distance = 30
        self.efx = cyal.efx.EfxExtension(self.context)
        
        self.listener = self.context.listener
        self.listener.position=(0,0,0)
        self.listener.orientation=[0, 1, 0, 0, 0, 1] # right-handed co-ordenate system. X is left to right, Y is backward to forward, Z is down to up. 
        self.soundgroups = weakref.WeakSet()
        self.filter = []
        self.sends = [
            None,
            None,
            None,
            None
        ]
        self.volume_categories = {
            "master": [options.get("volume_master", 100), weakref.WeakSet()],
            "self": [options.get("volume_self", 100), weakref.WeakSet()],
            "players": [options.get("volume_players", 100), weakref.WeakSet()],
            "zombies": [options.get("volume_zombies", 100), weakref.WeakSet()],
            "weapons": [options.get("volume_weapons", 100), weakref.WeakSet()],
            "ui": [options.get("volume_ui", 100), weakref.WeakSet()],
            "music": [options.get("volume_music", 100), weakref.WeakSet()],
            "ambience": [options.get("volume_ambience", 100), weakref.WeakSet()],
            "sound_source": [options.get("volume_sound_source", 100), weakref.WeakSet()],
            "miscelaneous": [options.get("volume_miscelaneous", 100), weakref.WeakSet()]
        }
        self.unbound_sources = []
        self.buffers = weakref.WeakValueDictionary()
    
    # Sets the orientation, taking (horizontal angle, pitch, lean)
    # if anyone goes anywhere near this function with a 10foot pole, you'll find yourself without a left testical
    def make_orientation(self, angle: float = 0.0, pitch: float = 0.0, lean: float = 0.0):
        # converts to radians for for use in math.sin and math.cos
        angle_rad = math.radians(angle)
        pitch_rad = math.radians(pitch)
        lean_rad = math.radians(lean)
        
        # forward x, y, and z indicate which way the listener is pointing
        forward_x = math.sin(angle_rad) # The x component of the forward vector only deppends on the horizontal angle
        forward_y = math.cos(angle_rad) # the Y component of the forward vector only deppends on the horizontal angle
        forward_z = math.sin(pitch_rad) * math.cos(lean_rad) # multiplies the sine of the pitch by the cosine of the lean in order to create the correct direction when leaning/pitching. when lean is 0, the pitch is multiplied by 1 so no querky behavia
        
        # the up x, y and z indicate which way is up from the listener's perspective
        up_x = -math.sin(pitch_rad) * math.sin(angle_rad) + math.sin(lean_rad) # multiplies the negative sine of pitch by the sine of angle so that when facing forward, x is 0. Adds the sine of lean so that when leaning away from 0 degrees, the necesary lean offset is added. The negative sine of pitch is used so the correct perpedicular angle between the forward and up vectors are kept. 
        up_y = -math.sin(pitch_rad) * math.cos(angle_rad) + math.sin(lean_rad) # multiplies the negative sine of pitch by the cos of angle so that when facing forward, y is 0. Adds the sine of lean so that when leaning away from 0 degrees, the necesary lean offset is added. The negative sine of pitch is used so the correct perpedicular angle between the forward and up vectors are kept. 
        up_z = math.cos(pitch_rad) * math.cos(lean_rad) # same as forward z, except uses to cosine pitch in order to maintain a perpendicular angle

        return (forward_x, forward_y, forward_z, up_x, up_y, up_z)
    @property
    def orientation(self):
        return self.listener.orientation
    
    @orientation.setter
    def orientation(self, value: tuple):
        self.listener.orientation = self.make_orientation(*value)

    @property
    def position(self):
        return self.listener.position
    
    @position.setter
    def position(self, value: tuple):
        self.listener.position=value
    
    def load_buffer(self, path: str) -> cyal.Buffer | None:
        if path.split(":")[0] == "server_sounds":
            path = path.split(":")[1]
            if not os.path.exists(path):
                if path.startswith("server_sounds/") and not os.path.exists("data/server_sounds/"):
                    os.mkdir("data/server_sounds")
                data = requests.get(f"{consts.SERVER_SOUNDS_URL}{path}")
                if data.ok:
                    try:
                        with open(f"data/{path}", 'wb+') as f:
                            f.write(data.content)
                    except e:
                        print(e)
        if path.split("/")[0] != "data": path= f"data/{path}"
        if not path.endswith(".ogg"): path = path_utils.random_item(path)
        path = os.path.realpath(path)
        if path in self.buffers.keys():
            return self.buffers[path]
        try:
            file = pyogg.VorbisFile(path)
            try: buffer = self.context.gen_buffer()
            except cyal.exceptions.InvalidOperationError as e:
                print(e)
                buffer = self.context.gen_buffer()
        
            format = None
            match file.channels:
                case 1: format= cyal.BufferFormat.MONO16
                case 2: format = cyal.BufferFormat.STEREO16
                case _: raise(RuntimeError("file is neither mono or stereo 16 bit"))
            buffer.set_data(
                file.buffer,
                sample_rate=file.frequency,
                format = format
            )
            self.buffers[path] = buffer
            return buffer
        except:
            print("unable to load file")
            return None

    def set_volume(self, cat, volume):
        with contextlib.suppress(RuntimeError, AttributeError):
            with self.context.batch():
                if cat not in self.volume_categories.keys(): cat="master"
                self.volume_categories[cat][0] = volume
                options.set(f"volume_{cat}", volume)
                if cat == "master":
                    self.listener.gain = self.volume_categories["master"][0] / 100
                    return
                
                for source in self.volume_categories[cat][1]:
                    gain = (self.volume_categories[cat][0] / 100) * (source.volume / 100)
                    if not source.muted: source.source.gain = gain

    def play_unbound(self, path, x, y, z, looping=False, cat="miscelaneous", direct=False, cone_inner_angle=360, cone_outer_angle=360, cone_outer_gain=0.4, cone_outer_gainhf=0.4, direction=(0,0,0), velocity=(0,0,0), volume=100):
        if self.muted and not looping: return
        direction=self.make_orientation(*direction)
        buffer = self.load_buffer(path)
        if not buffer: return
        if not self.volume_categories[cat] or cat == "master": return
        source = self.context.gen_source(
            looping=looping, 
            gain = 
            (volume / 100) *
            (self.volume_categories[cat][0]/100),
            direction=direction, 
            position=(x,y,z), 
            velocity=velocity
        )
        if direct:
            source.direct_channels=True
            source.spatialize = False
        else:
            source.direct_channels = False
            source.spatialize=True
            source.cone_inner_angle = cone_inner_angle
            source.cone_outer_angle = cone_outer_angle
            source.cone_outer_gain = cone_outer_gain
            source.set("cone_outer_gainhf", cone_outer_gainhf)
            

        source.buffer = buffer
        snd = Sound(source, volume, False, cat=cat)
        self.unbound_sources.append(snd)
        if len(self.filter) > 0 and self.filter[-1] is not None: source.direct_filter = self.filter[-1]
        for i in self.sends:
            try: self.efx.send(source, self.sends.index(i), i, filter=self.filter[-1] if len(self.filter) > 0 else None)
            except cyal.exceptions.InvalidOperationError as e: print(e)
        source.play()
        self.volume_categories["master"][1].add(source)
        self.volume_categories[cat][1].add(source)
        return snd

    def loop(self):
        with contextlib.suppress(RuntimeError):
            with self.context.batch():
                for source in self.unbound_sources:
                    if source.source.state == cyal.SourceState.STOPPED:
                        self.unbound_sources.pop(self.unbound_sources.index(source))
                        source.destroy()
                        break
                for soundgroup in self.soundgroups:
                    soundgroup.loop()
    
    def create_soundgroup(self, direct=False, radius=0.5, filterable=False):
        sg = SoundGroup(self.context, self, direct, radius=radius, filterable=filterable)
        for i in self.filter: sg.apply_filter(i)
        for i in self.sends:
            sg.apply_effect(i, self.sends.index(i))
        
        self.soundgroups.add(sg)
        return sg
    


    def apply_effect(self, slot, sendnum=0, filter=None):
        self.sends[sendnum] = slot
        for source in self.unbound_sources:
            self.efx.send(source.source, sendnum, slot, filter=self.filter[-1] if len(self.filter) > 0 else None)
        for sg in self.soundgroups:
            sg.apply_effect(slot, sendnum, filter=filter)
        
    def apply_filter(self, filter, exclude=[], replace=True, clear=False):
        if clear: self.filter.clear()
        if filter is not None: 
            if replace and len(self.filter) > 0: self.filter.pop()
            self.filter .append(filter)
        elif len(self.filter) > 0: self.filter.pop()

        for source in self.unbound_sources:
            if filter is not None: source.source.direct_filter = filter
            else: 
                del source.source.direct_filter
                if len(self.filter) > 0 and self.filter[-1] is not None: source.source.direct_filter = self.filter[-1]

        for sg in self.soundgroups:
            if sg not in exclude: sg.apply_filter(filter, replace=replace, clear=clear)
    
    def gen_filter(self, type, *args):
        try: filter = self.efx.gen_filter(type=type)
        except cyal.exceptions.InvalidOperationError as e:
            print(e)
            return None
        for param in args:
            try: filter.set(*param)
            except cyal.exceptions.InvalidAlEnumError as e: print(f"{e} in audio_manager.gen_filter with parameters {param}")
        return filter
    
    def gen_effect(self, type, *args):
        try:
            efx= self.efx.gen_effect(type=type)
            for param in args:
                try: efx.set(*param)
                except cyal.exceptions.InvalidAlEnumError as e: print(f"{e} in audio_manager.gen_effect on parameters {param}")
            slot = self.efx.gen_auxiliary_effect_slot()
            slot.effect = efx
            return slot
        except MemoryError as e:
            print(e)
            return None
        except cyal.exceptions.InvalidOperationError:
            print(e)
            return None
