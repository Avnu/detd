#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

import os
import subprocess
import unittest

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


    def assertMappingEqual(self, mapping,
                           available_socket_prios, available_tcs, available_tx_queues,
                           tc_to_soprio, soprio_to_pcp, tc_to_hwq):

        self.assertEqual(mapping.available_socket_prios, available_socket_prios)
        self.assertEqual(mapping.available_tcs, available_tcs)
        self.assertEqual(mapping.available_tx_queues, available_tx_queues)

        self.assertEqual(mapping.tc_to_soprio, tc_to_soprio)
        self.assertEqual(mapping.soprio_to_pcp, soprio_to_pcp)
        self.assertEqual(mapping.tc_to_hwq, tc_to_hwq)


    def test_add_talker_success(self):

        config = setup_config(self.mode)

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
        config = setup_config(self.mode)

        with RunContext(self.mode):
            vlan_interface, soprio = manager.add_talker(config)

        self.assertEqual(vlan_interface, "eth0.3")
        self.assertEqual(soprio, 7)

        available_socket_prios = [8, 9, 10, 11, 12, 13]
        available_tcs = [2, 3, 4, 5, 6, 7]
        available_tx_queues = [2, 3, 4, 5, 6, 7]
        self.assertMappingEqual(manager.talker_manager[interface_name].mapping,
                                available_socket_prios, available_tcs, available_tx_queues,
                                tc_to_soprio, soprio_to_pcp, tc_to_hwq)


        # A second stream
        config = setup_config(self.mode, interval=20*1000*1000, txoffset=600*1000)

        with RunContext(self.mode):
            vlan_interface, soprio = manager.add_talker(config)

        self.assertEqual(vlan_interface, "eth0.3")
        self.assertEqual(soprio, 8)

        available_socket_prios = [9, 10, 11, 12, 13]
        available_tcs = [3, 4, 5, 6, 7]
        available_tx_queues = [3, 4, 5, 6, 7]
        self.assertMappingEqual(manager.talker_manager[interface_name].mapping,
                                available_socket_prios, available_tcs, available_tx_queues,
                                tc_to_soprio, soprio_to_pcp, tc_to_hwq)

        # Five more streams until we reach the maximum available number for 8 queues
        for txoffset_us in [800, 1000, 1400, 1800, 2200]:
            config = setup_config(self.mode, interval=20*1000*1000, txoffset=txoffset_us*1000)
            with RunContext(self.mode):
                vlan_interface, soprio = manager.add_talker(config)

        self.assertEqual(vlan_interface, "eth0.3")
        self.assertEqual(soprio, 13)

        available_socket_prios = []
        available_tcs = []
        available_tx_queues = []
        self.assertMappingEqual(manager.talker_manager[interface_name].mapping,
                                available_socket_prios, available_tcs, available_tx_queues,
                                tc_to_soprio, soprio_to_pcp, tc_to_hwq)

        # We try to add one stream once we have exhausted the maximum number possible
        config = setup_config(self.mode, interval=20*1000*1000, txoffset=2600*1000)
        with RunContext(self.mode):
            self.assertRaises(IndexError, manager.add_talker, config)


    def test_remove_max_talkers_success_and_error(self):

        interface_name = "eth0"

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

        with RunContext(self.mode):
            manager = Manager()

        # Add seven streams until we reach the maximum available number for 8 queues
        for txoffset_us in [200, 400, 800, 1000, 1400, 1800, 2200]:
            config = setup_config(self.mode, interval=20*1000*1000, txoffset=txoffset_us*1000)
            with RunContext(self.mode):
                vlan_interface, soprio = manager.add_talker(config)

        self.assertEqual(vlan_interface, "eth0.3")
        self.assertEqual(soprio, 13)

        available_socket_prios = []
        available_tcs = []
        available_tx_queues = []
        self.assertMappingEqual(manager.talker_manager[interface_name].mapping,
                                available_socket_prios, available_tcs, available_tx_queues,
                                tc_to_soprio, soprio_to_pcp, tc_to_hwq)

        mapping = manager.talker_manager[interface_name].mapping

        # Remove seventh stream
        soprio = 13
        tc = 7
        queue = 7
        mapping.unmap_and_free(soprio, tc, queue)
        available_socket_prios = [13]
        available_tcs = [7]
        available_tx_queues = [7]
        self.assertMappingEqual(manager.talker_manager[interface_name].mapping,
                                available_socket_prios, available_tcs, available_tx_queues,
                                tc_to_soprio, soprio_to_pcp, tc_to_hwq)


        # Remove sixth stream
        soprio = 12
        tc = 6
        queue = 6
        mapping.unmap_and_free(soprio, tc, queue)
        available_socket_prios = [12, 13]
        available_tcs = [6, 7]
        available_tx_queues = [6, 7]
        self.assertMappingEqual(manager.talker_manager[interface_name].mapping,
                                available_socket_prios, available_tcs, available_tx_queues,
                                tc_to_soprio, soprio_to_pcp, tc_to_hwq)




    def test_add_talker_qdisc_error(self):

        config = setup_config(self.mode)

        with RunContext(self.mode, qdisc_exc=subprocess.CalledProcessError(1, "tc")):
            manager = Manager()

            self.assertRaises(RuntimeError, manager.add_talker, config)


    def test_add_talker_vlan_error(self):

        config = setup_config(self.mode)

        with RunContext(self.mode, vlan_exc=ValueError("Interface could not be found")):
            manager = Manager()

            self.assertRaises(RuntimeError, manager.add_talker, config)


    def test_add_talker_device_error(self):

        config = setup_config(self.mode)

        with RunContext(self.mode, device_exc=subprocess.CalledProcessError(1, "ethtool")):
            manager = Manager()

            self.assertRaises(RuntimeError, manager.add_talker, config)




if __name__ == '__main__':
    unittest.main()
