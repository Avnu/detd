#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

""" Module ip

This module provides a class to execute iproute2's ip commands.

"""




import subprocess
from pyroute2 import IPRoute
from pyroute2.protocols import ETH_P_8021Q

from .common import CommandString




class CommandIp:

    def __init__(self):
        pass


    def set_vlan(self, interface, stream, mapping):

        soprio_to_pcp = transform_soprio_to_pcp(mapping.soprio_to_pcp)

        name = "{}.{}".format(interface.name, stream.vid)

        parent_interface_index = get_interface_index(interface.name)

        if parent_interface_index is None:
            raise ValueError("Interface {} could not be found".format(interface.name))

        ip = IPRoute()
        ip.link('add',
                ifname = name,
                kind = "vlan",
                link = parent_interface_index,
                vlan_id = stream.vid,
                protocol = ETH_P_8021Q,
                vlan_egress_qos = soprio_to_pcp
                )


    def unset_vlan(self, interface, stream):
        name = "{}.{}".format(interface.name, stream.vid)
        ip = IPRoute()
        ip.link('delete', ifname=name)


def transform_soprio_to_pcp(soprio_to_pcp):
    mapping = []
    for soprio, pcp in soprio_to_pcp.items():
        mapping.append(('IFLA_VLAN_QOS_MAPPING', {'from': soprio, 'to': pcp}))

    return {'attrs': mapping}


def get_interface_index(name):
    ip = IPRoute()
    interface_index = ip.link_lookup(ifname=name)

    if not interface_index:
        return None

    return interface_index[0]

