import boto3
import json
import datetime
import jmespath
import requests
from pick import pick
ecs_client = boto3.client('ecs')
ec2_client = boto3.client('ec2')
etcd_discovery_service = 'https://discovery.etcd.io/new?size=3'
#creates a discovery url for creating a 3 node etcd cluster
discovery_url = requests.get(etcd_discovery_service).text

def datetime_handler(x):
    '''Convert datetime into isoformat'''
    if isinstance(x, datetime.datetime):
        return x.isoformat()
    raise TypeError("Unknown type")

def get_cluster_instances(ecs_cluster_name):
    '''Returns a list of the ECS cluster instances in the cluster'''
    ecs_container_instances = ecs_client.list_container_instances(cluster=ecs_cluster_name)['containerInstanceArns']
    return ecs_container_instances

def get_instance_resources(ecs_cluster_name, ecs_instance_arn):
    '''Returns the EC2 instanceId and a list of the TCP ports that are in use on that instance'''
    ec2_instance_id = ecs_client.describe_container_instances(cluster=ecs_cluster_name, containerInstances=[ecs_instance_arn])['containerInstances'][0]['ec2InstanceId']
    ecs_instance_resources = ecs_client.describe_container_instances(cluster=ecs_cluster_name, containerInstances=[ecs_instance_arn])['containerInstances'][0]['registeredResources']
    tcp_ports = jmespath.search('[?name==`PORTS`].stringSetValue', ecs_instance_resources)[0]
    return ec2_instance_id, tcp_ports

def is_not_target(ec2_instance_id, ports):
    '''Determines whether the etcd ports are free on the container instances'''
    for port in ports:
        if port == '2379' or port == '2380' or port == '4001':
            print "Port %s on instance %s is in use." % (port, ec2_instance_id)
            not_target = True
            break
        else:
            not_target = False
    return not_target

def create_task_definition(host_ip):
    '''Creates task definition for etcd'''
    filename = 'taskdef.json'
    with open(filename, 'r') as f:
        taskdef = json.load(f)

        taskdef['family'] = 'etcd'
        taskdef['networkMode'] = 'host'
        taskdef['containerDefinitions'][0]['name'] = 'etcd'
        taskdef['containerDefinitions'][0]['image'] = 'quay.io/coreos/etcd:v2.3.8'
        taskdef['containerDefinitions'][0]['cpu'] = 1024
        taskdef['containerDefinitions'][0]['memory'] = 256
        taskdef['volumes'] = {
            'name': 'etcd-vol',
            'host': {
                'sourcePath': '/usr/share/ca-certificates/'
            }
                             },
        taskdef['containerDefinitions'][0]['mountPoints'] = {
            'sourceVolume': 'etcd-vol',
            'containerPath': '/etc/ssl/certs',
            'readOnly': False
                                                            },
        taskdef['containerDefinitions'][0]['portMappings'] = {
            'hostPort': 2380,
            'protocol': 'tcp',
            'containerPort': 2380
                                                             }, \
                                                             {
            'hostPort': 2379,
            'protocol': 'tcp',
            'containerPort': 2379
                                                             }, \
                                                             {
            'hostPort': 4001,
            'protocol': 'tcp',
            'containerPort': 4001
                                                             }
        taskdef['containerDefinitions'][0]['command'] = ['-name', 'etcd0', \
            '-advertise-client-urls', 'http://' + host_ip + ':2379,http://' + host_ip + ':4001', \
            '-listen-client-urls', 'http://0.0.0.0:2379,http://0.0.0.0:4001', \
            '-initial-advertise-peer-urls', 'http://' + host_ip + ':2380', \
            '-listen-peer-urls', 'http://0.0.0.0:2380', \
            '-initial-cluster-token', 'etcd-cluster-1', \
            '-initial-cluster', 'etcd0=http://' + host_ip + ':2380', \
            '-initial-cluster-state', 'new'] # to use the discovery service add , \ to this line and uncomment the next line
            #'-discovery', discovery_url]
        taskdef['placementConstraints'] = {
            'expression': 'attribute:name == etcd0',
            'type':'memberOf'
        },

    with open('etcd-taskdef.json', 'w') as f:
        json.dump(taskdef, f, indent=4, encoding='utf-8')

def set_instance_attributes(ecs_container_instance_id, ecs_cluster_name):
    ecs_client.put_attributes(
        cluster=ecs_cluster_name,
        attributes=[
            {
                'name': 'name',
                'value': 'etcd0',
                'targetType': 'container-instance',
                'targetId': ecs_container_instance_id
            },
        ]
    )

def get_container_instance_arn(ec2_instance_id,ecs_cluster_name):
    '''Returns the container instance id of the ec2 instance'''
    ecs_container_instances = ecs_client.list_container_instances(cluster=ecs_cluster_name)['containerInstanceArns']
    for ecs_container_instance in ecs_container_instances:
        ecs_container_instance_id = ecs_container_instance[ecs_container_instance.find('/')+1:]
        ecs_container_instances_attributes = ecs_client.describe_container_instances(cluster=ecs_cluster_name, containerInstances=[ecs_container_instance_id])
        if ecs_container_instances_attributes['containerInstances'][0]['ec2InstanceId']==ec2_instance_id:
            return ecs_container_instance_id


ecs_cluster_name = raw_input('Cluster name: ')
ecs_instance_arns = get_cluster_instances(ecs_cluster_name)
targets = {'instances':[]}
for ecs_instance_arn in ecs_instance_arns:
    ecs_instance_resources = get_instance_resources(ecs_cluster_name, ecs_instance_arn)
    ec2_instance_id = ecs_instance_resources[0]
    ports = ecs_instance_resources[1]
    if is_not_target(ec2_instance_id, ports):
        print '%s is not a target for etcd' % (ec2_instance_id)
    else:
        #print '%s is a target for etcd' % (ec2_instance_id)
        ec2_private_ip = ec2_client.describe_instances(InstanceIds = [ec2_instance_id])['Reservations'][0]['Instances'][0]['PrivateIpAddress']
        targets['instances'].append({'instanceId':ec2_instance_id, 'hostIp': ec2_private_ip})

title = 'Please choose the host IP for etcd: '
host_ip, index = pick(jmespath.search('instances[*].hostIp', targets), title)

#re-assign value of ec2_instance_id after making a selection
ec2_instance_id = list(filter(lambda x: x['hostIp'] == host_ip, targets['instances']))[0]['instanceId']

ecs_container_instance_id = get_container_instance_arn(ec2_instance_id,ecs_cluster_name)
set_instance_attributes(ecs_container_instance_id, ecs_cluster_name)

create_task_definition(host_ip)
