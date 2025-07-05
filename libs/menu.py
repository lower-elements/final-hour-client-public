import contextlib

import pygame as pg

from . import state
from . import globals as g
from . import options, speech, consts


class Menu(state.State):
    def __init__(
        self,
        game,
        title: str,
        wrapping=False,
        up_down=True,
        left_right=False,
        autoclose=False,
        parrent=None,
    ):
        super().__init__(game, parrent=parrent)
        self.direct_soundgroup = self.game.direct_soundgroup
        self.title = title
        self.autoclose = autoclose
        self.wrapping = wrapping
        self.up_down = up_down
        self.left_right = left_right
        self.items = []
        self.pos = -1

        # sound filepaths.
        self.click = ""
        self.close = ""
        self.edge = ""
        self.enter_sound = ""
        self.open = ""
        self.wrap = ""
        self.music = ""
        self.mus=None
        self.music_volume = None

    def return_first_match(self, text, current_index=0):
        """return the first index that has an item that matches the text"""
        # first, check if there are any items after current_index
        for i in self.items[current_index + 1 :]:
            item_name = (i[0]() if callable(i[0]) else i[0]).lower()
            if item_name.startswith(text.lower()):
                return self.items.index(i)
        # no matching item after current_index, lets check the items above it.
        for i in self.items[:current_index]:
            item_name = (i[0]() if callable(i[0]) else i[0]).lower()
            if item_name.startswith(text.lower()):
                return self.items.index(i)
        # no matching item at all, so just return current_index
        return current_index

    def enter(self):
        super().enter()
        speech.speak(self.title, id="menu_title")
        if self.open:
            self.direct_soundgroup.play(self.open, cat="ui")

    def add_items(self, items: list[tuple]):
        """
        adds the items given in a list of items. each item is a tuple of (str|callable, callable)
        if [0] is a callable it will use its return value to speak its label. when enter is pressed, calls [1]
        """
        for i in items:
            self.items.append(i)

    def set_sounds(self, click="", close="", edge="", enter="", open="", wrap=""):
        self.click = click
        self.close = close
        self.edge = edge
        self.enter_sound = enter
        self.open = open
        self.wrap = wrap

    def set_music(self, music_path: str, gain=None):
        if gain is None:
            gain = options.get("menu_music_volume", 50)
        self.music = music_path
        mus = self.game.audio_mngr.create_soundgroup(direct=True)
        self.mus = mus.play(self.music, looping=True, cat="music")
        if self.mus.source is not None: self.mus.source.gain = gain / 100
        self.mus.volume = gain
        self.music_volume = gain

    def speak_current_item(self):
        text = self.items[self.pos][0]
        if callable(text):
            text = text()
        speech.speak(text, id="menu_item")

    def update(self, events):
        super().update(events)
        for event in events:
            if event.type == pg.KEYDOWN:
                key = event.key
                if self.up_down and key == pg.K_DOWN:
                    self.move_down()

                elif self.up_down and key == pg.K_UP:
                    self.move_up()

                if self.up_down and key == pg.K_END:
                    self.move_end()

                elif self.up_down and key == pg.K_HOME:
                    self.move_top()

                elif key == pg.K_RETURN or key == pg.K_SPACE:
                    if self.pos != -1:
                        self.select_current_item()
                elif key == pg.K_ESCAPE:
                    # activate the last option, we'll assume it exits the menu.
                    self.items[-1][1]()
                    if self.autoclose:
                        if self.parrent:
                            self.parrent.pop_last_substate()
                        else:
                            self.game.pop()

                elif key == pg.K_PAGEDOWN and self.music_volume is not None:
                    self.set_music_volume(self.music_volume - 5)

                elif key == pg.K_PAGEUP and self.music_volume is not None:
                    self.set_music_volume(self.music_volume + 5)
                elif event.unicode:
                    new_pos = self.return_first_match(event.unicode, self.pos)
                    if new_pos != self.pos:
                        self.pos = new_pos
                        if self.click:
                            self.direct_soundgroup.play(self.click, cat="ui")
                        self.speak_current_item()
            elif event.type == pg.KEYUP:
                return [event]
        return True

    def select_current_item(self):
        self.items[self.pos][1]()
        if self.enter_sound != "":
            self.direct_soundgroup.play(self.enter_sound, cat="ui")
        if self.autoclose:
            if self.parrent:
                self.parrent.pop_last_substate()
            else:
                self.game.pop()

    def move_up(self):
        if self.pos > 0:
            self.pos -= 1
            if self.click != "":
                self.direct_soundgroup.play(self.click, cat="ui")
        elif self.wrapping:
            self.pos = len(self.items) - 1
            if self.wrap != "":
                self.direct_soundgroup.play(self.wrap, cat="ui")
        else:
            self.pos = 0
            if self.edge != "":
                self.direct_soundgroup.play(self.edge, "ui")
        self.speak_current_item()

    def move_down(self):
        if self.pos < len(self.items) - 1:
            self.pos += 1
            if self.click != "":
                self.direct_soundgroup.play(self.click, cat="ui")
        elif self.wrapping:
            self.pos = 0
            if self.wrap != "":
                self.direct_soundgroup.play(self.wrap, cat="ui")
        else:
            self.pos = self.pos
            if self.edge != "":
                self.direct_soundgroup.play(self.edge, cat="ui")
        self.speak_current_item()

    def move_top(self):
        self.pos = 0
        self.speak_current_item()
        if self.click != "":
            self.direct_soundgroup.play(self.click, cat="ui")

    def move_end(self):
        self.pos = len(self.items) - 1
        self.speak_current_item()
        if self.click != "":
            self.direct_soundgroup.play(self.click, cat="ui")

    def set_music_volume(self, gain: float, changepref=True):
        if 0 <= gain <= 100:
            self.music_volume = gain
            if self.mus.source is not None: self.mus.source.gain = gain / 100
            self.mus.volume = gain
        options.set("menu_music_volume", self.music_volume)
        speech.speak(f"music volume set to {self.music_volume}%", id="music_volume")

    def exit(self):
        super().exit()
        options.save()
        if self.mus != None:
            self.game.automate(
                self.mus.source, "gain", 0.0, 500, 
                callback= self.mus.destroy, cancelable=False
            )
        if self.close:
            self.direct_soundgroup.play(self.close, cat="ui")
