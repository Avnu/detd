#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

Gbps_to_bps = 1000 * 1000 * 1000

""" Module devices

This module contains the classes to handle networking devices.

There is an abstract Device class. Each concrete device should have its own
class derived from that. The selection of the specific concrete class is
performed by looking at the pci_ids presented by it.

The implementation of the class for each device should be kept as platform
independent as possible.

The number of dependencies on other modules should also be kept as reduced as
possible.

For a commented example about how to support a new device, see:
    * class IntelMgbeEhl
    * class Device classmethod from_pci_id

To include your new device in the host testing environment, some changes are
required. You may need to modify RunContext locally to reference the specific
PCI ID, add support for a DETD_PCI_ID environment variable, or extend the
mocking infrastructure to iterate through all the available classes when
running host based tests.

"""


class Device:

    """
    An abstract class to derive specific devices

    Also provides the class method from_pci_id. That is used to return the
    specific instance to handle a give device, identified by its PCI ID.

    """

    def __init__(self, num_tx_queues, num_rx_queues):
        """
        num_tx_queues: number of Tx queues
        num_rx_queues: number of Rx queues
        """

        self.num_tx_queues = num_tx_queues
        self.num_rx_queues = num_rx_queues
        self.best_effort_tx_queues = list(range(0, num_tx_queues))

        # self.features
        # Taking the name from ethtool's "features" option.
        # Currently, the code just passes the key and value to ethtool.
        # Ideally, this should be stored in a way independent from ethtool.
        # Features will be initialized by the specific device class
        self.features = {}

        # FIXME: this should be done in runtime and not hardcoded
        # FIXME: e.g. adding the ethtool query to SystemInformation
        # FIXME: and providing it to the constructor.
        self.rate = 1 * Gbps_to_bps # bits per second
        # FIXME: runtime changes in rate need to be managed


    @classmethod
    def from_pci_id(cls, pci_id):

        # This list contains the class name for all the devices intended to be
        # detected. If you are implementing a new device, make sure that you
        # add the name of the handler class here.
        devices = [ IntelMgbeEhl, IntelMgbeTgl, IntelMgbeTglH, IntelMgbeAdl,
                    IntelI210, IntelI225, IntelI226 ]

        # Find a match for the PCI ID by checking the class attribute PCI_IDS
        # Make sure to provide the class attribute PCI_IDS when creating your
        # own class
        for device in devices:
            if pci_id in device.PCI_IDS:
                return device(pci_id)

        raise NameError("Unrecognized PCI ID: {}".format(pci_id))


    def get_base_time_multiple(self):
        '''Returns the number of cycles that will be added to the start of the
        next cycle to determine the base time. This is only used to make some
        quick tests easier, so no network planner is involved.

        A negative figure will set the base time in the past.

        Subclass this to account for your device's specific handling of
        allowed base times.
        '''

        return 0


    def supports_schedule(self, schedule):
        '''Returns True if the device is able to implement the schedule,
        False otherwise

        It is intended to prevent developers to try to set up a schedule
        not supported by the underlying hardware implementation.

        Subclass this to account for your device's constraints. It may be
        used to account for bugs, but also limits like maximum cycle time.
        '''

        raise NotImplementedError("The handler class for the device must implement this function")


    @property
    def supports_split_channels(self):
        '''Returns true if the device allows to independently configure the
        Rx and Tx channels, false otherwise.

        "Channel" follows the ethtool convention.

        Subclass this when your device supports separated Rx and Tx channels.
        '''

        raise NotImplementedError("The handler class for the device must implement this function")




class IntelMgbeEhl(Device):

    # Use this docstring as the reference for your device
    """ Device handler for the integrated Intel mGBE controller on the
    Elkhart Lake platform
    """

    NUM_TX_QUEUES = 8
    NUM_RX_QUEUES = 8

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
        super().__init__(IntelMgbeEhl.NUM_TX_QUEUES, IntelMgbeEhl.NUM_RX_QUEUES)

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


    @property
    def supports_split_channels(self):
        return True



# FIXME: All the classes below should be implemented

class IntelMgbeTgl(Device):

    PCI_IDS = ['8086:A0AC']

    def __init__(self, pci_id):
        raise NotImplementedError("Handler class for Tiger Lake UP3's integrated TSN controller not yet implemented")


class IntelMgbeTglH(Device):

    PCI_IDS = ['8086:A0AC', '8086:43AC', '8086:43A2']

    def __init__(self, pci_id):
        raise NotImplementedError("Handler class for Tiger Lake H's integrated TSN controller not yet implemented")


class IntelMgbeAdl(Device):

    PCI_IDS = ['8086:7AAC', '8086:7AAD', '8086:54AC']

    def __init__(self, pci_id):
        raise NotImplementedError("Handler class for Alder Lake's integrated TSN controller not yet implemented")


class IntelI225(Device):

    NUM_TX_QUEUES = 4
    NUM_RX_QUEUES = 4

    # Devices supporting TSN: i225-LM, i225-IT
    PCI_IDS_VALID = ['8086:0D9F', '8086:15F2']

    # Devices not supporting TSN: i225-V, i225-LMvP
    PCI_IDS_NON_TSN = ['8086:15F3', '8086:5502']

    # Hardware default. Empty Flash Image (or NVM configuration loading failed)
    PCI_IDS_UNPROGRAMMED = ['8086:15FD']

    PCI_IDS = PCI_IDS_VALID + PCI_IDS_NON_TSN + PCI_IDS_UNPROGRAMMED


    def __init__(self, pci_id):
        super().__init__(IntelI225.NUM_TX_QUEUES, IntelI225.NUM_RX_QUEUES)

        if pci_id in IntelI225.PCI_IDS_NON_TSN:
            raise "This i225 device does not support TSN."

        if pci_id in IntelI225.PCI_IDS_UNPROGRAMMED:
            raise "The flash image in this i225 device is empty, or the NVM configuration loading failed."

        self.features['rxvlan'] = 'off'
        #self.features['hw-tc-offload'] = 'on'

        # self.num_tx_ring_entries and self.num_rx_ring_entries
        # Provides the number of ring entries for Tx and Rx rings.
        # Currently, the code just passes the value to ethtool's --set-ring.
        self.num_tx_ring_entries = 1024
        self.num_rx_ring_entries = 1024


    def get_base_time_multiple(self):
        return -1


    def supports_schedule(self, schedule):

        if schedule.opens_gate_multiple_times_per_cycle():
            return False

        # FIXME: check additional constraints, like maximum cycle time

        return True


    @property
    def supports_split_channels(self):
        return False


class IntelI226(Device):

    # Devices supporting TSN: i226-LM, i226-IT
    PCI_IDS_VALID = ['8086:125B', '8086:125D']

    # Hardware default. Empty Flash Image (or NVM configuration loading failed)
    PCI_IDS_UNPROGRAMMED = ['8086:125F']

    PCI_IDS = PCI_IDS_VALID + PCI_IDS_UNPROGRAMMED

    def __init__(self, pci_id):
        raise NotImplementedError("Handler class for i226 TSN Ethernet controller not yet implemented")


class IntelI210(Device):

    PCI_IDS_VALID = ['8086:1533', '8086:1536', '8086:1537', '8086:1538', '8086:157B',
                     '8086:157C', '8086:15F6']

    # Hardware default. Empty Flash Image (or NVM configuration loading failed)
    PCI_IDS_UNPROGRAMMED = ['8086:1531']

    PCI_IDS = PCI_IDS_VALID + PCI_IDS_UNPROGRAMMED

    def __init__(self, pci_id):
        raise NotImplementedError("Handler class for i210 Ethernet controller not yet implemented")
