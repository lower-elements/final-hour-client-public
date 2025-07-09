import functools
from operator import mod
from string import Template
from . import menu, options, updater, keyconfig, consts, speech, audio_manager
from .key_config_screen import Key_config_screen
from .os_tools import get_os
import pygame
import cyal.util

def linux_change_speech_module(game, func_call, replace_call = None, parent=None):
    def set_module(module):
        speech.linux_speaker.set_output_module(module)
        options.set("linux_speech_module", module) 

    modules_menu = menu.Menu(game, "Select your speech module", parrent=parent)
    set_default_sounds(modules_menu)
    items = []
    for i in speech.linux_speaker.list_output_modules():
        items.append((i, functools.partial(set_module, i)))
    items.append(("back", func_call))
    modules_menu.add_items(items)
    if replace_call is None: (modules_menu)
    else: replace_call(modules_menu)


def linux_change_rate(game, func_call, replace_call=None):
    def set_rate(rate):
        try:
            speech.linux_speaker.set_rate(int(rate))
            options.set("linux_speech_rate", int(rate)) 
            speech.speak("Done!")
        except ValueError:
            speech.speak("Input a valid number please?")
        func_call()

    if replace_call is None: replace_call = game.replace
    replace_call(game.input.run("Input the rate you want to set", handeler=set_rate))


def linux_change_pitch(game, func_call, replace_call=None):
    def set_pitch(pitch):
        try:
            speech.linux_speaker.set_pitch(int(pitch))
            options.set("linux_speech_pitch", int(pitch))
        except ValueError:
            speech.speak("Input a valid number please?")
        func_call()

    if replace_call is None: replace_call = game.replace
    replace_call(game.input.run("Input the pitch you want to set", handeler=set_pitch))


def linux_change_volume(game, func_call, replace_call=None):
    def set_volume(volume):
        try:
            speech.linux_speaker.set_volume(int(volume))
            options.set("linux_speech_volume", int(volume))
        except ValueError:
            speech.speak("Input a valid number please?")
        func_call()

    if replace_call is None: replace_call = game.replace
    replace_call(game.input.run("Input the volume you want to set", handeler=set_volume))


def main_menu(game):
    """replace the current game state with the main menu."""
    m = menu.Menu(
        game,
        "Main menu.",
    )
    set_default_sounds(m)
    m.add_items(
        (
            ("Login", game.login),
            ("Set account", game.set_account),
            ("Create account", game.create_account),
            ("options", lambda: options_menu(game, lambda: main_menu(game))),
            ("Exit", game.exit),
        )
    )
    m.set_music("music/10.ogg")
    game.replace(m)


def no_account(game):
    """append the no account menu to the games stack."""
    m = menu.Menu(
        game,
        "you have no account set, would you like to set an account or create a new one? ",
    )
    m.add_items([
        ("Set an account with existing credentials", game.set_account),
        ("Create a new account from scratch", game.create_account),
        ("go back", lambda: main_menu(game))
    ])
    set_default_sounds(m)
    game.replace(m)

def options_menu(game, func_call, replace_call=None, parent=None, in_game=False):
    """append the options menu to the games stack."""
    m = menu.Menu(game, "Options menu", parrent=parent, )
    set_default_sounds(m)
    items=[
        (f"Server hostname: {options.get('host', consts.DEFAULT_HOST)}", lambda: configure_host(game, func_call, replace_call)),
        (f"Server port: {options.get('port', consts.DEFAULT_PORT)}", lambda: configure_port(game, func_call, replace_call)),
        (f"Select output device - currently set to {options.get('audio_device', '==============system default')[14:]}", lambda: output_menu(game, func_call=func_call if in_game else lambda: options_menu(game, func_call, replace_call=replace_call, parent=parent, in_game=in_game), replace_call=replace_call, parent=parent)),
        (f"Select input device - currently set to {options.get('audio_input_device', '==============system default')[14:]}", lambda: input_menu(game, func_call=func_call if in_game else lambda: options_menu(game, func_call, replace_call=replace_call, parent=parent, in_game=in_game), replace_call=replace_call, parent=parent, in_game=in_game)),
        (f"Voice Chat Jitter Buffer: {options.get('jitter_buffer', 60)}", lambda: configure_jitter_buffer(game, func_call, replace_call)),
        (game.toggle_item("Voice Chat", "voice_chat", True)),
        (game.toggle_item("microphone", "microphone", True)),
        (game.toggle_item("Player beacons", "beacons")),
        (game.toggle_item("play intro at start up", "play_intro_at_start")),
        (
            game.toggle_item(
                "Stream ambience: turning this off might introduce more memory usage and map loading time, but better performance and less CPU usage",
                "stream_ambience",
            )
        ),
        (game.toggle_item("Mute audio when the game window does not have focus", "mute_on_focus_loss")),
        (game.toggle_item("Mute speech when out of the game window", "mute_speech_on_focus_loss")),
        (game.toggle_item(
            "speak your direction when finished turning", 
            "speak_on_turn"
        )),
        (game.toggle_item("receive typing indicators", "typing")),
        (
            "Set how you would like timestamps in the end of buffer items to be displayed",
            lambda: buffer_timing_menu(game, func_call=func_call if in_game else lambda: options_menu(game, func_call, in_game=in_game), replace_call=replace_call, parent=parent),
        ),
        (
            "Set which HRTF Model you would like to use. Currently set to "+str(options.get("hrtf_model", game.audio_mngr.hrtf.current_model)),
            lambda: hrtf_model_menu(game, func_call=func_call if in_game else lambda: options_menu(game, func_call, in_game=in_game), replace_call=replace_call, parent=parent)
        ),
        ("edit location template. Currently set to: "+options.get("location_template", "{x}, \r\n{y}, \r\n{z}, \r\nOn {tile} \r\nFacing {direction} at {angle} degrees with a pitch of {pitch} degrees. \r\nYou are leaning by {lean} degrees and you are {balanced}. "), lambda: configure_location_template(game, func_call=func_call if in_game else lambda: options_menu(game, func_call, in_game=in_game), replace_call=replace_call)),
        ("reset your location template to default", lambda: options.set("location_template",             "{x}, \r\n{y}, \r\n{z}, \r\nOn {tile} \r\nFacing {direction} at {angle} degrees with a pitch of {pitch} degrees. \r\nYou are leaning by {lean} degrees and you are {balanced}. ")),
        ("Configure key bindings.", lambda: keyconfig_menu(game, func_call=func_call if in_game else lambda: options_menu(game, func_call, in_game=in_game), replace_call=replace_call, parent=parent, in_game=in_game)),
    ]
    items.append(("Back", lambda: func_call()))
    m.add_items(items)
    if replace_call is None: game.replace(m)
    else: replace_call(m)


def buffer_timing_menu(game, func_call, replace_call=None, parent=None):
    """append the buffer time display menu to the games stack."""
    m = menu.Menu(
        game,
        "How would you like timestamps to be displayed in buffer items?",
        parrent=parent
    )
    set_default_sounds(m)
    m.add_items(
        (
            ("Absolute time", lambda: set_buffer_timing(game, 1, func_call)),
            ("Relative time", lambda: set_buffer_timing(game, 2, func_call)),
            ("Don't display timestamps", lambda: set_buffer_timing(game, 3, func_call)),
            ("Back", func_call),
        )
    )
    if replace_call is None: game.replace(m)
    else: replace_call(m)

def hrtf_model_menu(game, func_call, replace_call=None, parent=None):
    m = menu.Menu(
        game, 
        "Select your HRTF model",
        parrent=parent
    )
    set_default_sounds(m)
    for model in game.audio_mngr.hrtf.models():
        m.add_items([
            (model, functools.partial(set_hrtf_model, model, game, func_call))
        ])
    m.add_items([
        ("Disable HRTF", lambda: set_hrtf_model(None, game, func_call)),
        ("go back", func_call)
    ])
    if replace_call is None: game.replace(m)
    else: replace_call(m)

def set_hrtf_model(model, game, func_call):
    game.audio_mngr.hrtf.use(model)
    options.set("hrtf_model", model)
    func_call()
    speech.speak(f"using HRTF model {model}")


def keyconfig_menu(game, func_call, replace_call=None, parent=None, in_game=False):
    """append a menu for binding keyboard keys to functions."""
    default_keys = keyconfig.Keyconfig("default_keyconfig.json")
    m = menu.Menu(
        game,
        "Please select a function to bind a key to.",
        parrent=parent
    )
    set_default_sounds(m)
    if replace_call is None: replace_call=game.replace
    items = []
    for i in default_keys.keys.keys():
        func = functools.partial(replace_call, Key_config_screen(game, i, options_menu=func_call if in_game else lambda: keyconfig_menu(game, func_call, in_game=in_game)))
        # we use functools.partial because lambdas dont work as they should with loops like that.
        items.append(
            (
                f"{i}: {pygame.key.name(game.keyconfig.get(i, default_keys.keys[i]))}",
                func,
            )
        )

    # the list comprehention above basicly adds all the keys of default_keys.keys(which are function strings) as the item text and a lambda function that will append a key config screen for that function.
    items.append(("Back", func_call))
    m.add_items(items)
    replace_call(m)


def update_question(game, canceler):
    """ask user if they want to update. replace with {canceler} if the user presses no"""
    m = menu.Menu(game, "An update is available! Would you like to update now?")
    set_default_sounds(m)
    m.add_items(
        (
            ("Yes", lambda: game.replace(updater.Updater(game, check=False))),
            ("No", lambda: game.replace(canceler)),
        )
    )
    game.replace(m)


def set_default_sounds(m):
    m.set_sounds(
        click="menu/move.ogg",
        enter="menu/select.ogg",
        open="menu/open.ogg",
        close="menu/close.ogg",
    )

def configure_location_template(game, func_call, replace_call=None):
    if replace_call is None: replace_call = game.replace
    replace_call(
        game.input.run(
            "Enter a template. Surround variable names in braces. Variable names can be found in the documentation. ",
            default=options.get("location_template",             "{x}, \r\n{y}, \r\n{z}, \r\nOn {tile} \r\nFacing {direction} at {angle} degrees with a pitch of {pitch} degrees. \r\nYou are leaning by {lean} degrees and you are {balanced}. "),
            handeler=lambda message: configure_location_template2(game, message, func_call)
        )
    )

def configure_location_template2(game, message, func_call):
    if message.strip()=="": 
        func_call()
        speech.speak("canceled")
        return
    
    options.set("location_template", message)
    func_call()


def set_buffer_timing(game, option, func_call):
    options.set("buffer_timing", option)
    func_call()




def output_menu(game, func_call, replace_call=None, parent=None):
    m = menu.Menu(game, "select audio output", parrent=parent)
    set_default_sounds(m)
    
    m.add_items([
        (f"system default: {cyal.util.get_default_all_device_specifier()[14:]}", lambda: set_device(game, "system default", func_call))
    ])
    for device in cyal.util.get_all_device_specifiers():
        m.add_items([
            (device[14:], functools.partial(set_device, game, device, func_call))
        ])
    m.add_items([
        ("go back", func_call)
    ])
    if replace_call is None: game.replace(m)
    else: replace_call(m)
    

def set_device(game, device, func_call):
    options.set("audio_device", device)
    if device == "system default": device = cyal.util.get_default_all_device_specifier()
    game.audio_mngr.context.device.reopen(name=device)
    game.audio_mngr.hrtf.use(options.get("hrtf_model", "Built-In HRTF"))
    func_call()

def input_menu(game, func_call, replace_call=None, parent=None, in_game=False):
    m = menu.Menu(game, "select audio input", parrent=parent)
    set_default_sounds(m)
    capture = cyal.CaptureExtension()
    m.add_items([
        (f"system default: {str(capture.default_device)[14:]}", lambda: set_input_device(game, 'system default', func_call, parent, capture, in_game))
    ])
    for device in capture.devices:
        m.add_items([
            (device[14:], functools.partial(set_input_device, game, device, func_call, parent, capture, in_game))
        ])
    m.add_items([
        ("go back", func_call)
    ])
    if replace_call is None: game.replace(m)
    else: replace_call(m)
    

def set_input_device(game, device, func_call, parent, capture, in_game=False):
    options.set("audio_input_device", device)
    if device == "system default": device = str(capture.default_device.decode('utf-8'))
    if in_game and parent.voice_chat.audio_input.name != device: 
        del parent.voice_chat.audio_input
        parent.voice_chat.audio_input = parent.voice_chat.capture_ext.open_device(name=device.encode(), sample_rate=48000, format=cyal.BufferFormat.MONO16)
    func_call()


def configure_jitter_buffer(game, func_call, replace_call=None):
    if replace_call is None: replace_call = game.replace
    replace_call(
        game.input.run(
            "Enter the value for your voice chat Jitter buffer. This is how long the client should wait  to start playing voice chats to allow for audio data to back up, preventing stuttering. A lower jitter buffer will decrease latency but may cause stuttering if internet is not stable enough. A higher jitter buffer will increase latency but will have a more stable sound. Minimum is 20ms and maximum is 120ms.",
            default=str(options.get("jitter_buffer", 60)),
            handeler=lambda message: configure_jitter_buffer2(game, message, func_call)
        )
    )

def configure_jitter_buffer2(game, message, func_call):
    if message.strip()=="": 
        func_call()
        speech.speak("canceled")
        return
    message = int(message)
    if message < 20: message = 20
    if message > 120: message = 120

    options.set("jitter_buffer", message)
    game.audio_mngr.silent_buffer = bytearray(96 * options.get("jitter_buffer", 60))
    func_call()




def configure_host(game, func_call, replace_call=None):
    if replace_call is None: replace_call = game.replace
    replace_call(
        game.input.run(
            "Enter the hostname of the server to connect to.",
            default=str(options.get("host", consts.DEFAULT_HOST)),
            handeler=lambda message: configure_host2(game, message, func_call)
        )
    )

def configure_host2(game, message, func_call):
    if message.strip()=="": 
        func_call()
        speech.speak("canceled")
        return

    options.set("host", message)
    func_call()


def configure_port(game, func_call, replace_call=None):
    if replace_call is None: replace_call = game.replace
    replace_call(
        game.input.run(
            "Enter the UDP port of the server to connect to.",
            default=str(options.get("port", consts.DEFAULT_PORT)),
            handeler=lambda message: configure_port2(game, message, func_call)
        )
    )

def configure_port2(game, message, func_call):
    if message.strip()=="": 
        func_call()
        speech.speak("canceled")
        return
    message = int(message)
    if message not in range(1, 2 **     16):
        func_call()
        speech.speak("Invalid port number")
        return

    options.set("port", message)
    func_call()
