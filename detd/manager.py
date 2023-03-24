#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

""" Module manager

This module implements the core management functionality.
    * Manager: system-wide manager
    * InterfaceManager: per-interface manager

The Manager receives the QoS requests, and hand them over to the specific
InterfaceManager.
"""




import threading
import time

from .scheduler import Scheduler
from .scheduler import Traffic
from .scheduler import TrafficType
from .systemconf import SystemInformation
from .mapping import Mapping
from .common import Check

from .devices import device

from .logger import get_logger


logger = get_logger(__name__)




class Interface:

    def __init__(self, name):

        if not Check.is_interface(name):
            logger.error(f"{name} is not a valid network interface name")
            raise TypeError(f"{name} is not a valid network interface name")
            
        self.name = name

        sysinfo = SystemInformation()

        # XXX Passing self before completing __init__ is really weird but it
        # helps to keep the interfaces offered by SystemInformation and
        # SystemConfiguration consistent (e.g. they all accept Interface as
        # the representation for a network interface)
        pci_id = sysinfo.get_pci_id(self)
        self.device = device.from_pci_id(pci_id)


    @property
    def rate(self):
        return self.device.get_rate(self)


    def setup(self, mapping, scheduler, stream, options):
        self.device.setup(self, mapping, scheduler, stream, options)




class Manager():


    def __init__(self):

        logger.info(f"Initializing {__class__.__name__}")

        self.talker_manager = {}
        self.lock = threading.Lock()


    def add_talker(self, config):

        logger.info("Adding talker to Manager")

        with self.lock:

            if not config.interface.name in self.talker_manager:
                interface_manager = InterfaceManager(config.interface, config.options)
                self.talker_manager[config.interface.name] = interface_manager

            return self.talker_manager[config.interface.name].add_talker(config)




class InterfaceManager():

    def __init__(self, interface, options):

        logger.info(f"Initializing {__class__.__name__}")

        self.interface = interface
        self.options = options
        
        if self.options.qdiscmap == "nomap":
            self.mapping = Mapping(self.interface)
        else:
            self.mapping = Mapping(self.interface, self.options)
        self.scheduler = Scheduler(self.mapping)


    def add_talker(self, config):
        '''
        Performs the local configuration for the configuration provided
        and returns the associated VLAN interface and socket priority


        Parameters:

            config: configuration


        Returns:

            VLAN interface
            socket priority
        '''

        logger.info("Adding talker to InterfaceManager")


        # Retrieve device rate
        try:
           rate = self.interface.rate
        except RuntimeError:
            logger.exception("Error while retrieving device rate")
            raise


        # Assign resources
        soprio, tc, queue = self.mapping.assign_and_map(config.stream.pcp, self.scheduler.traffics)

        traffic = Traffic(rate, TrafficType.SCHEDULED, config)
        traffic.tc = tc


        # Add stream to schedule
        try:
            self.scheduler.add(traffic)
        except Exception as ex:
            logger.exception(f"Error while adding traffic to schedule:\n{self.scheduler.schedule}")
            self.mapping.unmap_and_free(soprio, traffic.tc, queue)
            raise


        # Make sure that the target device is able to implement the resulting schedule
        if not self.interface.device.supports_schedule(self.scheduler.schedule):
            # FIXME: add the limitations in the devices.py class handling the device
            # and then print the docstrings when this error happens
            logger.error(f"The device associated to the network interface does not support the schedule:\n{self.scheduler.schedule}")
            self.scheduler.remove(traffic)
            self.mapping.unmap_and_free(soprio, traffic.tc, queue)
            raise TypeError("The device associated to the network interface does not support the resulting schedule")


        # Normally, the base_time will be determined by the network planning process
        # However, for quick tests, we may just want to give a value that allows us
        # to send frames according to a given schedule. That is what a value of
        # None in the base_time will trigger.
        if config.stream.base_time is None:
            self.update_base_time(config)


        # Configure the system
        try:
            self.interface.setup(self.mapping, self.scheduler, config.stream, config.options)
        except:
            # Leave the internal structures in a consistent state
            logger.error("Error applying the configuration on the system")
            self.scheduler.remove(traffic)
            self.mapping.unmap_and_free(soprio, traffic.tc, queue)
            raise RuntimeError("Error applying the configuration on the system")

        #Calculate MAC offset
        txoffsetmin = config.stream.txoffset - self.interface.device.hardware_delay_max
        txoffsetmax = config.stream.txoffset - self.interface.device.hardware_delay_min
        
        # FIXME: generate the name to use for the VLAN interface in the manager
        # instead of in the command string class.

        vlan_interface = "{}.{}".format(self.interface.name, config.stream.vid)
        return vlan_interface, soprio, txoffsetmin, txoffsetmax


    # Unfortunately, not all devices accept base_time in the future, or base_time
    # in the past, throwing errors if the wrong choice is taken. This method
    # avoids those problems by setting a base_time according to each device
    # specific behaviour.
    # Please note this is just a helper for quick experimentation, the base
    # time should be provided by the network configuration.
    def update_base_time(self, config):

        period = config.traffic.interval
        # The device object gives an integer that will determine how many
        # cycles in the past or the future are added to the time of the next
        # cycle start.
        multiple = self.interface.device.get_base_time_multiple()

        # XXX: evil trick to run on python3 < 3.9...
        # The hardcoded 11 (taken from /usr/include/linux/time.h) must be
        # replaced by time.CLOCK_TAI
        # now = time.clock_gettime_ns(time.CLOCK_TAI)
        CLOCK_TAI = 11
        now = time.clock_gettime_ns(CLOCK_TAI)
        ns_until_next_cycle = period - (now % period)
        safety_margin = multiple * period

        config.stream.base_time = (now + ns_until_next_cycle) + safety_margin
