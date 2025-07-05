import os
import shutil
import random


def random_item(dir):
    """return a random item (a folder or a ffile) given a folder path.
    if the path given doesnt lead to a folder, returns the given path"""
    try: return f"{dir}/{random.choice(os.listdir(dir))}" if os.path.isdir(dir) else dir
    except IndexError as e: 
        print(e)
        return ""


def copy_folder(src, dst):
    """
    Copy all files and folders from src to dst, overwriting existing files and folders in dst
    """
    if not src.endswith("/") and not src.endswith("\\"):
        src = src + "/"
    if not dst.endswith("/") and not dst.endswith("\\"):
        dst = dst + "/"

    for src_dir, dirs, files in os.walk(src):
        dst_dir = src_dir.replace(src, dst, 1)
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
        for file_ in files:
            src_file = os.path.join(src_dir, file_)
            dst_file = os.path.join(dst_dir, file_)
            if os.path.exists(dst_file):
                # in case of the src and dst are the same file
                if os.path.samefile(src_file, dst_file):
                    continue
                os.remove(dst_file)
            shutil.copy(src_file, dst_dir)
