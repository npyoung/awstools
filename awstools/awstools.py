#!/usr/bin/env python
import click
import boto3
import subprocess
from os.path import expanduser, isfile

ec2 = boto3.resource('ec2')


def instances_by_name(name):
    response = ec2.instances.filter(
        Filters=[
            {
                'Name': 'tag:Name',
                'Values': [name]
            }
        ]
    )
    return response


@click.group()
def main():
    pass


@main.command()
@click.argument('name', type=str)
@click.argument('type', type=str, required=False)
def type(name, type=None):
    instances = instances_by_name(name)
    for instance in instances:
        if not type:
            print("{:s}: {:s}".format(instance.private_ip_address,
                                      instance.instance_type))
        else:
            instance.modify_attribute(
                InstanceType={
                    'Value': type
                }
            )

@main.command()
@click.argument('name', type=str)
def start(name):
    instances = instances_by_name(name)
    for instance in instances:
        instance.start()


@main.command()
@click.argument('name', type=str)
def attach(name):
    instances = instances_by_name(name)
    ips = [instance.private_ip_address for instance in instances]
    if len(ips) == 1:
        ip = ips[0]
        print("Logging into {:s}".format(ip))
        subprocess.call('ssh -oStrictHostKeyChecking=no ' + ip,
                        shell=True)
    else:
        raise ValueError("There were {:d} instances by that name".format(len(ips)))


@main.command()
@click.argument('name', type=str)
@click.argument('port', type=int, default=8888)
def forward(name, port):
    instances = instances_by_name(name)
    ips = [instance.private_ip_address for instance in instances]
    if len(ips) == 1:
        ip = ips[0]
        print("Forwarding port {:d} from {:s}".format(port, ip))
        socket_name = expanduser("~/.ssh/" + ip.replace('.', '-') + ".ctl")
        subprocess.Popen(["ssh",
                          "-oStrictHostKeyChecking=no",
                          "-S", socket_name,
                          "-fNTM",
                          "-L", "{0:d}:localhost:{0:d}".format(port),
                          ip])
    else:
        raise ValueError("There were {:d} instances by that name".format(len(ips)))


@main.command()
@click.argument('name', type=str)
def list_forwards(name):
    instances = instances_by_name(name)
    ips = [instance.private_ip_address for instance in instances]
    for ip in ips:
        socket_name = expanduser("~/.ssh/" + ip.replace('.', '-') + ".ctl")
        subprocess.Popen(["ssh",
                          "-S", socket_name,
                          "-TO", "check",
                          ip])


@main.command()
@click.argument('name', type=str)
@click.argument('port', type=int, default=8888)
def unforward(name, port):
    instances = instances_by_name(name)
    for instance in instances:
        ip = instance.private_ip_address
        socket_name = expanduser("~/.ssh/" + ip.replace('.', '-') + ".ctl")
        if isfile(socket_name):
            print("Closing open port forward: " + socket_name)
            subprocess.Popen(["ssh",
                              "-S", socket_name,
                              "-TO", "exit",
                              ip])


@main.command()
@click.argument('name', type=str)
def stop(name):
    instances = instances_by_name(name)
    for instance in instances:
        ip = instance.private_ip_address
        socket_name = expanduser("~/.ssh/" + ip.replace('.', '-') + ".ctl")
        if isfile(socket_name):
            print("Closing open port forward: " + socket_name)
            subprocess.Popen(["ssh",
                              "-S", socket_name,
                              "-TO", "exit",
                              ip])
        instances.stop()


if __name__ == "__main__":
    main()
