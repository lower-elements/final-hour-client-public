from . import state
from .speech import speak

import pygame


class volume_mixer(state.State):
    def __init__(self, game, parent=None):
        super().__init__(game, parrent=parent)
        self.audio_mngr = self.game.audio_mngr
        self.sliders = []
        for cat in self.audio_mngr.volume_categories.keys():
            self.sliders.append({
                "label": cat,
                "volume": self.audio_mngr.volume_categories[cat][0]
            })
        self.current_index = -1
    
    def update(self, events):
        super().update(events)
        for event in events:
            if event.type == pygame.KEYDOWN:
                key = event.key
                if key == pygame.K_TAB:
                    if event.mod & pygame.KMOD_SHIFT:
                        if self.current_index > 0: self.current_index -= 1
                        elif self.current_index <= 0: self.current_index = len(self.sliders)-1
                    else:
                        if self.current_index < len(self.sliders)-1: self.current_index+=1
                        else: self.current_index = 0
                    speak(f"{self.sliders[self.current_index]['label']}. Slider: {self.sliders[self.current_index]['volume']}%")
                elif key == pygame.K_RETURN or key == pygame.K_ESCAPE:
                    if self.parrent: self.parrent.pop_last_substate()
                    else: self.game.pop()
                elif key == pygame.K_DOWN and self.sliders[self.current_index]["volume"] > 1: 
                    self.sliders[self.current_index]["volume"] -= 1
                    self.audio_mngr.set_volume(self.sliders[self.current_index]["label"], self.sliders[self.current_index]["volume"])
                    speak(str(self.sliders[self.current_index]["volume"]))
                elif key == pygame.K_END and self.sliders[self.current_index]["volume"] > 0: 
                    self.sliders[self.current_index]["volume"] = 1
                    self.audio_mngr.set_volume(self.sliders[self.current_index]["label"], self.sliders[self.current_index]["volume"])
                    speak(str(self.sliders[self.current_index]["volume"]))
                elif key == pygame.K_PAGEDOWN and self.sliders[self.current_index]["volume"] >= 11: 
                    self.sliders[self.current_index]["volume"] -= 10
                    self.audio_mngr.set_volume(self.sliders[self.current_index]["label"], self.sliders[self.current_index]["volume"])
                    speak(str(self.sliders[self.current_index]["volume"]))
                elif key == pygame.K_UP and self.sliders[self.current_index]["volume"] < 100: 
                    self.sliders[self.current_index]["volume"] += 1
                    self.audio_mngr.set_volume(self.sliders[self.current_index]["label"], self.sliders[self.current_index]["volume"])
                    speak(str(self.sliders[self.current_index]["volume"]))
                elif key == pygame.K_HOME and self.sliders[self.current_index]["volume"] < 100: 
                    self.sliders[self.current_index]["volume"] = 100
                    self.audio_mngr.set_volume(self.sliders[self.current_index]["label"], self.sliders[self.current_index]["volume"])
                    speak(str(self.sliders[self.current_index]["volume"]))
                elif key == pygame.K_PAGEUP and self.sliders[self.current_index]["volume"] <= 90: 
                    self.sliders[self.current_index]["volume"] += 10
                    self.audio_mngr.set_volume(self.sliders[self.current_index]["label"], self.sliders[self.current_index]["volume"])
                    speak(str(self.sliders[self.current_index]["volume"]))
        return True
    
    def enter(self):
        super().enter()
        speak("volume mixer.")
    
    def exit(self):
        super().exit()
        speak("closed")
        