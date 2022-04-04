#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine


from enum import Enum
from unittest import mock

from detd import QdiscConfigurator
from detd import VlanConfigurator
from detd import DeviceConfigurator
from detd import StreamConfiguration
from detd import TrafficSpecification
from detd import Configuration
from detd import Interface
from detd import Traffic
from detd import TrafficType
from detd import Manager

from contextlib import AbstractContextManager


s_to_ns = 1000 * 1000 * 1000
ms_to_ns = 1000 * 1000
us_to_ns = 1000
Gbps_to_bps = 1000 * 1000 * 1000


class TestMode:
    HOST = 1
    TARGET = 2


class RunContext(AbstractContextManager):

    def __init__(self, mode, qdisc_exc=None, vlan_exc=None, device_exc=None):
        if mode not in [TestMode.HOST, TestMode.TARGET]:
            raise TypeError("Invalid test mode")

        self.mode = mode

        if mode == TestMode.HOST:
            self.qdisc_mock  = mock.patch.object(QdiscConfigurator,  'run', side_effect=qdisc_exc)
            self.vlan_mock   = mock.patch.object(VlanConfigurator,   'run', side_effect=vlan_exc)
            self.device_mock = mock.patch.object(DeviceConfigurator, 'run', side_effect=device_exc)


    def __enter__(self):

        if self.mode == TestMode.HOST:
            self.qdisc_mock.start()
            self.vlan_mock.start()
            self.device_mock.start()


    def __exit__(self, exc_type, exc_value, traceback):

        if self.mode == TestMode.HOST:
            self.qdisc_mock.stop()
            self.vlan_mock.stop()
            self.device_mock.stop()




def traffic_helper(txoffset, interval):

    interface_name = 'eth0'

    size = 1522                 # Bytes

    addr = "03:C0:FF:EE:FF:AB"
    vid = 3
    pcp = 6

    rate = 1 * Gbps_to_bps

    stream = StreamConfiguration(addr, vid, pcp, txoffset)
    traffic = TrafficSpecification(interval, size)
    interface = Interface(interface_name)
    config = Configuration(interface, stream, traffic)


    return Traffic(TrafficType.SCHEDULED, config)
