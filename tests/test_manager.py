#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

import unittest
import subprocess
from unittest.mock import patch
from unittest import mock
from subprocess import CalledProcessError

from detd import StreamConfiguration
from detd import TrafficSpecification
from detd import Interface
from detd import Configuration
from detd import SystemConfigurator

import os

from .common import *


class TestManager(unittest.TestCase):


    def setUp(self):

        env_var = os.getenv("DETD_TESTENV")
        if env_var == "HOST":
            self.mode = TestMode.HOST
        elif env_var == "TARGET":
            self.mode = TestMode.TARGET
        else:
            self.mode = TestMode.HOST

        interface_name = "eth0"

        interval = 20 * 1000 * 1000 # ns
        size = 1522                 # Bytes

        txoffset = 250 * 1000       # ns
        addr = "7a:b9:ed:d6:d2:12"
        vid = 3
        pcp = 6

        interface = Interface(interface_name)
        traffic = TrafficSpecification(interval, size)
        stream = StreamConfiguration(addr, vid, pcp, txoffset)

        self.config = Configuration(interface, stream, traffic)


    def test_add_talker_success(self):

        with RunContext(self.mode):
            manager = Manager()
            vlan_interface, soprio = manager.add_talker(self.config)

        self.assertEqual(vlan_interface, "eth0.3")
        self.assertEqual(soprio, 7)


    def test_add_talker_qdisc_error(self):

        with RunContext(self.mode, qdisc_exc=subprocess.CalledProcessError(1, "tc")):
            manager = Manager()

            self.assertRaises(subprocess.CalledProcessError, manager.add_talker, self.config)


    def test_add_talker_vlan_error(self):

        with RunContext(self.mode, vlan_exc=subprocess.CalledProcessError(1, "ip")):
            manager = Manager()

            self.assertRaises(subprocess.CalledProcessError, manager.add_talker, self.config)


    def test_add_talker_device_error(self):

        with RunContext(self.mode, device_exc=subprocess.CalledProcessError(1, "ethtool")):
            manager = Manager()

            self.assertRaises(subprocess.CalledProcessError, manager.add_talker, self.config)




if __name__ == '__main__':
    unittest.main()
