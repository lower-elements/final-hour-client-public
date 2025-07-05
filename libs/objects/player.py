from .. import consts 
from ..speech import speak
from .entity import Entity
from random import randint as random


class Player(Entity):
    def __init__(self, game, map, x, y, z, hp=100, player=False):
        super().__init__(game, map, x, y, z, hp, "player", player=player)
        self.locked = False
        self.dead=False
        self.death_filter=None
        self.lock_weapon=True
        self.double_tap_root_beer = False
        self.speed_cola = False
        self.walktime = 270
        self.runtime = 184
        self.drown_clock = self.game.new_clock()
        self.drownable = False
        self.movetime = self.walktime
        self.turntime = 5
        self.turning_clock = game.new_clock()
        self.player = True
        self.is_user = True
        self.vc_source.gain = 0.1
        

    def move(self, x, y, z, play_sound=True, mode="walk", send=False):
        super().move(x, y, z, play_sound, mode)
        if send and self.game.network:
            self.send_movement(mode)

    def send_movement(self, mode):
        self.game.network.send(
            consts.CHANNEL_MAP,
            "move",
            {
                "x": self.x,
                "y": self.y,
                "z": self.z,
                "play_sound": True,
                "mode": mode,
            },
        )

    def walk(
        self,
        back=False,
        left=False,
        right=False,
        down=False,
        up=False,
        mode="walk",
        send=False,
        swim=False
    ):
        if self.bfacing < 30 and self.bfacing > -30 and self.locked == False or self.map.get_tile_at(self.x, self.y, self.z) in ["deep_water", "underwater"] and self.locked == False:
            value = super().walk(back, left, right, down, up, mode)
            if send and value:
                self.send_movement(mode)
            return value
        elif self.bfacing < -30 and self.map.get_tile_at(self.x, self.y, self.z) not in ["deep_water", "underwater"] or self.bfacing > 30 and self.map.get_tile_at(self.x, self.y, self.z) not in ["deep_water", "underwater"]:
            speak("you are unbalanced, perhaps streighten up first? ")

    def face(self, *args, **kwargs):
        super().face(*args, **kwargs)

    def death(self):
        pass

    def fall_stop(self):
        super().fall_stop()
        self.hp = self.hp - (self.fall_distance / 2 + random(-3, 3))
        self.game.network.send(consts.CHANNEL_MISC, "set_hp", {"amount": self.hp})
        self.fall_distance = 0
        self.stunned = True
        self.stunned_clock.restart()
        self.play_sound("death/start.ogg", cat="self")
        if self.hp <= 0 or self.hp > 100:
            self.hp = 100

    @property
    def hp(self):
        return self._hp
    
    @hp.setter
    def hp(self, value):
        if self.lock_weapon: return
        self._hp = value if 0 <= value <= 100 else self._hp