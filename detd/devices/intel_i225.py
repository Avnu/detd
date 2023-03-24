#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

""" Module intel_i225

"""

import time

from ..logger import get_logger

from .device import Capability
from .device import Device


logger = get_logger(__name__)




class IntelI225(Device):

    NUM_TX_QUEUES = 4
    NUM_RX_QUEUES = 4

    CAPABILITIES = [Capability.Qbv]

    #Placeholder MAC+PHY latency
    HARDWARE_LATENCY_MIN = 1000
    HARDWARE_LATENCY_MAX = 2000

    # Devices supporting TSN: i225-LM, i225-IT
    PCI_IDS_VALID = ['8086:0D9F', '8086:15F2']

    # Devices not supporting TSN: i225-V, i225-LMvP
    PCI_IDS_NON_TSN = ['8086:15F3', '8086:5502']

    # Hardware default. Empty Flash Image (or NVM configuration loading failed)
    PCI_IDS_UNPROGRAMMED = ['8086:15FD']

    PCI_IDS = PCI_IDS_VALID + PCI_IDS_NON_TSN + PCI_IDS_UNPROGRAMMED


    def __init__(self, pci_id):

        logger.info(f"Initializing {__class__.__name__}")

        super().__init__(IntelI225.NUM_TX_QUEUES, IntelI225.NUM_RX_QUEUES, IntelI225.HARDWARE_LATENCY_MIN, IntelI225.HARDWARE_LATENCY_MAX)

        if pci_id in IntelI225.PCI_IDS_NON_TSN:
            raise "This i225 device does not support TSN."

        if pci_id in IntelI225.PCI_IDS_UNPROGRAMMED:
            raise "The flash image in this i225 device is empty, or the NVM configuration loading failed."

        self.capabilities = [Capability.Qbv]

        self.features['rxvlan'] = 'off'
        #self.features['hw-tc-offload'] = 'on'

        # self.num_tx_ring_entries and self.num_rx_ring_entries
        # Provides the number of ring entries for Tx and Rx rings.
        # Currently, the code just passes the value to ethtool's --set-ring.
        self.num_tx_ring_entries = 1024
        self.num_rx_ring_entries = 1024


    def get_rate(self, interface):

        # Without a small delay, the program flow will call ethtool twice too
        # fast, causing it to return "Unknown!" speed
        time.sleep(1)

        return self.systeminfo.get_rate(interface)


    def get_base_time_multiple(self):
        return -1


    def supports_schedule(self, schedule):

        if schedule.opens_gate_multiple_times_per_cycle():
            return False

        # FIXME: check additional constraints, like maximum cycle time

        return True
