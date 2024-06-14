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
from detd import SystemInformation
from detd import CommandEthtool
from detd import CommandTc
from detd import CommandIp
from detd import Check

from contextlib import AbstractContextManager


s_to_ns = 1000 * 1000 * 1000
ms_to_ns = 1000 * 1000
us_to_ns = 1000
Gbps_to_bps = 1000 * 1000 * 1000
Mbps_to_bps = 1000 * 1000


class TestMode:
    HOST = 1
    TARGET = 2


class RunContext(AbstractContextManager):

    def __init__(self, mode, qdisc_exc=None, vlan_exc=None, device_exc=None):
        if mode not in [TestMode.HOST, TestMode.TARGET]:
            raise TypeError("Invalid test mode")

        self.mode = mode

        if mode == TestMode.HOST:
            self.qdisc_conf_mock  = mock.patch.object(CommandTc,  'run', side_effect=qdisc_exc)
            self.vlan_conf_mock   = mock.patch.object(CommandIp,   'set_vlan', side_effect=vlan_exc)
            self.device_conf_mock = mock.patch.object(CommandEthtool, 'run', side_effect=device_exc)
            self.device_pci_id_mock = mock.patch.object(SystemInformation, 'get_pci_id', return_value=('8086:4B30'))
            self.device_channels_mock = mock.patch.object(SystemInformation, 'get_channels_information', return_value=(8,8))
            self.device_rate_mock = mock.patch.object(SystemInformation, 'get_rate', return_value=1000 * Mbps_to_bps)
            self.check_is_interface = mock.patch.object(Check, 'is_interface', return_value=True)


    def __enter__(self):

        if self.mode == TestMode.HOST:
            self.qdisc_conf_mock.start()
            self.vlan_conf_mock.start()
            self.device_conf_mock.start()
            self.device_pci_id_mock.start()
            self.device_channels_mock.start()
            self.device_rate_mock.start()
            self.check_is_interface.start()


    def __exit__(self, exc_type, exc_value, traceback):

        if self.mode == TestMode.HOST:
            self.qdisc_conf_mock.stop()
            self.vlan_conf_mock.stop()
            self.device_conf_mock.stop()
            self.device_pci_id_mock.stop()
            self.device_channels_mock.stop()
            self.device_rate_mock.stop()
            self.check_is_interface.stop()




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

    rate = 1 * Gbps_to_bps

    return Traffic(rate, TrafficType.SCHEDULED, config)




def setup_config(mode, interface_name="eth0", interval=20*1000*1000, size=1522,
                       txoffset=250*1000, addr="7a:b9:ed:d6:d2:12", vid=3, pcp=6):

    with RunContext(mode):
        interface = Interface(interface_name)
        traffic = TrafficSpecification(interval, size)
        stream = StreamConfiguration(addr, vid, pcp, txoffset)

        config = Configuration(interface, stream, traffic)

    return config
