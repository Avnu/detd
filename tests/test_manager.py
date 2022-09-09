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
from detd import MappingNaive
from detd import Configuration
from detd import Scheduler
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


    def setup_config(self, interface_name="eth0", interval=20*1000*1000, size=1522,
                           txoffset=250*1000, addr="7a:b9:ed:d6:d2:12", vid=3, pcp=6):

        with RunContext(self.mode):
            interface = Interface(interface_name)
            traffic = TrafficSpecification(interval, size)
            stream = StreamConfiguration(addr, vid, pcp, txoffset)

            config = Configuration(interface, stream, traffic)

        return config


    def assertMappingEqual(self, interface_name, manager,
                           available_socket_prios, available_tcs, available_tx_queues,
                           tc_to_soprio, soprio_to_pcp, tc_to_hwq):

        mapping = manager.talker_manager[interface_name].mapping

        self.assertEqual(mapping.available_socket_prios, available_socket_prios)
        self.assertEqual(mapping.available_tcs, available_tcs)
        self.assertEqual(mapping.available_tx_queues, available_tx_queues)

        self.assertEqual(mapping.tc_to_soprio, tc_to_soprio)
        self.assertEqual(mapping.soprio_to_pcp, soprio_to_pcp)
        self.assertEqual(mapping.tc_to_hwq, tc_to_hwq)


    def test_add_talker_success(self):

        config = self.setup_config()

        with RunContext(self.mode):
            manager = Manager()
            vlan_interface, soprio = manager.add_talker(config)

        self.assertEqual(vlan_interface, "eth0.3")
        self.assertEqual(soprio, 7)


    def test_add_max_talkers_success_and_error(self):

        interface_name = "eth0"

        num_tx_queues = 8

        # These three mappings are expected to remain immutable
        tc_to_soprio = [0, 7, 8, 9, 10, 11, 12, 13]
        soprio_to_pcp = {
            0: 0,
            7: 1,
            8: 2,
            9: 3,
            10: 4,
            11: 5,
            12: 6,
            13: 7
        }
        tc_to_hwq = [
            {"offset":0, "num_queues":1},
            {"offset":1, "num_queues":1},
            {"offset":2, "num_queues":1},
            {"offset":3, "num_queues":1},
            {"offset":4, "num_queues":1},
            {"offset":5, "num_queues":1},
            {"offset":6, "num_queues":1},
            {"offset":7, "num_queues":1},
        ]


        # Initialize the manager to be used in all the sequence
        with RunContext(self.mode):
            manager = Manager()


        # A first stream
        config = self.setup_config()


        with RunContext(self.mode):
            vlan_interface, soprio = manager.add_talker(config)

        self.assertEqual(vlan_interface, "eth0.3")
        self.assertEqual(soprio, 7)

        available_socket_prios = [8, 9, 10, 11, 12, 13]
        available_tcs = [2, 3, 4, 5, 6, 7]
        available_tx_queues = [2, 3, 4, 5, 6, 7]
        self.assertMappingEqual(interface_name, manager,
                                available_socket_prios, available_tcs, available_tx_queues,
                                tc_to_soprio, soprio_to_pcp, tc_to_hwq)


        # A second stream
        config = self.setup_config(interval=20*1000*1000, txoffset=600*1000)

        with RunContext(self.mode):
            vlan_interface, soprio = manager.add_talker(config)

        self.assertEqual(vlan_interface, "eth0.3")
        self.assertEqual(soprio, 8)

        available_socket_prios = [9, 10, 11, 12, 13]
        available_tcs = [3, 4, 5, 6, 7]
        available_tx_queues = [3, 4, 5, 6, 7]
        self.assertMappingEqual(interface_name, manager,
                                available_socket_prios, available_tcs, available_tx_queues,
                                tc_to_soprio, soprio_to_pcp, tc_to_hwq)

        # Five more streams until we reach the maximum available number for 8 queues
        for txoffset_us in [800, 1000, 1400, 1800, 2200]:
            config = self.setup_config(interval=20*1000*1000, txoffset=txoffset_us*1000)
            with RunContext(self.mode):
                vlan_interface, soprio = manager.add_talker(config)

        self.assertEqual(vlan_interface, "eth0.3")
        self.assertEqual(soprio, 13)

        available_socket_prios = []
        available_tcs = []
        available_tx_queues = []
        self.assertMappingEqual(interface_name, manager,
                                available_socket_prios, available_tcs, available_tx_queues,
                                tc_to_soprio, soprio_to_pcp, tc_to_hwq)

        # We try to add one stream once we have exhausted the maximum number possible
        config = self.setup_config(interval=20*1000*1000, txoffset=2600*1000)
        self.assertRaises(IndexError, manager.add_talker, config)




    def test_add_talker_qdisc_error(self):

        config = self.setup_config()

        with RunContext(self.mode, qdisc_exc=subprocess.CalledProcessError(1, "tc")):
            manager = Manager()

            self.assertRaises(subprocess.CalledProcessError, manager.add_talker, config)


    def test_add_talker_vlan_error(self):

        config = self.setup_config()

        with RunContext(self.mode, vlan_exc=subprocess.CalledProcessError(1, "ip")):
            manager = Manager()

            self.assertRaises(subprocess.CalledProcessError, manager.add_talker, config)


    def test_add_talker_device_error(self):

        config = self.setup_config()

        with RunContext(self.mode, device_exc=subprocess.CalledProcessError(1, "ethtool")):
            manager = Manager()

            self.assertRaises(subprocess.CalledProcessError, manager.add_talker, config)


    def test_mappingnaive_assignqueueandmap(self):

        with RunContext(self.mode):

            interface_name = "eth0"
            interface = Interface(interface_name)
            tc = None

            mapping = MappingNaive(interface)
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


    def test_mappingnaive_unmapandfreequeue(self):

        with RunContext(self.mode):

            interface_name = "eth0"
            interface = Interface(interface_name)
            tc = None

            mapping = MappingNaive(interface)
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



    def test_schedule_conflictswithtraffic_matchfull(self):

        with RunContext(self.mode):
            interface_name = "eth0"
            interface = Interface(interface_name)
            mapping = Mapping(interface)
            scheduler = Scheduler(mapping)

            config = self.setup_config(txoffset=100*1000)
            traffic = Traffic(TrafficType.SCHEDULED, config)
            scheduler.add(traffic)

            config = self.setup_config(txoffset=100*1000)
            traffic = Traffic(TrafficType.SCHEDULED, config)
            res = scheduler.schedule.conflicts_with_traffic(traffic)
            self.assertEqual(res, True)



    def test_schedule_conflictswithtraffic_nomatch(self):

        with RunContext(self.mode):
            interface_name = "eth0"
            interface = Interface(interface_name)
            mapping = Mapping(interface)
            scheduler = Scheduler(mapping)

            config = self.setup_config(txoffset=100*1000)
            traffic = Traffic(TrafficType.SCHEDULED, config)
            scheduler.add(traffic)

            config = self.setup_config(txoffset=500*1000)
            traffic = Traffic(TrafficType.SCHEDULED, config)
            res = scheduler.schedule.conflicts_with_traffic(traffic)
            self.assertEqual(res, False)



    def test_schedule_conflictswithtraffic_leftmatch(self):

        with RunContext(self.mode):
            interface_name = "eth0"
            interface = Interface(interface_name)
            mapping = Mapping(interface)
            scheduler = Scheduler(mapping)

            config = self.setup_config(txoffset=100*1000)
            traffic = Traffic(TrafficType.SCHEDULED, config)
            scheduler.add(traffic)

            config = self.setup_config(txoffset=99*1000)
            traffic = Traffic(TrafficType.SCHEDULED, config)
            conflict = scheduler.schedule.conflicts_with_traffic(traffic)
            self.assertEqual(conflict, True)



    def test_schedule_conflictswithtraffic_rightmatch(self):

        with RunContext(self.mode):
            interface_name = "eth0"
            interface = Interface(interface_name)
            mapping = Mapping(interface)
            scheduler = Scheduler(mapping)

            config = self.setup_config(txoffset=100*1000)
            traffic = Traffic(TrafficType.SCHEDULED, config)
            scheduler.add(traffic)

            config = self.setup_config(txoffset=110*1000)
            traffic = Traffic(TrafficType.SCHEDULED, config)
            res = scheduler.schedule.conflicts_with_traffic(traffic)
            self.assertEqual(res, True)



if __name__ == '__main__':
    unittest.main()
