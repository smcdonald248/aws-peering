"""AWS VPC Peering connector."""

import boto3
import botocore
import csv
import time

with open('config.csv') as csv_file:
    config = csv.reader(csv_file, delimiter=',')
    line_count = 0

    for row in config:
        if line_count == 0:            
            lables = [row[0], row[1], row[2], row[3], row[8]]
            line_count += 1
        else:
            from_peer = {lables[0]:row[0], lables[1]:row[1], lables[2]:row[2], lables[3]:row[3]}
            to_peer = {lables[0]:row[4], lables[1]:row[5], lables[2]:row[6], lables[3]:row[7],lables[4]:row[8]}
            #print(f'\t{from_peer} will peer with {to_peer}')

            from_session = boto3.Session(
                profile_name=from_peer['profile'],
                region_name=from_peer['region']
            )
            
            from_client = from_session.client('ec2')
            from_resource = from_session.resource('ec2')

            #for to in to_peer:
            to_session = boto3.Session(
            profile_name=to_peer['profile'],
            region_name=to_peer['region']
            )
            to_client = to_session.client('ec2')
            to_resource = to_session.resource('ec2')

            print("""Peering from VPC {} ({}, {}) to {} ({}, {})""".format(
            from_peer['vpc-id'],
            from_peer['profile'],
            from_peer['region'],
            to_peer['vpc-id'],
            to_peer['profile'],
            to_peer['region']
            ))
            
            try:
                from_vpc = from_resource.Vpc(
                    from_peer['vpc-id']
                )
                to_vpc = to_resource.Vpc(
                    to_peer['vpc-id']
                )
                                
                from_name = [
                    n for n in from_vpc.tags if n['Key'] == 'Name'
                ][0]['Value']

                to_name = [
                    n for n in to_vpc.tags if n['Key'] == 'Name'
                ][0]['Value']

                print("""CIDR Block of {}: {}""".format(from_name, from_vpc.cidr_block))
                print("""CIDR Block of {}: {}""".format(to_name, to_vpc.cidr_block))            
                
                print("Creating Peer Connection . . .")
                response = from_client.create_vpc_peering_connection(
                    DryRun=False,
                    VpcId=from_peer['vpc-id'],
                    PeerVpcId=str(to_peer['vpc-id']),
                    PeerOwnerId=str(to_peer['account']),
                    PeerRegion=str(to_peer['region'])
                )

                print("Sleeping for 5 seconds as we wait for the pcx to come up . . .")
                time.sleep(5)

                connectionId = response[
                    'VpcPeeringConnection'
                ]['VpcPeeringConnectionId']
                tags = [
                    {
                        'Key': 'Name',
                        'Value': '{}---{}'.format(from_name, to_name)
                    }
                ]
                
                print("""Adding tags to {}""".format(connectionId))
                from_client.create_tags(
                    Resources=[connectionId],
                    Tags=tags
                )
                to_client.create_tags(
                    Resources=[connectionId],
                    Tags=tags
                )
                
                print("""Accepting Peer Connection {}""".format(connectionId))
                target = to_client.accept_vpc_peering_connection(
                    VpcPeeringConnectionId=connectionId
                )
                
                print("""Modifying Route Table {}""".format(from_peer['routetb']))
                s = from_resource.RouteTable(from_peer['routetb'])
                print(s.create_route(
                    DryRun=False,
                    DestinationCidrBlock=to_vpc.cidr_block,
                    VpcPeeringConnectionId=connectionId
                ))
                print("RouteTable {} updated with route".format(from_peer['routetb']))

                print("""Modifying Route Table {}""".format(to_peer['routetb']))
                s = to_resource.RouteTable(to_peer['routetb'])
                print(s.create_route(
                    DryRun=False,
                    DestinationCidrBlock=from_vpc.cidr_block,
                    VpcPeeringConnectionId=connectionId
                ))
                print("RouteTable {} updated with route".format(to_peer['routetb']))
            except Exception as e:
                print(e)
            line_count += 1
    print(f'Created {line_count-1} Peers.')

"""
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

        print """'''Peering from VPC {} ({}) to {} in {}'''""".format(
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
"""