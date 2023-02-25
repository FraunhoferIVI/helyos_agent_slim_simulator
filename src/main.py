import os, json, time
from threading import Thread
from data_publishing import periodic_publish_state_and_sensors
from helyos_agent_sdk import HelyOSClient, AgentConnector, connect_rabbitmq
from helyos_agent_sdk.models import AssignmentCurrentStatus, AGENT_STATE, AgentCurrentResources, ASSIGNMENT_STATUS
from utils.MockROSCommunication import MockROSCommunication
from instant_actions import cancel_assignm_callback, my_other_callback, release_callback, reserve_callback
from operation_simulator import assignment_execution_local_simulator


# CONSTANTS
RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'local_message_broker')
RABBITMQ_PORT = os.environ.get('RABBITMQ_PORT', '5672')
VEHICLE_NAME = os.environ.get('NAME', '')
ASSIGNMENT_FORMAT = os.environ.get('ASSIGNMENT_FORMAT', 'autotruck-path')
PATH_TRACKER = os.environ.get('PATH_TRACKER', 'perfect')
UUID = os.environ.get('UUID', "Bb34069fc5-fdgs-434b-b87e-f19c5435113")
YARD_UID = os.environ.get('YARD_UID', "1")
X0 = float(os.environ.get('X0', 0))
Y0 = float(os.environ.get('Y0', 0))
ORIENTATION_0 = float(os.environ.get('ORIENTATION', 0))
GEOMETRY_FORMAT = os.environ.get('GEOMETRY_FORMAT', "trucktrix-vehicle")
GEOMETRY_FILENAME = os.environ.get('GEOMETRY_FILENAME', "geometry.json")
AGENT_OPERATIONS =  os.environ.get('AGENT_OPERATIONS', "drive,")
VEHICLE_PARTS =  int(os.environ.get('VEHICLE_PARTS', 1))

try:
    with open(GEOMETRY_FILENAME) as f:
        GEOMETRY =json.load(f)
except:
    GEOMETRY = {}


# 1 - AGENT INITIALIZATION

initial_orientations = [0] * VEHICLE_PARTS
initial_orientations[0] = ORIENTATION_0

agent_data = {          
                'name': VEHICLE_NAME,
                'pose': {'x': X0, 'y':Y0, 'orientations':initial_orientations},
                'geometry': GEOMETRY,
                'factsheet': GEOMETRY,
                'data_format': GEOMETRY_FORMAT
         }


initial_status = AGENT_STATE.FREE
operations = AGENT_OPERATIONS.split(',')
resources = AgentCurrentResources(operation_types_available=operations, work_process_id=None, reserved=False)
assignment = AssignmentCurrentStatus(id=None, status=None, result={})

helyOS_client = HelyOSClient(RABBITMQ_HOST, RABBITMQ_PORT, uuid=UUID)
helyOS_client.perform_checkin(yard_uid=YARD_UID, agent_data=agent_data, status=initial_status.value)
helyOS_client.get_checkin_result()         

print("\n checkin_data:", helyOS_client.checkin_data)
agentConnector = AgentConnector(helyOS_client)
agentConnector.publish_state(initial_status, resources, assignment_status=assignment)



# Internal communication

# Creating a thread-safe messaging mechanisms
driving_operation_ros =  MockROSCommunication('driving_operation_ros')       
position_sensor_ros = MockROSCommunication('position_sensor_ros')  
vehi_state_ros = MockROSCommunication('vehi_state_ros')  
current_assignment_ros = MockROSCommunication('current_assignment_ros')  

vehi_state_ros.publish({"agent_state": initial_status})
driving_operation_ros.publish({"CANCEL_DRIVING":False, "destination":None, "path_array":None})
current_assignment_ros.publish({'id':None, 'status': None})
position_sensor_ros.publish({ "x":X0, "y":Y0, "orientations":initial_orientations, "sensors":{}})




# 2 - AGENT PUBLISHES MESSAGES

# Use a separate thread to publish position, state and sensors periodically
new_helyOS_client_for_THREAD = HelyOSClient(RABBITMQ_HOST, RABBITMQ_PORT, uuid=UUID)
new_helyOS_client_for_THREAD.connection = connect_rabbitmq(RABBITMQ_HOST, RABBITMQ_PORT, 
                                            helyOS_client.checkin_data['rbmq_username'], 
                                            helyOS_client.checkin_data['rbmq_password'])


publishing_topics =  (current_assignment_ros, vehi_state_ros, position_sensor_ros)
position_thread = Thread(target=periodic_publish_state_and_sensors,args=[new_helyOS_client_for_THREAD, *publishing_topics])
position_thread.start()



# 3- AGENT RECEIVES MESSAGES 

# Register instant actions callbacks 

def my_reserve_callback(*args): return reserve_callback(vehi_state_ros, agentConnector, *args)
def my_release_callback(*args): return release_callback(vehi_state_ros, agentConnector, *args )
def my_cancel_assignm_callback(*args): return cancel_assignm_callback(driving_operation_ros, agentConnector, *args )
def my_any_other_instant_action_callback(*args): return my_other_callback(agentConnector, *args)

agentConnector.consume_instant_action_messages(my_reserve_callback, my_release_callback, my_cancel_assignm_callback, my_any_other_instant_action_callback)



# Register the assignment callback 

def my_assignment_callback(ch, method, properties, inst_assignment_msg): 
    print(" => assignment is received")

    assignment_metadata = inst_assignment_msg.assignment_metadata
    current_assignment_ros.publish({'id':assignment_metadata.id, 'status':ASSIGNMENT_STATUS.ACTIVE})
    vehi_state_ros.publish({"agent_state": AGENT_STATE.BUSY}) 

    print(" <= assignment is active")      
    time.sleep(1)

    operation_topics = (current_assignment_ros, vehi_state_ros, position_sensor_ros, driving_operation_ros)
    assignment_execution_thread = Thread(target=assignment_execution_local_simulator, args=(inst_assignment_msg, ASSIGNMENT_FORMAT, *operation_topics))
    assignment_execution_thread.start()

agentConnector.consume_assignment_messages(assignment_callback=my_assignment_callback)



# Agent consume messages from helyOS 

agentConnector.start_consuming()