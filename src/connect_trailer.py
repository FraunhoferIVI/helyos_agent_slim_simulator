import time
from helyos_agent_sdk.models import  AGENT_STATE 
from helyos_agent_sdk import AgentConnector



def trailer_connection(command_body,vehi_state_ros, position_sensor_ros, helyOS_client2, datareq_rpc):
    states_ros = vehi_state_ros.read()
    agentConnector = AgentConnector(helyOS_client2)

    if "disconnect_trailer" in command_body:
        # Disconnect with the trailer 
        states_ros['CONNECTED_TRAILER']['status']=AGENT_STATE.FREE.value           
        vehi_state_ros.publish({**states_ros})
        time.sleep(3)

        agentConnector.publish_general_updates({'followers':[]})
        vehi_state_ros.publish({**states_ros, 'CONNECTED_TRAILER': None})
        sensor_patch = {  'instant_actions_response':{
                        'trailer_control':{
                                'title':"Trailer",
                                'type': "string",
                                'value':"dettached",
                                'unit':""},
                        }
            }   


    elif "connect_trailer" in command_body:  
        try:
            trailer_uuid = command_body.split("connect_trailer")[1]
            trailer_uuid = trailer_uuid.strip()
            leader_uuid = agentConnector.helyos_client.uuid   

            # # Connect with the trailer             
            agentConnector.publish_general_updates({'followers':[trailer_uuid]})

            # # Confirm if the interconnection has worked
            if datareq_rpc:
                found_trailer = False; i = 0
                while not found_trailer and i < 3 :
                        time.sleep(1)
                        follower_agents = datareq_rpc.call({'query':"allFollowers", 'conditions':{"uuid":leader_uuid}})
                        for trailer in follower_agents: found_trailer = found_trailer or trailer['uuid'] == trailer_uuid
                        print("trailer data", follower_agents)
                        i = i + 1

                if not found_trailer:
                        raise Exception("Trailer not found as follower.")
            else:
                time.sleep(3)
                
            vehi_state_ros.publish({**states_ros, 'CONNECTED_TRAILER': {'uuid':trailer_uuid, 'status': AGENT_STATE.BUSY.value, 'geometry': trailer['geometry']}})
            sensor_patch = {  'instant_actions_response':{
                            'trailer_control':{
                                    'title':"Trailer",
                                    'type': "string",
                                    'value':"attached",
                                    'unit':""},
                            }
                }   
            
            
        except Exception as e:
                print(e)
                sensor_patch = {  'instant_actions_response':{
                                'trailer_control':{
                                        'title':"Trailer",
                                        'type': "string",
                                        'value':"attachment failed",
                                        'unit':""},
                                }
                    }
                
    agent_data = position_sensor_ros.read()
    sensors = {**agent_data['sensors'], **sensor_patch}
    agent_data['sensors'] = sensors
    position_sensor_ros.publish(agent_data)  
    return True 