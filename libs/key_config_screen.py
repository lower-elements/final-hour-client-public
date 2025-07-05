import pygame
from . import state, audio_manager
from .speech import speak


class Key_config_screen(state.State):
    def __init__(self, game, func, options_menu=None):
        """get a function string and set the first pressed key as the key for that function, updating the players key config and pop."""
        super().__init__(game)
        self.func = func
        self.func_call= options_menu

    def enter(self):
        self.game.direct_soundgroup.play("ui/keyconfig/start.ogg")
        speak(f"Please press the key you want for {self.func}.")

    def update(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                speak(pygame.key.name(event.key))
                self.game.keyconfig.set(event.key, self.func)
                self.func_call()
                break

    def exit(self):
        self.game.direct_soundgroup.play("ui/keyconfig/end.ogg")
        speak("Done.", False)
