#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

""" Module intel_i210

"""


import time

from ..logger import get_logger

from .device import Capability
from .device import Device


logger = get_logger(__name__)




class IntelI210(Device):


    NUM_TX_QUEUES = 4
    NUM_RX_QUEUES = 4
    
    CAPABILITIES  = [Capability.LTC]

    #MAC+PHY latency assuming 100 mbit link
    HARDWARE_LATENCY_MIN = 2168
    HARDWARE_LATENCY_MAX = 2384

    PCI_IDS_VALID = ['8086:1533', '8086:1536', '8086:1537', '8086:1538', '8086:157B',
                     '8086:157C', '8086:15F6']

    # Hardware default. Empty Flash Image (or NVM configuration loading failed)
    PCI_IDS_UNPROGRAMMED = ['8086:1531']

    PCI_IDS = PCI_IDS_VALID + PCI_IDS_UNPROGRAMMED

    def __init__(self, pci_id):

        logger.info(f"Initializing {__class__.__name__}")

        super().__init__(IntelI210.NUM_TX_QUEUES, IntelI210.NUM_RX_QUEUES, IntelI210.HARDWARE_LATENCY_MIN, IntelI210.HARDWARE_LATENCY_MAX)

        self.capabilities = [Capability.LTC]

        self.features['rxvlan'] = 'off'

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

        return True
