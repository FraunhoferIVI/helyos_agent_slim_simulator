
import time, json, math, os
from helyos_agent_sdk import AgentConnector
from helyos_agent_sdk.models import AssignmentCurrentStatus
GEOMETRY_FILENAME = os.environ.get('GEOMETRY_FILENAME', "geometry.json")
try:
    with open(GEOMETRY_FILENAME) as f:
        GEOMETRY =json.load(f)
except:
    GEOMETRY = {}


# These functions can be used to parse data

def get_vehicle_position(position_sensor_ros):
    # Get x, y, orientations from the vehicle
    return position_sensor_ros.read()


def get_trailer_position(position_sensor_ros, truck_geometry):
    # Get x, y, orientations from the vehicle
    truck_sensors = {**position_sensor_ros.read()}
    try:
        trailer_joint_angle = truck_sensors['orientations'][1]
    except:
        trailer_joint_angle = 0
        
    absolut_truck_angle = truck_sensors['orientations'][0]
    absolut_trailer_angle = absolut_truck_angle - trailer_joint_angle
    # we use the position of the first axis  as the global x, y for the truck 
    # and truck-trailer connection point as global x, y position for the trailer.
    rear_position_from_chassi = truck_geometry['rear_joint_position']
    first_axis_position_from_chassi = truck_geometry['axles'][0]['position']
    rear_position_from_first_axis = {'x': rear_position_from_chassi['x'] - first_axis_position_from_chassi['x'], 
                                     'y': rear_position_from_chassi['y'] - first_axis_position_from_chassi['y']}
  
    truck_rear_joint_distance_to_reference = math.sqrt(rear_position_from_first_axis['x']**2 + rear_position_from_first_axis['y']**2)
    trailer_front_joint_distance_to_reference = 0 # by definition


    trailer = {'pose':{}}
    trailer['pose']['x'] = truck_sensors['x'] - truck_rear_joint_distance_to_reference * math.cos(absolut_truck_angle/1000) 
                                            #   - trailer_front_joint_distance_to_reference * math.cos(absolut_trailer_angle/1000) this is zero
    
    trailer['pose']['y'] = truck_sensors['y'] - truck_rear_joint_distance_to_reference * math.sin(absolut_truck_angle/1000) 
                                            #   - trailer_front_joint_distance_to_reference * math.sin(absolut_trailer_angle/1000) this is zero
    
    trailer['pose']['orientations'] = [absolut_trailer_angle]
    
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


        trailer = vehi_state_ros.read().get('CONNECTED_TRAILER', None)
        if trailer is not None:
            try:
                truck_geometry = GEOMETRY[0]
                trailer_data = get_trailer_position(position_sensor_ros, truck_geometry)
                body = trailer_data
                message= json.dumps({'type': 'agent_sensors','body': body})
                helyOS_client2.publish(routing_key=f"agent.{trailer['uuid']}.visualization", message=message)
                message= json.dumps({'type': 'agent_state','body': {'status':trailer['status']}})
                helyOS_client2.publish(routing_key=f"agent.{trailer['uuid']}.state", message=message)

                
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