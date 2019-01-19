from components.hatch import Hatch
from magicbot import StateMachine, state, timed_state


class HatchController(StateMachine):
    hatch: Hatch

    def start_match(self):
        """Initialise the hatch system at the start of the match."""
        self.engage()
    
    @timed_state(must_finish=True, duration=0.1, next_state="retracting")
    def punching(self):
        self.hatch.punch()

    @state(must_finish=True)
    def retracting(self):
        self.hatch.retract()
        self.done()
        





