import wpilib
import ctre


class Hatch:
    top_puncher: wpilib.Solenoid
    left_puncher: wpilib.Solenoid
    right_puncher: wpilib.Solenoid

    self.all_limit_switch = self.top_limit_switch or self.left_limit_switch or self.right_limit_switch

    def __init__(self):
        self.punch_on = False
        self.retracter = True
        self.last_puncher = None
        self.last_retracter = None

    def setup(self):
        """This is called after variables are injected by magicbot."""

    def on_enable(self):
        """This is called whenever the robot transitions to being enabled."""
        self.last_puncher = None
        self.last_retracter = None

    def execute(self):
        """Run at the end of every control loop iteration."""
        if self.last_puncher != self.punch_on:
            self.top_puncher.set(self.punch_on)
            self.left_puncher.set(self.punch_on)
            self.right_puncher.set(self.punch_on)

            self.last_puncher = self.punch_on

    def punch(self):
        self.punch_on = True

    def retract(self):
        self.punch_on = False

    def toggle_puncher(self):
        self.punch_on = not self.punch_on
        
    def hatch_in(self):
        if self.all_limit_switch.get() = True:
            return True
        else:
            return False
            


