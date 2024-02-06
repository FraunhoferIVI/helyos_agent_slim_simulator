import os, json, time
from threading import Thread
from data_publishing import periodic_publish_state_and_sensors
from helyos_agent_sdk import HelyOSClient, HelyOSMQTTClient, AgentConnector, DatabaseConnector
from helyos_agent_sdk.models import AssignmentCurrentStatus, AGENT_STATE, AgentCurrentResources, ASSIGNMENT_STATUS
from utils.MockROSCommunication import MockROSCommunication
from instant_actions import cancel_assignm_callback, my_other_callback, release_callback, reserve_callback
from operation_simulator import assignment_execution_local_simulator
import uuid
from helyos_agent_sdk.crypto import verify_signature
from helyos_agent_sdk.utils import replicate_helyos_client


# CONSTANTS
RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', "local_message_broker")
RABBITMQ_HOST = os.environ.get('RBMQ_HOST', "local_message_broker")
RABBITMQ_PORT = int(os.environ.get('RABBITMQ_PORT', "5672"))
RABBITMQ_PORT = int(os.environ.get('RBMQ_PORT', "5672"))
ENABLE_SSL = os.environ.get('ENABLE_SSL', "False") == "True"
PROTOCOL = os.environ.get('PROTOCOL', "AMQP")
CACERTIFICATE_FILENAME = os.environ.get('CACERTIFICATE_FILENAME', "ca_certificate.pem")


VEHICLE_NAME = os.environ.get('NAME', '')
TOOL_TYPE = os.environ.get('TOOL_TYPE', "truck")

ASSIGNMENT_FORMAT = os.environ.get('ASSIGNMENT_FORMAT', "trajectory")
PATH_TRACKER = os.environ.get('PATH_TRACKER', "ideal")
UUID = os.environ.get('UUID', "RANDOM_UUID")
YARD_UID = os.environ.get('YARD_UID', "1")
X0 = float(os.environ.get('X0', 0))
Y0 = float(os.environ.get('Y0', 0))
ORIENTATION_0 = float(os.environ.get('ORIENTATION', 0))
GEOMETRY_FORMAT = os.environ.get('GEOMETRY_FORMAT', "trucktrix-vehicle")
GEOMETRY_FILENAME = os.environ.get('GEOMETRY_FILENAME', "geometry.json")

AGENT_OPERATIONS =  os.environ.get('AGENT_OPERATIONS', "drive,")
VEHICLE_PARTS =  int(os.environ.get('VEHICLE_PARTS', 1))
CHECKIN_MAX_ATTEMPTS = int(os.environ.get('CHECKIN_MAX_ATTEMPTS', "5"))
RBMQ_USERNAME = os.environ.get('RBMQ_USERNAME', None)
RBMQ_PASSWORD = os.environ.get('RBMQ_PASSWORD', None)
UPDATE_RATE = os.environ.get('UPDATE_RATE', 2)

if UUID == "RANDOM_UUID":
    UUID = str(uuid.uuid1())

try:
    with open(GEOMETRY_FILENAME) as f:
        GEOMETRY =json.load(f)
except:
    GEOMETRY = {}

try:
    with open(CACERTIFICATE_FILENAME, "r") as f:
        CA_CERTIFICATE = f.read()
except:
    CA_CERTIFICATE = ""

MessageBrokerClient = HelyOSClient

if PROTOCOL == "AMQP":   
    MessageBrokerClient = HelyOSClient
if PROTOCOL == "MQTT":
    MessageBrokerClient = HelyOSMQTTClient

# 1 - AGENT INITIALIZATION

initial_orientations = [0] * VEHICLE_PARTS
initial_orientations[0] = ORIENTATION_0

agent_data = {          
                'name': VEHICLE_NAME,
                'tool_type': TOOL_TYPE,
                'agentClass': 'vehicle',
                'pose': {'x': X0, 'y':Y0, 'orientations':initial_orientations},
                'geometry': GEOMETRY,
                'factsheet': GEOMETRY,
                'data_format': ASSIGNMENT_FORMAT,
         }


initial_sensor =  {    'helyos_agent_control':{
                                        'current_task_progress':{
                                            'title':"Progress of drive operation",
                                            'type': "number",
                                             'value':0,
                                             'unit':"",
                                             'maximum': 1},
                        },
                        'temperatures':{
                                        'sensor_t1': {
                                            'title':"cabine",
                                            'type' :"number",
                                            'value': 30,
                                            'unit': "oC"}
                        },                
                        'actuators':{
                                    'sensor_act1': {
                                        'title':"Tail Lift",
                                        'type' :"string",
                                        'value': 'up',
                                        'unit': ""}
                        },
                        
            }   

initial_status = AGENT_STATE.FREE
operations = AGENT_OPERATIONS.split(',')
resources = AgentCurrentResources(operation_types_available=operations, work_process_id=None, reserved=False)
assignment = AssignmentCurrentStatus(id=None, status=None, result={})

## 1.1 Instantiate main helyOS client - we create one RabbitMQ connection per helyos_client
helyOS_client = MessageBrokerClient(RABBITMQ_HOST, RABBITMQ_PORT, uuid=UUID, enable_ssl=ENABLE_SSL, ca_certificate=CA_CERTIFICATE)
attempts = 0; helyos_excep = None
while attempts < CHECKIN_MAX_ATTEMPTS:
    try:
        if RBMQ_USERNAME and RBMQ_PASSWORD:
            helyOS_client.connect(RBMQ_USERNAME, RBMQ_PASSWORD)

        print(f"Check in, attempt {attempts+1} ...")
        helyOS_client.perform_checkin(yard_uid=YARD_UID, agent_data=agent_data, status=initial_status.value)
        break
    except Exception as e:
        attempts += 1
        helyos_excep = e
        time.sleep(2)
if attempts == CHECKIN_MAX_ATTEMPTS:
    raise helyos_excep

helyOS_client.get_checkin_result()
print("\n connected to message broker")

## 1.2 Instantiate main Agent Connector  
agentConnector = AgentConnector(helyOS_client)
agentConnector.publish_state(initial_status, resources, assignment_status=assignment)



## 1.3 Internal communication -  thread-safe messaging mechanisms
driving_operation_ros =  MockROSCommunication("driving_operation_ros")       
position_sensor_ros = MockROSCommunication("position_sensor_ros")  
vehi_state_ros = MockROSCommunication("vehi_state_ros")  
current_assignment_ros = MockROSCommunication("current_assignment_ros")  

vehi_state_ros.publish({'agent_state': initial_status, 'CONNECTED_TRAILER': None})
driving_operation_ros.publish({'CANCEL_DRIVING':False, 'destination':None, 'path_array':None})
current_assignment_ros.publish({'id':None, 'status': None})
position_sensor_ros.publish({ 'x':X0, 'y':Y0, 'orientations':initial_orientations, 'sensors':initial_sensor})



# 2 - AGENT PUBLISHES MESSAGES
# Use a separate thread to publish position, state and sensors periodically

## 2.1 Instantiate second helyOS client to work in different thread.
privkey = helyOS_client.private_key
pubkey = helyOS_client.public_key

new_helyOS_client_for_THREAD = replicate_helyos_client(helyOS_client)
if RBMQ_USERNAME and RBMQ_PASSWORD:
    new_helyOS_client_for_THREAD.connect(RBMQ_USERNAME, RBMQ_PASSWORD) 
else:
    new_helyOS_client_for_THREAD.connect(helyOS_client.checkin_data.body['rbmq_username'], 
                                                 helyOS_client.rbmq_password)
    
## 2.2 Start thread to publish messages
publishing_topics =  (current_assignment_ros, vehi_state_ros, position_sensor_ros)
position_thread = Thread(target=periodic_publish_state_and_sensors,args=[new_helyOS_client_for_THREAD, *publishing_topics])
position_thread.start()


## 3 - Instantiate RPC requester. RPC is only supported by AMQP protocol.
new_helyOS_client_for_THREAD2 = replicate_helyos_client(helyOS_client)
if RBMQ_USERNAME and RBMQ_PASSWORD:
    new_helyOS_client_for_THREAD2.connect(RBMQ_USERNAME, RBMQ_PASSWORD) 
else:
    new_helyOS_client_for_THREAD2.connect(helyOS_client.checkin_data.body['rbmq_username'], 
                                                 helyOS_client.rbmq_password)

if PROTOCOL == "AMQP":
    datareq_rpc = DatabaseConnector(new_helyOS_client_for_THREAD2)
    follower_agents = datareq_rpc.call({'query':"allFollowers", 'conditions':{"uuid":UUID}})
    try:
        if len(follower_agents) > 0:
            print(follower_agents)
            vehi_state_ros.publish({**vehi_state_ros.read(), 'CONNECTED_TRAILER': {'uuid':follower_agents[0]['uuid'],
                                                                                'status': AGENT_STATE.BUSY.value, 
                                                                                'geometry': follower_agents[0]['geometry']}})
    except:
        print("\n==> Interconnection not supported. Please update your helyOS core.\n")
else:
    datareq_rpc = None
    

# 3- AGENT RECEIVES MESSAGES 

# Register instant actions callbacks 

def my_reserve_callback(*args):        return reserve_callback(vehi_state_ros, agentConnector, *args)
def my_release_callback(*args):        return release_callback(vehi_state_ros, agentConnector, *args )
def my_cancel_assignm_callback(*args): return cancel_assignm_callback(driving_operation_ros, current_assignment_ros, agentConnector, *args )
def my_any_other_instant_action_callback(*args): return my_other_callback(position_sensor_ros,driving_operation_ros,vehi_state_ros, agentConnector,
                                                                          datareq_rpc, *args)

agentConnector.consume_instant_action_messages(my_reserve_callback, my_release_callback, my_cancel_assignm_callback, my_any_other_instant_action_callback)



# Register the assignment callback 

def my_assignment_callback(ch, sender, inst_assignment_msg, msg_str, signature): 
    print(" => assignment is received")

    try:
        verify_signature(msg_str, signature, helyOS_client.helyos_public_key)
    except Exception as e:
        print(e)
        print("Signature verification failed")
        return

    assignment_metadata = inst_assignment_msg.metadata
    current_assignment_ros.publish({'id':assignment_metadata.id, 'status':ASSIGNMENT_STATUS.ACTIVE})
    vehi_state_ros.publish({**vehi_state_ros.read(),'agent_state': AGENT_STATE.BUSY}) 

    print(" <= assignment is active")      
    time.sleep(1)

    operation_topics = (current_assignment_ros, vehi_state_ros, position_sensor_ros, driving_operation_ros)
    assignment_execution_thread = Thread(target=assignment_execution_local_simulator, args=(inst_assignment_msg, ASSIGNMENT_FORMAT, new_helyOS_client_for_THREAD, datareq_rpc, *operation_topics))
    assignment_execution_thread.start()

agentConnector.consume_assignment_messages(assignment_callback=my_assignment_callback)



# Agent consume messages from helyOS 

agentConnector.start_listening()