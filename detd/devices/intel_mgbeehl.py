#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

""" Module intel_mgbeehl

"""




from ..logger import get_logger

from .device import Capability
from .device import Device


logger = get_logger(__name__)




class IntelMgbeEhl(Device):

    # Use this docstring as the reference for your device
    """ Device handler for the integrated Intel mGBE controller on the
    Elkhart Lake platform
    """

    NUM_TX_QUEUES = 8
    NUM_RX_QUEUES = 8

    HARDWARE_DELAY_MIN = 1000
    HARDWARE_DELAY_MAX = 2000

    # PCI IDs associated to the host. This is Intel Elkhart Lake specific.
    PCI_IDS_HOST = [ '8086:4B30', '8086:4B31', '8086:4B32']

    # PCI IDs associated to the PSE. This is Intel Elkhart Lake specific.
    PCI_IDS_PSE = [ '8086:4BA0', '8086:4BA1', '8086:4BA2',
                    '8086:4BB0', '8086:4BB1', '8086:4BB2' ]

    # Static attribute enumerating the PCI IDs that will be used to match this
    # device.
    # Make sure to expose this in your device class.
    PCI_IDS = PCI_IDS_HOST + PCI_IDS_PSE


    # FIXME support for listener stream
    # If the stream is time aware, flows should be configured for PTP traffic
    # e.g. ethtool -N $IFACE flow-type ether proto 0x88f7 queue $PTP_RX_Q
    # For Rx redirection:
    # ethtool --set-rxfh-indir ${INTERFACE} equal 2

    def __init__(self, pci_id):

        logger.info(f"Initializing {__class__.__name__}")

        super().__init__(IntelMgbeEhl.NUM_TX_QUEUES, IntelMgbeEhl.NUM_RX_QUEUES, IntelMgbeEhl.HARDWARE_DELAY_MIN, IntelMgbeEhl.HARDWARE_DELAY_MAX)

        self.capabilities = [Capability.Qbv]

        self.features['rxvlan'] = 'off'
        self.features['hw-tc-offload'] = 'on'

        self.num_tx_ring_entries = 1024
        self.num_rx_ring_entries = 1024

        # Please note other features are currently set for all devices in the
        # systemconf module.
        # For example, Energy Efficient Ethernet is disabled for all devices.


    def get_base_time_multiple(self):
        return 2


    def supports_schedule(self, schedule):

        # FIXME: check additional constraints, like maximum cycle time

        return True
