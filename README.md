# helyos_agent_slim_simulator

It simulates agent in helyOS framework. It can be used for front-end development or to test path planning algorithms.

## Getting started

Run with the default settings:
```
docker run agent_helyos_slim_simulator
```

Or use a docker-compose as shown in `/example/docker-compose.yml`.


## Build

```
docker build --no-cache -t helyos2020/helyos_agent_slim_simulator
docker push helyos2020/helyos_agent_slim_simulator
```

## Settings

The simulator is configured by the environment variables:

| VARIABLE | DESCRIPTION |
| --- | --- |
| UUID | String with unique identifcation code of agent |
| REGISTRATION_TOKEN | Allow agent to check in even if not registered in helyOS |
| NAME | Agent name |
| --- | --- |
| X0 | Initial horizontal position (arb. unit)|
| Y0 | Initial vertical position (arb. unit)|
| ORIENTATION | Initial orientation in mrads |
| VELOCITY | Driving velocity 0 to 10. (arb. unit) |
| PATH_ALGORITHM | fixed, stepped-path, straight_to_destination, clothoid_to_destination (default:autotruck-path)|
| --- | --- |
| RABBITMQHOST | HelyOS RabbitMQ Server  |
| RABBITMPORT | HelyOS RabbitMQ Port (default:5672)  |
| RBMQ_USERNAME | Agent RabbitMQ account name (optional) |
| RBMQ_PASSWORD | Agent RabbitMQ account password (optional)  |



## Test and Deploy

***

### Author

*   Carlos E. Viol Barbosa



### License

This project is licensed under the MIT License.