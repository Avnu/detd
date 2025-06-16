#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

""" Module device

This module contains:
     * from_pci_id: a function to instantiate device handler classes
     * Device: an abstract class to implement the handlers for concrete devices

"""




import enum

from ..systemconf import SystemConfigurator
from ..systemconf import SystemInformation

from ..common import DataPath
from ..common import TxSelection
from ..common import Hints

from ..logger import get_logger


logger = get_logger(__name__)

def from_pci_id(pci_id):

    # Retrieve all the subclasses inheriting from class Device
    devices = [ cls for cls in Device.__subclasses__()]

    # Find a match for the PCI ID by checking the class attribute PCI_IDS
    # Make sure to provide the class attribute PCI_IDS when creating your
    # own class
    for device in devices:
        if pci_id in device.PCI_IDS:
            return device(pci_id)

    raise NameError("Unrecognized PCI ID: {}".format(pci_id))

class Capability(enum.Enum):
    Qbv = 0
    Qbu = 1
    LTC = 2

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

        self.systeminfo = SystemInformation()
        self.systemconf = SystemConfigurator()

        self.capabilities = []

        self.num_tx_queues = num_tx_queues
        self.num_rx_queues = num_rx_queues
        self.best_effort_tx_queues = list(range(0, num_tx_queues))

        self.mapping = None

        # self.features
        # Taking the name from ethtool's "features" option.
        # Currently, the code just passes the key and value to ethtool.
        # Ideally, this should be stored in a way independent from ethtool.
        # Features will be initialized by the specific device class
        self.features = {}


    def setup_talker(self, interface, mapping, scheduler, stream, hints):
        '''Performs the configuration of the talker stream provided.
        '''

        self.systemconf.setup_talker(interface, mapping, scheduler, stream, hints)

    def setup_listener(self, interface, stream, mapping, scheduler, hints, maddress):

        self.systemconf.setup_listener(interface, stream, mapping, scheduler, hints, maddress)


    def get_rate(self, interface):
        # FIXME: runtime changes in rate need to be managed
        sysinfo = SystemInformation()

        return sysinfo.get_rate(interface)


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
    
    def default_hints(self):
        '''Returns device supported default Hints.
        '''
        preemption = False
        launch_time_control = False
        tx_selection_offload = False
        datapath = DataPath.AF_PACKET
        tx_selection = TxSelection.Qbv
        
        return Hints(tx_selection, tx_selection_offload ,datapath, preemption, launch_time_control)
    
    def check_hints(self, config):

        preemption = config.hints.preemption
        launch_time_control = config.hints.launch_time_control
        tx_selection_offload = config.hints.tx_selection_offload
        datapath = DataPath(config.hints.data_path)
        tx_selection = TxSelection(config.hints.tx_selection)

        # Add feature later
        if datapath != DataPath.AF_PACKET:
            raise ValueError(f"Device does not support the requested DataPath feature."
                             f"Requested: {datapath}")

        if  tx_selection == TxSelection.EST and tx_selection_offload == True:
            if Capability.Qbv not in self.capabilities:
                raise ValueError(f"Device does not support the requested Tx selection feature."
                                 f"Requested Tx_selection: {tx_selection}, Requested tx_selection_offload: {tx_selection_offload}")
    
        if preemption == True:
            if Capability.Qbu not in self.capabilities:
                raise ValueError(f"Device does not support the requested Tx selection feature."
                                 f"Requested Tx_selection: {tx_selection}, Requested preemption: {preemption}")

        if  launch_time_control == True:
            if Capability.LTC not in self.capabilities:
                raise ValueError(f"Device does not support the requested launch_time_control feature."
                                 f"Requested: {launch_time_control}")
        
        return Hints(tx_selection, tx_selection_offload ,datapath, preemption, launch_time_control)     
