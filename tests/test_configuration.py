#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

from random import seed
from random import random
import subprocess
from subprocess import CalledProcessError
import unittest
from unittest.mock import patch
from unittest import mock

from detd import StreamConfiguration
from detd import TrafficSpecification
from detd import Interface
from detd import Configuration

from detd import setup_root_logger



import os

from .common import *


class TestConfiguration(unittest.TestCase):


    def setUp(self):

        setup_root_logger('./detd-server-unittest.log')

        env_var = os.getenv("DETD_TESTENV")
        if env_var == "HOST":
            self.mode = TestMode.HOST
        elif env_var == "TARGET":
            self.mode = TestMode.TARGET
        else:
            self.mode = TestMode.HOST



    def test_configuration_wrong_interface(self):

        seed(1)
        interface_name = "eth0{}".format(random())

        with self.assertRaises(TypeError):
            interface = Interface(interface_name)


    def test_configuration_wrong_dmac(self):

        interface_name = "eth0"

        interval = 20 * 1000 * 1000 # ns
        size = 1522                 # Bytes

        txoffset = 250 * 1000       # ns
        addr = "7a:b9:ed:d6:d2:12:23"
        vid = 3
        pcp = 6

        with self.assertRaises(TypeError):
            stream = StreamConfiguration(addr, vid, pcp, txoffset)


    def test_configuration_negative_vid(self):

        with RunContext(self.mode):
            interface_name = "eth0"

            interval = 20 * 1000 * 1000 # ns
            size = 1522                 # Bytes

            txoffset = 250 * 1000       # ns
            addr = "7a:b9:ed:d6:d2:12"
            vid = -1
            pcp = 6

            with self.assertRaises(TypeError):
                stream = StreamConfiguration(addr, vid, pcp, txoffset)


    def test_configuration_negative_pcp(self):

        with RunContext(self.mode):
            interface_name = "eth0"

            interval = 20 * 1000 * 1000 # ns
            size = 1522                 # Bytes

            txoffset = 250 * 1000       # ns
            addr = "7a:b9:ed:d6:d2:12"
            vid = 3
            pcp = -1

            with self.assertRaises(TypeError):
                stream = StreamConfiguration(addr, vid, pcp, txoffset)


    def test_configuration_negative_txoffset(self):

        with RunContext(self.mode):
            interface_name = "eth0"

            interval = 20 * 1000 * 1000 # ns
            size = 1522                 # Bytes

            txoffset = -250 * 1000       # ns
            addr = "7a:b9:ed:d6:d2:12"
            vid = 3
            pcp = 4

            with self.assertRaises(TypeError):
                stream = StreamConfiguration(addr, vid, pcp, txoffset)


    def test_configuration_negative_interval(self):

        with RunContext(self.mode):
            interface_name = "eth0"

            interval = -20 * 1000 * 1000 # ns
            size = 1522                 # Bytes

            txoffset = 250 * 1000       # ns
            addr = "7a:b9:ed:d6:d2:12"
            vid = 3
            pcp = 4

            with self.assertRaises(TypeError):
                traffic = TrafficSpecification(interval, size)


    def test_configuration_negative_size(self):

        with RunContext(self.mode):
            interface_name = "eth0"

            interval = 20 * 1000 * 1000 # ns
            size = -1                   # Bytes

            txoffset = 250 * 1000       # ns
            addr = "7a:b9:ed:d6:d2:12"
            vid = 3
            pcp = 4

            with self.assertRaises(TypeError):
                traffic = TrafficSpecification(interval, size)


    def test_configuration_txoffset_exceeds_interval(self):

        with RunContext(self.mode):
            interface_name = "eth0"

            interval = 20 * 1000 * 1000  # ns
            size = 50                    # Bytes

            txoffset = 250 * 1000 * 1000 # ns
            addr = "7a:b9:ed:d6:d2:12"
            vid = 3
            pcp = 4

            interface = Interface(interface_name)
            traffic = TrafficSpecification(interval, size)
            stream = StreamConfiguration(addr, vid, pcp, txoffset)


            with self.assertRaises(TypeError):
                config = Configuration(interface, stream, traffic)





if __name__ == '__main__':
    unittest.main()
