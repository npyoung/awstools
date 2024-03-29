#!/usr/bin/env python
import click
import boto3
from prettytable import PrettyTable
from retrying import retry

from os.path import expanduser, isfile
import re
import subprocess
from time import sleep, time
import webbrowser


FORWARD_DELAY = 10 # seconds to wait for instance ssh to be up


ec2 = boto3.resource('ec2')


def click_warn(msg):
    click.secho(msg, fg='yellow')


def click_error(msg):
    click.secho(msg, fg='red')
    click.Abort()


def click_info(msg):
    click.echo(msg)


def instance_name_complete(ctx, param, incomplete):
    instances = instances_by_name(incomplete + "*")
    names = []
    for instance in instances:
        for tag in instance.tags:
            if tag['Key'] == 'Name':
                names.append(tag['Value'])
    return names


def instances_by_name(name):
    response = ec2.instances.filter(
        Filters=[
            {
                'Name': 'tag:Name',
                'Values': [name]
            }
        ]
    )
    instances = [x for x in response]
    if len(instances) == 0:
        click_error(f"No instances found by name {name:s}")
    else:
        click_info(f"Found {len(instances):d} instances by name {name:s}")
        
    return instances


def wait(instance, state, timeout=None, interval=0.5):
    t0 = time()
    while instance.state['Name'] != state:
        instance.reload()
        if (timeout is not None) and (time() - t0 > timeout):
            return False
        else:
            sleep(interval)
    return True


@retry(wait_exponential_multiplier=1000, wait_exponential_max=120 * 1000)
def _forward(instance, from_port=8888, to_port=8888):
    """Map a port (default: 8888) from your local machine to a named EC2 instance."""
    ip = instance.public_ip_address

    if to_port == -1:
        to_port = from_port

    click_info("Forwarding port {:d} to {:s}:{:d}".format(from_port, ip, to_port))
    socket_name = expanduser("~/.ssh/" + ip.replace('.', '-') + ".ctl")

    cmd = ["ssh",
           "-oStrictHostKeyChecking=no",
           "-S", socket_name,
           "-fNT"
           ]

    if isfile(socket_name):
        click_info("Using existing control socket at {:s}".format(socket_name))
    else:
        cmd.append("-M")

    cmd.extend(["-L",
                "{:d}:localhost:{:d}".format(from_port, to_port),
                "ubuntu@{:s}".format(ip)
                ])

    subprocess.Popen(cmd)
    webbrowser.open_new_tab("http://localhost:{:d}".format(from_port))


@click.group()
def main():
    pass


@main.command()
@click.option('--name', '-n', type=str, default=None)
@click.option('--state', '-s', type=str, default=None)
@click.option('--type', '-t', type=str, default=None)
@click.option('--key', '-k', type=str, default=None)
def list(name, state, type, key):
    """List all EC2 instances with some basic info, optionally specifying a list of states."""
    filters = []

    if name:
        filters.append({
            'Name': 'tag:Name',
            'Values': [name]
        })

    if state:
        filters.append({
            'Name': 'instance-state-name',
            'Values': [state]
        })

    if type:
        filters.append({
            'Name': 'instance-type',
            'Values': [type]
        })

    if key:
        filters.append({
            'Name': 'key-name',
            'Values': [key]
        })

    if len(filters) > 0:
        response = ec2.instances.filter(
            Filters=filters
        )
    else:
        response = ec2.instances.all()

    table = PrettyTable(['Name', 'State', 'Type', 'Public IP', 'Key'])
    table.align = 'l'
    for instance in response:
        name = ""
        for tag in instance.tags:
            if tag['Key'] == 'Name':
                name = tag['Value']

        state = instance.state['Name']

        table.add_row([
            name, state, instance.instance_type, instance.public_ip_address, instance.key_name
        ])

    click_info(table)


@main.command()
@click.argument('identifier', type=str)
@click.argument('name', type=str)
def name(identifier):
    id_regex = r"^i-[\d\w]{17}%"
    #ip_regex = r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$"
    #dns_regex = r"^ec2-(?:[0-9]{1,3}-){3}[0-9]{1,3}.[\S]+.compute.amazonaws.com$"

    if re.fullmatch(id_regex, identifier):
        ec2.create_tags(Resources=[identifier], Tags=[{'Key': 'Name', 'Value': name}])
    else:
        raise ValueError("identifier is not a valid EC2 instance ID")


@main.command()
@click.argument('name', type=str, shell_complete=instance_name_complete)
@click.argument('type', type=str, required=False)
def type(name, type=None):
    """Get or set the instance type of a named EC2 instance."""
    instances = instances_by_name(name)
    for instance in instances:
        if not type:
            click_info(
                "{:s}: {:s}".format(
                    instance.instance_id,
                    instance.instance_type
                )
            )
        else:
            instance.modify_attribute(
                InstanceType={
                    'Value': type
                }
            )


@main.command()
@click.argument('original', type=str, shell_complete=instance_name_complete)
@click.argument('new', type=str)
def name(original, new):
    """Name an instance"""
    instances = instances_by_name(original)
    for instance in instances:
        instance.create_tags(Tags=[{'Key': 'Name',
                                    'Value': new}])
        click_info(original + " ==> " + new)


@main.command()
@click.argument('name', type=str, shell_complete=instance_name_complete)
def status(name):
    """Get or set the status (starting, started, stopped, etc) of a named EC2 instance."""
    instances = instances_by_name(name)
    for instance in instances:
        click_info("{:s}".format(instance.state['Name']))

@main.command()
@click.argument('name', type=str, shell_complete=instance_name_complete)
@click.option('--forward', '-f', is_flag=True, default=False)
def start(name, forward):
    """Start an EC2 instance and wait until it's running."""
    instances = instances_by_name(name)
    for instance in instances:
        instance.start()
    click_info("Waiting for instances to start...")
    for instance in instances:
        wait(instance, 'running')
    if forward:
        sleep(FORWARD_DELAY)
        for instance in instances:
            _forward(instance)
            break


@main.command()
@click.argument('name', type=str, shell_complete=instance_name_complete)
def ip(name):
    """List the public and private IPs of a named instance."""
    instances = instances_by_name(name)
    for instance in instances:
        click_info(name)
        click_info("  Public:  {:}".format(instance.public_ip_address))
        click_info("  Private: {:}".format(instance.private_ip_address))


@main.command()
@click.argument('name', type=str, shell_complete=instance_name_complete)
def attach(name):
    """Drop into a shell connection to a named instance via SSH."""
    instances = instances_by_name(name)
    ips = [instance.public_ip_address for instance in instances]
    if len(ips) == 1:
        ip = ips[0]
        click_info("Logging into {:s}".format(ip))
        cmd = 'ssh -t -oStrictHostKeyChecking=no ' + "ubuntu@{:s} ".format(ip) + "'screen -xRR'"
        click_info("Running " + cmd)
        subprocess.call(cmd, shell=True)
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
            substituted_paths.append("ubuntu@" + new_path)
        else:
            substituted_paths.append(path)

    click_info("Rsyncing from {:s} to {:s}".format(*substituted_paths))
    subprocess.Popen(["rsync",
                      "-arvz",
                      "--progress",
                      "{:s}".format(substituted_paths[0]),
                      "{:s}".format(substituted_paths[1])])


@main.command()
@click.argument('name', type=str, shell_complete=instance_name_complete)
@click.argument('from_port', type=int, default=8888)
@click.argument('to_port', type=int, default=-1)
def forward(name, from_port, to_port):
    """Map a port (default: 8888) from your local machine to a named EC2 instance."""
    for instance in instances_by_name(name):
        _forward(instance, from_port, to_port)
        break


@main.command()
@click.argument('name', type=str, shell_complete=instance_name_complete)
def list_forwards(name):
    instances = instances_by_name(name)
    ips = [instance.public_ip_address for instance in instances]
    for ip in ips:
        socket_name = expanduser("~/.ssh/" + ip.replace('.', '-') + ".ctl")
        subprocess.Popen(["ssh",
                          "-S", socket_name,
                          "-TO", "check",
                          ip])


@main.command()
@click.argument('name', type=str, shell_complete=instance_name_complete)
@click.argument('port', type=int, default=8888)
def unforward(name, port):
    instances = instances_by_name(name)
    for instance in instances:
        ip = instance.public_ip_address
        socket_name = expanduser("~/.ssh/" + ip.replace('.', '-') + ".ctl")
        if isfile(socket_name):
            click_info("Closing open port forward: " + socket_name)
            subprocess.Popen(["ssh",
                              "-S", socket_name,
                              "-TO", "exit",
                              ip])


@main.command()
@click.argument('name', type=str, shell_complete=instance_name_complete)
@click.option('--block/--no-block', default=True)
def reboot(name, block):
    """Reboot a named EC2 instance and optionally wait for the instance to be back online."""
    instances = instances_by_name(name)
    for instance in instances:
        instance.reboot()
    if block:
        click_info("Waiting on instances to stop")
        for instance in instances:
            wait(instance, 'running')
    for instance in instances:
        click_info("{:s} is now {:s}".format(ip.private_ip_address, instance.state['Name']))


@main.command()
@click.argument('name', type=str, shell_complete=instance_name_complete)
@click.option('--block/--no-block', default=False)
def stop(name, block):
    """Stop a named EC2 instance and optionally wait for completed shutdown."""
    instances = instances_by_name(name)
    for instance in instances:
        ip = instance.public_ip_address
        socket_name = expanduser("~/.ssh/" + ip.replace('.', '-') + ".ctl")
        if isfile(socket_name):
            click_info("Closing open port forward: " + socket_name)
            subprocess.Popen(["ssh",
                              "-S", socket_name,
                              "-TO", "exit",
                              ip])
    instances.stop()
    if block:
        click_info("Waiting on instances to stop")
        for instance in instances:
            wait(instance, 'stopped')
    for instance in instances:
        click_info("{:s} is now {:s}".format(instance.instance_id, instance.state['Name']))


@main.command()
@click.argument('name', type=str, shell_complete=instance_name_complete)
def terminate(name):
    """Terminate a named EC2 instance."""
    instances = instances_by_name(name)
    click.confirm('Are you sure you want to delete these instances?', abort=True)
    for instance in instances:
        p = instance.public_ip_address
        socket_name = expanduser("~/.ssh/" + ip.replace('.', '-') + ".ctl")
        if isfile(socket_name):
            click_info("Closing open port forward: " + socket_name)
            subprocess.Popen(["ssh",
                              "-S", socket_name,
                              "-TO", "exit",
                              ip])
    instances.terminate()


if __name__ == "__main__":
    main()
