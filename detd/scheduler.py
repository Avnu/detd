#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

""" Module scheduler

This module provides the local scheduling facilities for multiple streams.

It deals with domain entities. E.g. it is decoupled from the actual system
interface to apply such changes.

It also contains the classes defining a stream configuration, and those
modelling different traffic types.
"""




import enum
import math

from .common import Check

from .logger import get_logger


s_to_ns = 1000 * 1000 * 1000
Bytes_to_bits = 8


logger = get_logger(__name__)



class Configuration:

    def __init__(self, interface, stream, traffic, hints = None):

        if stream.txoffset > traffic.interval:
            raise TypeError("Invalid TxOffset, it exceeds Interval")

        self.interface = interface
        self.stream = stream
        self.traffic = traffic
        self.hints = hints


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

    def __init__(self, rate, traffic_type=TrafficType.BEST_EFFORT, config=None):

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


    def conflicts_with_traffic(self, traffic):

        if traffic.type == TrafficType.BEST_EFFORT:
            return False

        for slot in [s for s in self if s.traffic.type == TrafficType.SCHEDULED]:

            # The scheduled traffic starts into a non BE slot
            if traffic.start >= slot.start and traffic.start <= slot.end:
                return True

            # The scheduled traffic ends into a non BE slot
            if traffic.end >= slot.start and traffic.end <= slot.end:
                return True


        return False


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

        logger.info(f"Initializing {__class__.__name__}")

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

        logger.info("Adding traffic to schedule")

        if self.schedule.conflicts_with_traffic(traffic):
            logger.error(f"Traffic conflicts with schedule: {self.schedule}")
            raise ValueError("Traffic conflicts with existing schedule")
        self.traffics.append(traffic)
        self.reschedule()


    def remove(self, traffic):
        self.traffics.remove(traffic)
        self.reschedule()


    def reschedule(self):
        if len(self.traffics) == 1 and self.traffics[0].type == TrafficType.BEST_EFFORT:
            self.schedule = Schedule()

        else:
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

class DataPath(enum.Enum):
    AF_PACKET = 0
    AF_XDP_ZC = 1

class TxSelection(enum.Enum):
    EST = 0            # ENHANCEMENTS_FOR_SCHEDULED_TRAFFIC
    STRICT_PRIO = 1    # STRICT_PRIORITY (Preemption)

class Hints:
    """
    A configuration class for managing traffic specifications and QoS (Quality of Service)
    settings for network devices.

    Attributes:
        tx_selection (str): Determines the transmission selection mechanism to use.
            Possible values are:
            - 'ENHANCEMENTS_FOR_SCHEDULED_TRAFFIC' (802.1Qbv)
            - 'STRICT_PRIORITY'
        tx_selection_offload (bool): Indicates whether a hardware offload for the
            tx_selection mechanism is used. True means hardware offload is enabled,
            false implies a software-based approach.
        data_path (str): Specifies the data path technology used. Current options include:
            - 'AF_PACKET'
            - 'AF_XDP_ZC'
            Future expansions may include other data paths like 'DPDK'.
        preemption (bool): Enables or disables preemption in the data transmission.
        launch_time_control (bool): Enables or disables launch time control for packets.

    """
    def __init__(self, tx_selection: TxSelection, tx_selection_offload: bool, data_path: DataPath, preemption: bool, launch_time_control: bool):
       
        self.tx_selection = tx_selection
        self.tx_selection_offload = tx_selection_offload
        self.data_path = data_path
        self.preemption = preemption
        self.launch_time_control = launch_time_control

    def __repr__(self):
        return (f"Hints(tx_selection={self.tx_selection.name}, "
                f"tx_selection_offload={self.tx_selection_offload}, "
                f"data_path={self.data_path.name}, "
                f"preemption={self.preemption}, "
                f"launch_time_control={self.launch_time_control})")


