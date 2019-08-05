#!/usr/bin/env python
import click
import boto3
import subprocess
from os.path import expanduser, isfile
from time import sleep, time
import webbrowser

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
    if len([x for x in response]) == 0:
        print("No instances found by that name")
    return response

def wait(instance, state, timeout=None, interval=0.5):
    t0 = time()
    while instance.state['Name'] != state:
        instance.reload()
        if (timeout is not None) and (time() - t0 > timeout):
            return False
        else:
            sleep(interval)
    return True

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
def status(name):
    instances = instances_by_name(name)
    for instance in instances:
        print("{:s}".format(instance.state['Name']))

@main.command()
@click.argument('name', type=str)
def start(name):
    instances = instances_by_name(name)
    for instance in instances:
        instance.start()
    print("Waiting for instances to start")
    for instance in instances:
        wait(instance, 'running')


@main.command()
@click.argument('name', type=str)
def ip(name):
    instances = instances_by_name(name)
    ips = [instance.public_ip_address for instance in instances]
    for ip in ips:
        print(ip)


@main.command()
@click.argument('name', type=str)
def attach(name):
    instances = instances_by_name(name)
    ips = [instance.public_ip_address for instance in instances]
    if len(ips) == 1:
        ip = ips[0]
        print("Logging into {:s}".format(ip))
        subprocess.call('ssh -oStrictHostKeyChecking=no ' + "ubuntu@{:s}".format(ip),
                        shell=True)
    else:
        raise ValueError("There were {:d} instances by that name".format(len(ips)))


@main.command()
@click.argument('frm', type=str)
@click.argument('to', type=str)
def sync(frm, to):
    substituted_paths = []
    for path in [frm, to]:
        if ':' in path:
            name, trail = path.split(':', 1)
            instances = instances_by_name(name)
            ips = [instance.public_ip_address for instance in instances]
            if len(ips) == 1:
                ip = ips[0]
            else:
                raise ValueError("There were {:d} instances by that name".format(len(ips)))
            new_path = ':'.join([ip, trail])
            substituted_paths.append(new_path)
        else:
            substituted_paths.append(path)

    print("Rsyncing from {:s} to {:s}".format(*substituted_paths))
    subprocess.Popen(["rsync",
                      "-arvz",
                      "--progress",
                      "{:s}".format(substituted_paths[0]),
                      "{:s}".format(substituted_paths[1])])


@main.command()
@click.argument('name', type=str)
@click.argument('port', type=int, default=8888)
def forward(name, port):
    instances = instances_by_name(name)
    ips = [instance.public_ip_address for instance in instances]
    if len(ips) == 1:
        ip = ips[0]
        print("Forwarding port {:d} from {:s}".format(port, ip))
        socket_name = expanduser("~/.ssh/" + ip.replace('.', '-') + ".ctl")
        subprocess.Popen(["ssh",
                          "-oStrictHostKeyChecking=no",
                          "-S", socket_name,
                          "-fNTM",
                          "-L", "{0:d}:localhost:{0:d}".format(port),
                          "ubuntu@{:s}".format(ip)])
        webbrowser.open_new_tab("http://localhost:{0:d}".format(port))
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
@click.option('--block/--no-block', default=True)
def reboot(name, block):
    instances = instances_by_name(name)
    for instance in instances:
        instance.reboot()
    if block:
        print("Waiting on instances to stop")
        for instance in instances:
            wait(instance, 'running')
    for instance in instances:
        print("{:s} is now {:s}".format(ip.private_ip_address, instance.state['Name']))


@main.command()
@click.argument('name', type=str)
@click.option('--block/--no-block', default=False)
def stop(name, block):
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
    if block:
        print("Waiting on instances to stop")
        for instance in instances:
            wait(instance, 'stopped')
    for instance in instances:
        print("{:s} is now {:s}".format(instance.private_ip_address, instance.state['Name']))


if __name__ == "__main__":
    main()
