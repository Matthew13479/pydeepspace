#!/usr/bin/env python3

import magicbot
import wpilib

from automations.hatch import HatchController
from components.hatch import Hatch


class Robot(magicbot.MagicRobot):

    hatch: Hatch

    def createObjects(self):
        """Create motors and stuff here."""
        self.top_puncher = wpilib.Solenoid(0)
        self.left_puncher = wpilib.Solenoid(1)
        self.right_puncher = wpilib.Solenoid(2)
        self.actuator_arm = wpilib.Solenoid(3)

        self.joystick = wpilib.Joystick(0)
        self.gamepad = wpilib.XboxController(1)

    def teleopInit(self):
        """Initialise driver control."""
        pass

    def teleopPeriodic(self):
        """Allow the drivers to control the robot."""
        if self.gamepad.getBButtonPressed():
            self.hatch.punch()

        if self.gamepad.getAButtonPressed():
            self.hatch.retract()


if __name__ == "__main__":
    wpilib.run(Robot)
