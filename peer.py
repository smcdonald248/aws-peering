"""AWS VPC Peering connector."""

import boto3
import botocore
import yaml


with open('./config.yml', 'r') as file:
    config = yaml.load(file)

for peer in config['peer']:

    from_peer = peer['from']
    to_peer = peer['to']
    from_session = boto3.Session(
        profile_name=from_peer['profile'],
        region_name=peer['region']
    )

    from_client = from_session.client('ec2')
    from_resource = from_session.resource('ec2')

    for to in to_peer:
        to_session = boto3.Session(
            profile_name=to['profile'],
            region_name=peer['region']
        )
        to_client = to_session.client('ec2')
        to_resource = to_session.resource('ec2')

        print """Peering from VPC {} ({}) to {} in {}""".format(
            from_peer['vpc-id'],
            from_peer['profile'],
            to['vpc-id'],
            to['profile']
        )
        try:
            from_vpc = from_resource.Vpc(
                from_peer['vpc-id']
            )
            to_vpc = to_resource.Vpc(
                to['vpc-id']
            )
            print from_vpc.cidr_block
            print to_vpc.cidr_block
            from_name = [
                n for n in from_vpc.tags if n['Key'] == 'Name'
            ][0]['Value']

            to_name = [
                n for n in to_vpc.tags if n['Key'] == 'Name'
            ][0]['Value']

            response = from_client.create_vpc_peering_connection(
                DryRun=False,
                VpcId=from_peer['vpc-id'],
                PeerVpcId=str(to['vpc-id']),
                PeerOwnerId=str(to['account'])
            )

            connectionId = response[
                'VpcPeeringConnection'
            ]['VpcPeeringConnectionId']
            tags = [
                {
                    'Key': 'Name',
                    'Value': '{}---{}'.format(from_name, to_name)
                }
            ]
            from_client.create_tags(
                Resources=[connectionId],
                Tags=tags
            )
            to_client.create_tags(
                Resources=[connectionId],
                Tags=tags
            )
            target = to_client.accept_vpc_peering_connection(
                VpcPeeringConnectionId=connectionId
            )

            for table in from_peer['routetables']:
                s = from_resource.RouteTable(table)
                print s.create_route(
                    DryRun=False,
                    DestinationCidrBlock=to_vpc.cidr_block,
                    VpcPeeringConnectionId=connectionId
                )
                print "RouteTable {} updated with route".format(table)

            for table in to['routetables']:
                s = to_resource.RouteTable(table)
                print s.create_route(
                    DryRun=False,
                    DestinationCidrBlock=from_vpc.cidr_block,
                    VpcPeeringConnectionId=connectionId
                )

                print "RouteTable {} updated with route".format(table)

        except Exception as e:
            print e
