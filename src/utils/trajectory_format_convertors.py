def convert_autotruck_path_to_trajectory(autotruck_path):
    steps = autotruck_path['payload']['tasks'][0]['payload']['operations'][0]['payload']['data_payload']['steps']
    orientation_head = 0; orientation_trailer = 0;  trajectory=[]

    for step in steps:
        parts = step['step']['vehicles']
        head = parts[0]['vehicle']
        x = head['position'][0]
        y = head['position'][1]
        orientation_head = head['orientation']
        if len(parts) > 1:
            trailer = parts[1]['vehicle']
            orientation_trailer = trailer['orientation']

        trajectory.append({"x":x, "y":y, "orientations":[orientation_head, orientation_trailer], "time":None})

    return trajectory


