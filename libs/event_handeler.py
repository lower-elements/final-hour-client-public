import time
import random
import os
import base64
import cyal.exceptions
import pyperclip
import functools
import contextlib
import webbrowser
import cyal
from . import audio_manager, buffer, gameplay, menu, menus, options, consts
from .speech import speak
from .weapons import weapon
from . import tickets
from pyogg import OpusDecoder

class EventHandeler:
    def __init__(self, client, game):
        self.client = client
        self.game = game
        self.gameplay = gameplay.Gameplay(self.game)
        self.tickets = tickets.Tickets(self.game)

    def create_fail(self, data):
        menus.main_menu(self.game)
        speak("Account creation failed.", False)

    def create_done(self, data):
        menus.main_menu(self.game)
        speak(
            "Account creation finished. You can now login using the given information",
            False,
        )

    def connected(self, data):
        self.client.put(("connected", True))
        self.game.replace(self.gameplay)
        self.gameplay.player.name = data["username"]
        speak("Welcome. You are now online")

    def speak(self, data):
        if data["buffer"]:
            buffer.add_item(
                self.game,
                data["buffer"],
                data["text"],
                True,
                sound=data.get("sound", ""),
            )
            speak(data["text"], silent=True, id=f'buffer_{data["buffer"]}')
        else:
            speak(data["text"], data["interupt"], not data["buffer"])
            if data["sound"]:
                self.game.direct_soundgroup.play(data["sounds"])

    def online(self, data):
        buffer.add_item(
            self.game,
            "players",
            f'{data["username"]} came online.',
            sound="ui/online.ogg",
        )

    def offline(self, data):
        buffer.add_item(
            self.game,
            "players",
            f'{data["username"]} went offline.',
            sound="ui/offline.ogg",
        )

    def kick(self, data):
        buffer.add_item(
            self.game, "players", f'{data["username"]} was kicked by a moderator. '
        )

    def ping(self, data):
        if self.gameplay:
            speak(
                f"The ping took {int((time.time() - self.gameplay.last_ping_time)*1000)}ms"
            )
            self.gameplay.pingging = False

    def parse_map(self, data):
        self.game.automations.clear()
        self.game.audio_mngr.apply_filter(
            None, exclude=self.game.exclude_water, clear=True
        )
        self.gameplay.parser.load(data["data"])
        self.gameplay.player.move(data["x"], data["y"], data["z"], play_sound=False)

    def update_map(self, data):
        for a in self.game.automations.copy():
            if a.cancelable:
                self.game.automations.pop(self.game.automations.index(a))
        self.game.audio_mngr.apply_filter(
            None, exclude=self.game.exclude_water, clear=True
        )
        self.gameplay.player.in_water = False
        self.game.ignore_others_water = False
        self.game.exclude_water.clear()
        for i in self.gameplay.map.entities.values():
            i.in_water = False
            i.water_check()

        self.gameplay.parser.load(data["data"], False)
        self.gameplay.player.move(
            self.gameplay.player.x, self.gameplay.player.y, self.gameplay.player.z
        )

    def rebuild_elements(self, data):
        elements = data["elements"]
        map = self.gameplay.map
        for element in elements:
            type = element["type"]
            id = element["data"]["id"]
            if hasattr(map, f"spawn_{type}"):
                getattr(map, f"spawn_{type}")(**element["data"])

    def spawn_entity(self, data):
        entity = self.gameplay.map.spawn_entity(
            data["name"], data["x"], data["y"], data["z"]
        )
        if data.get("voice_channel", None) != None:
            self.gameplay.voice_channels[data["voice_channel"]] = entity
        if data.get("player", False):
            entity.player = True
            
        if data.get("beacon", False) and options.get("beacons"):
            try: 
                entity.beacon = entity.play_sound(
                "ui/beacon.ogg", looping=True, cat="players"
            )
                entity.beacon.force_to_destroy = True
                try:
                    entity.beacon.source.pitch = random.randint(98, 102) / 100
                except AttributeError as e:
                    print(e)
            except:
                pass

    def remove_entity(self, data):
        self.gameplay.voice_channels = { k: v for k, v in self.gameplay.voice_channels.items() if v.name != data["name"] }
        self.gameplay.map.remove_entity(data["name"])

    def play_sound(self, data):
        if entity := (
            self.gameplay.player
            if data["name"] == self.gameplay.player.name
            else self.gameplay.map.entities.get(data["name"])
        ):
            entity.play_sound(
                data["sound"],
                data["looping"],
                id=data.get("id", ""),
                cat=data.get("cat", "miscelaneous"),
                volume=data.get("volume", 100),
            )
            if data["dist_path"]:
                entity.play_sound_dist(
                    data["dist_path"],
                    data["looping"],
                    data["volume"],
                    data.get("id", ""),
                    cat=data.get("cat", "miscelaneous")
                )

    def play_direct(self, data):
        self.game.direct_soundgroup.play(
            data["sound"], data["looping"], data["id"], volume=data["volume"], cat=data.get("cat", "miscelaneous")
        )

    def play_unbound(self, data):
        self.game.audio_mngr.play_unbound(
            data["sound"], data["x"], data["y"], data["z"], False, volume=data["volume"], cat=data.get("cat", "miscelaneous")
        )

    def move(self, data):
        entity = self.gameplay.map.entities.get(data["name"])
        if not entity and data["name"] == self.gameplay.player.name:
            entity = self.gameplay.player
        if entity:
            if "angle" not in data:
                data["angle"] = 0
            if "mode" not in data:
                data["mode"] = "walk"
            entity.move(
                data["x"], data["y"], data["z"], data["play_sound"], data["mode"]
            )
            entity.face(data["angle"], entity.vfacing, entity.bfacing)

    def quit(self, data):
        self.game.put(lambda: self.gameplay.quit("quit"))
        speak(data.get("message", "your connection was closed."), True)

    def typing(self, data):
        if options.get("typing") == True:
            speak(data["message"], False)

    def copy(self, data):
        pyperclip.copy(data["data"])
        speak(data.get("message", "Coppied"))

    def make_menu(self, data):
        def on_select(value, close):
            if close:
                self.gameplay.pop_last_substate()
            self.client.send(consts.CHANNEL_MENUS, data["event"], {"value": value})

        m = menu.Menu(self.game, data["title"])
        options = []
        for i in data["options"]:
            options.append(
                (i["title"], functools.partial(on_select, i["value"], i["close"]))
            )
        options.append(("Close", self.gameplay.pop_last_substate))
        m.add_items(options)
        menus.set_default_sounds(m)
        self.gameplay.add_substate(m)

    def add_weapon(self, data):
        self.gameplay.wmanager.add(weapon.weapon(self.game, self.gameplay, **data))

    def modify_weapon(self, data):
        self.gameplay.wmanager.modify(data["num"], data["data"])

    def clear_weapons(self, data):
        self.gameplay.wmanager.clear()

    def replace_weapon(self, data):
        self.gameplay.wmanager.replace(
            weapon.weapon(self.game, self.gameplay, **data["weapon_data"]), data["num"]
        )

    def open_rules(self, data):
        webbrowser.open("https://final-hour.net/agreement")

    def death(self, data):  # sourcery skip: avoid-builtin-shadow
        if data["dead"] == True:
            fall_direction = random.randint(1, 2)
            player = self.gameplay.player
            if fall_direction == 1:
                player.face(player.hfacing, -90, random.randint(-45, 45))
                speak("you fall on to your front")
            elif fall_direction == 2:
                player.face(player.hfacing, 90, random.randint(-45, 45))
                speak("you fall on to your back")

            if self.gameplay.wmanager.activeWeapon != None:
                self.gameplay.wmanager.activeWeapon.locked = True
            self.game.direct_soundgroup.play("death/start.ogg", False)
            self.gameplay.player.dead = True
            self.gameplay.camera.move(
                self.gameplay.player.x, self.gameplay.player.y, self.gameplay.player.z
            )
            filter = self.game.audio_mngr.gen_filter("lowpass", ("GAINHF", 1.0))
            self.gameplay.player.death_filter = filter
            for i in self.gameplay.map.get_ambiences_at(
                self.gameplay.player.x, self.gameplay.player.y, self.gameplay.player.z
            ):
                i.leave()

            def automation_death(value):
                filter.set("GAINHF", value)
                self.game.audio_mngr.apply_filter(filter, replace=True)

            self.game.automate(
                None, None, 0.05, 1000, step_callback=automation_death, start_value=1.0
            )
            self.game.direct_soundgroup.play("death/loop.ogg", True, "death", volume=20)
            self.gameplay.player.locked = True
        elif data["dead"] == False:
            self.gameplay.player.face(0, 0, 0)
            if self.gameplay.wmanager.activeWeapon != None:
                self.gameplay.wmanager.activeWeapon.locked = False
            self.gameplay.player.death_filter = None
            for i in self.gameplay.map.get_ambiences_at(
                self.gameplay.player.x, self.gameplay.player.y, self.gameplay.player.z
            ):
                i.enter()
            self.game.audio_mngr.apply_filter(None)
            self.gameplay.player.drown_clock.restart()
            self.gameplay.player.drownable = False

            self.gameplay.player.dead = False
            self.gameplay.camera.move(
                self.gameplay.player.x, self.gameplay.player.y, self.gameplay.player.z
            )
            self.game.direct_soundgroup.play("death/end.ogg", False, "death")
            self.gameplay.player.locked = False

    def set_hp(self, data):
        if self.gameplay.player.lock_weapon:
            return
        self.gameplay.player.hp = data["amount"]

    def open_door(self, data):
        if door := self.gameplay.map.get_door_at(data["x"], data["y"], data["z"]):
            door.switch_state(data["locked"], to_open=True, silent=data["silent"])
        else:
            speak("error opening door")

    def close_door(self, data):
        if door := self.gameplay.map.get_door_at(data["x"], data["y"], data["z"]):
            door.switch_state(data["locked"], to_open=False)
        else:
            speak("error closing door")

    def switch_weapon(self, data):
        self.gameplay.wmanager.switchWeapon(data["slot"])

    def make_input(self, data):
        def online_submit(value):
            self.gameplay.pop_last_substate()
            self.client.send(consts.CHANNEL_MENUS, data["event"], {"value": value, "data": data["data"]})

        self.gameplay.add_substate(self.game.input.run(data["prompt"], handeler=online_submit, default=data.get("default", "")))

    def tickets_menu(self, data):
        if not data:
            return
        self.tickets.view_tickets(data["tickets"])

    def view_closed_tickets(self, data):
        if not data:
            return
        self.tickets.view_tickets(data["tickets"])

    def enter_match(self, data):
        self.gameplay.player.lock_weapon = False

    def exit_match(self, data):
        self.gameplay.player.lock_weapon = True

    def login_failed(self, data):
        if not data:
            return
        self.game.pop()
        menus.main_menu(self.game)
        speak(data["message"])


    def double_tap_root_beer(self, data):
        if not data:
            return
        if "value" not in data:
            data["value"] = False
        self.gameplay.player.double_tap_root_beer = data["value"]

    def speed_cola(self, data):
        print("hi")
        if not data:
            return
        if "value" not in data:
            data["value"] = False
        self.gameplay.player.speed_cola = data["value"]



    def process_voice_data(self, data, channelID):
        if not options.get("voice_chat", True): return
        if channelID in self.gameplay.voice_channels.keys():
            vc_source = self.gameplay.voice_channels[channelID].vc_source
            radio_source = self.gameplay.voice_channels[channelID].radio_source
            self.gameplay.voice_channels[channelID].vc_compression.recieve(data, vc_source, radio_source, channelID, self.gameplay)

    def has_radio(self, data):
        if data["channel"] not in self.gameplay.voice_channels.keys(): return
        self.gameplay.voice_channels[data["channel"]].has_radio = data["enable"]
    
    def has_radio_self(self, data):
        self.gameplay.player.has_radio = data["enable"]

    def ban(self, data):
        if data["message"]:
            self.game.put(lambda: self.gameplay.quit("quit"))
            speak(data["message"])
