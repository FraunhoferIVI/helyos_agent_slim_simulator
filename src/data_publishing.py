
import time, json, math
from helyos_agent_sdk import AgentConnector
from helyos_agent_sdk.models import AssignmentCurrentStatus


# These functions can be used to parse data

def get_vehicle_position(position_sensor_ros):
    # Get x, y, orientations from the vehicle
    return position_sensor_ros.read()

def get_trailer_position(position_sensor_ros):
    # Get x, y, orientations from the vehicle
    truck = {**position_sensor_ros.read()}
    trailer = {'pose':{}}
    trailer['pose']['x'] = truck['x'] - 4000 * math.cos(truck['orientations'][0]/1000)
    trailer['pose']['y'] = truck['y'] - 4000 * math.sin(truck['orientations'][0]/1000)
    trailer['pose']['orientations'] = truck['orientations']
    trailer['sensors'] =   {  'temperatures':{
                                        'sensor_t1': {
                                            'title':"trailer temperature",
                                            'type' :"number",
                                            'value': 40,
                                            'unit': "oC"}
                        }}

    return trailer

def get_assignment_state(current_assignment_ros):
    ''' Get vehicle state: "failed", "active", "succeeded", etc... '''    
    return current_assignment_ros.read()


def interprete_vehicle_state(vehicle_data, assignm_data, vehi_state_ros ): 
    ''' agent state ("free", "ready", "busy"...). '''
    return vehi_state_ros.read()




def periodic_publish_state_and_sensors(helyOS_client2, current_assignment_ros, vehi_state_ros, position_sensor_ros):
    agentConnector2 = AgentConnector(helyOS_client2)
    period = 1 # second
    z=0
    while True:
        time.sleep(period)
        
        try:
            agent_data = get_vehicle_position(position_sensor_ros)
            agentConnector2.publish_sensors(x=agent_data["x"], y=agent_data["y"], z=0,
                                            orientations=agent_data['orientations'], sensors=agent_data['sensors'])
        except Exception as e:
            print("cannot read position.", e)


        trailer_uuid = vehi_state_ros.read().get('CONNECTED_TRAILER', None)
        if trailer_uuid is not None:
            try:
                trailer_data = get_trailer_position(position_sensor_ros)
                body = trailer_data
                message= json.dumps({'type': 'agent_sensors','body': body})
                helyOS_client2.publish(routing_key=f"agent.{trailer_uuid}.visualization", message=message)
                
            except Exception as e:
                print("cannot read trailer position.", e)

        
        try:
            assignm_data = get_assignment_state(current_assignment_ros)
            vehicle_data = interprete_vehicle_state(agent_data, assignm_data, vehi_state_ros)            

            agentConnector2.publish_state(status=vehicle_data['agent_state'], 
                                 assignment_status=AssignmentCurrentStatus(id=assignm_data['id'], 
                                                                       status=assignm_data['status'],
                                                                        result=assignm_data.get('result',{})))
        except Exception as e:
            print("cannot read states.", e)