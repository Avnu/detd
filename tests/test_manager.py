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
from detd import Mapping
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

        with RunContext(self.mode):
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


    def test_assignqueueandmap(self):

        with RunContext(self.mode):

            interface_name = "eth0"
            interface = Interface(interface_name)
            tc = None

            mapping = Mapping(interface)
            expected_mapping = [ {"offset":0, "num_queues":8} ]
            self.assertEqual(mapping.tc_to_hwq, expected_mapping)

            mapping.assign_queue_and_map(tc)
            expected_mapping = [
                {"offset":0, "num_queues":7},
                {"offset":7, "num_queues":1}]
            self.assertEqual(mapping.tc_to_hwq, expected_mapping)

            mapping.assign_queue_and_map(tc)
            expected_mapping = [
                {"offset":0, "num_queues":6},
                {"offset":6, "num_queues":1},
                {"offset":7, "num_queues":1}]
            self.assertEqual(mapping.tc_to_hwq, expected_mapping)

            mapping.assign_queue_and_map(tc)
            expected_mapping = [
                {"offset":0, "num_queues":5},
                {"offset":5, "num_queues":1},
                {"offset":6, "num_queues":1},
                {"offset":7, "num_queues":1}]
            self.assertEqual(mapping.tc_to_hwq, expected_mapping)

            mapping.assign_queue_and_map(tc)
            expected_mapping = [
                {"offset":0, "num_queues":4},
                {"offset":4, "num_queues":1},
                {"offset":5, "num_queues":1},
                {"offset":6, "num_queues":1},
                {"offset":7, "num_queues":1}]
            self.assertEqual(mapping.tc_to_hwq, expected_mapping)

            mapping.assign_queue_and_map(tc)
            expected_mapping = [
                {"offset":0, "num_queues":3},
                {"offset":3, "num_queues":1},
                {"offset":4, "num_queues":1},
                {"offset":5, "num_queues":1},
                {"offset":6, "num_queues":1},
                {"offset":7, "num_queues":1}]
            self.assertEqual(mapping.tc_to_hwq, expected_mapping)

            mapping.assign_queue_and_map(tc)
            expected_mapping = [
                {"offset":0, "num_queues":2},
                {"offset":2, "num_queues":1},
                {"offset":3, "num_queues":1},
                {"offset":4, "num_queues":1},
                {"offset":5, "num_queues":1},
                {"offset":6, "num_queues":1},
                {"offset":7, "num_queues":1}]
            self.assertEqual(mapping.tc_to_hwq, expected_mapping)

            mapping.assign_queue_and_map(tc)
            expected_mapping = [
                {"offset":0, "num_queues":1},
                {"offset":1, "num_queues":1},
                {"offset":2, "num_queues":1},
                {"offset":3, "num_queues":1},
                {"offset":4, "num_queues":1},
                {"offset":5, "num_queues":1},
                {"offset":6, "num_queues":1},
                {"offset":7, "num_queues":1}]
            self.assertEqual(mapping.tc_to_hwq, expected_mapping)

            with self.assertRaises(IndexError):
                mapping.assign_queue_and_map(tc)


    def test_unmapandfreequeue(self):

        with RunContext(self.mode):

            interface_name = "eth0"
            interface = Interface(interface_name)
            tc = None

            mapping = Mapping(interface)
            mapping.assign_queue_and_map(tc)
            mapping.assign_queue_and_map(tc)
            mapping.assign_queue_and_map(tc)
            mapping.assign_queue_and_map(tc)
            mapping.assign_queue_and_map(tc)
            mapping.assign_queue_and_map(tc)
            mapping.assign_queue_and_map(tc)
            expected_mapping = [
                {"offset":0, "num_queues":1},
                {"offset":1, "num_queues":1},
                {"offset":2, "num_queues":1},
                {"offset":3, "num_queues":1},
                {"offset":4, "num_queues":1},
                {"offset":5, "num_queues":1},
                {"offset":6, "num_queues":1},
                {"offset":7, "num_queues":1}]
            self.assertEqual(mapping.tc_to_hwq, expected_mapping)

            mapping.unmap_and_free_queue(tc)
            expected_mapping = [
                {"offset":0, "num_queues":2},
                {"offset":2, "num_queues":1},
                {"offset":3, "num_queues":1},
                {"offset":4, "num_queues":1},
                {"offset":5, "num_queues":1},
                {"offset":6, "num_queues":1},
                {"offset":7, "num_queues":1}]
            self.assertEqual(mapping.tc_to_hwq, expected_mapping)

            mapping.unmap_and_free_queue(tc)
            expected_mapping = [
                {"offset":0, "num_queues":3},
                {"offset":3, "num_queues":1},
                {"offset":4, "num_queues":1},
                {"offset":5, "num_queues":1},
                {"offset":6, "num_queues":1},
                {"offset":7, "num_queues":1}]
            self.assertEqual(mapping.tc_to_hwq, expected_mapping)

            mapping.unmap_and_free_queue(tc)
            expected_mapping = [
                {"offset":0, "num_queues":4},
                {"offset":4, "num_queues":1},
                {"offset":5, "num_queues":1},
                {"offset":6, "num_queues":1},
                {"offset":7, "num_queues":1}]
            self.assertEqual(mapping.tc_to_hwq, expected_mapping)

            mapping.unmap_and_free_queue(tc)
            expected_mapping = [
                {"offset":0, "num_queues":5},
                {"offset":5, "num_queues":1},
                {"offset":6, "num_queues":1},
                {"offset":7, "num_queues":1}]
            self.assertEqual(mapping.tc_to_hwq, expected_mapping)

            mapping.unmap_and_free_queue(tc)
            expected_mapping = [
                {"offset":0, "num_queues":6},
                {"offset":6, "num_queues":1},
                {"offset":7, "num_queues":1}]
            self.assertEqual(mapping.tc_to_hwq, expected_mapping)

            mapping.unmap_and_free_queue(tc)
            expected_mapping = [
                {"offset":0, "num_queues":7},
                {"offset":7, "num_queues":1}]
            self.assertEqual(mapping.tc_to_hwq, expected_mapping)

            mapping.unmap_and_free_queue(tc)
            expected_mapping = [ {"offset":0, "num_queues":8} ]
            self.assertEqual(mapping.tc_to_hwq, expected_mapping)

            with self.assertRaises(IndexError):
                mapping.unmap_and_free_queue(tc)




if __name__ == '__main__':
    unittest.main()
