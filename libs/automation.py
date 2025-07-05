class Automation_Task():
    def __init__(self, game, obj, attribute, target_value, time, callback=None, time_step=20, step_callback=None, start_value=None, cancelable=True):
        self.game = game
        self.object = obj
        self.attribute = attribute
        self.cancelable = cancelable
        try: self.start_value = getattr(self.object, self.attribute)
        except: self.start_value = start_value
        self.target_value = target_value
        self.time = time
        try: self.increment = (self.target_value - self.start_value) / self.time
        except: self.increment = 0
        self.timer = self.game.new_clock()
        self.time_step = time_step
        self.callback = callback
        self.step_callback = step_callback
        try: self.current_value = getattr(self.object, self.attribute, self.start_value)
        except: self.current_value = self.start_value
    
    def loop(self):
        if self.timer.elapsed >= self.time_step:
            val_change = self.increment * self.time_step
            if val_change == 0.0: return
            try: val = getattr(self.object, self.attribute, self.current_value)
            except: val = self.current_value
            if val +val_change <= self.target_value and self.increment<0 or val + val_change >= self.target_value and self.increment>0: 
                try: setattr(self.object, self.attribute, self.target_value)
                except: pass
                self.current_value=self.target_value
                if self.step_callback is not None: self.step_callback(self.current_value)
                if self.callback is not None: self.callback()
                self.game.automations.pop(
                    self.game.automations.index(self)
                )
                del self.timer
                del self
                return
            try: setattr(self.object, self.attribute, val+val_change)
            except: pass
            self.current_value=val+val_change
            if val_change == 0: return
            self.timer.restart()
            if self.step_callback is not None: self.step_callback(self.current_value)