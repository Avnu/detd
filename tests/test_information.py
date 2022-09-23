#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

import unittest
import subprocess
from unittest.mock import patch
from unittest import mock
from unittest.mock import mock_open
from subprocess import CalledProcessError

from detd import SystemInformation
from detd import CommandEthtool

import os

from .common import *


class TestSystemInformation(unittest.TestCase):


    def setUp(self):

        env_var = os.getenv("DETD_TESTENV")
        if env_var == "HOST":
            self.mode = TestMode.HOST
        elif env_var == "TARGET":
            self.mode = TestMode.TARGET
        else:
            self.mode = TestMode.HOST


    def test_getpcidbdf_success(self):

        driver_information = [
            'driver: st_gmac',
            'version: 5.17.1-rt17',
            'firmware-version:',
            'expansion-rom-version:',
            'bus-info: 0000:00:1d.1',
            'supports-statistics: yes',
            'supports-test: no',
            'supports-eeprom-access: no',
            'supports-register-dump: yes',
            'supports-priv-flags: no'
        ]

        with RunContext(self.mode):
            sysinfo = SystemInformation()
            interface = Interface("eth0")

        with mock.patch.object(CommandEthtool, 'get_driver_information', return_value=driver_information):
            domain, bus, device, function = sysinfo.get_pci_dbdf(interface)
            self.assertEqual(domain, "0000")
            self.assertEqual(bus, "00")
            self.assertEqual(device, "1d")
            self.assertEqual(function, "1")


    def test_gethex(self):

        vendor_or_product_id = '0x8086'
        mocked_open = mock.mock_open(read_data=vendor_or_product_id)
        with mock.patch('builtins.open', mocked_open):
            sysinfo = SystemInformation()
            filename = "da/file"
            value = sysinfo.get_hex(filename)
            self.assertEqual(value, '8086')


    def test_getchannelsinformation_success(self):

        # Using a sequence of different numbers in order to check correct parsing
        # E.g. the max and current values are inconsistent
        channels_information = [
            'Channel parameters for eth0:',
            'Pre-set maximums:',
            'RX:             1',
            'TX:             2',
            'Other:          3',
            'Combined:       4',
            'Current hardware settings:',
            'RX:             5',
            'TX:             6',
            'Other:          7',
            'Combined:       8',
        ]



        with RunContext(self.mode):
            sysinfo = SystemInformation()
            interface = Interface("eth0")

        with mock.patch.object(CommandEthtool, 'get_channels_information', return_value=channels_information):
            max_rx, max_tx = sysinfo.get_channels_information(interface)
            self.assertEqual(max_rx, "1")
            self.assertEqual(max_tx, "2")


    def test_getrate_success(self):
        device_info = [
            'Settings for eth0:',
            '        Supported ports: [ TP    MII ]',
            '        Supported link modes:   10baseT/Full',
            '                                100baseT/Full',
            '                                1000baseT/Full',
            '        Supported pause frame use: Symmetric Receive-only',
            '        Supports auto-negotiation: Yes',
            '        Supported FEC modes: Not reported',
            '        Advertised link modes:  10baseT/Full',
            '                                100baseT/Full',
            '                                1000baseT/Full',
            '        Advertised pause frame use: Symmetric Receive-only',
            '        Advertised auto-negotiation: Yes',
            '        Advertised FEC modes: Not reported',
            '        Link partner advertised link modes:  10baseT/Full',
            '                                             100baseT/Full',
            '                                             1000baseT/Full',
            '        Link partner advertised pause frame use: No',
            '        Link partner advertised auto-negotiation: Yes',
            '        Link partner advertised FEC modes: Not reported',
            '        Speed: 1000Mb/s',
            '        Duplex: Full',
            '        Auto-negotiation: on',
            '        master-slave cfg: preferred slave',
            '        master-slave status: slave',
            '        Port: Twisted Pair',
            '        PHYAD: 1',
            '        Transceiver: external',
            '        MDI-X: Unknown',
            '        Supports Wake-on: ubgs',
            '        Wake-on: d',
            '        SecureOn password: 00:00:00:00:00:00',
            '        Current message level: 0x0000003f (63)',
            '                               drv probe link timer ifdown ifup',
            '        Link detected: yes',
      ]


        with RunContext(self.mode):
            sysinfo = SystemInformation()
            interface = Interface("eth0")

        with mock.patch.object(CommandEthtool, 'get_information', return_value=device_info):
            rate = sysinfo.get_rate(interface)
            self.assertEqual(rate, 1000 * 1000 * 1000)


    def test_getrate_unknown(self):
        device_info = [
            'Settings for eth0:',
            '        Supported ports: [ TP    MII ]',
            '        Supported link modes:   10baseT/Full',
            '                                100baseT/Full',
            '                                1000baseT/Full',
            '        Supported pause frame use: Symmetric Receive-only',
            '        Supports auto-negotiation: Yes',
            '        Supported FEC modes: Not reported',
            '        Advertised link modes:  10baseT/Full',
            '                                100baseT/Full',
            '                                1000baseT/Full',
            '        Advertised pause frame use: Symmetric Receive-only',
            '        Advertised auto-negotiation: Yes',
            '        Advertised FEC modes: Not reported',
            '        Link partner advertised link modes:  10baseT/Full',
            '                                             100baseT/Full',
            '                                             1000baseT/Full',
            '        Link partner advertised pause frame use: No',
            '        Link partner advertised auto-negotiation: Yes',
            '        Link partner advertised FEC modes: Not reported',
            '        Speed: Unknown!',
            '        Duplex: Full',
            '        Auto-negotiation: on',
            '        master-slave cfg: preferred slave',
            '        master-slave status: slave',
            '        Port: Twisted Pair',
            '        PHYAD: 1',
            '        Transceiver: external',
            '        MDI-X: Unknown',
            '        Supports Wake-on: ubgs',
            '        Wake-on: d',
            '        SecureOn password: 00:00:00:00:00:00',
            '        Current message level: 0x0000003f (63)',
            '                               drv probe link timer ifdown ifup',
            '        Link detected: yes',
      ]


        with RunContext(self.mode):
            sysinfo = SystemInformation()
            interface = Interface("eth0")

        with mock.patch.object(CommandEthtool, 'get_information', return_value=device_info):
            self.assertRaises(RuntimeError, sysinfo.get_rate, interface)




if __name__ == '__main__':
    unittest.main()
