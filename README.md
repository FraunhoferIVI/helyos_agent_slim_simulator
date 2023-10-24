# helyos_agent_slim_simulator

It simulates an agent in the helyOS framework. It can be used for front-end development or for testing path planning algorithms.

## Getting started

Run with the default settings:
```
docker run helyosframework/agent_helyos_slim_simulator
```

Or use a docker-compose as shown in `/example/docker-compose.yml`.


## Build

```
docker build --no-cache -t helyosframework/helyos_agent_slim_simulator:0.7.1 .
docker push helyosframework/helyos_agent_slim_simulator:0.7.1 
```

## Assignment data formats
### Trajectory

```python
assignment = { "trajectory": [{"x": float, "y": float, "orientations":List[float], time:float}, ...] }

```
### Destination point
``` python
assignment = { "destination": {"x": float, "y": float, "orientations":List[float]}  }
```

### AutoTruck-TruckTrix path format

https://app.swaggerhub.com/apis-docs/helyOS/Tructrix_API/4.0#/TrucktrixTrajectory


## Instant actions
Besides the helyOS-required instant actions (mission reserve, mission release and cancel),
we have implemented additional instant actions triggered by the following strings:

* "pause" or "resume" : pause/resume a running assignment.
* "tail lift up" or "tail lift down": change the value of the tail lift sensor.
* "headlight on" or "headlight off": change the value of the tail lift sensor.

## Settings

The simulator is configured by the environment variables:

| VARIABLE | DESCRIPTION |
| --- | --- |
| UUID | String with unique identifcation code of agent (use "RANDOM_UUID" for auto-generated uuids) |
| REGISTRATION_TOKEN | Allow agent to check in even if not registered in helyOS |
| NAME | Agent name |
| YARD_UID | Yard identifier |
| UPDATE_RATE | Frequency of published messages (Hz) |
| --- | --- |
| PATH_TRACKER |  ideal (arb. unit), stanley (mm), straight_to_destination(arb.unit)|
| ASSIGNMENT_FORMAT | fixed, trajectory, destination, trucktrix-path |
| VEHICLE_PARTS | Number of parts. eg. truck with trailer: 2 |
| --- | --- |
| X0 | Initial horizontal position (arb. unit, dep. PATH_TRACKER)|
| Y0 | Initial vertical position (arb. unit, dep. PATH_TRACKER)|
| ORIENTATION | Initial orientation in mrads |
| VELOCITY | Driving velocity 0 to 10. (arb. unit) |
| --- | --- |
| RABBITMQ_HOST | HelyOS RabbitMQ Server  |
| RABBITMQ_PORT | HelyOS RabbitMQ Port (e.g.,5671, 5672, 1883, 8883, default:5672)  |
| RBMQ_USERNAME | Agent RabbitMQ account name (optional) |
| RBMQ_PASSWORD | Agent RabbitMQ account password (optional)  |
| PROTOCOL | "AMQP" or "MQTT" (default: AMPQ)  |
| ENABLE_SSL | True or False (default: False)  |


For `ENABLE_SSL`=True, you must copy the server host CA certificate to the location app/ca_certificate.pem. Check in `./example`.

Optional environmnet variable for the `stanley` path tracker:

| VARIABLE | DESCRIPTION |
| --- | --- |
| STANLEY_K | control gain (default: 1) |
| STANLEY_KP | speed proportional gain (default: 0.5)|
| STANLEY_L |  Wheel base of vehicle length (m) (default: 2.9) |
| STANLEY_MAXSTEER | (rad) max steering angle (default: 12)|
| --- | --- |

Ref:
    - [Stanley: The robot that won the DARPA grand challenge](http://isl.ecst.csuchico.edu/DOCS/darpa2005/DARPA%202005%20Stanley.pdf)
    - [Autonomous Automobile Path Tracking](https://www.ri.cmu.edu/pub_files/2009/2/Automatic_Steering_Methods_for_Autonomous_Automobile_Path_Tracking.pdf)


## Test and Deploy

***

### Authors

*   Carlos E. Viol Barbosa



### License

This project is licensed under the MIT License.