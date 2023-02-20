

from helyos_agent_sdk.models import AssignmentCurrentStatus, AGENT_STATE, AgentCurrentResources, ASSIGNMENT_STATUS


def reserve_callback( vehi_state_ros, agentConnector, ch, method, properties, req_resources):
    print("=> reserve agent", req_resources)

    resources = AgentCurrentResources(operation_types_available = req_resources.operation_types_required,
                                      work_process_id           = req_resources.work_process_id,
                                      reserved                  = req_resources.reserved)
    
    vehi_state_ros.publish({"agent_state": AGENT_STATE.READY})
    agentConnector.publish_state(status=AGENT_STATE.READY, resources=resources, assignment_status=None)
    print("<= agent reserved", resources)
    
    
def release_callback(vehi_state_ros, agentConnector, ch, method, properties, req_resources):
    print(" => release agent", req_resources)
    
    resources = AgentCurrentResources(operation_types_available = req_resources.operation_types_required,
                                      work_process_id           = req_resources.work_process_id,
                                      reserved                  = req_resources.reserved)
    
    vehi_state_ros.publish({"agent_state": AGENT_STATE.FREE})
    agentConnector.publish_state(status=AGENT_STATE.FREE, resources=resources, assignment_status=None)   
    print(" <= agent released", resources)
    



def do_something_to_interrupt_assignment_operations(driving_operation_ros):
    driving_operation_ros.publish({"CANCEL_DRIVING":True})


def cancel_assignm_callback(vehi_state_ros, agentConnector,  driving_operation_ros, ch, method, properties, inst_assignm_cancel):
    assignment_metadata = inst_assignm_cancel.assignment_metadata   
    
    if assignment_metadata.id == agentConnector.current_assignment.id:
        do_something_to_interrupt_assignment_operations(driving_operation_ros)
        print(" * cancelling order dispatched")
    else:
        print("assignment id is not running in this agent")



def my_other_callback(ch, method, properties, received_str, agentConnector):
    print("not helyos-related instant action", received_str)