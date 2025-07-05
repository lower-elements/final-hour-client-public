import contextlib
import traceback

class Object:
    def __init__(self, game, map, x, y, z, radius=0.5):
        self.game = game
        self.map = map
        self.x = x
        self.y = y
        self.z = z
        self.radius = radius
        self.falling = False
        self.player=False
        self.fall_time = 80
        self.fall_clock = game.new_clock()
        self.soundgroup = self.game.audio_mngr.create_soundgroup(radius=radius)
        self.soundgroup.position = (x, y, z)

    def play_sound(
        self, sound, looping=False, cat="miscelaneous", id="", rel_x=0, rel_y=0, rel_z=0, volume=100
    ):
        try:
            return self.soundgroup.play(
                sound,
                looping=looping,
                cat= cat,
                id=id,
                rel_x=rel_x,
                rel_y=rel_y,
                rel_z = rel_z,
                volume=volume
            )
        except Exception as e:
            print("\a", e)
            traceback.print_exc()

    def play_sound_dist(
        self, sound, looping=False, volume=100, id="", rel_x=0, rel_y=0, rel_z=0, cat="miscelaneous"
    ):
        try:
            return self.soundgroup.play(
                sound,
                looping=looping,
                cat=cat,
                id=id,
                rel_x=rel_x,
                rel_y=rel_y,
                rel_z=rel_z,
                dist=True,
                volume=volume
            )
        except Exception as e:
            print("\a", e)
            traceback.print_exc()

    def on_hit(self, object, hp):
        pass

    def on_interact(self, object):
        pass

    def loop(self):
        pass


    def destroy(self):
        self.soundgroup.destroy()
