

import time, math, random, os
from helyos_agent_sdk.models import AGENT_STATE, ASSIGNMENT_STATUS
from connect_trailer import trailer_connection
from utils.path_followers import stanley_path_follower, straight_path_to_destination
from utils.data_format_convertors import convert_autotruck_path_to_trajectory, get_destination_from_assignment


# Thread-safe messaging mechanism using MockROSCommunication
# driving_operation_ros, position_sensor_ros, vehi_state_ros, current_assignment_ros

VELOCITY = float(os.environ.get('VELOCITY', 2.8)) # 2.8m/s ~ 10 kM/hour
PATH_TRACKER = os.environ.get('PATH_TRACKER', 'ideal')


def path_tracking(pose0, target_trajectory):
    if PATH_TRACKER == "perfect" or PATH_TRACKER == "ideal":
        actual_trajectory = target_trajectory
    if PATH_TRACKER == 'stanley':
        actual_trajectory = stanley_path_follower(pose0, target_trajectory)

    return actual_trajectory




def assignment_execution_local_simulator(inst_assignment_msg, ASSIGNMENT_FORMAT, helyOS_client2, datareq_rpc, *mock_ros_topics):
    """ Assignment simulator wrapper """

    current_assignment_ros, vehi_state_ros, position_sensor_ros, driving_operation_ros = mock_ros_topics
    assignment_metadata = inst_assignment_msg.metadata
    assignment_body = inst_assignment_msg.body
    pose0 = position_sensor_ros.read()

    if 'operation' in assignment_body:
        operation = assignment_body['operation']
    else:
        ASSIGNMENT_FORMAT = "autotruck-path" 
        operation = 'driving'
    
    if "driving" in operation:

        if ASSIGNMENT_FORMAT == "autotruck-path" or ASSIGNMENT_FORMAT == "trucktrix-path":
            target_trajectory = convert_autotruck_path_to_trajectory(autotruck_path=assignment_body)    

        if ASSIGNMENT_FORMAT == "trajectory":
            target_trajectory = assignment_body.get('trajectory', None)

        if ASSIGNMENT_FORMAT == "destination":
            #  It  drives a straight path to destination.
            destination = get_destination_from_assignment(assignment_body)
            target_trajectory = straight_path_to_destination(pose0, destination)

        if ASSIGNMENT_FORMAT == "fixed":
            #  It ignores the path and destination and always drives a fixed path.
            destination = pose0; destination['x'] = pose0['x'] + 10000 
            trajectory = straight_path_to_destination(pose0, destination)

        trajectory = path_tracking(pose0, target_trajectory)

    try:
        current_assignment_ros.publish({'id':assignment_metadata.id, 'status':ASSIGNMENT_STATUS.EXECUTING})
        vehi_state_ros.publish({**vehi_state_ros.read(),"agent_state": AGENT_STATE.BUSY})

        print(" <= assignment is executing")

        if operation == 'driving':
            operation_finished = drive_ivi_stepped(driving_operation_ros, position_sensor_ros, trajectory)
        elif "connect_trailer" in operation:
            operation_finished = trailer_connection(operation, vehi_state_ros, position_sensor_ros, helyOS_client2, datareq_rpc)

        if operation_finished:
            
            print(" * operation concluded")
            
            current_assignment_ros.publish({'id':assignment_metadata.id, 'status':ASSIGNMENT_STATUS.SUCCEEDED})
            vehi_state_ros.publish({**vehi_state_ros.read(),"agent_state": AGENT_STATE.READY})
            
            print(" <= assignment suceeded")
            
        else:
            
            print(" * operation interrupted")
            
            current_assignment_ros.publish({'id':assignment_metadata.id, 'status':ASSIGNMENT_STATUS.CANCELED})
            vehi_state_ros.publish({**vehi_state_ros.read(),"agent_state": AGENT_STATE.FREE})

            print(" <= assignment canceled")

        
    except Exception as e:
        
        current_assignment_ros.publish({'id':assignment_metadata.id, 'status':ASSIGNMENT_STATUS.FAILED})
        vehi_state_ros.publish({**vehi_state_ros.read(), "agent_state": AGENT_STATE.FREE}) 
                                                                       
        print(" <= assignment failed", e)
    

    
def drive_ivi_stepped(driving_operation_ros, position_sensor_ros, trajectory):
    """  Vehicle simple simulator to be used for the assignment execution.
         It folows the IVI-step data format used by the trucktrix planner.
    """
    print("========= driving stepped trajectory =========")
    num_steps = len(trajectory)

    for d in range(0,num_steps, 1):
        x = trajectory[d]['x']
        y = trajectory[d]['y']
        orientations = trajectory[d]['orientations']
        

        try:
            STOP_SIMULATOR = driving_operation_ros.read().get("CANCEL_DRIVING", False)
            FORCE_FAIL_SIMULATOR = driving_operation_ros.read().get("FORCE_FAIL_SIMULATOR", False)
            PAUSE_SIMULATOR = driving_operation_ros.read().get("PAUSE_ASSIGNMENT", False)

            if STOP_SIMULATOR:
                print("CANCEL_DRIVING")
                driving_operation_ros.publish({"CANCEL_DRIVING":False})
                return False

            if FORCE_FAIL_SIMULATOR: raise "error"

            sensor_patch = { 'helyos_agent_control':{
                                        'current_task_progress':{
                                            'title':'Progress of drive operation',
                                            'type': 'number',
                                             'value': d+1,
                                             'unit':'',
                                             'maximum': num_steps},
                        },
                        'temperatures':{
                                        'sensor_t1': {
                                            'title':"cabine",
                                            'type' :"number",
                                            'value':random.randint(20,40),
                                            'unit': "oC"}
                                         },
                      }   
            
            agent_data = position_sensor_ros.read()    
            sensors = {**agent_data['sensors'], **sensor_patch}   
            new_agent_data = {"x":x, "y":y, "z":0, "orientations":orientations, "sensors": sensors }
            position_sensor_ros.publish(new_agent_data)    

            while PAUSE_SIMULATOR:
                time.sleep(1)
                position_sensor_ros.publish(new_agent_data) 
                PAUSE_SIMULATOR = driving_operation_ros.read().get("PAUSE_ASSIGNMENT", False)

            if d < (num_steps-1):
                t0 = trajectory[d]['time']; t1 = trajectory[d+1]['time']
                if t0 is not None and t1 is not None:
                    dt = t1 - t0
                    time.sleep(dt)
                else:
                    xs = trajectory[d+1]['x'];  ys = trajectory[d+1]['y']  
                    ds = math.sqrt((xs - x)**2 + (ys - y)**2)/1000 # meters  
                    dt = ds/VELOCITY
                    time.sleep(dt)
            else:
                time.sleep(1)

            if not int((d/num_steps)*1000) % 100:
                print("driven steps:", f"{d}/{num_steps}")


        except  Exception as e:
            print("e", e)


    return True    



    