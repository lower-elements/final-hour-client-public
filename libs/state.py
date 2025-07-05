import contextlib
from .speech import speak

class State: 
    def __init__(self, game, parrent = None, ): 
        self.game = game
        self.parrent = parrent
        self.substates = []
    def enter(self): 
        for i in self.substates: 
            if isinstance(i, State): 
                i.enter()
    def update(self, events): 
        should_block = False
        if len(self.substates) > 0:
            substate = self.substates[-1]
            if isinstance(substate, State): 
                should_block = substate.update(events)
            elif callable(substate): 
                #stateless function.
                should_block = substate()
        return should_block
    def exit(self): 
        for i in self.substates: 
            if isinstance(i, State): 
                i.exit()
    def add_substate(self, substate): 
        if isinstance(substate, State): 
            substate.enter()
        self.substates.append(substate)
        return substate
    def pop_last_substate(self): 
        with contextlib.suppress(IndexError): 
            substate = self.substates.pop()
            if isinstance(substate, State): 
                substate.exit()
            return substate
    def replace_last_substate(self, substate): 
        self.pop_last_substate()
        return self.add_substate(substate)
    def cancel(self, message="Canceled."):
        self.pop_last_substate()
        speak(message)