#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2024 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

""" Module sysctl

This module provides a class to execute sysctl commands.

"""


import subprocess

from .common import CommandString




class CommandSysctl:

    def __init__(self):
        pass

    def run(self, command):
        cmd = command.split()
        result = subprocess.run(cmd, capture_output=True, text=True)

        success_codes = [0]
        if result.returncode not in success_codes:
            raise subprocess.CalledProcessError(result.returncode, command, result.stdout, result.stderr)

        return result

    def disable_ipv6(self, interface, vid=None):

        if vid == None:
            interface_name = interface.name
        else:
            interface_name = f"{interface.name}/{vid}"

        cmd = CommandStringSysctlDisableIpv6(interface_name)

        self.run(cmd)
 


###############################################################################
# sysctl command strings                                                     #
###############################################################################

class CommandStringSysctlDisableIpv6(CommandString):

    # The syntax for non VLAN tagged and VLAN interfaces is respectively:
    # * sysctl -w net.ipv6.conf.${INTERFACE}.disable_ipv6=1
    # * sysctl -w net.ipv6.conf.${INTERFACE}/3.disable_ipv6=1

    def __init__(self, interface):

        template = '''
           sysctl -w net.ipv6.conf.$interface.disable_ipv6=1'''

        params = {
            "interface" : interface,
        }

        super().__init__(template, params)
