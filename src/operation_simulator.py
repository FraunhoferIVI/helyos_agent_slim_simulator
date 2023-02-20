

from helyos_agent_sdk.models import AssignmentCurrentStatus, AGENT_STATE, AgentCurrentResources, ASSIGNMENT_STATUS
import time, math, random, os


# Thread-safe messaging mechanism
# from MockROSCommunication import MockROSCommunication
# driving_operation_ros =  MockROSCommunication('driving_operation_ros')       
# position_sensor_ros = MockROSCommunication('position_sensor_ros')  
# vehi_state_ros = MockROSCommunication('vehi_state_ros')  
# current_assignment_ros = MockROSCommunication('current_assignment_ros')  

VELOCITY = float(os.environ.get('VELOCITY', 2.8)) # 2.8m/s ~ 10 kM/hour


def assignment_execution_local_simulator(inst_assignment_msg, path_algorithm,
                                         current_assignment_ros, 
                                         vehi_state_ros, position_sensor_ros, driving_operation_ros):
    """ Assignment simulator wrapper """
    
    assignment_metadata = inst_assignment_msg.assignment_metadata
    assignment_body = inst_assignment_msg.body
    destination = None
    
    if 'destination' in assignment_body:
        destination = assignment_body.get('destination', None)
    else:
        xf = assignment_body.get('x', None)
        yf = assignment_body.get('y', None)
        orientationsf = assignment_body.get('orientations', [0,0])
        if xf and yf: destination = {'x': xf, 'y': yf, 'orientations': orientationsf}
    
    
    
    try:
        current_assignment_ros.publish({'id':assignment_metadata.id, 'status':ASSIGNMENT_STATUS.EXECUTING})
        vehi_state_ros.publish({"agent_state": AGENT_STATE.BUSY})

        print(" <= assignment is executing")
        
        if path_algorithm == "fixed":
            operation_finished = driving_fixed(driving_operation_ros, position_sensor_ros)
            
        if path_algorithm == "straight_to_destination":
            operation_finished = drive_straigth(driving_operation_ros, position_sensor_ros, destination)

        if path_algorithm == "IVI-stepped-path":
            path = assignment_body
            operation_finished = drive_ivi_stepped(driving_operation_ros, position_sensor_ros, path)

        if operation_finished:
            
            print(" * operation concluded")
            
            current_assignment_ros.publish({'id':assignment_metadata.id, 'status':ASSIGNMENT_STATUS.SUCCEEDED})
            vehi_state_ros.publish({"agent_state": AGENT_STATE.READY})
            
            print(" <= assignment suceeded")
            
        else:
            
            print(" * operation interrupted")
            
            current_assignment_ros.publish({'id':assignment_metadata.id, 'status':ASSIGNMENT_STATUS.CANCELED})
            vehi_state_ros.publish({"agent_state": AGENT_STATE.FREE})

            print(" <= assignment canceled")

        
    except Exception as e:
        
        current_assignment_ros.publish({'id':assignment_metadata.id, 'status':ASSIGNMENT_STATUS.FAILED})
        vehi_state_ros.publish({"agent_state": AGENT_STATE.FREE}) 
                                                                       
        print(" <= assignment failed", e)
    

    
def drive_ivi_stepped(driving_operation_ros, position_sensor_ros, path):
    """  Vehicle simple simulator to be used for the assignment execution.
         It folows the IVI-step data format used by the trucktrix planner.
         Note that this function communicates by writing the hard drive.
    """
    FORCE_FAIL_SIMULATOR = False

    steps = path['payload']['tasks'][0]['payload']['operations'][0]['payload']['data_payload']['steps']
    positions = []; orientations_head = []; orientations_trailer = [];
    for step in steps:
        parts = step['step']['vehicles']
        head = parts[0]['vehicle']
        positions.append(head['position'])
        orientations_head.append(head['orientation'])

        if len(parts) > 1:
            trailer = parts[1]['vehicle']
            orientations_trailer.append(trailer['orientation'])

    for d in range(0, len(steps), 1):
        x = positions[d][0]    
        y = positions[d][1]
        orientations = [orientations_head[d], orientations_trailer[d]]


        try:
            STOP_SIMULATOR = driving_operation_ros.read().get("CANCEL_DRIVING", False)
            if STOP_SIMULATOR:
                print("CANCEL_DRIVING", STOP_SIMULATOR)
                driving_operation_ros.publish({"CANCEL_DRIVING":False})
                return False

            if FORCE_FAIL_SIMULATOR: raise "error"

            sensors = { 'helyos_agent_control':{},
                        'temperatures':{
                                        'sensor_1': {
                                            'title':"cabine",
                                            'type' :"number",
                                            'value':random.randint(20,40),
                                            'unit': "oC"}
                                         }
                      }    

            position_sensor_ros.publish({"x":x, "y":y, "z":0, "orientations":orientations, "sensors":sensors})


            if d<len(steps)-1:
                xs = positions[d+1][0];  ys = positions[d+1][1]  
                ds = math.sqrt((xs - x)**2 + (ys - y)**2)/1000 # meters  
                dt = ds/VELOCITY
                time.sleep(dt)
            else:
                time.sleep(1)

            print("driven distance")
            print("<= publish sensor", f"{d}%")   


        except  Exception as e:
            print("e", e)


    return True    



def drive_straigth(driving_operation_ros, position_sensor_ros,destination):
    """  Vehicle simple simulator to be used for the assignment execution.
         It drives straightly to the destination; it interpolates a fixed number of points between origin and destine.
         Note that this function communicates by writing the hard drive.
    """
    FORCE_FAIL_SIMULATOR = False
    pose = position_sensor_ros.read()
    x0 = pose['x']    
    y0 = pose['y']
    orientations0 = pose['orientations']
    
    print("driven distance")
    for d in range(0, 10, 1):
        time.sleep(1)
        p = d/10
        x = (1-p)*x0 + (p)*destination['x']
        y = (1-p)*y0 + (p)*destination['y']
        o = (1-p)*orientations0[0] + (p)*destination['orientations'][0]
        orientations = [o, 0]
        print("<= publish sensor", f"{d}%")
        try:
            STOP_SIMULATOR = driving_operation_ros.read().get("CANCEL_DRIVING", False)
            if STOP_SIMULATOR:
                print("CANCEL_DRIVING", STOP_SIMULATOR)
                driving_operation_ros.publish({"CANCEL_DRIVING":False})
                return False
            
            if FORCE_FAIL_SIMULATOR: raise "error"

            sensors = { 'helyos_agent_control':{},
                        'temperatures':{
                                        'sensor_1': {
                                            'title':"cabine",
                                            'type' :"number",
                                            'value':random.randint(20,40),
                                            'unit': "oC"}
                                         }
                      }    

            position_sensor_ros.publish({"x":x, "y":y, "z":0, "orientations":orientations, "sensors":sensors})
        except  Exception as e:
            print("e", e)

            
    return True    
    
    
    


def driving_fixed(driving_operation_ros, position_sensor_ros):
    """  Vehicle simple simulator to be used for the assignment execution.
         It ignores the request and always drives a fixed straight line randonly updating sensors.
         Note that this function communicates by writing the hard drive.
    """
    FORCE_FAIL_SIMULATOR = False
    pose = position_sensor_ros.read()
    x0 = pose['x']    
    y0 = pose['y']
    
    print("driven distance")
    for d in range(0, 10000, 1000):
        time.sleep(1)
        x = x0 + d
        y = y0 + d
        print("<= publish sensor", d)
        try:
            STOP_SIMULATOR = driving_operation_ros.read().get("CANCEL_DRIVING", False)
            if STOP_SIMULATOR:
                print("CANCEL_DRIVING", STOP_SIMULATOR)
                driving_operation_ros.publish({"CANCEL_DRIVING":False})
                return False
            
            if FORCE_FAIL_SIMULATOR: raise "error"

            sensors = { 'helyos_agent_control':{},
                        'temperatures':{
                                        'sensor_1': {
                                            'title':"cabine",
                                            'type' :"number",
                                            'value':random.randint(20,40),
                                            'unit': "oC"}
                                         }
                      }    

            position_sensor_ros.publish({"x":x, "y":y, "z":0, "orientations":[0,0], "sensors":sensors})
        except  Exception as e:
            print("e", e)

            
    return True