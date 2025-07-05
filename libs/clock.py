class Clock:
    def __init__(self):
        self.elapsed = 0
        self.paused = False

    def update(self, delta):
        if not self.paused:
            self.elapsed += delta

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def restart(self):
        self.elapsed = 0
