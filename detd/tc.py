#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

""" Module tc

This module provides a class to execute iproute2's tc commands.

"""




import subprocess

from .common import CommandString




class CommandTc:

    def __init__(self):
        pass


    def run(self, command):
        cmd = command.split()
        result = subprocess.run(cmd, capture_output=True, text=True)

        success_codes = [0]
        if result.returncode not in success_codes:
            raise subprocess.CalledProcessError(result.returncode, command, result.stdout, result.stderr)

        return result


    def set_taprio_offload(self, interface, mapping, scheduler, base_time):

        # E.g. len(set([0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0]))
        num_tc = len(set(mapping.soprio_to_tc))
        soprio_to_tc = transform_soprio_to_tc(mapping.soprio_to_tc)
        tc_to_hwq = transform_tc_to_hwq(mapping.tc_to_hwq)
        schedule = extract_schedule(scheduler)
        sched_entries = transform_sched_entries(schedule)
        cmd = CommandStringTcTaprioOffloadSet(interface.name, num_tc, soprio_to_tc, tc_to_hwq, base_time, sched_entries)

        self.run(cmd)


    def unset_taprio_offload(self, interface):

        cmd = CommandStringTcTaprioOffloadUnset(interface.name)

        self.run(cmd)
    
    
    def set_taprio_software(self, interface, mapping, scheduler, base_time):

        # E.g. len(set([0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0]))
        num_tc = len(set(mapping.soprio_to_tc))
        soprio_to_tc = transform_soprio_to_tc(mapping.soprio_to_tc)
        tc_to_hwq = transform_tc_to_hwq(mapping.tc_to_hwq)
        schedule = extract_schedule(scheduler)
        sched_entries = transform_sched_entries(schedule)
        cmd = CommandStringTcTaprioSoftwareSet(interface.name, num_tc, soprio_to_tc, tc_to_hwq, base_time, sched_entries)

        self.run(cmd)


    def unset_taprio_software(self, interface):

        cmd = CommandStringTcTaprioOffloadUnset(interface.name)

        self.run(cmd)
        
        
    def set_taprio_txassist(self, interface, mapping, scheduler, base_time):

        # E.g. len(set([0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0]))
        num_tc = len(set(mapping.soprio_to_tc))
        soprio_to_tc = transform_soprio_to_tc(mapping.soprio_to_tc)
        tc_to_hwq = transform_tc_to_hwq(mapping.tc_to_hwq)
        schedule = extract_schedule(scheduler)
        sched_entries = transform_sched_entries(schedule)
        handle = "100"
        txtime_delay = "500000"
        cmd = CommandStringTcTaprioTxassistSet(interface.name, num_tc, soprio_to_tc, tc_to_hwq, base_time, sched_entries, handle, txtime_delay)

        self.run(cmd)


    def unset_taprio_txassist(self, interface):

        cmd = CommandStringTcTaprioOffloadUnset(interface.name)

        self.run(cmd)
        
        
    def install_etf(self, interface):
        
        parent = "100:1"
        delta = "500000"
        
        cmd = CommandStringTcEtfInstall(interface.name, parent, delta)
        
        self.run(cmd)
        

def num_tc(soprio_to_tc):
    return len(set(soprio_to_tc))


def transform_soprio_to_tc(soprio_to_tc):
    return ' '.join([str(tc) for tc in soprio_to_tc])


def transform_tc_to_hwq(tc_to_hwq):
    mapping = []
    for m in tc_to_hwq:
        mapping.append("{0}@{1}".format(m["num_queues"], m["offset"]))

    return ' '.join(mapping)


def extract_schedule(scheduler):
    schedule = []
    for slot in scheduler.schedule:
        entry = {}
        entry["command"] = "SetGateStates"
        tc = slot.traffic.tc
        gatemask = ""
        for i in reversed(range(0,8)):
            if i == tc:
                gatemask += "1"
            else:
                gatemask += "0"
        entry["gatemask"] = gatemask
        entry["interval"] = slot.length
        schedule.append(entry)
    return schedule


def transform_sched_entries(schedule):
    entries = []
    for slot in schedule:
        entries.append(transform_sched_entry(slot))

    return '\n'.join(entries)


def transform_sched_entry(slot):
    assert slot["command"] == "SetGateStates"
    if slot["command"] == "SetGateStates":
        command = "S"
    gatemask = gatemask_to_hex(slot["gatemask"])
    interval = slot["interval"]

    return "         sched-entry {0} {1} {2}".format(command, gatemask, interval)


def gatemask_to_hex(bitmask):

    low = int(bitmask, 2) & 0x0F
    high = int(bitmask, 2) >> 4

    return "{0:01X}{1:01X}".format(high, low)




###############################################################################
# tc command strings                                                          #
###############################################################################

class CommandStringTcTaprioOffloadSet(CommandString):

    def __init__(self, interface, num_tc, soprio_to_tc, tc_to_hwq, base_time, sched_entries):

        template = '''
           tc qdisc replace
                    dev       $interface
                    parent    root
                    taprio
                    num_tc    $num_tc
                    map       $soprio_to_tc
                    queues    $tc_to_hwq
                    base-time $base_time
                    $sched_entries
                    flags     0x2'''

        params = {
            'interface'     : interface,
            'num_tc'        : num_tc,
            'soprio_to_tc'  : soprio_to_tc,
            'tc_to_hwq'     : tc_to_hwq,
            'base_time'     : base_time,
            'sched_entries' : sched_entries
        }

        super().__init__(template, params)




class CommandStringTcTaprioOffloadUnset(CommandString):

    def __init__(self, interface):

        template = '''
           tc qdisc del
              dev $interface
              root'''

        params = {"interface" : interface}

        super().__init__(template, params)
        
        
class CommandStringTcTaprioSoftwareSet(CommandString):

    def __init__(self, interface, num_tc, soprio_to_tc, tc_to_hwq, base_time, sched_entries):

        template = '''
           tc qdisc replace
                    dev       $interface
                    parent    root
                    taprio
                    num_tc    $num_tc
                    map       $soprio_to_tc
                    queues    $tc_to_hwq
                    base-time $base_time
                    $sched_entries
                    flags     0x0
                    clockid CLOCK_TAI'''

        params = {
            'interface'     : interface,
            'num_tc'        : num_tc,
            'soprio_to_tc'  : soprio_to_tc,
            'tc_to_hwq'     : tc_to_hwq,
            'base_time'     : base_time,
            'sched_entries' : sched_entries
        }

        super().__init__(template, params)
        
        
class CommandStringTcTaprioTxassistSet(CommandString):

    def __init__(self, interface, num_tc, soprio_to_tc, tc_to_hwq, base_time, sched_entries, handle, txtime_delay):

        template = '''
           tc qdisc replace
                    dev       $interface
                    parent    root
                    handle    $handle
                    taprio
                    num_tc    $num_tc
                    map       $soprio_to_tc
                    queues    $tc_to_hwq
                    base-time $base_time
                    $sched_entries
                    flags     0x1
                    txtime-delay $txtime_delay
                    clockid CLOCK_TAI'''
                    
        params = {
            'interface'     : interface,
            'handle'        : handle,
            'num_tc'        : num_tc,
            'soprio_to_tc'  : soprio_to_tc,
            'tc_to_hwq'     : tc_to_hwq,
            'base_time'     : base_time,
            'sched_entries' : sched_entries,
            'txtime-delay'  : txtime_delay
        }

        super().__init__(template, params)
        
        
class CommandStringTcEtfInstall(CommandString):

    def __init__(self, interface, parent, delta):

        template = '''
           tc qdisc replace
                    dev       $interface
                    parent    $parent
                    etf
                    clockid   CLOCK_TAI
                    delta     $delta
                    offload
                    skip_sock_check'''
                    
        params = {
            'interface'     : interface,
            'parent'        : parent,
            'delta'         : delta
        }

        super().__init__(template, params)


