#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

""" Module manager

This module implements the core functionality:
    * QoS requests: class Manager and specially class InterfaceManager
    * Local scheduling of multiple streams: class Scheduler
    * Resource allocation and dellocation: class Mapping

It also contains the classes defining a stream configuration, and those
modelling different traffic types.
"""




import enum
import math
import threading
import time

from .systemconf import SystemConfigurator
from .systemconf import SystemInformation
from .common import Check
from .devices import Device




s_to_ns = 1000 * 1000 * 1000
Bytes_to_bits = 8




class Configuration:

    def __init__(self, interface, stream, traffic):

        if not Check.is_interface(interface.name):
            raise TypeError("Invalid interface")

        if stream.txoffset > traffic.interval:
            raise TypeError("Invalid TxOffset, it exceeds Interval")

        self.interface = interface
        self.stream = stream
        self.traffic = traffic


class StreamConfiguration:

    def __init__(self, addr, vid, pcp, txoffset, base_time=None):

        if not Check.is_mac_address(addr):
            raise TypeError("Invalid MAC address")

        if not Check.is_valid_vlan_id(vid):
            raise TypeError("Invalid VLAN ID")

        if not Check.is_valid_pcp(pcp):
            raise TypeError("Invalid VLAN PCP")

        if not Check.is_natural(txoffset):
            raise TypeError("Invalid TxOffset")

        if not Check.is_natural(base_time):
            if base_time is not None:
                raise TypeError("Invalid base_time")

        self.addr = addr
        self.vid = vid
        self.pcp = pcp
        self.txoffset = txoffset
        self.base_time = base_time


class TrafficSpecification:

    def __init__(self, interval, size):

        if not Check.is_natural(interval):
            raise TypeError("Invalid Interval")

        if not Check.is_natural(size):
            raise TypeError("Invalid Size")

        self.interval = interval
        self.size = size




class TrafficType(enum.Enum):
    BEST_EFFORT = 0
    SCHEDULED = 1

    @classmethod
    def contains(cls, value):
        return value in cls._value2member_map_




'''
Only one gate open at the same time
'''
class Traffic:

    def __init__(self, traffic_type=TrafficType.BEST_EFFORT, config=None):

        self.type = traffic_type
        if traffic_type == TrafficType.SCHEDULED:
            self.interval = config.traffic.interval
            self.size = config.traffic.size
            self.start = config.stream.txoffset
            self.addr = config.stream.addr
            self.vid = config.stream.vid
            self.pcp = config.stream.pcp
            self.tc = None
            # Pre-calculate to improve readability
            rate = config.interface.device.rate
            self.length = (self.size * Bytes_to_bits) / (rate / s_to_ns)
            self.end = self.start + self.length


    def __str__(self):
        if self.type == TrafficType.SCHEDULED:
            short_type = "Sc"
            start = self.start
            end = self.end
            interval = self.interval
            output = "{} {} [{} {}]".format(short_type, interval, start, end)
        elif self.type == TrafficType.BEST_EFFORT:
            short_type = "BE"
            output = "{}".format(short_type)
        else:
            output = "Unknown Traffic"

        return output


    def __repr__(self):
        return self.__str__()


    def __eq__(self, other):

        if not isinstance(other, Traffic):
            return False

        if dir(self) != dir(other):
            return False

        for attr in dir(self):
            if getattr(self, attr) != getattr(other, attr):
                return False

        # Return True if all attributes are the same
        return True


    def __hash__(self):

        assert(TrafficType.contains(self.type))

        traffic_type = self.type
        if traffic_type == TrafficType.BEST_EFFORT:
            interval = None
            size = None
            start = None
            addr = None
            vid = None
            pcp = None
            tc = None
        elif traffic_type == TrafficType.SCHEDULED:
            interval = self.interval
            size = self.size
            start = self.start
            addr = self.addr
            vid = self.vid
            pcp = self.pcp
            tc = self.tc

        fields_to_hash = [traffic_type, interval, size, start, addr, vid, pcp, tc]

        return hash(fields_to_hash)




class Slot:

    def __init__(self, start, end, traffic):
        self.start = int(start) # ns
        self.end = int(end)     # ns
        self.length = int(self.end-self.start) #ns
        self.traffic = traffic

    def __eq__(self, other):
        return self.start == other.start

    def __lt__(self, other):
        return self.start < other.start




class Schedule(list):
    '''Represents the schedule as a list of slots.

    Each slot:
    * Is defined by its start and end time relative to the start of the cycle
    * Holds a single traffic class
    '''

    def __init__(self):
        super().__init__(self)
        self.period = 0


    def add_scheduled_traffic(self, start, end, traffic):
        self.append(Slot(start, end, traffic))
        self.sort()


    def add_best_effort_padding(self, traffic):

        end = 0
        i = 0
        n = len(self)
        while i < n:
            assert end <= self[i].start, "i={0}: {1} > {2}".format(i, end, self[i].start)
            if end < self[i].start:
                # We add all the padding slots at the end and will sort later
                # This way we do not need to deal with re-indexing
                self.append(Slot(end, self[i].start, traffic))
                end = self[i].end
            elif end == self[i].start:
                end = self[i].end
            i += 1
        # We sort the list of slots that now contains scheduled and best effort
        self.sort()
        # The last best effort padding element may cover the remaining until period
        if self[-1].end < self.period:
            self.append(Slot(self[-1].end, self.period, traffic))


    def opens_gate_multiple_times_per_cycle(self):
        '''Returns True if any gate opens more than once over the same cycle.

        Some devices do not allow a hardware queue to be opened more than once
        in the same cycle.
        '''

        opened_once = []

        # Traverse the slots in the schedule and check how many times the gate
        # for a traffic type has to be opened.
        i = 0
        n = len(self)

        while i < n:

            # Determine traffic in this slot and in the previous one
            traffic = self[i].traffic
            if i == 0:
                previous_traffic = None
            else:
                previous_traffic = self[i-1].traffic

            if traffic in opened_once:
                # If this slot contains the previous traffic, there is no
                # new open event, as the gate simply remains open.
                if previous_traffic == traffic:
                    pass
                else:
                    return True
            else:
                opened_once.append(traffic)

            i = i + 1


        return False


    def __str__(self):
        slots = ["|{0} {1}|".format(s.start, s.end) for s in self]
        return "<" + ",".join(slots) + '>\n'




# Lowest common multiple
def lcm(numbers):

    lcm = 1
    for n in numbers:
        lcm = abs(lcm * n) // math.gcd(lcm, n)

    return lcm




class Scheduler:

    def __init__(self, mapping):
        self.schedule = Schedule()

        # traffics will hold all the traffics including best effort
        # The specific index will be referenced from each slot in the schedule
        # E.g. 0 will always contain Best Effort
        # FIXME: make this independent from OS

        self.traffics = []

        best_effort_traffic = Traffic(TrafficType.BEST_EFFORT)
        best_effort_traffic.socket_prio = mapping.best_effort_socket_prio
        best_effort_traffic.queue = mapping.interface.device.best_effort_tx_queues[0]
        best_effort_traffic.tc = mapping.best_effort_tc

        self.traffics.append(best_effort_traffic)


    def add(self, traffic):
        self.traffics.append(traffic)
        self.reschedule()


    def remove(self, traffic):
        self.traffics.remove(traffic)
        self.reschedule()


    def reschedule(self):
        if len(self.traffics) == 1 and self.traffics[0].type == TrafficType.BEST_EFFORT:
            self.schedule = Schedule()

        else:
            # FIXME: add check so there are no overlapping txoffsets
            scheduled = [t for t in self.traffics if t.type == TrafficType.SCHEDULED]

            self.schedule = Schedule()
            self.schedule.period = lcm([tc.interval for tc in scheduled])

            for traffic in scheduled:
                # Number of times that the traffic will be sent for the schedule's period
                n = self.schedule.period / traffic.interval
                i = 0
                offset = traffic.start
                interval = traffic.interval
                length = traffic.length
                while i < n:
                    start = offset + (interval * i)
                    end = start + length
                    self.schedule.add_scheduled_traffic(start, end, traffic)
                    i += 1

            self.schedule.add_best_effort_padding(self.traffics[0])
            # FIXME: error handling




class Interface:

    def __init__(self, name):
        self.name = name

        sysinfo = SystemInformation()
        pci_id = sysinfo.get_pci_id(name)
        self.device = Device.from_pci_id(pci_id)




class Mapping():

    """
    A class mapping the hardware and system resources (socket priorities,
    queues, etc) to implement specific traffic types, given a set of
    conventions.

    It deals with the following elements:
    - Network traffic classes and traffic types (e.g. based on PCP)
    - Linux traffic classes used by the tc infrastructure
    - Socket priorities
    - Queues used by the tc infrastructure, including device hardware queues

    Different mappings are expected to be available by subclassing it. The
    default class allows for Best Effort and up to 7 streams.

    The conventions followed are:
    - Two traffic types supported: Best Effort and Scheduled (Time Critical)
    - Best Effort:
      - Socket priority 0 (default)
      - Linux tc Traffic Class 0
      - PCP 0
      - Hardware queues minimum 1, default all
    - Scheduled
      - Socket priorities 7 to 254
      - Linux tc Traffic Classes 1 to max hw queues minus one
      - PCP 1 to max hw queues minus one
      - Hardware queues maximum all but one, default none

    This class is Linux specific.
    """


    def __init__(self, interface):

        self.interface = interface

        # Initialize socket priority mappings
        # Socket prio 0 is configured as the default
        # because Linux will use it as the default
        # Socket prios 1 to 6 are not used in reservations
        # because they can be set without CAP_NET_ADMIN (see man 7 socket)
        # Socket prios 7 for 255 are available for reservation
        # because their setup is restricted to CAP_NET_ADMIN
        self.available_socket_prios = list(range(7, 256))
        self.best_effort_socket_prio = 0
        self.used_socket_prios = set([0])

        # Initialize best effort traffic type
        # Use TC0 for BE for consistency with socket priority 0
        self.best_effort_tc = 0

        # Assumes the BE mappings to socket prio 0 and TC 0
        # Index: tc, Value: soprio
        # See also the property soprio_to_tc
        self.tc_to_soprio = [0]
        # FIXME set up socket making it option


        # FIXME more sophisticathed mapping to pcps, based e.g. on std mappings
        # like IEC 60802
        # {soprio: pcp}
        self.soprio_to_pcp = {0: 0}

        # Index: traffic class
        # [{offset:, numqueues:}, {}]

        # Initially, all queues are used for best effort traffic
        # Everytime that a new traffic class is added, a best effort queue
        # will be removed and assigned to it
        num_tx_queues = self.interface.device.num_tx_queues
        self.tc_to_hwq = [ {"offset":0, "num_queues":num_tx_queues} ]

        # Tx queues available to be assigned to streams
        self.available_tx_queues = list(reversed(range(0, num_tx_queues)))



    @property
    def soprio_to_tc(self):
        # First we assign all socket prios to traffic class 0 (Best Effort)
        mapping = [0] * 16
        # Then we assign those socket prios used by other traffic classes
        for tc, soprio in enumerate(self.tc_to_soprio):
            mapping[soprio] = tc

        return mapping


    def assign_and_map(self, pcp, traffics):

        # Assign a socket priority for this stream
        soprio = self.assign_soprio_and_map(pcp)

        # Assign a traffic class to the new traffic and map
        tc = self.assign_tc_and_map(soprio, traffics)

        # Assign the queue indicated by the device
        queue = self.assign_queue_and_map(tc)

        return soprio, tc, queue


    def unmap_and_free(self, soprio, queue):
        self.unmap_and_free_queue(queue)
        self.unmap_and_free_tc(soprio)
        self.unmap_and_free_soprio(soprio)




    def assign_soprio_and_map(self, pcp):
        # FIXME handle the case when no socket prios are available
        assert len(self.available_socket_prios) > 0
        soprio = self.available_socket_prios.pop(0)
        self.soprio_to_pcp[soprio] = pcp

        return soprio


    def unmap_and_free_soprio(self, soprio):
        del self.soprio_to_pcp[soprio]
        self.available_socket_prios.append(soprio)


    def assign_tc_and_map(self, soprio, traffics):
        tc = len(traffics)
        self.tc_to_soprio.append(soprio)

        return tc


    def unmap_and_free_tc(self, soprio):
        assert len(self.tc_to_soprio) > 1
        self.tc_to_soprio.remove(soprio)


    def assign_queue_and_map(self, tc):

        # There must be at least one queue available for best effort traffic
        if len(self.available_tx_queues) == 1:
            raise IndexError

        queue = self.available_tx_queues.pop(0)

        # Remove one queue from the best effort allocation
        self.tc_to_hwq[0]["num_queues"] = self.tc_to_hwq[0]["num_queues"] - 1

        # Assign the allocated queue to the new traffic class
        new_offset = self.tc_to_hwq[0]["num_queues"]
        self.tc_to_hwq.insert(1, {"offset": new_offset, "num_queues": 1})


        return queue


    def unmap_and_free_queue(self, tc):
        # XXX In the default mapper, this is a rollback function. E.g. that is
        # not intended to dynamically add or remove streams. It should only
        # be called immediately after having called assign_queue_and_map, when
        # a follow-up operation fails and the system would be left in an
        # inconsistent state.
        # Hence, it makes some assumptions about the last item added to the
        # mapping, that would not proceed in a general function to free the
        # queue assigned to a given traffic class.

        # There must be at least one traffic class available for best effort
        if len(self.tc_to_hwq) == 1:
            raise IndexError

        self.tc_to_hwq[0]["num_queues"] = self.tc_to_hwq[0]["num_queues"] + 1
        del self.tc_to_hwq[1]

        # Add the queue number to the available tx queues
        self.available_tx_queues.append(self.available_tx_queues[-1] + 1)




class Manager():


    def __init__(self):

        self.talker_manager = {}
        self.lock = threading.Lock()


    def add_talker(self, config):

        with self.lock:

            if not config.interface.name in self.talker_manager:
                self.talker_manager[config.interface.name] = InterfaceManager(config.interface)

            return self.talker_manager[config.interface.name].add_talker(config)




class InterfaceManager():

    def __init__(self, interface):

        self.interface = interface
        self.mapping = Mapping(self.interface)

        self.runner = SystemConfigurator()

        # Best effort traffic gets socket prio 0, the default
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


        soprio, tc, queue = self.mapping.assign_and_map(config.stream.pcp, self.scheduler.traffics)

        traffic = Traffic(TrafficType.SCHEDULED, config)
        traffic.tc = tc
        self.scheduler.add(traffic)
        if not self.interface.device.supports_schedule(self.scheduler.schedule):
            # FIXME: add the limitations in the devices.py class handling the device
            # and then print the docstrings when this error happens
            print(self.scheduler.schedule)
            raise TypeError("The device associated to the network interface does not support the resulting schedule")


        # Normally, the base_time will be determined by the network planning process
        # However, for quick tests, we may just want to give a value that allows us
        # to send frames according to a given schedule. That is what a value of
        # None in the base_time will trigger.
        if config.stream.base_time is None:
            self.update_base_time(config)

        try:
            self.runner.setup(self.interface, self.mapping, self.scheduler, config.stream)
        except:
            # Leave the internal structures in a consistent state
            self.scheduler.remove(traffic)
            self.mapping.unmap_and_free(soprio, queue)
            raise

        # FIXME: generate the name to use for the VLAN inteface in the manager
        # instead of in the command string class.

        vlan_interface = "{}.{}".format(self.interface.name, config.stream.vid)
        return vlan_interface, soprio


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
