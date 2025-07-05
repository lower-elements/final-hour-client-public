import cyal, cyal.efx
import contextlib
import math
import weakref

import cyal.exceptions
from .sound import Sound
from ..movement import get_3d_distance

class SoundGroup:
    def __init__(self, context: cyal.Context, parent, direct=False, radius=0.5, filterable=False):
        self.context = context
        self.parent = parent
        self.direct = direct
        self.filterable=filterable
        self.muted=False
        self.filter = []
        self.sends = [
            None,
            None,
            None,
            None
        ]
        self.labeled_sources = {}
        self.unlabeled_sources = []
        
        self._velocity = (0,0,0)
        self._position = (0,0,0)
        self._orientation = self.parent.make_orientation(0, 0, 0)
        self._inner_cone_angle = 360
        self._outer_cone_angle = 360
        self._cone_outer_gain=0.4
        self._cone_outer_gainhf=0.4
        self._pitch=1.0
        self._radius = radius
        
        
    
    
    @property
    def position(self):
        return self._position
    
    @position.setter
    def position(self, value: tuple):
        self._position = value
        with contextlib.suppress(RuntimeError, AttributeError):
            with self.context.batch():
                for source in self.labeled_sources.values(): source.source.position=value
                for source in self.unlabeled_sources: source.source.position = value
    

    @property
    def velocity(self):
        return self._velocity
    
    @velocity.setter
    def velocity(self, value: (float, float, float)):
        self._velocity = value
        with contextlib.suppress(RuntimeError, AttributeError):
            with self.context.batch():
                for source in self.labeled_sources.values(): source.source.velocity = value
                for source in self.unlabeled_sources: source.source.velocity = value
    

    @property
    def inner_cone_angle(self):
        return self._inner_cone_angle
    
    @inner_cone_angle.setter
    def inner_cone_angle(self, value: float):
        self._inner_cone_angle = value
        with contextlib.suppress(RuntimeError, AttributeError):
            with self.context.batch():
                for source in self.labeled_sources.values(): source.source.inner_cone_angle = value
                for source in self.unlabeled_sources: source.source.inner_cone_angle = value
    

    @property
    def outer_cone_angle(self):
        return self._outer_cone_angle
    
    @outer_cone_angle.setter
    def outer_cone_angle(self, value: float):
        self._outer_cone_angle = value
        with contextlib.suppress(RuntimeError, AttributeError):
            with self.context.batch():
                for source in self.labeled_sources.values(): source.source.outer_cone_angle = value
                for source in self.unlabeled_sources: source.source.outer_cone_angle = value
    

    @property
    def orientation(self):
        return self._orientation
    
    @orientation.setter
    def orientation(self, value: tuple):
        self._orientation= self.parent.make_orientation(*value)
        with contextlib.suppress(RuntimeError, AttributeError):
            with self.context.batch():
                for source in self.labeled_sources.values(): source.source.direction = self.parent.make_orientation(*value)
                for source in self.unlabeled_sources: source.source.direction = self.parent.make_orientation(*value)
    

    def play(self, path, looping=False, id="", dist=False, cat="miscelaneous", rel_x=0, rel_y=0, rel_z=0, volume=100, ):
        if self.parent.muted and not looping or self.parent.muted and id not in ["", None]: return
        buffer = self.parent.load_buffer(path)
        if not buffer: 
            print("unable to load buffer")
            return None
        if cat not in self.parent.volume_categories.keys() or cat == "master": cat = "miscelaneous"
        try: 
            source = self.context.gen_source(
                looping=looping, 
                gain = 
                (volume/100) *
                (self.parent.volume_categories[cat][0]/100),
                direction=self.orientation, 
                position=(self.position[0]+rel_x, self.position[1]+rel_y, self.position[2]+rel_z), 
                velocity=self.velocity
            )
        except MemoryError as e:
            print(f"{e}")
        except cyal.exceptions.InvalidOperationError as e:
            print(e)
            source = self.context.gen_source(
                looping=looping, 
                gain = 
                (volume/100) *
                (self.parent.volume_categories[cat][0]/100),
                direction=self.orientation, 
                position=(self.position[0]+rel_x, self.position[1]+rel_y, self.position[2]+rel_z), 
                velocity=self.velocity
            )
        if self.direct:
            source.direct_channels=True
            source.spatialize = False
        else:
            source.direct_channels = False
            source.spatialize = True
            source.cone_inner_angle = self.inner_cone_angle
            source.cone_outer_angle = self.outer_cone_angle
            source.cone_outer_gain = self._cone_outer_gain
            source.set("cone_outer_gainhf", 0.4)
            

        source.buffer = buffer
        snd = Sound(source, volume, dist, cat=cat)
        if id == "" or id == None:
            self.unlabeled_sources.append(snd)
        else: 
            if id in self.labeled_sources.keys():
                self.labeled_sources[id].source.stop()
                self.labeled_sources[id].destroy()
            
            self.labeled_sources[id] = snd
        self.mute_if_far()
        for i in self.sends:
            try: self.parent.efx.send(source, self.sends.index(i), i, filter=self.filter[-1] if len(self.filter) > 0 else None)
            except cyal.exceptions.InvalidOperationError as e: pass
        if self.filter is not None and len(self.filter) > 0: source.direct_filter=self.filter[-1]
        source.play()
        self.parent.volume_categories["master"][1].add(snd)
        self.parent.volume_categories[cat][1].add(snd)
        return snd
    
    def pause(self):
        with self.context.batch():
            for sound in self.labeled_sources.values():
                if sound.source: sound.source.pause()
            for sound in self.unlabeled_sources:
                if sound.source: sound.source.pause()

    def resume(self):
        with self.context.batch():
            for sound in self.labeled_sources.values():
                if sound.source: sound.source.play()
            for sound in self.unlabeled_sources:
                if sound.source: sound.source.play()

    
    
    def destroy(self):
        with self.context.batch():
            for sound in self.labeled_sources.values():
                sound.destroy()
            for sound in self.unlabeled_sources:
                sound.destroy()
        self.unlabeled_sources.clear()
        self.labeled_sources.clear()
    
    def apply_effect(self, slot, sendnum: int=0, filter=None):
        if self.direct: return
        self.sends[sendnum] = slot
        with self.context.batch():
                for source in self.unlabeled_sources:
                    if source.source is None: continue
                    self.parent.efx.send(source.source, sendnum, slot, filter=self.filter[-1] if len(self.filter) > 0 else None)
                for source in self.labeled_sources.values():
                    if source.source is None: continue
                    self.parent.efx.send(source.source, sendnum, slot, filter=self.filter[-1] if len(self.filter) > 0 else None)

    def apply_filter(self, filter, replace = False, clear=False):
        if not self.filterable and self.direct: return
        if clear: self.filter.clear()
        if filter is not None: 
            if replace and len(self.filter) > 0: self.filter.pop()
            self.filter .append(filter)
        elif len(self.filter) > 0: self.filter.pop()
        with contextlib.suppress(RuntimeError, AttributeError):
            with self.context.batch():
                for source in self.labeled_sources.values():
                    if source.source is None : continue
                    if filter is not None: source.source.direct_filter = filter
                    else: 
                        del source.source.direct_filter
                        if len(self.filter) > 0 and self.filter[-1] is not None: source.source.direct_filter = self.filter[-1]
                for source in self.unlabeled_sources:
                    if source.source is None: continue
                    if filter is not None: source.source.direct_filter = filter
                    else: 
                        try: del source.source.direct_filter
                        except cyal.exceptions.InvalidOperationError as e: del source.source.direct_filter
                            
                        if len(self.filter) > 0 and self.filter[-1] is not None: source.source.direct_filter = self.filter[-1]

    @property
    def radius(self):
        return self._radius

    @radius.setter
    def radius(self, value):
        self._radius = value
        with contextlib.suppress(RuntimeError, AttributeError):
            with self.context.batch():
                for source in self.unlabeled_sources: source.source.radius =value
                for source in self.labeled_sources.values(): source.source.radius = value
    
    

    @property
    def pitch(self):
        return self._pitch
    @pitch.setter
    def pitch(self, value):
        self._pitch = value
        with contextlib.suppress(RuntimeError, AttributeError):
            with self.context.batch():
                for source in self.unlabeled_sources: source.source.pitch=value
                for source in self.labeled_sources.values(): source.source.pitch = value
    
    
    def loop(self):
        self.mute_if_far()
            
        for source in self.labeled_sources:
            if self.labeled_sources[source].source is None: 
                source.destroy()
                continue
            if self.labeled_sources[source].source.state == cyal.SourceState.STOPPED: 
                source = self.labeled_sources.pop(source)
                source.destroy()
                break
        for source in self.unlabeled_sources:
            if source.source is None: 
                source.destroy()
                continue

            if source.source.state == cyal.SourceState.STOPPED: 
                source = self.unlabeled_sources.pop(self.unlabeled_sources.index(source))
                source.destroy()
                break

    def mute_if_far(self):
        if self.direct: return
        for source in self.labeled_sources:
            if self.labeled_sources[source].source is None: continue
            if self.parent.volume_categories[self.labeled_sources[source].cat][0] == 0.0: return
            if self.muted and self.labeled_sources[source].source.gain > 0.0 and not self.labeled_sources[source].dist or self.muted and self.labeled_sources[source].source.gain > 0.0 and self.labeled_sources[source].dist: 
                self.labeled_sources[source].source.gain=0.0
                self.labeled_sources[source].muted = True
            elif not self.muted and self.labeled_sources[source].source.gain == 0.0 and not self.labeled_sources[source].dist or self.muted and self.labeled_sources[source].source.gain == 0.0 and self.labeled_sources[source].dist: 
                self.labeled_sources[source].source.gain = (self.labeled_sources[source].volume / 100) * (self.parent.volume_categories[self.labeled_sources[source].cat][0] / 100)
                self.labeled_sources[source].muted = False

        for source in self.unlabeled_sources:
            if source.source is None: continue
            if self.parent.volume_categories[source.cat][0] == 0.0: continue
            if self.muted and source.source.gain > 0.0 and not source.dist or not self.muted and source.source.gain > 0.0 and source.dist: 
                source.source.gain = 0.0 
                source.muted = True
            elif not self.muted and source.source.gain == 0.0 and not source.dist or self.muted and source.source.gain == 0.0 and source.dist: 
                source.source.gain = (source.volume / 100) * (self.parent.volume_categories[source.cat][0] / 100)
                source.muted=False
        distance = get_3d_distance(*self.parent.position, *self.position)
        if distance > self.parent.max_distance: self.muted = True
        else: self.muted = False

    def aclude_check(self, map):
        if not self.muted:
            result = map.valid_straight_path(
                self.position,
                self.parent.position
            )
            if result is None: return
            if result == True:
                self.apply_filter(None, replace=True)
            else:
                filter = self.parent.gen_filter("LOWPASS")
                filter.set("GAINHF", 0.3)
                filter.set("GAIN", 0.4)
                self.apply_filter(filter, replace=True)