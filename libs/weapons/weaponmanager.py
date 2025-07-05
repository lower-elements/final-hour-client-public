import contextlib
from . import weapon
from ..speech import speak
from .. import consts


class weaponManager:
    def __init__(self, game, owner=None):
        self.game = game
        self.weapons = []
        self.owner = owner
        self.activeWeapon = None

    def modify(self, num, data):
        with contextlib.suppress(IndexError):
            weapon = self.weapons[num]
            for key, value in data.items():
                setattr(weapon, key, value)

    def add(self, w):
        self.weapons.append(w)

    def clear(self):
        self.weapons.clear()
        self.activeWeapon = None

    def replace(self, weapon, num):
        try:
            num = self.weapons.index(self.activeWeapon) if num == -1 else num
            self.weapons[num] = weapon
        except ValueError:
            self.add(weapon)

    def switchWeapon(self, num, send=True):
        if self.owner.locked:
            return
        with contextlib.suppress(IndexError):
            if self.activeWeapon and self.activeWeapon.locked:
                return
            self.activeWeapon = self.weapons[num]
            speak(self.activeWeapon.name)
            if send:
                self.game.network.send(
                    consts.CHANNEL_WEAPONS, "draw_weapon", {"num": num}
                )

    def fire(self, hangle=0, vangle=0):
        if self.owner.locked:
            return
        if self.activeWeapon is not None:
            self.activeWeapon.fire(hangle=hangle, vangle=vangle)

    def find_by_name(self, name):
        for i in self.weapons:
            if i.name == name:
                return i

    def reload(self):
        if self.owner.locked:
            return
        if self.activeWeapon is not None:
            self.activeWeapon.reload()

    def checkAmmo(self):
        if self.owner.locked:
            return
        if self.activeWeapon is not None:
            if not self.activeWeapon.melee:
                speak(f"{self.activeWeapon.ammo} ammo currently loaded. ")
            else:
                speak("No ammunition is needed for melee weapons!")

    def checkReserves(self):
        if self.owner.locked:
            return
        if self.activeWeapon is not None:
            if not self.activeWeapon.melee:
                speak(f"{self.activeWeapon.reserved_ammo} ammo currently in reserve. ")
            else:
                speak("No ammunition is needed for melee weapons!")
