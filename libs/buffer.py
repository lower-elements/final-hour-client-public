import datetime
import os
import threading
from time import localtime, strftime
import urllib.parse as urlparse

import linkpreview, urlextract
import pyperclip

from . import speech, time_utils, options, audio_manager

url_extract = urlextract.URLExtract(extract_localhost=False)

url_previews = {}


def convert_to_valid_url(url):
    if "://" in url:
        return url
    p = urlparse.urlparse(url, "https")
    netloc = p.netloc or p.path
    path = p.path if p.netloc else ""
    p = urlparse.ParseResult("https", netloc, path, *p[3:])
    return p.geturl()


def get_preview(url):
    if url in url_previews:
        preview = url_previews[url]
    else:
        preview = linkpreview.link_preview(url)
        url_previews[url] = preview
    return preview


def truncate_string(str_input, max_length):
    length = len(str_input)
    if length > max_length:
        str_end = "..."
        return str_input[: max_length - len(str_end)] + str_end
    return str_input


def format_url(url, truncate=True, include_description=True, original_url=False):
    text = ""
    if url["title"]:
        text += f'{url["title"]} , '
    if url["description"] and include_description:
        text += f'{url["description"]} , '
    the_url = url["origin_str"] if original_url else url["url"]
    url_text = truncate_string(the_url, 75) if truncate else the_url

    text += f"{url_text} "
    return text


def absolute_time(message=""):
    pending_output = ""

    output = pending_output + message
    (output, not_used, pending_output) = output.rpartition("\n")
    if output == "":
        timestamp = strftime("%Y-%m-%d %X")
        output = f"[{timestamp}] " + output.replace("\n", "\n" + timestamp + " ")
        return output


bufferindex = 0


class buffer:
    def __init__(self, name, permanent=False, cap=500):
        self.name = name
        self.items = []
        self.unexported_items = []
        self.index = 0
        self.cap = cap
        self.muted = False
        self.interrupt = False
        self.permanent = permanent

    def speak_item(self):
        td = options.get("buffer_timing", 1)
        if len(self.items) > 0:
            if td == 1:
                speech.speak(
                    self.items[self.index].format_text()
                    + " , "
                    + time_utils.absolute_time(False, self.items[self.index].time)
                    + ". ",
                    id=f"buffer_{self.name}",
                )
            elif td == 2:
                speech.speak(
                    self.items[self.index].format_text()
                    + " , "
                    + time_utils.relative_time(self.items[self.index].time.timestamp()),
                    id=f"buffer_{self.name}",
                )
            else:
                speech.speak(
                    self.items[self.index].format_text(), id=f"buffer_{self.name}"
                )
        else:
            speech.speak("No events.", id=f"buffer_{self.name}")


class buffer_item:
    def __init__(self, text):
        self.text = text
        self.time = datetime.datetime.now()
        urls = url_extract.find_urls(text, only_unique=True)
        self.urls = []
        for i in urls:
            url = {
                "title": "",
                "description": "",
                "url": convert_to_valid_url(i),
                "origin_str": i,
            }
            self.urls.append(url)

    def format_text(self):
        text = self.text
        for i in self.urls:
            text = text.replace(
                i["origin_str"],
                format_url(i, include_description=False, original_url=True),
            )
        return text

    def preview_link(self, url):
        preview = get_preview(url["url"])
        url["title"] = preview.title
        url["description"] = preview.description


buffers = []


def export_buffers():
    path = ""
    if not os.path.isdir(os.path.expanduser("~/Documents") + "/final_hour"):
        if os.path.isdir(os.path.expanduser("~/documents")): 
            path = os.path.expanduser("~/Documents") + "/final_hour"
            os.mkdir(path)
        else:
            if not os.path.isdir("./logs"): 
                path = "./logs/"
                os.mkdir(path)
    else:
        path = os.path.expanduser("~/Documents") + "/final_hour"

    for i in buffers:
        f = open(
             path + i.name + ".log",
            "ab",
        )
        text = f"\r\nexported at {absolute_time()}" + "\n"
        for i2 in i.unexported_items:
            text += f"{i2.text}: {time_utils.absolute_time(True, i2.time)}" + "\n"
        try:
            f.write(text.encode("utf-8"))
            i.unexported_items = []
        except IOError as __ERR__:
            speech.speak(
                str(
                    f"Error: Unable to export buffers to files. \r\nReturned IO Error: {__ERR__} "
                )
            )
    speech.speak(
        str(
            f"Successfully exported buffers at {time_utils.absolute_time(True)}"
        )
    )


def add_buffer(*args):
    buffers.append(buffer(*args))


def add_item(game, name, text, speak=True, sound=""):
    item = buffer_item(text)
    for i in buffers:
        if i.name == name:
            if sound and not i.muted:
                game.direct_soundgroup.play(sound)
            i.items.append(item)
            i.unexported_items.append(item)
            if name != "main":
                buffers[0].items.append(item)
            if speak == True and i.muted == False:
                speech.speak(item.format_text(), i.interrupt, id=f"buffer_{i.name}")
            return
    add_buffer(name)
    add_item(game, name, text, speak)


def cycle_item(dir):
    global bufferindex
    speak = True
    if dir == 1:
        buffers[bufferindex].index -= 1
        if buffers[bufferindex].index < 0:
            speak = False
            buffers[bufferindex].index = 0
    elif dir == 2:
        buffers[bufferindex].index += 1
        if buffers[bufferindex].index >= len(buffers[bufferindex].items):
            speak = False
            buffers[bufferindex].index = len(buffers[bufferindex].items) - 1
    elif dir == 3:
        buffers[bufferindex].index = 0
    elif dir == 4:
        buffers[bufferindex].index = len(buffers[bufferindex].items) - 1
    if speak:
        buffers[bufferindex].speak_item()


def cycle(dir):
    global bufferindex
    speak = True
    if dir == 1:
        bufferindex -= 1
        bufferindex = max(bufferindex, 0)
    elif dir == 2:
        bufferindex += 1
        bufferindex = min(bufferindex, len(buffers) - 1)
    elif dir == 3:
        bufferindex = 0
    elif dir == 4:
        bufferindex = len(buffers) - 1
    if speak:
        status = " (muted)" if buffers[bufferindex].muted == True else ""
        speech.speak(
            buffers[bufferindex].name
            + status
            + ". "
            + str(len(buffers[bufferindex].items))
            + ". "
            + str(bufferindex + 1)
            + " of "
            + str(len(buffers)),
            id="buffer_name",
        )


def toggle_mute():
    if buffers[bufferindex].muted == False:
        buffers[bufferindex].muted = True
        speech.speak(f"{buffers[bufferindex].name} muted")
    else:
        buffers[bufferindex].muted = False
        speech.speak(f"{buffers[bufferindex].name} unmuted")


def toggle_interrupt():
    if buffers[bufferindex].interrupt == False:
        buffers[bufferindex].interrupt = True
        speech.speak(f"{buffers[bufferindex].name} interrupting")
    else:
        buffers[bufferindex].interrupt = False
        speech.speak(f"{buffers[bufferindex].name} polite")


def move(dir):
    global bufferindex
    if bufferindex <= 0 and dir == 1:
        speech.speak("Top")
        return
    if bufferindex >= len(buffers) - 1 and dir == 2:
        speech.speak("Bottom")
        return
    newindex = bufferindex - 1 if dir == 1 else bufferindex + 2
    buffers.insert(newindex, buffers[bufferindex])
    if dir == 1:
        buffers.pop(bufferindex + 1)
        bufferindex -= 1
    else:
        buffers.pop(bufferindex)
        bufferindex += 1
    speech.speak(f"{buffers[bufferindex].name} moved to {str(bufferindex + 1)}")


def copy_item():
    pyperclip.copy(buffers[bufferindex].items[buffers[bufferindex].index].text)
    speech.speak("Copied")


def speak_total_item_count():
    items = sum(len(i.items) for i in buffers)
    speech.speak(f"{str(items)} items across {len(buffers)} buffers.")


def get_current_links():
    item = buffers[bufferindex]
    return item.items[item.index].urls


def remove_buffer():
    global bufferindex
    if buffers[bufferindex].permanent == True:
        speech.speak("This buffer is permanent.")
        return
    speech.speak(f"{buffers[bufferindex].name} removed.")
    buffers.remove(buffers[bufferindex])
    bufferindex -= 1


add_buffer("main")
add_buffer("chat")
add_buffer("tell")
add_buffer("players")
