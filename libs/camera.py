from . import consts, movement, options
from .speech import speak


class Camera:
    def __init__(self, game):
        self.game = game
        self.sonar = options.get("sonar", False)
        self.reverb = None
        
        self.soundgroup = self.game.audio_mngr.create_soundgroup(False)
        self.scans = {
            "east": ((), ""),
            "west": ((), ""),
            "north": ((), ""),
            "south": ((), ""),
        }
        self.focus_object = None
        self.currentzone = ""
        self.x = 0.0
        self.y = 0.0
        self.z = 0.0

    def set_focus_object(self, target):
        if self.focus_object:
            if self.focus_object.on_move == self.move:
                self.focus_object.on_move = None
            if self.focus_object.on_turn == self.turn:
                self.focus_object.on_turn = None
        self.focus_object = target
        target.on_move = self.move
        target.on_turn = self.turn
        self.move(target.x, target.y, target.z)
        self.turn(target.hfacing, target.vfacing, target.bfacing)

    def move(self, x, y, z):
        ambiences_to_pause = list(
            self.focus_object.map.get_ambiences_at(self.x, self.y, self.z)
        )
        musics_to_pause = list(
            self.focus_object.map.get_musics_at(self.x, self.y, self.z)
        )
        self.x = x
        self.y = y
        self.z = z
        self.game.audio_mngr.position = (self.x, self.y, self.z)
        self.soundgroup.position = (self.x, self.y, self.z)

        filter = self.game.audio_mngr.gen_filter(
            type="LOWPASS"
        )
        
        def automation_water(value):
            filter.set("GAINHF", value)
            self.game.audio_mngr.apply_filter(filter, self.game.exclude_water, replace=True)
            self.focus_object.vc_source.direct_filter = filter
        
        
        if not self.focus_object.in_water and self.focus_object.map.get_tile_at(self.focus_object.x, self.focus_object.y, self.focus_object.z) == "underwater":
            self.focus_object.play_sound("foley/swim/start/", cat="self")
            self.focus_object.in_water = True
            self.focus_object.drownable = False
            self.focus_object.drown_clock.restart()
            self.game.ignore_others_water = True
            self.focus_object.drown_clock.restart()
            muffling = 0.05 * self.focus_object.depth
            self.game.automate(
                None, None,
                muffling, 500,
                step_callback = automation_water, start_value=1.0
            )
        if self.focus_object.in_water and self.focus_object.map.get_tile_at(self.focus_object.x, self.focus_object.y, self.focus_object.z) != "underwater":
            self.focus_object.play_sound("foley/swim/end/", cat="self")
            muffling = 0.05 * self.focus_object.depth
            self.game.automate(
                None, None,
                1.0, 500,
                step_callback = automation_water, start_value=muffling
            )
            self.focus_object.in_water=False
            self.focus_object.drownable = False
            self.game.ignore_others_water = False
        if round(self.focus_object.depth, 3) != round(self.focus_object.recorded_depth,3) and self.focus_object.in_water:
            muffling = 0.05 * round(self.focus_object.depth,3)
            self.game.automate(
                None, None,
                muffling, 50,
                step_callback = automation_water, start_value=0.05*round(self.focus_object.recorded_depth,3)
            )
            self.focus_object.recorded_depth = round(self.focus_object.depth,3)


        # change reverb if required.
        reverb = self.focus_object.map.get_reverb_at(self.x, self.y, self.z)
        if reverb != self.reverb and not self.focus_object.dead:
            self.reverb = reverb
            if reverb is None:
                self.focus_object.soundgroup.apply_effect(None, 0)
            else:
                self.focus_object.soundgroup.apply_effect(reverb.reverb, 0)
            
        # enter/leave zones
        zone = self.focus_object.map.get_zone_at(self.x, self.y, self.z)
        if zone and zone != self.currentzone:
            speak(f"{zone}")
            self.currentzone = zone
        # enter/leave ambiences
        for i in self.focus_object.map.get_ambiences_at(self.x, self.y, self.z):
            if i in ambiences_to_pause:
                ambiences_to_pause.remove(i)
                if not i.playing:
                    i.enter()
                continue
            i.enter()
        for i in ambiences_to_pause:
            i.leave()
        # enter/leave musics
        for i in self.focus_object.map.get_musics_at(self.x, self.y, self.z):
            if i in musics_to_pause:
                musics_to_pause.remove(i)
                if not i.playing:
                    i.enter()
                continue
            i.enter()
        for i in musics_to_pause:
            i.leave()
        if self.sonar:
            self.scan_around()

    def scan_around(self):
        self.scan_east()
        self.game.call_after(20, self.scan_north)
        self.game.call_after(40, self.scan_west)

    def turn(self, hdeg, vdeg, bdeg=0):
        self.game.audio_mngr.orientation = (hdeg, vdeg, bdeg)

    def scan_north(self):
        dist = self.x, self.y, self.z
        for _ in range(10):
            dist = movement.move(dist, (self.focus_object.hfacing) % 360).get_tuple
            if not self.focus_object.map.in_bound(*dist):
                break
            tile = self.focus_object.map.get_tile_at(*dist)
            scan = self.scans["north"]
            if not tile or tile == "air":
                if scan[0] != dist and scan[1] != "air":
                    self.scans["north"] = dist, "air"
                    self.soundgroup.play(
                        "camera/air.ogg", rel_x=(dist[0] - self.x) / 4, rel_y=(dist[1] - self.y) / 4
                    )
                break

            elif tile.startswith("wall"):
                if scan[0] != dist and scan[1] != "wall":
                    self.scans["north"] = dist, "wall"
                    self.soundgroup.play(
                        "camera/wall.ogg",
                        rel_x=dist[0] - self.x,
                        rel_y=dist[1] - self.y,
                    )
                break

        else:
            if scan[0] != dist and scan[1] != "":
                self.scans["north"] = dist, ""
                self.soundgroup.play(
                    "camera/opening.ogg", rel_x=dist[0] - self.x, rel_y=dist[1] - self.y
                )

    def scan_east(self):
        dist = self.x, self.y, self.z
        for _ in range(10):
            dist = movement.move(dist, (self.focus_object.hfacing + 90) % 360).get_tuple
            if not self.focus_object.map.in_bound(*dist):
                break
            tile = self.focus_object.map.get_tile_at(*dist)
            scan = self.scans["east"]
            if not tile or tile == "air":
                if scan[0] != dist and scan[1] != "air":
                    self.scans["east"] = dist, "air"
                    self.soundgroup.play(
                        "camera/air.ogg", rel_x=dist[0] - self.x, rel_y=dist[1] - self.y
                    )
                break
            elif tile.startswith("wall"):
                if scan[0] != dist and scan[1] != "wall":
                    self.scans["east"] = dist, "wall"
                    self.soundgroup.play(
                        "camera/wall.ogg",
                        rel_x=dist[0] - self.x,
                        rel_y=dist[1] - self.y,
                    )
                break
        else:
            if scan[0] != dist and scan[1] != "":
                self.scans["east"] = dist, ""
                self.soundgroup.play(
                    "camera/opening.ogg", rel_x=dist[0] - self.x, rel_y=dist[1] - self.y
                )

    def scan_west(self):
        dist = self.x, self.y, self.z
        for _ in range(10):
            dist = movement.move(dist, (self.focus_object.hfacing - 90) % 360).get_tuple
            if not self.focus_object.map.in_bound(*dist):
                break
            tile = self.focus_object.map.get_tile_at(*dist)
            scan = self.scans["west"]
            if not tile or tile == "air":
                if scan[0] != dist and scan[1] != "air":
                    self.scans["west"] = dist, "air"
                    self.soundgroup.play(
                        "camera/air.ogg", rel_x=dist[0] - self.x, rel_y=dist[1] - self.y
                    )
                break
            elif tile.startswith("wall"):
                if scan[0] != dist and scan[1] != "wall":
                    self.scans["west"] = dist, "wall"
                    self.soundgroup.play(
                        "camera/wall.ogg",
                        rel_x=dist[0] - self.x,
                        rel_y=dist[1] - self.y,
                    )
                break
        else:
            if scan[0] != dist and scan[1] != "":
                self.scans["west"] = dist, ""
                self.soundgroup.play(
                    "camera/opening.ogg", rel_x=dist[0] - self.x, rel_y=dist[1] - self.y
                )
