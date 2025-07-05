# map parser.
from .speech import speak
from . import data_parser


class Map_parser:
    def __init__(self, game, world_map):
        self.game = game
        self.mapobj = world_map
        self.map_data = ""

    def load(self, data: dict, destroy_entities=True):
        try:
            self.mapobj.destroy(destroy_entities)
        except Exception as e:
            print(e)
        self.map_data = data
        self.mapobj.minx = data["minx"]
        self.mapobj.miny = data["miny"]
        self.mapobj.minz = data["minz"]
        self.mapobj.maxx = data["maxx"]
        self.mapobj.maxy = data["maxy"]
        self.mapobj.maxz = data["maxz"]
        for element in data["elements"]:
            key = element["type"]
            if hasattr(self.mapobj, f"spawn_{key}"):
                try:
                    getattr(self.mapobj, f"spawn_{key}")(**element["data"])
                except Exception  as e:
                    print(e)
                    speak(f"Map Error: {e}")
