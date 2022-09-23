#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

import os
import unittest

from detd import Mapping
from detd import StreamConfiguration
from detd import TrafficSpecification
from detd import Interface
from detd import Scheduler
from detd import Traffic
from detd import TrafficType

from .common import *




class TestSchedulerMethods(unittest.TestCase):


    def setUp(self):

        env_var = os.getenv("DETD_TESTENV")
        if env_var == "HOST":
            self.mode = TestMode.HOST
        elif env_var == "TARGET":
            self.mode = TestMode.TARGET
        else:
            self.mode = TestMode.HOST




    def assert_slot(self, scheduler, index, start, end):
        self.assertEqual(scheduler.schedule[index].start, start)
        self.assertEqual(scheduler.schedule[index].end, end)


    def assert_traffic(self, traffic, txoffset, interval):
        self.assertEqual(traffic.start, txoffset)
        self.assertEqual(traffic.interval, interval)


    def assert_schedule_empty(self, schedule):
        self.assertEqual(schedule.period, 0)
        self.assertEqual(len(schedule), 0)


    def test_add_single_scheduled_traffic_start_0(self):

        with RunContext(TestMode.HOST):
            interface = Interface("eth0")
            mapping = Mapping(interface)
            scheduler = Scheduler(mapping)

            txoffset = 0 * us_to_ns
            interval = 20 * ms_to_ns
            traffic = traffic_helper(txoffset, interval)
            scheduler.add(traffic)

            self.assertEqual(scheduler.schedule.period, 20000000)

            self.assert_slot(scheduler, 0,     0,    12176)
            self.assert_slot(scheduler, 1, 12176, 20000000)


    def test_add_remove_single_scheduled_traffic_start_0(self):

        with RunContext(TestMode.HOST):
            interface = Interface("eth0")
            mapping = Mapping(interface)
            scheduler = Scheduler(mapping)

            txoffset = 0 * us_to_ns
            interval = 20 * ms_to_ns
            traffic = traffic_helper(txoffset, interval)
            scheduler.add(traffic)

            self.assertEqual(scheduler.schedule.period, 20000000)

            self.assert_slot(scheduler, 0,     0,    12176)
            self.assert_slot(scheduler, 1, 12176, 20000000)

            scheduler.remove(traffic)

            self.assert_schedule_empty(scheduler.schedule)


    def test_add_single_scheduled_traffic_start_non_0(self):

        with RunContext(TestMode.HOST):
            interface = Interface("eth0")
            mapping = Mapping(interface)
            scheduler = Scheduler(mapping)

            txoffset = 250 * us_to_ns
            interval = 20 * ms_to_ns
            traffic = traffic_helper(txoffset, interval)
            scheduler.add(traffic)

            self.assert_slot(scheduler, 0,      0,   250000)
            self.assert_slot(scheduler, 1, 250000,   262176)
            self.assert_slot(scheduler, 2, 262176, 20000000)


    def test_add_remove_single_scheduled_traffic_start_non_0(self):

        with RunContext(TestMode.HOST):
            interface = Interface("eth0")
            mapping = Mapping(interface)
            scheduler = Scheduler(mapping)

            txoffset = 250 * us_to_ns
            interval = 20 * ms_to_ns
            traffic = traffic_helper(txoffset, interval)
            scheduler.add(traffic)

            self.assert_slot(scheduler, 0,      0,   250000)
            self.assert_slot(scheduler, 1, 250000,   262176)
            self.assert_slot(scheduler, 2, 262176, 20000000)

            scheduler.remove(traffic)

            self.assert_schedule_empty(scheduler.schedule)


    def test_add_two_scheduled_traffics_same_interval(self):

        with RunContext(TestMode.HOST):
            interface = Interface("eth0")
            mapping = Mapping(interface)
            scheduler = Scheduler(mapping)

            txoffset = 250 * us_to_ns
            interval = 1 * ms_to_ns
            traffic1 = traffic_helper(txoffset, interval)
            scheduler.add(traffic1)

            txoffset = 550 * us_to_ns
            interval = 1 * ms_to_ns
            traffic2 = traffic_helper(txoffset, interval)
            scheduler.add(traffic2)

            self.assertEqual(scheduler.schedule.period, 1000000)
            self.assert_traffic(scheduler.traffics[1], 250000, 1000000)
            self.assert_traffic(scheduler.traffics[2], 550000, 1000000)

            self.assert_slot(scheduler, 0,      0,  250000)
            self.assert_slot(scheduler, 1, 250000,  262176)
            self.assert_slot(scheduler, 2, 262176,  550000)
            self.assert_slot(scheduler, 3, 550000,  562176)
            self.assert_slot(scheduler, 4, 562176, 1000000)



    def test_add_two_scheduled_traffics_different_interval(self):

        with RunContext(TestMode.HOST):
            interface = Interface("eth0")
            mapping = Mapping(interface)
            scheduler = Scheduler(mapping)

            txoffset = 250 * us_to_ns
            interval = 2 * ms_to_ns
            traffic1 = traffic_helper(txoffset, interval)
            scheduler.add(traffic1)

            txoffset =  750 * us_to_ns
            interval = 3 * ms_to_ns
            traffic2 = traffic_helper(txoffset, interval)
            scheduler.add(traffic2)

            self.assertEqual(scheduler.schedule.period, 6000000)

            self.assert_slot(scheduler, 0,      0, 250000)
            self.assert_slot(scheduler, 1, 250000, 262176)

            self.assert_slot(scheduler, 2, 262176, 750000)
            self.assert_slot(scheduler, 3, 750000, 762176)

            self.assert_slot(scheduler, 4,  762176, 2250000)
            self.assert_slot(scheduler, 5, 2250000, 2262176)

            self.assert_slot(scheduler, 6, 2262176, 3750000)
            self.assert_slot(scheduler, 7, 3750000, 3762176)

            self.assert_slot(scheduler, 8, 3762176, 4250000)
            self.assert_slot(scheduler, 9, 4250000, 4262176)


            self.assert_slot(scheduler, 10, 4262176, 6000000)


    def test_add_remove_last_to_first_two_scheduled_traffics_different_interval(self):

        with RunContext(TestMode.HOST):
            interface = Interface("eth0")
            mapping = Mapping(interface)
            scheduler = Scheduler(mapping)

            txoffset = 250 * us_to_ns
            interval = 2 * ms_to_ns
            traffic1 = traffic_helper(txoffset, interval)
            scheduler.add(traffic1)

            txoffset =  750 * us_to_ns
            interval = 3 * ms_to_ns
            traffic2 = traffic_helper(txoffset, interval)
            scheduler.add(traffic2)

            self.assertEqual(scheduler.schedule.period, 6000000)

            self.assert_slot(scheduler, 0,      0, 250000)
            self.assert_slot(scheduler, 1, 250000, 262176)

            self.assert_slot(scheduler, 2, 262176, 750000)
            self.assert_slot(scheduler, 3, 750000, 762176)

            self.assert_slot(scheduler, 4,  762176, 2250000)
            self.assert_slot(scheduler, 5, 2250000, 2262176)

            self.assert_slot(scheduler, 6, 2262176, 3750000)
            self.assert_slot(scheduler, 7, 3750000, 3762176)

            self.assert_slot(scheduler, 8, 3762176, 4250000)
            self.assert_slot(scheduler, 9, 4250000, 4262176)

            self.assert_slot(scheduler, 10, 4262176, 6000000)

            # Remove traffic2
            scheduler.remove(traffic2)

            self.assertEqual(scheduler.schedule.period, 2000000)

            self.assert_slot(scheduler, 0,      0, 250000)
            self.assert_slot(scheduler, 1, 250000, 262176)

            self.assert_slot(scheduler, 2, 262176, 2000000)

            # Remove traffic1
            scheduler.remove(traffic1)

            self.assert_schedule_empty(scheduler.schedule)


    def test_add_remove_first_to_last_two_scheduled_traffics_different_interval(self):

        with RunContext(TestMode.HOST):
            interface = Interface("eth0")
            mapping = Mapping(interface)
            scheduler = Scheduler(mapping)

            txoffset = 250 * us_to_ns
            interval = 2 * ms_to_ns
            traffic1 = traffic_helper(txoffset, interval)
            scheduler.add(traffic1)

            txoffset =  750 * us_to_ns
            interval = 3 * ms_to_ns
            traffic2 = traffic_helper(txoffset, interval)
            scheduler.add(traffic2)

            self.assertEqual(scheduler.schedule.period, 6000000)

            self.assert_slot(scheduler, 0,      0, 250000)
            self.assert_slot(scheduler, 1, 250000, 262176)

            self.assert_slot(scheduler, 2, 262176, 750000)
            self.assert_slot(scheduler, 3, 750000, 762176)

            self.assert_slot(scheduler, 4,  762176, 2250000)
            self.assert_slot(scheduler, 5, 2250000, 2262176)

            self.assert_slot(scheduler, 6, 2262176, 3750000)
            self.assert_slot(scheduler, 7, 3750000, 3762176)

            self.assert_slot(scheduler, 8, 3762176, 4250000)
            self.assert_slot(scheduler, 9, 4250000, 4262176)

            self.assert_slot(scheduler, 10, 4262176, 6000000)

            # Remove traffic2
            scheduler.remove(traffic1)

            self.assertEqual(scheduler.schedule.period, 3000000)

            self.assert_slot(scheduler, 0,      0, 750000)
            self.assert_slot(scheduler, 1, 750000, 762176)

            self.assert_slot(scheduler, 2, 762176, 3000000)

            # Remove traffic1
            scheduler.remove(traffic2)

            self.assert_schedule_empty(scheduler.schedule)





    def test_schedule_conflictswithtraffic_matchfull(self):

        with RunContext(self.mode):
            interface_name = "eth0"
            interface = Interface(interface_name)
            mapping = Mapping(interface)
            scheduler = Scheduler(mapping)

            txoffset = 100 * us_to_ns
            interval = 20 * ms_to_ns
            traffic = traffic_helper(txoffset, interval)
            scheduler.add(traffic)

            txoffset = 100 * us_to_ns
            interval = 20 * ms_to_ns
            traffic = traffic_helper(txoffset, interval)
            res = scheduler.schedule.conflicts_with_traffic(traffic)
            self.assertEqual(res, True)




    def test_schedule_conflictswithtraffic_nomatch(self):

        with RunContext(self.mode):
            interface_name = "eth0"
            interface = Interface(interface_name)
            mapping = Mapping(interface)
            scheduler = Scheduler(mapping)

            txoffset = 100 * us_to_ns
            interval = 20 * ms_to_ns
            traffic = traffic_helper(txoffset, interval)
            scheduler.add(traffic)

            txoffset = 500 * us_to_ns
            interval = 20 * ms_to_ns
            traffic = traffic_helper(txoffset, interval)
            res = scheduler.schedule.conflicts_with_traffic(traffic)
            self.assertEqual(res, False)



    def test_schedule_conflictswithtraffic_leftmatch(self):

        with RunContext(self.mode):
            interface_name = "eth0"
            interface = Interface(interface_name)
            mapping = Mapping(interface)
            scheduler = Scheduler(mapping)

            txoffset = 100 * us_to_ns
            interval = 20 * ms_to_ns
            traffic = traffic_helper(txoffset, interval)
            scheduler.add(traffic)

            txoffset = 99 * us_to_ns
            interval = 20 * ms_to_ns
            traffic = traffic_helper(txoffset, interval)
            conflict = scheduler.schedule.conflicts_with_traffic(traffic)
            self.assertEqual(conflict, True)



    def test_schedule_conflictswithtraffic_rightmatch(self):

        with RunContext(self.mode):
            interface_name = "eth0"
            interface = Interface(interface_name)
            mapping = Mapping(interface)
            scheduler = Scheduler(mapping)

            txoffset = 100 * us_to_ns
            interval = 20 * ms_to_ns
            traffic = traffic_helper(txoffset, interval)
            scheduler.add(traffic)

            txoffset = 110 * us_to_ns
            interval = 20 * ms_to_ns
            traffic = traffic_helper(txoffset, interval)
            res = scheduler.schedule.conflicts_with_traffic(traffic)
            self.assertEqual(res, True)


if __name__ == '__main__':
    unittest.main()
