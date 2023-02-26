def convert_autotruck_path_to_trajectory(autotruck_path):
    steps = autotruck_path['payload']['tasks'][0]['payload']['operations'][0]['payload']['data_payload']['steps']
    orientation_head = 0;  trajectory=[]

    for step in steps:
        parts = step['step']['vehicles']
        head = parts[0]['vehicle']
        x = head['position'][0]
        y = head['position'][1]
        orientation_head = head['orientation']
        orientations = [orientation_head]

        if len(parts) > 1:
            for ind in range(1, len(parts)):
                part = parts[ind]['vehicle']
                orientations.append(part['orientation'])

        trajectory.append({"x":x, "y":y, "orientations":orientations, "time":None})

    return trajectory



def get_destination_from_assignment(assignment_body):
    destination = None
    if 'destination' in assignment_body:
        destination = assignment_body.get('destination', None)
    else:
        xf = assignment_body.get('x', None)
        yf = assignment_body.get('y', None)
        orientationsf = assignment_body.get('orientations',[0])
        if xf and yf: destination = {'x': xf, 'y': yf, 'orientations': orientationsf}
    return destination
