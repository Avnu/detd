#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

""" Module mapping

This module provides Mapping classes. Each Mapping class implements an strategy
to deal with:

 * Resource allocation and deallocation: e.g. keeping a list of available
   traffic classes and handling which ones are already allocated to streams or
   traffics.

 * Resource mapping and unmapping: e.g. keeping track of which hardware queue
   corresponds to which traffic class.
"""




from .logger import get_logger


logger = get_logger(__name__)






class MappingNaive():

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
    - Dynamics
      - Traffic classes are static and can only be initialized once
      - Schedule can be changed as oong as traffic classes are unmodified

    This class is Linux specific.
    """


    def __init__(self, interface, options = None):

        logger.info(f"Initializing {__class__.__name__}")

        # FIXME: make the number of Tx queues a parameter, so things are not hardcoded

        self.interface = interface
        self.options = options


        # Socket priorities

        # Initialize socket priority mappings
        # Socket prio 0 is configured as the default
        # because Linux will use it as the default
        # Socket prios 1 to 6 are not used in reservations
        # because they can be set without CAP_NET_ADMIN (see man 7 socket)
        # Socket prios 7 for 255 are available for reservation
        # because their setup is restricted to CAP_NET_ADMIN
        self.best_effort_socket_prio = 0

        # Even though the socket prio assignments are static, we still need to
        # return the specific socket prio when adding a talker
        #self.available_socket_prios = [7, 8, 9, 10, 11, 12, 13]
        self.available_socket_prios = list(range(7, 7 + self.interface.device.num_tx_queues - 1))


        # Traffic classes

        # Initialize best effort traffic type
        # Use TC0 for BE for consistency with socket priority 0
        self.best_effort_tc = 0

        # Although the traffic classes are static, we still need to return the
        # specific tc when adding a talker
        #self.available_tcs = [1, 2, 3, 4, 5, 6, 7]
        self.available_tcs = list(range(1, 1 + self.interface.device.num_tx_queues - 1))

        # Assumes the BE mappings to socket prio 0 and TC 0
        # See also the property soprio_to_tc
        # Index: tc, Value: soprio
        # E.g. with 8 traffic classes:
        # self.tc_to_soprio = [0, 7, 8, 9, 10, 11, 12, 13]
        self.tc_to_soprio = [0]

        num_tx_queues = self.interface.device.num_tx_queues
        for i in range(num_tx_queues - 1):
            self.tc_to_soprio.append(7 + i)


        # PCPs

        # We do not need to change the soprio to PCP mapping in runtime
        # {soprio: pcp}
        # E.g.:
        # self.soprio_to_pcp = {
        #    0: 0,
        #    7: 1,
        #    8: 2,
        #    9: 3,
        #   10: 4,
        #   11: 5,
        #   12: 6,
        #   13: 7
        # }
        #
        # FIXME: make all PCPs for streams 6 or 7

        pcp = 0
        self.soprio_to_pcp = {}
        for soprio in self.tc_to_soprio:
            self.soprio_to_pcp[soprio] = pcp
            pcp = pcp + 1


        # Tx Queues

        # Index: traffic class
        # [{offset:, numqueues:}, {}]

        # self.tc_to_hwq = [
        #    {"offset":0, "num_queues":1},
        #    {"offset":1, "num_queues":1},
        #    {"offset":2, "num_queues":1},
        #    {"offset":3, "num_queues":1},
        #    {"offset":4, "num_queues":1},
        #    {"offset":5, "num_queues":1},
        #    {"offset":6, "num_queues":1},
        #    {"offset":7, "num_queues":1},
        # ]

        # We pre-assign all the queues for the expected traffic classes
        # New traffic classes won't be assigned during runtime
        num_tx_queues = self.interface.device.num_tx_queues

        self.tc_to_hwq = []
        for i in range(num_tx_queues):
            self.tc_to_hwq.append({"offset":i, "num_queues":1})

        # Tx queues available to be assigned to streams
        #self.available_tx_queues = [1, 2, 3, 4, 5, 6, 7]
        self.available_tx_queues = list(range(1, 1 + self.interface.device.num_tx_queues - 1))


    @property
    def soprio_to_tc(self):
        # First we assign all socket prios to traffic class 0 (Best Effort)
        mapping = [0] * 16
        # Then we assign those socket prios used by other traffic classes
        for tc, soprio in enumerate(self.tc_to_soprio):
            mapping[soprio] = tc
        
        if self.options is None:
            return mapping
        else:
            return [int(x) for x in self.options.qdiscmap.split()]


    def assign_and_map(self, pcp, traffics):

        logger.info("Assigning and mapping resources")

        # Assign a socket priority for this stream
        soprio = self.assign_soprio_and_map(pcp)

        # Assign a traffic class to the new traffic and map
        tc = self.assign_tc_and_map(soprio, traffics)

        # Assign the queue indicated by the device
        queue = self.assign_queue_and_map(tc)

        return soprio, tc, queue


    def unmap_and_free(self, soprio, tc, queue):
        self.unmap_and_free_queue(queue)
        self.unmap_and_free_tc(tc, soprio)
        self.unmap_and_free_soprio(soprio)


    def assign_soprio_and_map(self, pcp):

        # We ran out of socket prios to add new streams
        if len(self.available_socket_prios) == 0:
            raise IndexError

        soprio = self.available_socket_prios.pop(0)

        # The mapping was already done in the constructor

        return soprio


    def unmap_and_free_soprio(self, soprio):
        # Mapping is static, hence no unmapping required
        self.available_socket_prios.insert(0, soprio)


    def assign_tc_and_map(self, soprio, traffics):
        # We ran out of traffic classes to add new streams
        if len(self.available_tcs) == 0:
            raise IndexError

        tc = self.available_tcs.pop(0)

        # The TC to soprio mapping is static, hence no need to change it

        return tc


    def unmap_and_free_tc(self, tc, soprio):

        # The TC to soprio mapping is static, hence no need to change it

        self.available_tcs.insert(0, tc)


    def assign_queue_and_map(self, tc):

        # We ran out of queues to add new streams
        if len(self.available_tx_queues) == 0:
            raise IndexError("All available Tx queues are allocated already")

        queue = self.available_tx_queues.pop(0)

        # The hardware queue to traffic class is static, hence no need to change it

        return queue


    def unmap_and_free_queue(self, queue):

        # There must be at least one traffic class available for best effort
        if len(self.tc_to_hwq) == 1:
            raise IndexError

        self.available_tx_queues.insert(0, queue)

        # The hardware queue to traffic class is static, hence no need to change it
