

import json
from helyos_agent_sdk.models import AssignmentCurrentStatus, AGENT_STATE, AgentCurrentResources, ASSIGNMENT_STATUS
from connect_trailer import trailer_connection

def reserve_callback( vehi_state_ros, agentConnector, ch, sender, req_resources, msg_str, signature):
    print("=> reserve agent", req_resources)

    resources = AgentCurrentResources(operation_types_available = req_resources.operation_types_required,
                                      work_process_id           = req_resources.work_process_id,
                                      reserved                  = req_resources.reserved)
    
    vehi_state_ros.publish({**vehi_state_ros.read(),"agent_state": AGENT_STATE.READY})
    agentConnector.publish_state(status=AGENT_STATE.READY, resources=resources, assignment_status=None)
    print("<= agent reserved", resources)
    
    
def release_callback(vehi_state_ros, agentConnector, ch, sender, req_resources, msg_str, signature):
    print(" => release agent", req_resources)
    
    resources = AgentCurrentResources(operation_types_available = req_resources.operation_types_required,
                                      work_process_id           = req_resources.work_process_id,
                                      reserved                  = req_resources.reserved)
    
    vehi_state_ros.publish({**vehi_state_ros.read(),'agent_state': AGENT_STATE.FREE})
    agentConnector.publish_state(status=AGENT_STATE.FREE, resources=resources, assignment_status=None)   
    print(" <= agent released", resources)
    



def do_something_to_interrupt_assignment_operations(driving_operation_ros):
    operation_commands = driving_operation_ros.read()
    driving_operation_ros.publish({**operation_commands, 'CANCEL_DRIVING': True, 'PAUSE_ASSIGNMENT': False})


def cancel_assignm_callback(driving_operation_ros, current_assignment_ros, agentConnector, ch, server, inst_assignm_cancel, msg_str, signature):
    assignment_metadata = inst_assignm_cancel.metadata   
    assignm_data = current_assignment_ros.read()
    agentConnector.current_assignment = AssignmentCurrentStatus(id=assignm_data['id'], status=assignm_data['status'], result=assignm_data.get('result',{}))

    if assignment_metadata.id == agentConnector.current_assignment.id:
        do_something_to_interrupt_assignment_operations(driving_operation_ros)
        print(" * cancelling order dispatched")
    else:
        print("assignment id is not running in this agent")
        print("cancelling assignment:", assignment_metadata.id)
        print("current assignment:", agentConnector.current_assignment.id)



def my_other_callback(position_sensor_ros, driving_operation_ros, vehi_state_ros, agentConnector, datareq_rpc, ch, sender, received_str):
    print("not helyos-related instant action", received_str)
    agent_data = position_sensor_ros.read()    
    operation_commands = driving_operation_ros.read()

    try: 
        message = json.loads(received_str)['message']
        print(message)
        command =  json.loads(message) 
    except:
        print("\nAgent does not know how interpret the command:", received_str[0:50])
        return
    
    sensor_patch = {}

    try:
        if "connect_trailer" in command['body']:
            return trailer_connection(command['body'], vehi_state_ros,position_sensor_ros, agentConnector.helyos_client, datareq_rpc)

        if "pause" == command['body']:     
            driving_operation_ros.publish({**operation_commands, 'PAUSE_ASSIGNMENT': True})
            sensor_patch = {  'instant_actions_response':{
                                'task_control':{
                                        'title':"Task status",
                                        'type': "string",
                                        'value':"paused",
                                        'unit':""},
                            }
                    }    

        if "resume" == command['body']:                                                
            driving_operation_ros.publish({**operation_commands, 'PAUSE_ASSIGNMENT': False})
            sensor_patch = {  'instant_actions_response':{
                                        'task_control':{
                                                'title':"Task status",
                                                'type': "string",
                                                'value':"normal",
                                                'unit':""},
                                    }
                            }     

        
        if "tail lift" in command['body']:     
            if command['body'] == "tail lift down": value = "down"
            if command['body'] == "tail lift up":  value = "up"

            sensor_patch = {   'actuators':{
                                        'sensor_act1': {
                                            'title':"Tail Lift",
                                            'type' :"string",
                                            'value': value,
                                            'unit': ""}
                                        }
                        } 

        if "headlight" in command['body']:     
            if command['body'] == "headlight on": value = "on"
            if command['body'] == "headlight off":  value = "off"

            sensor_patch = {   'lights':{
                                        'sensor_hl1': {
                                            'title':"Headlight",
                                            'type' :"string",
                                            'value': value,
                                            'unit': ""}
                                        }
                        } 

            
        sensors = {**agent_data['sensors'], **sensor_patch}
        agent_data['sensors'] = sensors
        position_sensor_ros.publish(agent_data)    
    except Exception as e:
        print(e)