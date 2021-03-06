#!/usr/bin/env python3
import enum
import math

import rev
import ctre
import magicbot
import wpilib
from networktables import NetworkTables

from automations.alignment import (
    HatchIntakeAligner,
    HatchDepositAligner,
    CargoDepositAligner,
)
from automations.cargo import CargoManager
from components.cargo import Arm, Intake
from components.hatch import Hatch
from automations.climb import ClimbAutomation
from components.vision import Vision
from components.climb import Climber
from pyswervedrive.chassis import SwerveChassis
from pyswervedrive.module import SwerveModule
from utilities.functions import constrain_angle, rescale_js
from utilities.navx import NavX

ROCKET_ANGLE = 0.52  # measured field angle


class FieldAngle(enum.Enum):
    CARGO_FRONT = 0
    CARGO_RIGHT = math.pi / 2
    CARGO_LEFT = -math.pi / 2
    LOADING_STATION = math.pi
    ROCKET_LEFT_FRONT = ROCKET_ANGLE
    ROCKET_RIGHT_FRONT = -ROCKET_ANGLE
    ROCKET_LEFT_BACK = math.pi - ROCKET_ANGLE
    ROCKET_RIGHT_BACK = -math.pi + ROCKET_ANGLE

    @classmethod
    def closest(cls, robot_heading: float) -> "FieldAngle":
        return min(cls, key=lambda a: abs(constrain_angle(robot_heading - a.value)))


class Robot(magicbot.MagicRobot):
    # Declare magicbot components here using variable annotations.
    # NOTE: ORDER IS IMPORTANT.
    # Any components that actuate objects should be declared after
    # any higher-level components (automations) that depend on them.

    # Automations
    cargo: CargoManager
    cargo_deposit: CargoDepositAligner
    climb_automation: ClimbAutomation
    hatch_deposit: HatchDepositAligner
    hatch_intake: HatchIntakeAligner

    # Actuators
    arm: Arm
    chassis: SwerveChassis
    hatch: Hatch
    intake: Intake

    climber: Climber

    vision: Vision

    offset_rotation_rate = 20

    def createObjects(self):
        """Create motors and stuff here."""

        # a + + b - + c - - d + -
        x_dist = 0.2625
        y_dist = 0.2165
        self.module_a = SwerveModule(  # front right module
            "a",
            steer_talon=ctre.TalonSRX(3),
            drive_talon=ctre.TalonSRX(4),
            x_pos=x_dist,
            y_pos=y_dist,
            reverse_drive_encoder=True,
            reverse_drive_direction=True,
        )
        self.module_b = SwerveModule(  # front left module
            "b",
            steer_talon=ctre.TalonSRX(5),
            drive_talon=ctre.TalonSRX(6),
            x_pos=-x_dist,
            y_pos=y_dist,
        )
        self.module_c = SwerveModule(  # bottom left module
            "c",
            steer_talon=ctre.TalonSRX(1),
            drive_talon=ctre.TalonSRX(2),
            x_pos=-x_dist,
            y_pos=-y_dist,
        )
        self.module_d = SwerveModule(  # bottom right module
            "d",
            steer_talon=ctre.TalonSRX(7),
            drive_talon=ctre.TalonSRX(8),
            x_pos=x_dist,
            y_pos=-y_dist,
        )
        self.imu = NavX()

        self.sd = NetworkTables.getTable("SmartDashboard")
        wpilib.SmartDashboard.putData("Gyro", self.imu.ahrs)

        # hatch objects
        self.hatch_bottom_puncher = wpilib.Solenoid(0)
        self.hatch_left_puncher = wpilib.Solenoid(1)
        self.hatch_right_puncher = wpilib.Solenoid(2)

        self.hatch_left_limit_switch = wpilib.DigitalInput(8)
        self.hatch_right_limit_switch = wpilib.DigitalInput(9)

        self.climber_front_motor = rev.CANSparkMax(10, rev.MotorType.kBrushless)
        self.climber_back_motor = rev.CANSparkMax(11, rev.MotorType.kBrushless)
        self.climber_front_podium_switch = wpilib.DigitalInput(4)
        self.climber_back_podium_switch = wpilib.DigitalInput(5)
        self.climber_drive_motor = ctre.TalonSRX(20)
        self.climber_solenoid = wpilib.DoubleSolenoid(
            forwardChannel=4, reverseChannel=5
        )

        # cargo related objects
        self.intake_motor = ctre.TalonSRX(9)
        self.intake_switch = wpilib.DigitalInput(0)

        # boilerplate setup for the joystick
        self.joystick = wpilib.Joystick(0)
        self.gamepad = wpilib.XboxController(1)

        self.spin_rate = 2.5

    def disabledPeriodic(self):
        self.chassis.set_inputs(0, 0, 0)
        self.imu.resetHeading()
        self.vision.execute()  # Keep the time offset calcs running

    def teleopInit(self):
        """Initialise driver control."""
        self.chassis.set_inputs(0, 0, 0)

    def teleopPeriodic(self):
        """Allow the drivers to control the robot."""
        # self.chassis.heading_hold_off()

        throttle = max(0.1, (1 - self.joystick.getThrottle()) / 2)  # min 10%
        self.sd.putNumber("joy_throttle", throttle)

        # this is where the joystick inputs get converted to numbers that are sent
        # to the chassis component. we rescale them using the rescale_js function,
        # in order to make their response exponential, and to set a dead zone -
        # which just means if it is under a certain value a 0 will be sent
        # TODO: Tune these constants for whatever robot they are on
        joystick_vx = -rescale_js(
            self.joystick.getY(), deadzone=0.1, exponential=1.5, rate=4 * throttle
        )
        joystick_vy = -rescale_js(
            self.joystick.getX(), deadzone=0.1, exponential=1.5, rate=4 * throttle
        )
        joystick_vz = -rescale_js(
            self.joystick.getZ(), deadzone=0.2, exponential=20.0, rate=self.spin_rate
        )
        joystick_hat = self.joystick.getPOV()

        self.sd.putNumber("joy_vx", joystick_vx)
        self.sd.putNumber("joy_vy", joystick_vy)
        self.sd.putNumber("joy_vz", joystick_vz)

        # Allow big stick movements from the driver to break out of an automation
        if abs(joystick_vx) > 0.5 or abs(joystick_vy) > 0.5:
            self.hatch_intake.done()
            self.hatch_deposit.done()
            self.cargo_deposit.done()

        if not self.chassis.automation_running:
            if joystick_vx or joystick_vy or joystick_vz:
                self.chassis.set_inputs(
                    joystick_vx,
                    joystick_vy,
                    joystick_vz,
                    field_oriented=not self.joystick.getRawButton(6),
                )
            else:
                self.chassis.set_inputs(0, 0, 0)

            if joystick_hat != -1:
                if self.intake.has_cargo:
                    constrained_angle = -constrain_angle(
                        math.radians(joystick_hat) + math.pi
                    )
                else:
                    constrained_angle = -constrain_angle(math.radians(joystick_hat))
                self.chassis.set_heading_sp(constrained_angle)

        # Starts Hatch Alignment and Cargo State Machines
        if (
            self.joystick.getTrigger()
            or self.gamepad.getTriggerAxis(self.gamepad.Hand.kLeft) > 0.5
            or self.gamepad.getTriggerAxis(self.gamepad.Hand.kRight) > 0.5
        ):
            angle = FieldAngle.closest(self.imu.getAngle())
            self.logger.info("closest field angle: %s", angle)
            if angle is FieldAngle.LOADING_STATION:
                self.hatch_intake.engage()
            else:
                self.hatch_deposit.engage()
            self.chassis.set_heading_sp(angle.value)

        # Hatch Manual Fire/Retract
        if self.joystick.getRawButtonPressed(5):
            self.hatch.punch()
            self.hatch.clear_to_retract = True

        # Manual Retraction of both climb legs
        if self.gamepad.getXButtonPressed():
            self.climber.retract_all()

        # Stops Cargo Intake Motor
        if self.gamepad.getBackButtonPressed():
            self.intake.stop()

        # Cargo Floor Intake
        if (
            self.gamepad.getAButtonPressed()
            or self.joystick.getRawButtonPressed(3)
        ):
            self.cargo.intake_floor()

        # Cargo Loading Station Intake
        if self.gamepad.getYButtonPressed():
            self.cargo.intake_depot()

        # Toggles the Heading Hold
        if self.joystick.getRawButtonPressed(8):
            if self.chassis.hold_heading:
                self.chassis.heading_hold_off()
            else:
                self.chassis.heading_hold_on()

        # Resets the IMU's Heading
        if self.joystick.getRawButtonPressed(7):
            self.imu.resetHeading() 

        # Start Button starts Climb State Machine
        if self.gamepad.getStartButtonPressed():
            self.climb_automation.start_climb_lv3()

        # Back Button Ends Climb State Machine
        if self.gamepad.getBackButtonPressed():
            self.climb_automation.done()

    def robotPeriodic(self):
        super().robotPeriodic()
        for module in self.chassis.modules:
            self.sd.putNumber(
                module.name + "_pos_steer",
                module.steer_motor.getSelectedSensorPosition(0),
            )
            self.sd.putNumber(
                module.name + "_pos_drive",
                module.drive_motor.getSelectedSensorPosition(0),
            )
            self.sd.putNumber(
                module.name + "_drive_motor_reading",
                module.drive_motor.getSelectedSensorVelocity(0)
                * 10  # convert to seconds
                / module.drive_counts_per_metre,
            )
        self.sd.putBoolean("heading_hold", self.chassis.hold_heading)

    def testPeriodic(self):
        self.vision.execute()  # Keep the time offset calcs running

        joystick_vx = -rescale_js(
            self.joystick.getY(), deadzone=0.1, exponential=1.5, rate=0.5
        )
        self.sd.putNumber("joy_vx", joystick_vx)
        for button, module in zip((5, 3, 4, 6), self.chassis.modules):
            if self.joystick.getRawButton(button):
                module.store_steer_offsets()
                module.steer_motor.set(ctre.ControlMode.PercentOutput, joystick_vx)
                if self.joystick.getTriggerPressed():
                    module.steer_motor.set(
                        ctre.ControlMode.Position,
                        module.steer_motor.getSelectedSensorPosition(0)
                        + self.offset_rotation_rate,
                    )
                if self.joystick.getRawButtonPressed(2):
                    module.steer_motor.set(
                        ctre.ControlMode.Position,
                        module.steer_motor.getSelectedSensorPosition(0)
                        - self.offset_rotation_rate,
                    )

        if self.joystick.getRawButtonPressed(8):
            for module in self.chassis.modules:
                module.drive_motor.set(ctre.ControlMode.PercentOutput, 0.3)

        if self.joystick.getRawButtonPressed(12):
            for module in self.chassis.modules:
                module.steer_motor.set(
                    ctre.ControlMode.Position, module.steer_enc_offset
                )

        if self.gamepad.getStartButtonPressed():
            self.climber.retract_all()
        if self.gamepad.getBackButtonPressed():
            self.climber.stop_all()


if __name__ == "__main__":
    wpilib.run(Robot)
