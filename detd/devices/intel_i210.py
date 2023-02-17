#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

""" Module intel_i210

"""




from ..logger import get_logger

from .device import Device


logger = get_logger(__name__)




class IntelI210(Device):


    NUM_TX_QUEUES = 4
    NUM_RX_QUEUES = 4

    PCI_IDS_VALID = ['8086:1533', '8086:1536', '8086:1537', '8086:1538', '8086:157B',
                     '8086:157C', '8086:15F6']

    # Hardware default. Empty Flash Image (or NVM configuration loading failed)
    PCI_IDS_UNPROGRAMMED = ['8086:1531']

    PCI_IDS = PCI_IDS_VALID + PCI_IDS_UNPROGRAMMED

    def __init__(self, pci_id):

        logger.info(f"Initializing {__class__.__name__}")

        super().__init__(IntelI210.NUM_TX_QUEUES, IntelI210.NUM_RX_QUEUES)

        self.capabilities = []
       # raise NotImplementedError("Handler class for i210 Ethernet controller not yet implemented")


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

