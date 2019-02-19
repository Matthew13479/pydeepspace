from components.hatch import Hatch
from magicbot import StateMachine, state, timed_state


class HatchController(StateMachine):
    hatch: Hatch

<<<<<<< HEAD
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
        





=======
    def punch(self, force=False):
        self.engage(force=force)

    @state(first=True, must_finish=True)
    def punching(self):
        self.hatch.punch()
        self.next_state("retracting")

    @timed_state(must_finish=True, duration=1.2)
    def retracting(self, state_tm):
        if state_tm > 1:
            self.hatch.retract()
            self.done()
>>>>>>> hatch
