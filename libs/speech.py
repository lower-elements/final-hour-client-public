from . import options, consts
from accessible_output2 import outputs
import pygame
speaker = outputs.auto.Auto()

history = (
    []
)  # should only be used for viewing on the screen, might contain diffrant things than what's spoken.


def speak(text, interupt=True, store_in_history=True, id=None, silent=False):
    if options.get("mute_speech_on_focus_loss", False) and not pygame.key.get_focused(): silent = True
    if id is not None:
        for item in history:
            if item[1] == id:
                history.remove(item)
    if store_in_history:
        history.append((text, id))
    if not silent:
        speaker.output(text, interupt)
