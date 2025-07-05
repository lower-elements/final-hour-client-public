from random import randint
from math import sin,cos,radians

import contextlib
from .. import audio_manager, consts, path_utils


class weapon:
    def __init__(
        self,
        game,
        gameplay,
        name,
        melee=False,
        sounds_path="",
        fire_time=1000,
        reload_time=1000,
        automatic=False,
        shot_cost=1,
        max_ammo=10,
        max_reserved_ammo=10,
        ammo=10,
        reserved_ammo=10,
        recoil_chance=0,
    ):
        self.game = game
        self.gameplay = gameplay
        self.owner = self.gameplay.player
        self.melee = melee
        self.name = name
        self.fire_path = f"{sounds_path}/fire"
        self.dry_fire_path = f"{sounds_path}/dry"
        self.reload_path = f"{sounds_path}/reload"
        self.speed_reload_path = f"{sounds_path}/speed_reload"
        self.fire_time = fire_time
        self.reload_time = reload_time
        if reload_time == -1:
            with contextlib.suppress(Exception):
                self.reload_time = (
                    self.game.audio_mngr.load_buffer(
                        path_utils.random_item(consts.SOUNDPREPEND + self.reload_path)
                    ).sec_length
                    * 1000
                )
                self.speed_reload_time = (
                    self.game.audio_mngr.load_buffer(
                        path_utils.random_item(consts.SOUNDPREPEND + self.speed_reload_path)
                    ).sec_length
                    * 1000
                )
        self.automatic = automatic
        self.fire_clock = game.new_clock()
        self.reload_clock = game.new_clock()
        self.shot_cost = shot_cost
        self.max_ammo = max_ammo
        self.max_reserved_ammo = max_reserved_ammo
        self.ammo = ammo
        self.reserved_ammo = reserved_ammo
        self.locked = False
        self.recoil_chance = recoil_chance

    def recoil(self):
        if randint(0, 100) < self.recoil_chance:
            self.owner.play_sound("foley/recoil", cat="self")
            self.owner.face(
                self.owner.hfacing + randint(-13, 13),
                self.owner.vfacing + randint(-13, 13),
                randint(-13, 13),
            )

    def lock(self, ms):
        self.locked = True
        self.game.call_after(ms, lambda: setattr(self, "locked", False))

    def fire(self, hangle=0, vangle=0):
        fire_time = self.fire_time if not self.owner.double_tap_root_beer else self.fire_time / 2
        if not self.locked and self.fire_clock.elapsed >= fire_time:
            self.fire_clock.restart()
            if self.melee or self.ammo >= self.shot_cost:
                self.game.network.send(
                    consts.CHANNEL_WEAPONS,
                    "weapon_fire",
                    {"name": self.name, "angle": hangle, "pitch": vangle},
                )
                self.owner.play_sound(f"{self.fire_path}/", cat="self")
                x_adjust=1
                y_adjust=0
                if 225<hangle<=315:
                    x_adjust=0
                    y_adjust=1
                elif 45<hangle<=135:
                    x_adjust=0
                    y_adjust=-1
                elif 135<hangle<=225:
                    x_adjust=-1
                    y_adjust=0
                if not self.melee: self.game.audio_mngr.play_unbound(f"weapons/shell/{self.owner.map.get_tile_at(self.owner.x, self.owner.y, self.owner.z)}",self.owner.x+x_adjust, self.owner.y+y_adjust, self.owner.z, False, volume=30)
                self.ammo -= self.shot_cost
                self.recoil()
            else:
                self.owner.play_sound(f"{self.dry_fire_path}/", cat="self")

    def reload(self):  # sourcery skip: last-if-guard
        reload_time = self.reload_time if not self.owner.speed_cola else self.speed_reload_time
        if (
            not self.melee
            and self.ammo <= 0
            and not self.locked
            and self.reload_clock.elapsed >= reload_time
            and self.reserved_ammo
        ):
            self.reload_clock.restart()
            self.lock(self.reload_time if not self.owner.speed_cola else self.speed_reload_time)
            self.owner.play_sound(f"{self.reload_path if not self.owner.speed_cola else self.speed_reload_path}/", cat="self")
            self.game.network.send(
                consts.CHANNEL_WEAPONS, "weapon_reload", {"name": self.name}
            )
            if self.reserved_ammo >= self.max_ammo:
                self.ammo = self.max_ammo
                self.reserved_ammo -= self.max_ammo
            else:
                self.ammo += self.reserved_ammo
                self.reserved_ammo = 0
