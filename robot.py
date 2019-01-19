#!/usr/bin/env python3

import magicbot
import wpilib
import ctre
from automations.hatch import HatchController
from components.hatch import Hatch


class Robot(magicbot.MagicRobot):

    hatch: Hatch
    hatch_controller: HatchController

    def createObjects(self):
        """Create motors and stuff here."""
        self.top_puncher = wpilib.Solenoid(0)
        self.left_puncher = wpilib.Solenoid(1)
        self.right_puncher = wpilib.Solenoid(2)
        self.actuator_arm = ctre.TalonSRX(3)

        self.joystick = wpilib.Joystick(0)
        self.gamepad = wpilib.XboxController(1)
        self.top_limit_switch = wpilib.DigitalInput(1)
        self.left_limit_switch = wpilib.DigitalInput(2)
        self.right_limit_switch = wpilib.DigitalInput(3)

    def teleopInit(self):
        """Initialise driver control."""
        pass

    def teleopPeriodic(self):
        """Allow the drivers to control the robot."""
        if self.gamepad.getBButtonPressed():
            self.hatch_controller.punching()

        if self.gamepad.getBButtonReleased():
            self.hatch_controller.retracting()

        if self.gamepad.getXButtonPressed():
            self.hatch.toggle_puncher()


if __name__ == "__main__":
    wpilib.run(Robot)
