import platform
from . import consts


def get_os():
    system = platform.system()
    if system == "Darwin":
        return consts.OS_MAC
    elif system == "Windows":
        return consts.OS_WINDOWS
    elif system == "Linux":
        return consts.OS_LINUX
