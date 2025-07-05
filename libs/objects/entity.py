import os
from random import randint as random
from .. import options
from .. import voice_chat

import cyal.exceptions

from .. import movement, consts
from .object import Object

from ..audio import sound

class Entity(Object):
    def __init__(self, game, map, x, y, z, hp, name="None", player=False):
        super().__init__(game, map, x, y, z)
        self._player = player
        self.is_user = False
        self.on_move = None
        self.on_turn = None
        self.in_water = False
        self.depth= 1.0
        self.recorded_depth = self.depth
        self.limit_depth=1.0
        self.movement_clock = game.new_clock()
        self._hp = hp
        self.player_dead=False
        self.hfacing = 0
        self.vfacing = 0
        self.bfacing = 0
        self.fall_distance = 0
        self.beacon=None
        self.stun_time = 1000.0
        self.stunned = False
        self.stunned_clock = self.game.new_clock()
        self.name = name
        self.has_radio = False
    
    @property
    def player(self):
        return self._player

    @player.setter
    def player(self, value):
        self._player = value
        if value:
            try: self.vc_source, self.radio_source = self.game.audio_mngr.context.gen_sources(2)
            except cyal.exceptions.InvalidOperationError as e:
                print(e)
                self.vc_source, self.radio_source = self.game.audio_mngr.context.gen_sources(2) 
            self.vc_source.position = (self.x, self.y, self.z)
            self.radio_source.position = (0,0,0)
            self.radio_source.relative = True
            self.radio_source.gain=0.7
            eq_slot = self.soundgroup.parent.gen_effect(
                "EQUALIZER",
                ("low_gain", 0.126),
                ("low_cutoff", 800.0),
                ("high_gain", 0.126),
                ("high_cutoff", 4000.0)
            )
            self.distortion_slot = self.soundgroup.parent.gen_effect(
                "DISTORTION",
                ("edge", 0.5),
                ("gain", 0.2)
            )
            if self.distortion_slot is not None: self.distortion_slot.target = eq_slot
            self.soundgroup.parent.efx.send(self.radio_source, 1, self.distortion_slot)
            self.vc_compression = voice_chat.voice_chat_compression(self.game)




    def move(self, x, y, z, play_sound=True, mode="walk"):
        self.x = x
        self.y = y
        self.z = z
        if callable(self.on_move):
            self.on_move(x, y, z)
        reverb = self.map.get_reverb_at(self.x, self.y, self.z)
        if reverb is None: 
            self.soundgroup.apply_effect(None, 0)
            if self.player: self.game.audio_mngr.efx.send(self.vc_source, 0, None, filter=None)
        if reverb and reverb.reverb:
            try:
                self.soundgroup.apply_effect(reverb.reverb, 0) 
                if self.player: self.game.audio_mngr.efx.send(self.vc_source, 0, reverb.reverb, filter=self.soundgroup.filter[-1] if len(self.soundgroup.filter) > 0 else None)
            except cyal.exceptions.InvalidAlValueError as e:
                pass
            except cyal.exceptions.InvalidOperationError as e:
                pass
        if self.player:
            self.vc_source.position = (self.x, self.y, self.z)
            if movement.get_3d_distance(*self.vc_source.position, *self.game.audio_mngr.position) > self.game.audio_mngr.max_distance: self.vc_source.gain = 0.0
            else: self.vc_source.gain = 1.0
            if not self.soundgroup.muted:
                result = self.map.valid_straight_path(
                    self.vc_source.position,
                    self.game.audio_mngr.position
                )
                if result is None: pass
                elif result == True: 
                    del self.vc_source.direct_filter
                else: 
                    if len(self.soundgroup.filter) > 0: self.vc_source.direct_filter = self.soundgroup.filter[-1]
                    else: del self.vc_source.direct_filter
        self.soundgroup.position = (self.x, self.y, self.z)
        tile = self.map.get_tile_at(self.x, self.y, self.z)
        # start/stop falling if the current tile is air.
        if not self.falling and tile in ["air", ""]:
            self.fall_start()
        elif self.falling and tile not in ["air", "", "deep_water"]:
            self.fall_stop()
        if play_sound and not self.falling:
            if mode == "run" and not os.path.exists(
                f"{consts.SOUNDPREPEND}/steps/{tile}/run"
            ):
                mode = "walk"
            cat="zombies"
            if self == self.map.player: cat = "self"
            elif not self.name.startswith("zomby"): cat = "players"
            self.play_sound(
                f"steps/{tile}/{mode}",
                rel_z=-1,
                cat=cat
            )

    def face(self, hdeg, vdeg, bdeg=0, play_sound=False):
        if play_sound:
            self.play_sound("foley/turn/end.ogg", cat="players")
        self.hfacing = hdeg % 360
        self.vfacing = ((vdeg + 90) % 181) - 90
        self.bfacing = ((bdeg + 90) % 181) - 90
        if callable(self.on_turn):
            self.on_turn(self.hfacing, self.vfacing, self.bfacing)

    def walk(
        self, back=False, left=False, right=False, down=False, up=False, mode="walk"
    ):
        if self.map.get_tile_at(self.x, self.y, self.z) in ["deep_water", "underwater"] or not self.falling: self.fall_clock.restart()
        if self.stunned and self.stunned_clock.elapsed >= self.stun_time:
            self.stunned = False
            self.stunned_clock.restart()
        if not self.stunned:
            dist = movement.move((self.x, self.y, self.z), self.hfacing).get_tuple
            self.face(self.hfacing, 0)
            if back:
                dist = movement.move(
                    (self.x, self.y, self.z), self.hfacing + 180 % 360
                ).get_tuple
            if left:
                dist = movement.move(
                    (self.x, self.y, self.z), self.hfacing - 90 % 360
                ).get_tuple
            if right:
                dist = movement.move(
                    (self.x, self.y, self.z), self.hfacing + 90 % 360
                ).get_tuple
            if down:
                dist = (self.x, self.y, self.z - 1)
                if self.in_water:
                    if self.depth > 0.0:
                        if self.limit_depth >= 0.0: self.depth = round(self.depth - 0.1, 3) 
                        self.limit_depth -= 0.1
                    else:
                        self.depth = 0.0
                        self.limit_depth-=0.1
            if up:
                dist = (self.x, self.y, self.z + 1)
                if self.in_water:
                    if self.depth < 1.0:
                        if self.limit_depth >= 0.0: self.depth = round(self.depth + 0.1, 3)
                        self.limit_depth+=0.1
                    else: 
                        self.depth = 1.0
                        self.limit_depth = 1.0
            if self.map.in_bound(*dist):
                disttile = self.map.get_tile_at(*dist)
                if "wall" not in disttile:
                    if (up or down) and disttile in ["air", ""]:
                        return False
                    self.move(*dist, mode=mode)
                    return True
                self.play_sound(
                    f"walls/{disttile}.ogg",
                    rel_x=dist[0] - self.x,
                    rel_y=dist[1] - self.y,
                    rel_z=1,
                )
            return False

    def fall_start(self):
        self.fall_clock.restart()
        self.play_sound("foley/fall/start.ogg")
        self.falling = True

    def fall_stop(self):
        self.falling = False
        self.play_sound("foley/fall/end.ogg")
        # sound-simulate landing hard on a platform.
        for _ in range(random(3, 7)):
            self.game.call_after(
                random(10, 100), lambda: self.move(self.x, self.y, self.z, mode="run")
            )

    def loop(self):
        if self.player:
            with self.soundgroup.parent.context.batch():
                if self.vc_source.buffers_queued == 0 and not self.is_user: 
                    buffer = self.game.audio_mngr.context.gen_buffer()
                    buffer.set_data(
                        self.game.audio_mngr.silent_buf,
                        sample_rate=48000,
                        format=cyal.BufferFormat.MONO16
                    )
                    self.vc_source.queue_buffers(buffer)
                if self.radio_source.buffers_queued == 0: 
                    buffer = self.game.audio_mngr.context.gen_buffer()
                    buffer.set_data(
                        self.game.audio_mngr.silent_buf,
                        sample_rate=48000,
                        format=cyal.BufferFormat.MONO16
                    )
                    self.radio_source.queue_buffers(buffer)
        if (
            self.falling
            and self.fall_clock.elapsed >= self.fall_time
            and self.map.in_bound(self.x, self.y, self.z)
            or self.map.get_tile_at(self.x, self.y, self.z) in ["deep_water", "underwater"]
            and self.fall_clock.elapsed >= self.fall_time * 25
            and self.map.in_bound(self.x, self.y, self.z-1)
            and not self.map.get_tile_at(self.x, self.y, self.z-1).startswith("wall")
            and self.map.get_tile_at(self.x, self.y, self.z-1) not in ["air", ""]
        ):
            self.fall_clock.restart()
            self.move(self.x, self.y, self.z - 1, False)
            if self.is_user and self.game and self.game.network: 
                self.game.network.send(
                    consts.CHANNEL_MAP,
                    "move",
                    {
                        "x": self.x,
                        "y": self.y,    
                        "z": self.z,
                        "play_sound": False,
                        "mode": "walk",
                    },
                )

            if self.in_water:
                if self.depth > 0.0:
                    if self.limit_depth >= 0.0: self.depth = round(self.depth - 0.1, 3) 
                    self.limit_depth -= 0.1
                else:
                    self.depth = 0.0
                    self.limit_depth-=0.1
            if not self.in_water: self.face(random(-45, 45), random(-45, 45), random(-45, 45))
            self.fall_distance += 1
            if not self.map.in_bound(self.x, self.y, self.z):
                self.fall_stop()

    def on_hit(self):
        self.play_sound(f"entities/{self.name}/pain{random(1, 3)}.ogg)")

    def death(self):
        raise NotImplementedError

    def water_check(self):
        filter = self.game.audio_mngr.gen_filter(
            type="LOWPASS"
        )
        
        def automation_water(value):
            filter.set("GAINHF", value)
            self.soundgroup.apply_filter(filter, replace=True)
            if self.player:
                if filter is not None: self.vc_source.direct_filter = filter
                else: del self.vc_source.direct_filter
        
        if not self.in_water and self.map.get_tile_at(self.x, self.y, self.z) == "underwater":
            self.game.audio_mngr.play_unbound("foley/swim/start/", self.x, self.y, self.z)
            self.in_water = True
            self.game.exclude_water.append(self.soundgroup)
            muffling = 0.05 * self.depth
            if not self.game.ignore_others_water: self.game.automate(
                None, None,
                muffling, 500,
                step_callback = automation_water, start_value=1.0
            )
        if self.in_water and self.map.get_tile_at(self.x, self.y, self.z) != "underwater":
            self.game.audio_mngr.play_unbound("foley/swim/end/", self.x, self.y, self.z)
            muffling = 0.05 * self.depth
            if not self.game.ignore_others_water: self.game.automate(
                None, None,
                1.0, 500,
                step_callback = automation_water, start_value=muffling
            )
            self.in_water=False
            self.game.exclude_water.pop(self.game.exclude_water.index(self.soundgroup))
        if round(self.depth, 3) != round(self.recorded_depth,3) and self.in_water:
            muffling = 0.05 * round(self.depth,3)
            self.game.automate(
                None, None,
                muffling, 50,
                step_callback = automation_water, start_value=0.05*round(self.recorded_depth,3)
            )
            self.recorded_depth = round(self.depth,3)

    @property 
    def hp(self):
        return self._hp
    
    @hp.setter
    def hp(self, value):
        self._hp = value if 0 <= value <= 100 else self._hp
    
    def destroy(self):
        if self.player: self.vc_compression.put(None)
        if self.beacon is not None:
            self.beacon.destroy(force=True)
        super().destroy()
    

