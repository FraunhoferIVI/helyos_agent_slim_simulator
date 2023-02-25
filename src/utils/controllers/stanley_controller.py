"""

Path tracking simulation with Stanley steering control and PID speed control.

author: Atsushi Sakai (@Atsushi_twi)
https://github.com/AtsushiSakai/PythonRobotics/blob/master/PathTracking/stanley_controller/stanley_controller.py

Ref:
    - [Stanley: The robot that won the DARPA grand challenge](http://isl.ecst.csuchico.edu/DOCS/darpa2005/DARPA%202005%20Stanley.pdf)
    - [Autonomous Automobile Path Tracking](https://www.ri.cmu.edu/pub_files/2009/2/Automatic_Steering_Methods_for_Autonomous_Automobile_Path_Tracking.pdf)

"""
import numpy as np
import sys
import pathlib
import os
sys.path.append(str(pathlib.Path(__file__).parent.parent.parent))


k = float(os.environ.get("STANLEY_K", 0.5))     # control gain
Kp = float(os.environ.get("STANLEY_KP", 1.0))  # speed proportional gain
dt = 0.1  # [s] time difference
L = float(os.environ.get("STANLEY_L", 2.9))  # [m] Wheel base of vehicle
max_steer = float(os.environ.get("STANLEY_MAXSTEER", 30.0)) # [rad] max steering angle




class State(object):
    """
    Class representing the state of a vehicle.

    :param x: (float) x-coordinate
    :param y: (float) y-coordinate
    :param yaw: (float) yaw angle
    :param v: (float) speed
    """

    def __init__(self, x=0.0, y=0.0, yaw=0.0, v=0.0):
        """Instantiate the object."""
        super(State, self).__init__()
        self.x = x
        self.y = y
        self.yaw = yaw
        self.v = v

    def update(self, acceleration, delta):
        """
        Update the state of the vehicle.

        Stanley Control uses bicycle model.

        :param acceleration: (float) Acceleration
        :param delta: (float) Steering
        """
        delta = np.clip(delta, -max_steer, max_steer)

        self.x += self.v * np.cos(self.yaw) * dt
        self.y += self.v * np.sin(self.yaw) * dt
        self.yaw += self.v / L * np.tan(delta) * dt
        self.yaw = normalize_angle(self.yaw)
        self.v += acceleration * dt


def pid_control(target, current):
    """
    Proportional control for the speed.

    :param target: (float)
    :param current: (float)
    :return: (float)
    """
    return Kp * (target - current)


def stanley_control(state, cx, cy, cyaw, last_target_idx):
    """
    Stanley steering control.

    :param state: (State object)
    :param cx: ([float])
    :param cy: ([float])
    :param cyaw: ([float])
    :param last_target_idx: (int)
    :return: (float, int)
    """
    current_target_idx, error_front_axle = calc_target_index(state, cx, cy)

    if last_target_idx >= current_target_idx:
        current_target_idx = last_target_idx

    # theta_e corrects the heading error
    theta_e = normalize_angle(cyaw[current_target_idx] - state.yaw)
    # theta_d corrects the cross track error
    theta_d = np.arctan2(k * error_front_axle, state.v)
    # Steering control
    delta = theta_e + theta_d

    return delta, current_target_idx


def normalize_angle(angle):
    """
    Normalize an angle to [-pi, pi].

    :param angle: (float)
    :return: (float) Angle in radian in [-pi, pi]
    """
    while angle > np.pi:
        angle -= 2.0 * np.pi

    while angle < -np.pi:
        angle += 2.0 * np.pi

    return angle


def calc_target_index(state, cx, cy):
    """
    Compute index in the trajectory list of the target.

    :param state: (State object)
    :param cx: [float]
    :param cy: [float]
    :return: (int, float)
    """
    # Calc front axle position
    fx = state.x + L * np.cos(state.yaw)
    fy = state.y + L * np.sin(state.yaw)

    # Search nearest point index
    dx = [fx - icx for icx in cx]
    dy = [fy - icy for icy in cy]
    d = np.hypot(dx, dy)
    target_idx = np.argmin(d)

    # Project RMS error onto front axle vector
    front_axle_vec = [-np.cos(state.yaw + np.pi / 2),
                      -np.sin(state.yaw + np.pi / 2)]
    error_front_axle = np.dot([dx[target_idx], dy[target_idx]], front_axle_vec)

    return target_idx, error_front_axle


def calculate_steering_trajectory(x0,y0, orientations0, target_trajectory, target_speed=5):
    """Plot an example of Stanley steering control on a cubic spline.
    :param x0: float (mm)
    :param y0: float (mm)
    :param orientation0: [float] (mrad) 
    :return: (Trajectory)
    """
    #  target course
    cx, cy, cyaw = [], [], []

    print("* parsing trajectory")

    for step in target_trajectory:
        cx.append(step['x']/1000)
        cy.append(step['y']/1000)
        cyaw.append(step['orientations'][0]/1000)
    max_simulation_time = 100.0

    # Initial state
    print("* define initial state")
    state = State(x=x0/1000, y=y0/1000, yaw=orientations0[0]/1000, v=0.0)

    orientations = orientations0
    last_idx = len(cx) - 1
    time = 0.0

    actual_trajectory = []
    target_idx, _ = calc_target_index(state, cx, cy)
    while max_simulation_time >= time and last_idx > target_idx:
        ai = pid_control(target_speed, state.v)
        di, target_idx = stanley_control(state, cx, cy, cyaw, target_idx)
        state.update(ai, di)
        time += dt
        orientations[0] = state.yaw*1000
        orientations = [*orientations]

        drive_step =    {"x": state.x*1000,
                        "y": state.y*1000,
                        "orientations": orientations,
                        "time": time,
                        "velocity": state.v
                        }
        actual_trajectory.append(drive_step)
        
    
    return actual_trajectory
