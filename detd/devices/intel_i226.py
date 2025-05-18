#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

""" Module intel_i226

"""

import time

from ..logger import get_logger

from .device import Capability
from .device import Device

from ..mapping import MappingFixed

from ..scheduler import DataPath
from ..scheduler import TxSelection
from ..scheduler import Hints

logger = get_logger(__name__)




class IntelI226(Device):

    NUM_TX_QUEUES = 4
    NUM_RX_QUEUES = 4

    CAPABILITIES = [Capability.Qbv, Capability.LTC, Capability.Qbu]

    # Devices supporting TSN: i226-LM, i226-IT
    PCI_IDS_VALID = ['8086:125B', '8086:125D']

    # Devices not supporting TSN
    PCI_IDS_NON_TSN = []

    # Hardware default. Empty Flash Image (or NVM configuration loading failed)
    PCI_IDS_UNPROGRAMMED = ['8086:15FD']

    PCI_IDS = PCI_IDS_VALID + PCI_IDS_NON_TSN + PCI_IDS_UNPROGRAMMED


    def __init__(self, pci_id):

        logger.info(f"Initializing {__class__.__name__}")

        super().__init__(IntelI226.NUM_TX_QUEUES, IntelI226.NUM_RX_QUEUES)

        if pci_id in IntelI226.PCI_IDS_NON_TSN:
            raise "This i226 device does not support TSN."

        if pci_id in IntelI226.PCI_IDS_UNPROGRAMMED:
            raise "The flash image in this i226 device is empty, or the NVM configuration loading failed."

        self.mapping = MappingFixed(self)

        self.features['rxvlan'] = 'off'
        #self.features['hw-tc-offload'] = 'on'

        self.capabilities = [Capability.Qbv, Capability.LTC, Capability.Qbu]

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

    def default_hints(self):
        '''Returns device supported default Hints.
        '''
        preemption = False
        launch_time_control = False
        tx_selection_offload = True
        datapath = DataPath.AF_PACKET
        tx_selection = TxSelection.EST

        return Hints(tx_selection, tx_selection_offload ,datapath, preemption, launch_time_control)
