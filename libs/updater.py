import os
import shutil
import zipfile
import subprocess
from pygame import key
import requests
import pySmartDL as dl
from . import state, menus, menu
from .version import version
from .speech import speak

nothing = lambda: None


class Updater(state.State):
    def __init__(self, game, check=True):
        super().__init__(game)
        self.check = check
        try:
            self.downloader = dl.SmartDL(
                "https://final-hour.net/fh.zip",
                threads=2,
                progress_bar=False,
                timeout=10,
            )
        except Exception as e:
            self.game.exit()
        self.last_progress = 0
        self.paused = False

    def enter(self):
        super().enter()
        try:
            if self.check:
                speak("Checking version...")
                request = requests.get(
                    "https://final-hour.net/latest_version.txt"
                )
                request.raise_for_status()
                latest_version = request.text.strip()
                if version.compare(latest_version):
                    return menus.update_question(self.game, self.game.pop)
                menus.main_menu(self.game)
                speak("You are running the latest version", False)
                return
            else:
                speak("The download is starting...")
                self.downloader.start(blocking=False)
                self.replace_last_substate(self.downloading_menu())
        except Exception as e:
            speak(f"Error while trying to fetch the latest version: {e}")
            self.game.exit()

    def exit(self):
        super().exit()
        if not self.downloader.isFinished():
            self.downloader.stop()

    def update(self, events):
        super().update(events)
        current_progress = int(self.downloader.get_progress() * 100)
        if current_progress >= self.last_progress + 10:
            if key.get_focused():
                speak(f"{current_progress}%", id="progress", interupt=False)
            self.last_progress = current_progress
        if not self.check and self.downloader.isFinished():
            if self.downloader.isSuccessful():
                speak("Download complete.")
                speak("Unpacking...", False)
                filename = self.downloader.get_dest()
                path = os.path.dirname(filename)
                file = zipfile.ZipFile(filename, "r")
                last_cwd = os.getcwd()
                os.chdir(path)
                file.extractall()
                path = f"{path}/final_hour"
                subprocess.Popen(
                    [f"{path}/final_hour.exe", "move_to", last_cwd, str(os.getpid())],
                    cwd=path,
                )
                self.game.exit()
            else:
                speak("download failed...")
                print(self.downloader.get_errors())
                self.game.pop()

    def get_eta(self):
        return (
            self.downloader.get_eta(human=True)
            if self.downloader.get_eta()
            else "unknown"
        )

    def toggle_pause(self):
        if self.paused:
            self.downloader.resume()
            speak("Unpaused")
        else:
            self.downloader.pause()
            speak("Paused")

        self.paused = not self.paused

    def abort(self):
        if self.paused:
            self.paused = False
            self.downloader.resume()
        self.downloader.stop()

    def abort_question(self):
        m = menu.Menu(self.game, "Are you sure you want to abort the current download?")
        menus.set_default_sounds(m)
        m.add_items([("Yes", self.abort), ("No", self.pop_last_substate)])
        self.add_substate(m)

    def downloading_menu(self):
        m = menu.Menu(self.game, "Download progress and information")
        menus.set_default_sounds(m)
        m.add_items(
            [
                (lambda: f"Status: {self.downloader.get_status()}", nothing),
                (
                    lambda: f"Progress: {round(self.downloader.get_progress()*100, 1)}%",
                    nothing,
                ),
                (lambda: f"Speed: {self.downloader.get_speed(human = True)}", nothing),
                (
                    lambda: f"Estimated remaining time: {self.get_eta()}",
                    nothing,
                ),
                (lambda: "Resume" if self.paused else "Pause", self.toggle_pause),
                ("Abort download", self.abort_question),
            ]
        )

        m.set_music("music/6.ogg")
        return m
