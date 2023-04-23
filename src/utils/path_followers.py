

from utils.controllers.stanley_controller import calculate_steering_trajectory


def ideal_path_follower(target_trajectory):    
    trajectory = target_trajectory
    return trajectory


def stanley_path_follower(pose0, target_trajectory):
    x0 = pose0['x']    
    y0 = pose0['y']
    orientations0 = pose0['orientations']

    print("========= using stanely controller =========")
    try:
        trajectory = calculate_steering_trajectory(x0, y0, orientations0, target_trajectory)
    except Exception as E:
        print("========= fail in stanely controller =========")
        print(E)
        raise Exception(E)


    return trajectory


def straight_path_to_destination(pose0, destination):
    """  Vehicle simple simulator to be used for the assignment execution.
         It drives straightly to the destination; it interpolates a fixed number of points between origin and destine.
    """
    trajectory = []
    x0 = pose0['x']    
    y0 = pose0['y']
    orientations0 = pose0['orientations']
    
    for d in range(0, 10, 1):
        p = d/10
        x = (1-p)*x0 + (p)*destination['x']
        y = (1-p)*y0 + (p)*destination['y']
        orientation_head = (1-p)*orientations0[0] + (p)*destination['orientations'][0]

        trajectory.append({"x":x, "y":y, "orientations":[orientation_head, 0], "time":None})
        
    return trajectory