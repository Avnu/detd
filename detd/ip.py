#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

""" Module ip

This module provides a class to execute iproute2's ip commands.

"""




import subprocess

from .common import CommandString




class CommandIp:

    def __init__(self):
        pass


    def run(self, command):
        cmd = command.split()
        result = subprocess.run(cmd, capture_output=True, text=True)

        success_codes = [0]
        if result.returncode not in success_codes:
            raise subprocess.CalledProcessError(result.returncode, command, result.stdout, result.stderr)

        return result


    def set_vlan(self, interface, stream, mapping):

        soprio_to_pcp = transform_soprio_to_pcp(mapping.soprio_to_pcp)
        cmd = CommandStringIpLinkSetVlan(interface.name, stream.vid, soprio_to_pcp)

        self.run(str(cmd))


    def unset_vlan(self, interface, stream):
        cmd = CommandStringIpLinkUnsetVlan(interface.name, stream.vid)

        self.run(str(cmd))


def transform_soprio_to_pcp(soprio_to_pcp):
    mapping = []
    for soprio, pcp in soprio_to_pcp.items():
        mapping.append("{0}:{1}".format(soprio, pcp))

    return ' '.join(mapping)



###############################################################################
# ip command strings                                                          #
###############################################################################

class CommandStringIpLinkSetVlan (CommandString):

    def __init__(self, device, vid, soprio_to_pcp):

        template = '''
            ip link add
                    link     $device
                    name     $device.$id
                    type     vlan
                    protocol 802.1Q
                    id       $id
                    egress   $soprio_to_pcp'''

        params = {
            'device'        : device,
            'id'            : vid,
            'soprio_to_pcp' : soprio_to_pcp
        }

        super().__init__(template, params)




class CommandStringIpLinkUnsetVlan (CommandString):

    def __init__(self, device, vid):

        template = 'ip link delete $device.$id'

        params = {
            'device' : device,
            'id'     : vid
        }

        super().__init__(template, params)
