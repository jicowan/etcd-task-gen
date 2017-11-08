# etcd-task-gen
Generate an ECS task definition for running etcd in your cluster

The etcd-task-gen tool generates an ECS task definition for deploying a static etcd node in your ECS cluster. The definition can be used as a starting point for creating your own task definitions a production etcd cluster.

## Usage:

`$ python etcd.py`

## Example: 

```
{
    "family": "etcd", 
    "placementConstraints": [
        {
            "type": "memberOf", 
            "expression": "attribute:name == etcd0"
        }
    ], 
    "networkMode": "host", 
    "containerDefinitions": [
        {
            "mountPoints": [
                {
                    "sourceVolume": "etcd-vol", 
                    "readOnly": false, 
                    "containerPath": "/etc/ssl/certs"
                }
            ], 
            "name": "etcd", 
            "image": "quay.io/coreos/etcd:v2.3.8", 
            "disableNetworking": false, 
            "cpu": 1024, 
            "portMappings": [
                {
                    "protocol": "tcp", 
                    "containerPort": 2380, 
                    "hostPort": 2380
                }, 
                {
                    "protocol": "tcp", 
                    "containerPort": 2379, 
                    "hostPort": 2379
                }, 
                {
                    "protocol": "tcp", 
                    "containerPort": 4001, 
                    "hostPort": 4001
                }
            ], 
            "command": [
                "-name", 
                "etcd0", 
                "-advertise-client-urls", 
                "http://10.210.20.60:2379,http://10.210.20.60:4001", 
                "-listen-client-urls", 
                "http://0.0.0.0:2379,http://0.0.0.0:4001", 
                "-initial-advertise-peer-urls", 
                "http://10.210.20.60:2380", 
                "-listen-peer-urls", 
                "http://0.0.0.0:2380", 
                "-initial-cluster-token", 
                "etcd-cluster-1", 
                "-initial-cluster", 
                "etcd0=http://10.210.20.60:2380", 
                "-initial-cluster-state", 
                "new"
            ], 
            "memory": 256, 
            "privileged": true, 
            "essential": true
        }
    ], 
    "volumes": [
        {
            "host": {
                "sourcePath": "/usr/share/ca-certificates/"
            }, 
            "name": "etcd-vol"
        }
    ]
}
```

#### ECS CLI Commands
`aws ecs register-task-definition --cli-input-json file://<path_to_json_file>/nginx.json`

## More Info
#### What is a Task Definition?
A task definition is required to run Docker containers in Amazon ECS. Some of the parameters you can specify in a task definition include:

* Which Docker images to use with the containers in your task.
* How much CPU and memory to use with each container.
* The Docker networking mode to use for the containers in your task.

Please see the [Amazon ECS Documentation](http://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definitions.html) for more information on writing and running Task Definitions.

#### About Amazon ECS
Amazon EC2 Container Service (Amazon ECS) is a container management service that supports Docker containers and allows you to easily run applications on a managed cluster of Amazon EC2 instances. Amazon ECS eliminates the need for you to install, operate, and scale your own cluster management infrastructure. Learn more [here](https://aws.amazon.com/ecs).

#### Getting Help
* [Amazon ECS Documentation](http://docs.aws.amazon.com/AmazonECS/latest/developerguide/Welcome.html)
* [Amazon ECS Developer Forum](https://forums.aws.amazon.com/forum.jspa?forumID=187)
* [Stack Overflow](https://stackoverflow.com/questions/tagged/amazon-ecs)
* [AWS Support](https://aws.amazon.com/premiumsupport/)
