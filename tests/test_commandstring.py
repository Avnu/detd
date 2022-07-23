#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

import inspect
import re
import unittest

from detd import CommandStringIpLinkSetVlan
from detd import CommandStringIpLinkUnsetVlan
from detd import CommandStringEthtoolFeatures
from detd import CommandStringEthtoolSetCombinedChannels
from detd import CommandStringEthtoolSetSplitChannels
from detd import CommandStringEthtoolSetRing
from detd import CommandStringEthtoolGetDriverInformation




class TestCommandString(unittest.TestCase):


    def assert_commandstring_equal(self, one, another):

        harmonized_one = re.sub('\s+', ' ', str(one).strip())
        harmonized_another = re.sub('\s+', ' ', str(another).strip())

        self.assertEqual(harmonized_one, harmonized_another)




    def test_iplinksetvlan(self):

        interface_name = "eth0"
        stream_vid = 3
        soprio_to_pcp = {0:7, 1:6, 2:5, 3:4, 4:3, 5:2, 6:1, 7:0}

        cmd = CommandStringIpLinkSetVlan(interface_name, stream_vid, soprio_to_pcp)
        expected = """
            ip link add
                    link     eth0
                    name     eth0.3
                    type     vlan
                    protocol 802.1Q
                    id       3
                    egress   0:7 1:6 2:5 3:4 4:3 5:2 6:1 7:0"""

        self.assert_commandstring_equal(cmd, expected)




    def test_ethtoolfeatures(self):

        interface_name = "eth0"
        features = {'rxvlan': 'off', 'hw-tc-offload': 'on'}

        cmd = CommandStringEthtoolFeatures(interface_name, features)
        expected = 'ethtool --features eth0 rxvlan off hw-tc-offload on'

        self.assert_commandstring_equal(cmd, expected)




    def test_ethtoolsetsplitchannels(self):

        interface_name = "eth0"
        num_tx_queues = 4
        num_rx_queues = 6

        cmd = CommandStringEthtoolSetSplitChannels(interface_name, num_tx_queues, num_rx_queues)
        expected = 'ethtool --set-channels eth0 tx 4 rx 6'

        self.assert_commandstring_equal(cmd, expected)




    def test_ethtoolsetcombinedchannels(self):

        interface_name = "eth0"
        num_queues = 4

        cmd = CommandStringEthtoolSetCombinedChannels(interface_name, num_queues)
        expected = 'ethtool --set-channels eth0 combined 4'

        self.assert_commandstring_equal(cmd, expected)




    def test_ethtoolsetring(self):

        interface_name = "eth0"
        num_tx_rings = 1024
        num_rx_rings = 256

        cmd = CommandStringEthtoolSetRing(interface_name, num_tx_rings, num_rx_rings)
        expected = 'ethtool --set-ring eth0 tx 1024 rx 256'

        self.assert_commandstring_equal(cmd, expected)




    def test_ethtoolgetdriverinformation(self):

        interface_name = "eth0"

        cmd = CommandStringEthtoolGetDriverInformation(interface_name)
        expected = 'ethtool --driver eth0'

        self.assert_commandstring_equal(cmd, expected)






if __name__ == '__main__':
    unittest.main()
