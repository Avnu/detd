#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

""" Module ethtool

This module provides a class to execute ethtool commands.

"""




import subprocess

from .common import CommandString




class CommandEthtool:

    def __init__(self):
        pass

    def run(self, command):
        cmd = command.split()
        result = subprocess.run(cmd, capture_output=True, text=True)

        # ethtool returns 80 when the configuration does not change
        # so we need to handle this case manually because check=True
        # will just interpret any return code different than 0 as error
        success_codes = [0, 80]
        if result.returncode not in success_codes:
            raise subprocess.CalledProcessError(result.returncode, command, result.stdout, result.stderr)

        return result


    def get_driver_information(self, interface):
        cmd = CommandStringEthtoolGetDriverInformation(interface.name)

        result = self.run(cmd)

        return result.stdout.splitlines()


    def set_eee(self, interface, eee):
        check_eee(eee)
        cmd = CommandStringEthtoolSetEee(interface.name, eee)

        self.run(cmd)


    def set_rings(self, interface):
        cmd = CommandStringEthtoolSetRing(interface.name, interface.device.num_tx_ring_entries, interface.device.num_rx_ring_entries)

        self.run(cmd)


    def get_channels_information(self, interface):
        cmd = CommandStringEthtoolGetChannelsInformation(interface.name)

        result = self.run(cmd)

        return result.stdout.splitlines()


    def get_information(self, interface):
        cmd = CommandStringEthtoolGetInformation(interface.name)

        result = self.run(cmd)

        return result.stdout.splitlines()


    def set_split_channels(self, interface):
        cmd = CommandStringEthtoolSetSplitChannels(interface.name, interface.device.num_tx_queues, interface.device.num_rx_queues)

        self.run(cmd)


    def set_combined_channels(self, interface):
        cmd = CommandStringEthtoolSetCombinedChannels(interface.name, interface.device.num_tx_queues)

        self.run(cmd)


    def set_features(self, interface):
        cmd = CommandStringEthtoolFeatures(interface.name, interface.device.features)

        self.run(cmd)

    def set_features_ingress(self, interface):
        cmd = CommandStringEthtoolFeaturesIngress(interface.name, interface.device.features)

        self.run(cmd)


def check_eee(eee):
    if eee not in ["on", "off"]:
        raise ValueError("Invalid value to configure EEE with Ethtool: {}".format(eee))




###############################################################################
# ethtool command strings                                                     #
###############################################################################

class CommandStringEthtoolSetEee(CommandString):

    def __init__(self, interface, eee):

        template = '''
           ethtool --set-eee $interface
                             eee $eee'''

        params = {
            "interface" : interface,
            "eee"       : eee
        }

        super().__init__(template, params)




class CommandStringEthtoolFeatures(CommandString):

    def __init__(self, interface, features):

        template = 'ethtool --features $interface $features'

        params = {
            'interface' : interface,
            'features'  : ""
        }
        for feature, value in features.items():
            params['features'] += "{0} {1} ".format(feature, value)

        super().__init__(template, params)

class CommandStringEthtoolFeaturesIngress(CommandString):

    def __init__(self, interface, features):

        template = 'ethtool --features $interface rxvlan off hw-tc-offload on'

        params = {
            'interface' : interface,
            'features'  : ""
        }
        for feature, value in features.items():
            params['features'] += "{0} {1} ".format(feature, value)

        super().__init__(template, params)




class CommandStringEthtoolSetSplitChannels(CommandString):

    def __init__(self, interface, num_tx_queues, num_rx_queues):

        template = '''
           ethtool --set-channels $interface
                   tx $num_tx_queues
                   rx $num_rx_queues'''

        params = {
            'interface'     : interface,
            'num_tx_queues' : num_tx_queues,
            'num_rx_queues' : num_rx_queues
        }

        super().__init__(template, params)




class CommandStringEthtoolSetCombinedChannels(CommandString):

    def __init__(self, interface, num_queues):

        template = '''
           ethtool --set-channels $interface
                   combined $num_queues'''

        params = {
            'interface'  : interface,
            'num_queues' : num_queues
        }

        super().__init__(template, params)




class CommandStringEthtoolSetRing(CommandString):

    """
    Set number of Tx and Rx ring buffers entries.

    Each entry holds an SKB descriptor.
    """

    def __init__(self, interface, num_tx_ring_entries, num_rx_ring_entries):


        template = '''
           ethtool --set-ring $interface
                   tx $num_tx_ring_entries
                   rx $num_rx_ring_entries'''

        params = {
            'interface'           : interface,
            'num_tx_ring_entries' : num_tx_ring_entries,
            'num_rx_ring_entries' : num_rx_ring_entries
        }

        super().__init__(template, params)




class CommandStringEthtoolGetDriverInformation(CommandString):

    def __init__(self, interface):

        template = 'ethtool --driver $interface'

        params = {'interface' : interface}

        super().__init__(template, params)




class CommandStringEthtoolGetChannelsInformation(CommandString):

    def __init__(self, interface):

        template = 'ethtool --show-channels $interface'

        params = {'interface' : interface}

        super().__init__(template, params)




class CommandStringEthtoolGetInformation(CommandString):

    def __init__(self, interface):

        template = 'ethtool $interface'

        params = {'interface' : interface}

        super().__init__(template, params)
