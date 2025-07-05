# todo: add a less ugly way of handeling account creation and logging in.
import threading
import os, signal
import shutil
import subprocess
import time
import queue
from string import whitespace
import contextlib
import weakref
import sys
from collections import namedtuple
import enet
import pygame
from getmac import get_mac_address
import cyal.util, cyal.exceptions
import requests

from .version import version

from . import clock, consts, event_handeler, menus
from . import (
    menu,
    networking,
    options,
    virtual_input,
    state,
    audio_manager,
    speech,
    updater,
    path_utils,
    automation,
)
from .speech import speak
from .os_tools import get_os
from .keyconfig import Keyconfig
import psutil
import webbrowser

Delayed_function = namedtuple("delayed_function", ["clock", "time", "function"])


class Game:
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.SysFont("calibri", 24)
        self.lock = threading.RLock()
        self.queue = queue.SimpleQueue()
        self.get = self.queue.get_nowait
        self.clocks = weakref.WeakSet()
        self.keyconfig = Keyconfig(
            f"{options.config_dirs.user_config_dir}/keyconfig.json"
        )
        options.load()
        self.framerate = 60
        self.delta = 1 / self.framerate * 1000
        self.clock = pygame.time.Clock()
        self.stack = []
        self.events = []
        self.input_history = [""]
        self.input = virtual_input.Virtual_input(self)
        options.set("discord_intergration", True)
        self.network = None
        self.last_fps = 60
        self.automations = []
        self.exclude_water = []
        self.ignore_others_water=False
        self.delayed_functions = {}
        self.ids = 0
        self.mouse_buttons = {
            "left": False,
            "middle": False,
            "right": False,
            "wheel_up": False,
            "wheel_down": False,
        }
        
        self.audio_mngr = audio_manager.AudioManager()
        self.device_clock = self.new_clock()
        self.direct_soundgroup = self.audio_mngr.create_soundgroup(True)

    def start(self):
        if len(sys.argv) > 3:
            self.parse_arguments()
        # self.globals=globals
        if not options.get("heard_intro", False) or options.get("play_intro_at_start", False):
            options.set("heard_intro", True)
            sound = self.audio_mngr.play_unbound("intro.ogg", 0, 0, 0, False, direct=True)
            self.suspend(14.5)
            speak("Final Hour!")
            self.suspend(4.5)
        if "__compiled__" in globals():
            self.append(updater.Updater(self))
        else:
            menus.main_menu(self)
            speak("Bypassing updater in uncompiled version...", False)

    def parse_arguments(self):
        action, param, pid = sys.argv[1], sys.argv[2], sys.argv[3]
        with contextlib.suppress(Exception):
            os.kill(int(pid), signal.SIGTERM)
        speak("Please wait...")
        while psutil.pid_exists(int(pid)):
            time.sleep(0.018)
        if action == "move_to":
            # a past version asked this version to move itself.
            speak("Copying files...")
            path_utils.copy_folder("./", param)
            last_cwd = os.getcwd()
            subprocess.Popen(
                [f"{param}/final_hour.exe", "rm_dir", last_cwd, str(os.getpid())],
                cwd=param,
            )
            return self.exit()
        elif action == "rm_dir":
            if os.path.exists(param):
                shutil.rmtree(param)

    def make_text(self):
        lines = [i[0] for i in speech.history[-3:]]
        return [self.font.render(line, True, "white") for line in lines]

    def put(self, value):
        """puts value into the event queue to be processed. value could be one of the following:
        None: breaks the event loop. you can put that before joining the thread.
        callable(). calls the given callable inside this thread with no arguments. you could pass a lambda function if you want to call a function with arguments.
        tuple(string, any): set's the value of the variable named as the string given in [0] as the value given in [1]
        """
        self.queue.put_nowait(value)

    def new_id(self):
        self.ids += 1
        return self.ids

    def call_after(self, time, function):  # sourcery skip: avoid-builtin-shadow
        """call{function} after {time}ms. returns an id that you could use to stop a function before its executed"""
        id = self.new_id()
        delayed_function = Delayed_function(self.new_clock(), time, function)
        self.delayed_functions[id] = delayed_function
        return id

    def cancel_before(self, id):
        """takes an id and prevents the delayed function of that id (if any) from running if they havent been ran yet."""
        if self.delayed_functions[id]:
            del self.delayed_functions[id]

    def toggle(self, key, on_text="on", off_text="off", default=False):
        """toggle options[key]. speaks the new state(whether on or off)"""
        if option := options.get(key, default):
            speak(off_text)
            options.set(key, False)
            return False
        else:
            speak(on_text)
            options.set(key, True)
            return True

    def toggle_state(self, text, key, default=False):
        """returns {text} and whether its on or off. for example: test. off"""
        st = "on" if options.get(key, default) else "off"
        return f"{text}. {st}"

    def toggle_item(self, text, key, default=False):
        """returns a tuple to toggle {key} with the title as {text}. the tuple is accepted by Menu as a menu item only."""
        return (lambda: self.toggle_state(text, key, default=default), lambda: self.toggle(key, default=default))

    def login(self):
        if "__compiled__" in globals():
            speak("Checking version...")
            request = requests.get(
                "https://final-hour.net/latest_version.txt"
            )
            request.raise_for_status()
            latest_version = request.text.strip()
            if version.compare(latest_version):
                menus.main_menu(self)
                speak(f"You are not on the latest version, you are on {version.major}.{version.minor}.{version.patch}, you need to update to {latest_version}")
                return

        username = options.get("username")
        password = options.get("password")
        if not username or not password:
            menus.no_account(self)
            return speak("No credentials menu", False)
        try:
            self.network = networking.Client(
                self,
                options.get("host", "127.0.0.1"),
                options.get("port", 13000),
                event_handeler.EventHandeler,
            )
        except OSError as e:
            self.pop()
            menus.main_menu(self)
            speak("Failed to connect. \r\n{error}".format(error=e))
            return
        speak("Connecting to the server. Please wait...")
        self.replace(self.login2)

    def login2(self):
        if self.network.timeout_clock.elapsed >= consts.TIMEOUT:
            return self.connection_error()
        e = self.network.net.service(0)
        if not self.network.connected and e.type == enet.EVENT_TYPE_CONNECT:
            speak("Logging in. Please wait...")
            self.network.send(
                consts.CHANNEL_MISC,
                "login",
                {
                    "username": options.get("username"),
                    "password": options.get("password"),
                },
            )
            self.network.send(
                consts.CHANNEL_MISC,
                "new_mac_address",
                {
                    "address": get_mac_address()
                }
            )
            self.replace(self.network.loop)

    def set_account(self):
        self.append(self.input.run("Enter your username.", handeler=self.set_account2))

    def set_account2(self, username):
        if username.strip()=="": 
            return self.cancel()
        # change any whitespaces with dashes.
        for i in whitespace:
            username = username.replace(i, "-", -1)
        options.set("username", username)
        self.replace(
            self.input.run("Enter your password.", handeler=self.set_account_done)
        )

    def set_account_done(self, password):
        if password.strip()=="":
            return self.cancel()
        options.set("password", password)
        self.pop()
        self.pop()
        self.login()
        speak("done.", False)

    def create_account(self):
        m = menu.Menu(self, "Do you agree with this game's agreement?")
        menus.set_default_sounds(m)
        webbrowser.open("https://final-hour.net/agreement")
        m.add_items(
            [
                (
                    "Yes, I have read, understood, and agreed to everything in the agreement.",
                    lambda: self.replace(
                        self.input.run(
                            "Enter your username.", handeler=self.create_account2
                        )
                    ),
                ),
                ("No, I disagree.", lambda: menus.main_menu(self)),
            ]
        )
        self.replace(m)

    def create_account2(self, username):
        # change any whitespaces with dashes.
        for i in whitespace:
            username = username.replace(i, "-", -1)
        if len(username) < 3 or len(username) > 25:
            return self.cancel(
                "Error. Make sure your username is in the range of 4-25 characters."
            )
        options.set("username", username)
        self.replace(
            self.input.run("Enter your password.", handeler=self.create_account3)
        )

    def create_account3(self, password):
        if password.strip()=="":
            return self.cancel()
        if len(password) > 70:
            return self.cancel("Your password must be less than 70 characters.")
        options.set("password", password)
        if self.network:
            self.network.put(None)
            self.network.join()
        try:
            self.network = networking.Client(
                self,
                options.get("host", "127.0.0.1"),
                options.get("port", 13000),
                event_handeler.EventHandeler,
            )
        except OSError as e:
            self.pop()
            menus.main_menu(self)
            speak("Failed to connect. \r\n{error}".format(error=e))
            self.pop()
            return
        self.replace(self.creating)

    def creating(self):
        e = self.network.net.service(0)
        if not self.network.connected and e.type == enet.EVENT_TYPE_CONNECT:
            speak("Please wait. Creating your account...")
            self.network.send(
                consts.CHANNEL_MISC,
                "create",
                {
                    "username": options.get("username", ""),
                    "password": options.get("password", ""),
                },
            )
            return self.replace(self.network.loop)
        if (
            not self.network.connected
            and self.network.timeout_clock.elapsed >= consts.TIMEOUT
        ):
            self.network.timeout_clock.restart()
            self.connection_error()

    def exit(self):
        self.stack = []

    def new_clock(self):
        cl = clock.Clock()
        self.clocks.add(cl)
        return cl

    def loop(self):
        while True:
            self.loop_function()

    def loop_function(self):
            if not self.queue.empty():
                value = self.get()
                if value is None:
                    # another thread asked this thread to terminate, so lets break.
                    return False
                elif callable(value):
                    value()
                elif isinstance(value, tuple):
                    # another thread asked to set a value on this class.
                    setattr(self, value[0], value[1])
            with self.lock:
                self.update(self.delta)
                self.events = pygame.event.get()
                for event in self.events:
                    if (
                        event.type == pygame.KEYDOWN
                        and event.mod & pygame.KMOD_CTRL
                        and get_os() == consts.OS_LINUX
                    ):
                        speak("", True)
                self.audio_mngr.loop()
                for automation_task in self.automations:
                    automation_task.loop()
                if self.device_clock.elapsed >= 10000:
                    device = options.get("audio_device", cyal.util.get_default_all_device_specifier())
                    if device == "system default": device = cyal.util.get_default_all_device_specifier()
                    try:
                        if not self.audio_mngr.context.is_connected: 
                            self.audio_mngr.context.device.reopen(name=device)
                    except cyal.exceptions.InvalidDeviceError:
                        self.audio_mngr.context.device.reopen(name=cyal.util.get_default_all_device_specifier())
                    if self.audio_mngr.context.device.output_name != device:
                        try: 
                            self.audio_mngr.context.device.reopen(name=device)
                        except cyal.exceptions.InvalidDeviceError:
                            pass
                    self.device_clock.restart()
                if options.get("mute_on_focus_loss", False):
                    if pygame.key.get_focused() and self.audio_mngr.context.device.paused: 
                        self.audio_mngr.context.device.resume()
                        self.audio_mngr.muted = False
                    elif not pygame.key.get_focused() and self.audio_mngr.context.device.playing: 
                        self.audio_mngr.context.device.pause()
                        self.audio_mngr.muted = True
                if len(self.stack) == 0:
                    options.save()
                    self.keyconfig.save()
                    pygame.quit()
                    sys.exit()
                st = self.stack[-1]
                if isinstance(st, state.State):
                    st.update(self.events)
                elif callable(st):
                    st()
                self.last_fps = round(self.clock.get_fps())
                ids_to_remove = []
                for i in self.delayed_functions.copy():
                    if (
                        self.delayed_functions[i].clock.elapsed
                        >= self.delayed_functions[i].time
                    ):
                        if callable(self.delayed_functions[i].function):
                            self.delayed_functions[i].function()
                        ids_to_remove.append(i)
                for i in ids_to_remove:
                    del self.delayed_functions[i]
            self.delta = self.clock.tick(self.framerate)

    def update(self, delta):
        self.screen.fill("black")
        texts = self.make_text()
        for i, text in enumerate(texts):
            self.screen.blit(
                text,
                text.get_rect(
                    center=(
                        self.screen.get_width() // 2,
                        self.screen.get_height() // 3 + (50 * i),
                    )
                ),
            )
        pygame.display.update()
        for i in self.clocks:
            i.update(delta)

    def pop(self):
        with contextlib.suppress(IndexError):
            prev = self.stack.pop()
            if isinstance(prev, state.State):
                prev.exit()
            return prev

    def append(self, st):
        self.stack.append(st)
        if isinstance(st, state.State):
            st.enter()
        return st

    def replace(self, st):
        self.pop()
        return self.append(st)

    def disconnected(self):
        if self.network:
            self.network.put(None)
            self.network.join()
        menus.main_menu(self)

    def connection_error(self):
        menus.main_menu(self)
        speak("Connection error [timeout]", False)

    def cancel(self, message="Canceled."):
        self.pop()
        speak(message)

    def automate(self, object, attribute, target_value, time, callback=None, time_step=20, step_callback=None, start_value=None, cancelable=True):
        self.automations.append(
            automation.Automation_Task(
                self, object, attribute, target_value, time, time_step=time_step, callback=callback, step_callback=step_callback, start_value=start_value, cancelable=cancelable
            )
        )
    
    #a function that suspends input and blocking network and game threads without causing the app to stop presponding, when suspension is over, all incoming packets and events are processed.
    def suspend(self, secs):
        self.append(state.State(self))
        for i in range(0, int(secs / 0.02)):
            time.sleep(0.02)
            self.loop_function()
        self.pop()