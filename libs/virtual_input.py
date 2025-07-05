from operator import index, mod
import string
import time
from random import randint as random
from . import consts, options, audio_manager

import pygame
import pyperclip
from .speech import speak
import re


class Virtual_input:
    def __init__(self, game, **kwargbs):
        """Parameters:
        initial_msg (str): The initial contents of the input string
        password (bool): Dictates whether the characters will be spoken
        password_msg (str): The string spoken should the input be hidden
        repeat_keys (bool): Dictates whether the characters will be repeated after a certain length of time holding down the key
        enter (bool): Determines if the user can press enter to exit the input
        escape (bool): Determines whether the user can press escape to exit the input
        msg_length (int): Sets the maximum character limit one wishes to have in the string before returning
        repeat_first_ms (int): Determines the first instance after which the user's keys will be automatically held. Best left at 500 so the user would have to trigger this event intentionally
        repeat_second_ms (int): Time waited after the first event fires. I.e, assuming the first_ms = 500, the keys will first be repeated at 500, then 550, 600, etc.
        """
        self.game = game
        self.key_clock = game.new_clock()
        self.typing_clock = game.new_clock()
        self.current_string = kwargbs.get("initial_msg", "")
        self.start_selection = 0
        self.end_selection = len(self.current_string)
        self.selection = self.current_string[self.start_selection : self.end_selection]
        self.hist_pos = len(self.game.input_history) - 1
        self.line_num = 0
        self.line_list = re.split("\r?\n", self.current_string)
        self._cursor = max(0, len(self.current_string) - 1)
        self.hidden = kwargbs.get("password", False)
        self.password_message = kwargbs.get("password_msg", "*")
        self.repeating_characters = options.get("repeat_chars", True)
        self.repeating_words = options.get("repeat_words", True)
        self.repeating_keys = kwargbs.get("repeat_keys", True)
        self.can_exit = kwargbs.get("enter", True)
        # Escape will return an empty string regardless of what the user chose
        self.can_escape = kwargbs.get("escape", True)
        self.whitelisted_characters = list(string.printable)
        self.maximum_message_length = kwargbs.get("msg_length", -1)
        self._key_times = {}
        self.initial_key_repeating_time = kwargbs.get("repeat_first_ms", 500)
        self.repeating_increment = kwargbs.get("repeat_second_ms", 50)
        self.typing = False

    def toggle_character_repetition(self):
        if self.repeating_characters == False:
            self.repeating_characters = True
            return True
        elif self.repeating_characters == True:
            self.repeating_characters = False
            return False

    def toggle_word_repetition(self):
        if self.repeating_words == False:
            self.repeating_words = True
            return True
        elif self.repeating_words == True:
            self.repeating_words = False
            return False

    @property
    def is_at_character_limit(self):
        return (
            self.maximum_message_length != -1
            and len(self.current_string) >= self.maximum_message_length
        )

    @property
    def current_text(self):
        return self.current_string

    @current_text.setter
    def current_text(self, text):
        self.current_string = text
        self._cursor = max(0, len(self._current_string) - 1)

    def clear(self):
        self.current_string = ""
        self._cursor = 0
        self._key_times = {}
        self.key_clock.restart()

    def move_in_string(self, value):
        """Parameters:
        value (int): The value by which the cursor will be moved
        """
        self._cursor += value
        if self._cursor < 0:
            self._cursor = 0
        elif self._cursor > len(self.current_string):
            self._cursor = len(self.current_string)

    def get_character(self):
        """Retrieves the character at the cursor's position
        Return Value:
                        A single character if the cursor is in the bounds of the string and the string is not empty, empty string otherwise
        """
        return (
            ""
            if len(self.current_string) == 0 or self._cursor == len(self.current_string)
            else self.current_string[self._cursor]
        )

    def insert_character(self, character):
        """Inserts a character into the text
        Parameters:
                        character (str): The character to be inserted
        """
        if len(character) == 0:
            return
        self.current_string = (
            self.current_string[: max(0, self._cursor)]
            + character
            + self.current_string[max(0, self._cursor) :]
            if self._cursor < len(self.current_string)
            else self.current_string + character
        )
        self._cursor += len(character)
        self.speak_character(character, True)
        if re.match("\r?\n", character):
            self.line_num += 1
        if self.typing == False and self.current_string[0] != "/":
            if self.game.network:
                self.game.network.send(
                    consts.CHANNEL_MISC, "set_typing", {"typing": True}
                )
            self.typing = True
            self.typing_clock.restart()
        self.selection = self.get_character()
        self.start_selection = self._cursor - 1
        self.end_selection = self._cursor
        self.line_list = re.split("\r?\n", self.current_string)

    def remove_character(self):
        """Removes a character from the string based upon the cursor's position"""
        if self._cursor == 0:
            return
        self.speak_character(self.current_string[self._cursor - 1])
        if re.match("\r?\n", self.current_string[self._cursor - 1]):
            self.line_num -= 1
            self.line_list = re.split("\r?\n", self.current_string)
        if self._cursor == len(self.current_string):
            self.current_string = self.current_string[:-1]
        else:
            self.current_string = (
                self.current_string[: self._cursor - 1]
                + self.current_string[self._cursor :]
            )
        self._cursor -= 1
        if self.typing == False and self._cursor > 0:
            if self.current_string[0] != "/" and self.game.network:
                self.game.network.send(
                    consts.CHANNEL_MISC, "set_typing", {"typing": True}
                )
            self.typing = True
            self.typing_clock.restart()
        self.selection = self.get_character()
        self.start_selection = self._cursor - 1
        self.end_selection = self._cursor

    def speak_character(self, char, typing=False):
        """Outputs a given character respective the repeating_characters and password settings
        Parameters:
                        character (str): The character to be outputted
        """
        speak(self.current_string, silent=True, id="text_entry")
        if typing == True and not self.repeating_characters:
            return
        character = char
        if char == " ":
            character = "space"
        if char.isupper():
            character = f"cap {char}"
        if self.hidden:
            speak(self.password_message, True, False)
        else:
            speak(character, True, False)

    def snap_to_top(self):
        """Snaps to the top of text (0 on the cursor position)"""
        self._cursor = 0
        self.speak_character(self.get_character())

    def snap_to_bottom(self):
        """Snaps to the bottom of text (len(self.current_string))"""
        self._cursor = len(self.current_string)
        self.speak_character(self.get_character())

    def select_to_top(self):
        """selects to the top of text (0 on the cursor position)"""
        index = self._cursor
        self._cursor = 0
        self.selection = self.current_string[0:index]
        self.start_selection = 0
        self.end_selection = index
        speak("selected " + self.selection) if len(self.selection) <= 1000 else speak(
            "selected "
            + str(len(self.selection))
            + " characters from: "
            + self.selection[0:31]
            + ", to: "
            + self.selection[len(self.selection) - 30 :]
        )

    def select_to_bottom(self):
        """selects to the bottom of text (len(self.current_string))"""
        index = self._cursor
        self._cursor = len(self.current_string)
        self.selection = self.current_string[index:]
        self.start_selection = index
        self.end_selection = len(self.current_string)
        speak("selected " + self.selection) if len(self.selection) <= 1000 else speak(
            "selected "
            + str(len(self.selection))
            + " characters from: "
            + self.selection[0:31]
            + ", to: "
            + self.selection[len(self.selection) - 30 :]
        )

    def toggle_input_to_letters(self):
        """Toggles the input to select only ascii letters"""
        self.whitelisted_characters = list(string.ascii_letters)

    def toggle_input_to_digits(self, negative=False, decimal=False):
        """Toggles the input to select only ascii digits
        Parameters:
                        negative (bool): Dictates whether the user can type in a dash (-)
                        decimal (bool): Dictates whether a user can type in a period (.)
        """
        self.whitelisted_characters = list(string.digits)
        if negative:
            self.whitelisted_characters.append("-")
        if decimal:
            self.whitelisted_characters.append(".")

    def toggle_input_to_all(self):
        pass

    def toggle_input_to_custom(self, characters):
        """Toggles the input to select user-provided input
        Parameters:
                        characters (str): A string of characters the user wishes to allow the input to accept
        """
        self.whitelisted_characters = list(characters)

    def run(self, message, validate=False, default="", handeler=None):
        speak(message, True, id="text_entry_title")
        self.clear()
        if default != "":
            self.insert_character(default)
        self.typing_clock.restart()
        self.hist_pos = len(self.game.input_history) - 1
        self.line_list = re.split("\r?\n", self.current_string)
        self.line_num = 0
        return lambda: self.ck(message, handeler, validate)

    def ck(self, message, handler, validate):
        if self.typing_clock.elapsed >= 50000 and self.typing == True:
            self.typing = False
            if self.game.network:
                self.game.network.send(
                    consts.CHANNEL_MISC, "set_typing", {"typing": False}
                )
            self.typing_clock.restart()


        for event in self.game.events:
            if event.type == pygame.KEYDOWN:
                if self.repeating_keys and event.key not in self._key_times:
                    self._key_times[event.key] = [
                        self.key_clock.elapsed + self.initial_key_repeating_time,
                        event.unicode,
                        event.mod,
                    ]
                if (
                    self.can_exit
                    and event.key == pygame.K_RETURN
                    and not event.mod & pygame.KMOD_SHIFT
                ):
                    options.set("repeat_chars", self.repeating_characters)
                    options.set("repeat_words", self.repeating_words)
                    if self.current_string != "":
                        self.game.input_history[
                            len(self.game.input_history) - 1
                        ] = self.current_string
                        self.game.input_history.append("")
                    if self.game.network:
                        self.game.network.send(
                            consts.CHANNEL_MISC, "set_typing", {"typing": False}
                        )
                    self.typing = False
                    handler(self.current_text)
                elif self.can_escape and event.key == pygame.K_ESCAPE:
                    options.set("repeat_chars", self.repeating_characters)
                    options.set("repeat_words", self.repeating_words)
                    if self.game.network:
                        self.game.network.send(
                            consts.CHANNEL_MISC, "set_typing", {"typing": False}
                        )
                    self.typing = False
                    handler("")
                elif event.key == pygame.K_RETURN:
                    self.insert_character("\r\n")
                elif (
                    event.key == pygame.K_BACKSPACE
                    and not event.mod & pygame.KMOD_CTRL
                    or event.key == pygame.K_DELETE
                ):
                    if self._cursor==0: continue
                    if self.current_string != "":
                        self.selection = self.current_string[
                            self.start_selection : self.end_selection
                        ]
                        speak(
                            re.sub(
                                "\r?\n",
                                " blank ",
                                self.current_string[
                                    self.start_selection : self.end_selection
                                ]
                                + " deleted. ",
                            )
                        ) if len(self.selection) <= 1000 else speak(
                            str(len(self.selection))
                            + " characters deleted from: "
                            + self.selection[0:31]
                            + ", to: "
                            + self.selection[len(self.selection) - 30 :]
                        )
                        for i in re.finditer("\r?\n", self.selection):
                            self.line_num -= 1
                        self.current_string = (
                            self.current_string[0 : self.start_selection]
                            + self.current_string[self.end_selection :]
                        )
                        self.line_list = re.split("\r?\n", self.current_string)
                        self._cursor -= len(self.selection)
                        self.selection = self.get_character()
                        self.start_selection = self._cursor - 1
                        self.end_selection = self._cursor
                elif event.key == pygame.K_BACKSPACE:
                    if self.current_string != "":
                        word_string = re.sub("\r?\n", " nl ", self.current_string)
                        index = self._cursor
                        start_index = word_string.rfind(" ", 0, index)
                        if start_index != -1:
                            self._cursor = start_index
                            self.selection = self.get_character()
                            self.start_selection = self._cursor - 1
                            self.end_selection = self._cursor
                            speak(
                                "deleted " + word_string[start_index:index]
                            ) if word_string[
                                start_index:index
                            ].strip() != "nl" else speak(
                                "New line deleted"
                            )
                            self.current_string = (
                                self.current_string[0:start_index]
                                + self.current_string[index:]
                            )
                        else:
                            start_index = 0
                            self._cursor = start_index
                            self.selection = self.get_character()
                            self.start_selection = self._cursor - 1
                            self.end_selection = self._cursor
                            speak(
                                "deleted " + word_string[start_index:index]
                            ) if word_string[
                                start_index:index
                            ].strip() != "nl" else speak(
                                " new line deleted. "
                            )
                            self.current_string = (
                                self.current_string[0:start_index]
                                + self.current_string[index:]
                            )
                        self.line_list = re.split("\r?\n", self.current_string)
                elif event.key == pygame.K_TAB:
                    speak(message, True, False)
                elif (
                    event.key in [pygame.K_UP, pygame.K_DOWN]
                    and not event.mod & pygame.KMOD_ALT
                ):
                    if event.key == pygame.K_UP:
                        if self.line_num > 0:
                            self.line_num -= 1
                        else:
                            self.line_num = self.line_num
                    elif event.key == pygame.K_DOWN:
                        if self.line_num < len(self.line_list) - 1:
                            self.line_num += 1
                        else:
                            self.line_num = self.line_num
                    speak(self.line_list[self.line_num], True, id="text_entry")
                    pos = 0
                    for i in range(0, self.line_num):
                        pos += len(self.line_list[i]) + 1
                    self._cursor = pos

                elif event.key == pygame.K_DOWN:
                    if self.hist_pos < len(self.game.input_history) - 1:
                        self.hist_pos += 1
                        self.current_string = self.game.input_history[self.hist_pos]
                        speak(self.current_string)
                        self._cursor = 0
                        self.selection = self.current_string
                        self.start_selection = 0
                        self.end_selection = len(self.current_string)
                    else:
                        speak(self.current_string)
                        self.selection = self.current_string
                        self.start_selection = 0
                        self.end_selection = len(self.current_string)

                elif event.key == pygame.K_UP:
                    if self.hist_pos > 0:
                        self.hist_pos -= 1
                        self.current_string = self.game.input_history[self.hist_pos]
                        speak(self.current_string)
                        self._cursor = 0
                        self.selection = self.current_string
                        self.start_selection = 0
                        self.end_selection = len(self.current_string)
                    else:
                        speak(self.current_string)
                        self.selection = self.current_string
                        self.start_selection = 0
                        self.end_selection = len(self.current_string)
                elif (
                    event.key == pygame.K_LEFT
                    and not event.mod & pygame.KMOD_CTRL
                    and not event.mod & pygame.KMOD_SHIFT
                ):
                    self.move_in_string(-1)
                    self.speak_character(self.get_character())
                    self.selection = self.get_character()
                    self.start_selection = self._cursor - 1
                    self.end_selection = self._cursor
                    if re.match(
                        "\r?\n",
                        self.current_string[self._cursor - 2 : self._cursor - 1],
                    ):
                        self.line_num -= 1
                elif event.key == pygame.K_LEFT and not event.mod & pygame.KMOD_CTRL:
                    self.move_in_string(-1)
                    if self._cursor <= self.start_selection:
                        speak(self.get_character() + " selected. ")
                        self.start_selection = self._cursor
                        self.selection = self.current_string[
                            self.start_selection : self.end_selection
                        ]
                    elif self._cursor > self.start_selection:
                        speak(self.get_character() + " unselected. ")
                        self.end_selection = self._cursor
                        self.selection = self.current_string[
                            self.start_selection : self.end_selection
                        ]
                    if re.match(
                        "\r?\n",
                        self.current_string[self._cursor - 2 : self._cursor - 1],
                    ):
                        self.line_num -= 1
                elif event.key == pygame.K_LEFT and not event.mod & pygame.KMOD_SHIFT:
                    self.move_word_left()
                    self.selection = self.get_character()
                    self.start_selection = self._cursor - 1
                    self.end_selection = self._cursor

                elif event.key == pygame.K_LEFT:
                    self.select_word_left()

                elif (
                    event.key == pygame.K_RIGHT
                    and not event.mod & pygame.KMOD_CTRL
                    and not event.mod & pygame.KMOD_SHIFT
                ):
                    self.move_in_string(1)
                    self.speak_character(self.get_character())
                    self.selection = self.get_character()
                    self.start_selection = self._cursor - 1
                    self.end_selection = self._cursor
                    if re.match(
                        "\r?\n",
                        self.current_string[self._cursor - 2 : self._cursor - 1],
                    ):
                        self.line_num += 1
                elif event.key == pygame.K_RIGHT and not event.mod & pygame.KMOD_CTRL:
                    self.move_in_string(1)
                    if self._cursor + 1 >= self.end_selection:
                        speak(self.get_character() + " selected. ")
                        self.end_selection = self._cursor + 1
                        self.selection = self.current_string[
                            self.start_selection : self.end_selection
                        ]
                    elif self._cursor < self.end_selection:
                        speak(self.get_character() + " unselected. ")
                        self.start_selection = self._cursor
                        self.selection = self.current_string[
                            self.start_selection : self.end_selection
                        ]
                    if re.match(
                        "\r?\n",
                        self.current_string[self._cursor - 2 : self._cursor - 1],
                    ):
                        self.line_num += 1
                elif event.key == pygame.K_RIGHT and not event.mod & pygame.KMOD_SHIFT:
                    self.move_word_right()
                    self.selection = self.get_character()
                    self.start_selection = self._cursor - 1
                    self.end_selection = self._cursor

                elif event.key == pygame.K_RIGHT:
                    self.select_word_right()

                elif event.key == pygame.K_HOME and not event.mod & pygame.KMOD_SHIFT:
                    self.snap_to_top()
                    self.selection = self.get_character()
                    self.start_selection = self._cursor
                    self.end_selection = self._cursor + 1
                    self.line_num = 0
                elif event.key == pygame.K_END and not event.mod & pygame.KMOD_SHIFT:
                    self.snap_to_bottom()
                    self.selection = self.get_character()
                    self.start_selection = self._cursor
                    self.end_selection = self._cursor + 1
                    self.line_num = len(self.line_list) - 1
                elif event.key == pygame.K_HOME:
                    self.select_to_top()
                    self.line_num = 0

                elif event.key == pygame.K_END:
                    self.select_to_bottom()
                    self.line_num = len(self.line_list) - 1
                elif event.key == pygame.K_a and event.mod & pygame.KMOD_CTRL:
                    self.selection = self.current_string
                    self.start_selection = 0
                    self.end_selection = len(self.current_string)
                    speak("selected " + self.selection) if len(
                        self.selection
                    ) <= 1000 else speak(
                        "selected "
                        + str(len(self.selection))
                        + " characters from: "
                        + self.selection[:30]
                        + ", to: "
                        + self.selection[len(self.selection) - 30 :]
                    )
                    self.line_num = 0
                elif event.key == pygame.K_c and event.mod & pygame.KMOD_CTRL:
                    speak("coppied: " + self.selection)
                    pyperclip.copy(self.selection)
                elif event.key == pygame.K_v and event.mod & pygame.KMOD_CTRL:
                    speak("text pasted from clipboard")
                    self.insert_character(pyperclip.paste())
                elif event.key == pygame.K_F1:
                    speak("Word echo on") if self.toggle_word_repetition() else speak(
                        "word echo off"
                    )
                elif event.key == pygame.K_F2:
                    speak(
                        "Character repeat on"
                    ) if self.toggle_character_repetition() else speak(
                        "Character repeat off"
                    )

                elif event.unicode != "":
                    self.insert_character(event.unicode)
                    if event.unicode == " " and self.repeating_words:
                        index = self._cursor
                        start_index = self.current_string.rfind(" ", 0, index - 1)
                        if start_index != -1:
                            speak(self.current_string[start_index:index])
                        else:
                            speak(self.current_string[0 : index - 1])
            elif event.type == pygame.KEYUP:
                if event.key in self._key_times:
                    del self._key_times[event.key]
                else:
                    return [event]
        for key in self._key_times:
            if self.key_clock.elapsed >= self._key_times[key][0]:
                self._key_times[key][0] += self.repeating_increment
                pygame.event.post(
                    pygame.event.Event(
                        pygame.KEYDOWN,
                        key=key,
                        unicode=self._key_times[key][1],
                        mod=self._key_times[key][2],
                    )
                )
        # in case this is a substate, lets prevent the parrent state from getting events to prevent conflicts.
        return True

    def move_word_right(self):
        word_string = re.sub("\r?\n", " nl ", self.current_string)
        if self._cursor != len(word_string):
            index = word_string.find(" ", self._cursor + 1)
        else:
            index = len(word_string)
        if index == -1:
            index = len(word_string)
        self.move_in_string(index - self._cursor)
        start_index = word_string.rfind(" ", 0, self._cursor - 1)
        if start_index == -1:
            start_index = 0

        word = word_string[start_index:index]
        speak(word, store_in_history=False) if word.strip() != "nl" else speak(
            "blank", store_in_history=False
        )
        if word.strip() == "nl":
            self.line_num += 1

    def select_word_right(self):
        word_string = re.sub("\r?\n", " nl ", self.current_string)
        if self._cursor != len(word_string):
            index = word_string.find(" ", self._cursor + 1)
        else:
            index = len(word_string)
        if index == -1:
            index = len(word_string)
        self.move_in_string(index - self._cursor)
        start_index = word_string.rfind(" ", 0, self._cursor - 1)
        if start_index == -1:
            start_index = 0

        word = word_string[start_index:index]
        if index >= self.end_selection:
            speak(
                word + " selected. ", store_in_history=False
            ) if word.strip() != "nl" else speak(
                "blank selected. ", store_in_history=False
            )
            self.end_selection = index
        elif index < self.end_selection:
            speak(
                word + " unselected", store_in_history=False
            ) if word.strip() != "nl" else speak(
                "blank unselected", store_in_history=False
            )
            self.start_selection = index
        self.selection = self.current_string[self.start_selection : self.end_selection]
        if word.strip() == "nl":
            self.line_num += 1

    def move_word_left(self):
        word_string = re.sub("\r?\n", " nl ", self.current_string)
        if self._cursor != 0:
            index = word_string.rfind(" ", 0, self._cursor - 1)
        else:
            index = 0
        if index == -1:
            index = 0
            self.move_in_string(0 - self._cursor)
        else:
            self.move_in_string(index - self._cursor)
        end_index = word_string.find(" ", self._cursor + 1)
        if end_index == -1:
            end_index = len(self.current_string)
        word = word_string[index:end_index]
        speak(word, store_in_history=False) if word.strip() != "nl" else speak(
            "blank", store_in_history=False
        )
        if word.strip() == "nl":
            self.line_num -= 1

    def select_word_left(self):
        word_string = re.sub("\r?\n", " nl ", self.current_string)
        if self._cursor != 0:
            index = word_string.rfind(" ", 0, self._cursor - 1)
        else:
            index = 0
        if index == -1:
            index = 0
            self.move_in_string(0 - self._cursor)
        else:
            self.move_in_string(index - self._cursor)
        end_index = word_string.find(" ", self._cursor + 1)
        if end_index == -1:
            end_index = len(word_string)
        word = word_string[index:end_index]
        if index <= self.start_selection:
            speak(
                word + " selected. ", store_in_history=False
            ) if word.strip() != "nl" else speak(
                "blank selected", store_in_history=False
            )
            self.start_selection = index
        elif index > self.start_selection:
            speak(
                word + " unselected. ", store_in_history=False
            ) if word.strip() != "nl" else speak(
                "blank unselected", store_in_history=False
            )
            self.end_selection = index + 1
        self.selection = self.current_string[self.start_selection : self.end_selection]
        if word.strip() == "nl":
            self.line_num -= 1
