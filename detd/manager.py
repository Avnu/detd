#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

import enum
import math
import threading

from .systemconf import SystemConfigurator
from .systemconf import SystemInformation
from .systemconf import Check
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

    def __init__(self, addr, vid, pcp, txoffset):

        if not Check.is_mac_address(addr):
            raise TypeError("Invalid MAC address")

        if not Check.is_valid_vlan_id(vid):
            raise TypeError("Invalid VLAN ID")

        if not Check.is_valid_pcp(pcp):
            raise TypeError("Invalid VLAN PCP")

        if not Check.is_natural(txoffset):
            raise TypeError("Invalid TxOffset")

        self.addr = addr
        self.vid = vid
        self.pcp = pcp
        self.txoffset = txoffset


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
        best_effort_traffic.queue = mapping.interface.device.best_effort_queue
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
        self.tc_to_hwq = None


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
#        tc = len(self.scheduler.traffics)
        tc = len(traffics)
        self.tc_to_soprio.append(soprio)

        return tc


    def unmap_and_free_tc(self, soprio):
        assert len(self.tc_to_soprio) > 1
        self.tc_to_soprio.remove(soprio)


    def assign_queue_and_map(self, queue):
        queue = self.interface.device.assign_queue()
        # XXX FIX so actually queues are reserved and managed
        self.tc_to_hwq = [
            {"offset":0, "num_queues":1},
            {"offset":1, "num_queues":1},
            {"offset":2, "num_queues":1},
            {"offset":3, "num_queues":1},
            {"offset":4, "num_queues":1},
            {"offset":5, "num_queues":1},
            {"offset":6, "num_queues":1},
            {"offset":7, "num_queues":1}]

        return queue


    def unmap_and_free_queue(self, queue):
        # XXX FIX so actually queues are reserved and managed
        pass



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
