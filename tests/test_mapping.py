#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

import unittest

from detd import Interface
from detd import MappingFlexible

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


    def test_mappingnaive_assignqueueandmap(self):

        with RunContext(self.mode):

            interface_name = "eth0"
            interface = Interface(interface_name)
            tc = None

            mapping = MappingFlexible(interface)
            expected_tc_to_hwq_mapping = [ {"offset":0, "num_queues":8} ]
            self.assertEqual(mapping.tc_to_hwq, expected_tc_to_hwq_mapping)

            mapping.assign_queue_and_map(tc)
            expected_tc_to_hwq_mapping = [
                {"offset":0, "num_queues":7},
                {"offset":7, "num_queues":1}]
            self.assertEqual(mapping.tc_to_hwq, expected_tc_to_hwq_mapping)

            mapping.assign_queue_and_map(tc)
            expected_tc_to_hwq_mapping = [
                {"offset":0, "num_queues":6},
                {"offset":6, "num_queues":1},
                {"offset":7, "num_queues":1}]
            self.assertEqual(mapping.tc_to_hwq, expected_tc_to_hwq_mapping)

            mapping.assign_queue_and_map(tc)
            expected_tc_to_hwq_mapping = [
                {"offset":0, "num_queues":5},
                {"offset":5, "num_queues":1},
                {"offset":6, "num_queues":1},
                {"offset":7, "num_queues":1}]
            self.assertEqual(mapping.tc_to_hwq, expected_tc_to_hwq_mapping)

            mapping.assign_queue_and_map(tc)
            expected_tc_to_hwq_mapping = [
                {"offset":0, "num_queues":4},
                {"offset":4, "num_queues":1},
                {"offset":5, "num_queues":1},
                {"offset":6, "num_queues":1},
                {"offset":7, "num_queues":1}]
            self.assertEqual(mapping.tc_to_hwq, expected_tc_to_hwq_mapping)

            mapping.assign_queue_and_map(tc)
            expected_tc_to_hwq_mapping = [
                {"offset":0, "num_queues":3},
                {"offset":3, "num_queues":1},
                {"offset":4, "num_queues":1},
                {"offset":5, "num_queues":1},
                {"offset":6, "num_queues":1},
                {"offset":7, "num_queues":1}]
            self.assertEqual(mapping.tc_to_hwq, expected_tc_to_hwq_mapping)

            mapping.assign_queue_and_map(tc)
            expected_tc_to_hwq_mapping = [
                {"offset":0, "num_queues":2},
                {"offset":2, "num_queues":1},
                {"offset":3, "num_queues":1},
                {"offset":4, "num_queues":1},
                {"offset":5, "num_queues":1},
                {"offset":6, "num_queues":1},
                {"offset":7, "num_queues":1}]
            self.assertEqual(mapping.tc_to_hwq, expected_tc_to_hwq_mapping)

            mapping.assign_queue_and_map(tc)
            expected_tc_to_hwq_mapping = [
                {"offset":0, "num_queues":1},
                {"offset":1, "num_queues":1},
                {"offset":2, "num_queues":1},
                {"offset":3, "num_queues":1},
                {"offset":4, "num_queues":1},
                {"offset":5, "num_queues":1},
                {"offset":6, "num_queues":1},
                {"offset":7, "num_queues":1}]
            self.assertEqual(mapping.tc_to_hwq, expected_tc_to_hwq_mapping)

            with self.assertRaises(IndexError):
                mapping.assign_queue_and_map(tc)


    def test_mappingnaive_unmapandfreequeue(self):

        with RunContext(self.mode):

            interface_name = "eth0"
            interface = Interface(interface_name)
            tc = None

            mapping = MappingFlexible(interface)
            mapping.assign_queue_and_map(tc)
            mapping.assign_queue_and_map(tc)
            mapping.assign_queue_and_map(tc)
            mapping.assign_queue_and_map(tc)
            mapping.assign_queue_and_map(tc)
            mapping.assign_queue_and_map(tc)
            mapping.assign_queue_and_map(tc)
            expected_tc_to_hwq_mapping = [
                {"offset":0, "num_queues":1},
                {"offset":1, "num_queues":1},
                {"offset":2, "num_queues":1},
                {"offset":3, "num_queues":1},
                {"offset":4, "num_queues":1},
                {"offset":5, "num_queues":1},
                {"offset":6, "num_queues":1},
                {"offset":7, "num_queues":1}]
            self.assertEqual(mapping.tc_to_hwq, expected_tc_to_hwq_mapping)

            mapping.unmap_and_free_queue(tc)
            expected_tc_to_hwq_mapping = [
                {"offset":0, "num_queues":2},
                {"offset":2, "num_queues":1},
                {"offset":3, "num_queues":1},
                {"offset":4, "num_queues":1},
                {"offset":5, "num_queues":1},
                {"offset":6, "num_queues":1},
                {"offset":7, "num_queues":1}]
            self.assertEqual(mapping.tc_to_hwq, expected_tc_to_hwq_mapping)

            mapping.unmap_and_free_queue(tc)
            expected_tc_to_hwq_mapping = [
                {"offset":0, "num_queues":3},
                {"offset":3, "num_queues":1},
                {"offset":4, "num_queues":1},
                {"offset":5, "num_queues":1},
                {"offset":6, "num_queues":1},
                {"offset":7, "num_queues":1}]
            self.assertEqual(mapping.tc_to_hwq, expected_tc_to_hwq_mapping)

            mapping.unmap_and_free_queue(tc)
            expected_tc_to_hwq_mapping = [
                {"offset":0, "num_queues":4},
                {"offset":4, "num_queues":1},
                {"offset":5, "num_queues":1},
                {"offset":6, "num_queues":1},
                {"offset":7, "num_queues":1}]
            self.assertEqual(mapping.tc_to_hwq, expected_tc_to_hwq_mapping)

            mapping.unmap_and_free_queue(tc)
            expected_tc_to_hwq_mapping = [
                {"offset":0, "num_queues":5},
                {"offset":5, "num_queues":1},
                {"offset":6, "num_queues":1},
                {"offset":7, "num_queues":1}]
            self.assertEqual(mapping.tc_to_hwq, expected_tc_to_hwq_mapping)

            mapping.unmap_and_free_queue(tc)
            expected_tc_to_hwq_mapping = [
                {"offset":0, "num_queues":6},
                {"offset":6, "num_queues":1},
                {"offset":7, "num_queues":1}]
            self.assertEqual(mapping.tc_to_hwq, expected_tc_to_hwq_mapping)

            mapping.unmap_and_free_queue(tc)
            expected_tc_to_hwq_mapping = [
                {"offset":0, "num_queues":7},
                {"offset":7, "num_queues":1}]
            self.assertEqual(mapping.tc_to_hwq, expected_tc_to_hwq_mapping)

            mapping.unmap_and_free_queue(tc)
            expected_tc_to_hwq_mapping = [ {"offset":0, "num_queues":8} ]
            self.assertEqual(mapping.tc_to_hwq, expected_tc_to_hwq_mapping)

            with self.assertRaises(IndexError):
                mapping.unmap_and_free_queue(tc)




if __name__ == '__main__':
    unittest.main()
