#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

import collections
import enum
import inspect
import os
import math
import re
import socket
import stat
import subprocess
import time

from string import Template




class Check:

    """
    Functions to check validity and security of parameters

    Intended to be used for:
    - Boundaries (e.g. CLI inputs, IPC inputs...)
    - Command call parameter validation
    - etc
    """


    @classmethod
    def is_natural(cls, number):

        if number is None:
            return False

        if not isinstance(number, int):
            return False

        if number < 0:
            return False

        return True


    @classmethod
    def is_interface(cls, name):

        if name is None:
            return False

        interfaces = [i[1] for i in socket.if_nameindex()]
        if name in interfaces:
            return True
        else:
            return False


    @classmethod
    def is_mac_address(cls, addr):
        regex = re.compile("[0-9a-fA-F]{2}([:])[0-9a-fA-F]{2}(\\1[0-9a-fA-F]{2}){4}$")
        result = regex.match(addr)
        if result is None:
            return False
        else:
            return True


    @classmethod
    def is_valid_vlan_id(cls, vid):

        if 1 < vid < 4095:
            return True
        else:
            return False


    @classmethod
    def is_valid_pcp(cls, pcp):

        if 0 <= pcp <= 7:
            return True
        else:
            return False


    @classmethod
    def is_valid_path(cls, path):

        if path is None:
            return False

        # Check that path is absolute
        if not os.path.isabs(path):
            return False


        return True


    @classmethod
    def is_valid_file(cls, path):

        # Check that path is valid
        if not Check.is_valid_path(path):
            return False

        # Check if path is a symlink
        if os.path.islink(path):
            return False

        # Check if path is a hardlink
        # We can only identify if there is more than one reference
        try:
            if os.stat(path).st_nlink > 1:
                return False
        except FileNotFoundError:
            return False
        except:
            raise


        # Check if the path does not point to a regular file
        if not os.path.isfile(path):
            return False


        return True


    @classmethod
    def is_valid_unix_domain_socket(cls, path):

        # Check that path is valid
        if not Check.is_valid_path(path):
            return False

        # Check if path is a hardlink
        # We can only identify if there is more than one reference
        try:
            if os.stat(path).st_nlink > 1:
                return False
        except FileNotFoundError:
            return False
        except:
            raise

        # Check if the path points to a Unix Domain Socket
        mode = os.stat(path).st_mode
        if not stat.S_ISSOCK(mode):
            return False


        return True



"""
CommandString classes

Generate the strings required to call the different commands.

The resulting string is an executable Linux command with the right parameters
embedded.

Do not depend on any domain-specific knowledge or classes. E.g. all the
parameters are just basic Python data types.

Translation from domain-specific knowledge (e.g. a Scheduler class) is
performed by SystemConfigurator.

Input validation is performed by SystemConfigurator.
"""


# ip command strings

class CommandStringIpLinkSet (collections.UserString):

    def __init__(self, device, vid, soprio_to_pcp):

        template = Template(inspect.cleandoc('''
            ip link add
                    link     $device
                    name     $device.$id
                    type     vlan
                    protocol 802.1Q
                    id       $id
                    egress   $soprio_to_pcp'''))


        params = self._parameters(device, vid, soprio_to_pcp)
        # We replace newlines for the template string to work when invoked
        data = template.substitute(params).replace('\n', '')

        super().__init__(data)


    def _soprio_to_pcp(self, soprio_to_pcp):
        mapping = []
        for soprio, pcp in soprio_to_pcp.items():
            mapping.append("{0}:{1}".format(soprio, pcp))

        return ' '.join(mapping)


    def _parameters(self, device, vid, soprio_to_pcp):
        params = {}

        params['device'] = device
        params['id'] = vid
        params['soprio_to_pcp'] = self._soprio_to_pcp(soprio_to_pcp)

        return params


class CommandStringIpLinkUnset (collections.UserString):

    def __init__(self, device, vid):

        template = Template(inspect.cleandoc('''
            ip link delete $device.$id'''))


        params = self._parameters(device, vid)
        # We replace newlines for the template string to work when invoked
        data = template.substitute(params).replace('\n', '')

        super().__init__(data)



    def _parameters(self, device, vid):
        params = {}

        params['device'] = device
        params['id'] = vid

        return params



# tc command strings

class CommandStringTc (collections.UserString):

    def __init__(self, data):
        super().__init__(data)


    def _num_tc(self, soprio_to_tc):
        return len(set(soprio_to_tc))


    def _soprio_to_tc(self, soprio_to_tc):
        return ' '.join([str(tc) for tc in soprio_to_tc])


    def _tc_to_hwq(self, tc_to_hwq):
        mapping = []
        for m in tc_to_hwq:
            mapping.append("{0}@{1}".format(m["num_queues"], m["offset"]))

        return ' '.join(mapping)


    def _gatemask_to_hex(self, bitmask):

        low = int(bitmask, 2) & 0x0F
        high = int(bitmask, 2) >> 4

        return "{0:01X}{1:01X}".format(high, low)


    def _sched_entry(self, slot):
        assert slot["command"] == "SetGateStates"
        if slot["command"] == "SetGateStates":
            command = "S"
        gatemask = self._gatemask_to_hex(slot["gatemask"])
        interval = slot["interval"]

        return "         sched-entry {0} {1} {2}".format(command, gatemask, interval)


    def _sched_entries(self, schedule):
        entries = []
        for slot in schedule:
            entries.append(self._sched_entry(slot))

        return '\n'.join(entries)



class CommandStringTcTaprioOffloadSet(CommandStringTc):

    def __init__(self, interface, soprio_to_tc, tc_to_hwq, base_time, schedule):

        template = Template(inspect.cleandoc('''
           tc qdisc replace
                    dev       $interface
                    parent    root
                    taprio
                    num_tc    $num_tc
                    map       $soprio_to_tc
                    queues    $tc_to_hwq
                    base-time $base_time
           $sched_entries
                    flags     0x2'''))

        params = self._qdisc_parameters(interface, soprio_to_tc, tc_to_hwq, base_time, schedule)
        data = template.substitute(params).replace('\n', '')

        super().__init__(data)


    def _qdisc_parameters(self, interface, soprio_to_tc, tc_to_hwq, base_time, schedule):
        params = {}

        params['interface'] = interface
        params['num_tc'] = self._num_tc(soprio_to_tc)
        params['soprio_to_tc'] = self._soprio_to_tc(soprio_to_tc)
        params['tc_to_hwq'] = self._tc_to_hwq(tc_to_hwq)
        params['base_time'] = base_time
        params['sched_entries'] = self._sched_entries(schedule)

        return params


class CommandStringTcTaprioOffloadUnset(CommandStringTc):

    def __init__(self, interface):

        template = Template(inspect.cleandoc('''
           tc qdisc del
                    dev    $interface
                    root'''))

        params = {"interface": interface}
        data = template.substitute(params).replace('\n', '')

        super().__init__(data)


# ethtool command strings

class CommandStringEthtoolSetEee(collections.UserString):

    def __init__(self, interface, eee):

        self.check_args(interface, eee)

        template = Template(inspect.cleandoc('''
           ethtool --set-eee $interface
                             eee $eee'''))

        params = {"interface": interface, "eee": eee}
        data = template.substitute(params).replace('\n', '')

        super().__init__(data)


    def check_args(self, interface, eee):
        if eee not in ["on", "off"]:
            raise ValueError("Invalid value to configure EEE with Ethtool: {}".format(eee))




class CommandStringEthtoolFeatures(collections.UserString):

    def __init__(self, interface, features):

        self.check_args(interface, features)

        template = Template(inspect.cleandoc('''
           ethtool --features $interface $features'''))

        params = self._parameters(interface, features)
        data = template.substitute(params).replace('\n', '')

        super().__init__(data)


    def check_args(self, interface, eee):
        pass


    def _parameters(self, interface, features):
        parameters = {}
        parameters['interface'] = interface
        parameters['features'] = ""
        for feature, value in features.items():
            parameters['features'] += "{0} {1} ".format(feature, value)

        return parameters




class CommandStringEthtoolSetChannels(collections.UserString):

    def __init__(self, interface, num_tx_queues, num_rx_queues):

        template = Template(inspect.cleandoc('''
           ethtool --set-channels $interface
                   tx $num_tx_queues
                   rx $num_rx_queues'''))

        params = self._parameters(interface, num_tx_queues, num_rx_queues)
        data = template.substitute(params).replace('\n', '')

        super().__init__(data)



    def _parameters(self, interface, num_tx_queues, num_rx_queues):
        parameters = {}
        parameters['interface'] = interface
        parameters['num_tx_queues'] = num_tx_queues
        parameters['num_rx_queues'] = num_rx_queues

        return parameters




class CommandStringEthtoolSetRing(collections.UserString):

    """
    Set number of Tx and Rx ring buffers entries.

    Each entry holds an SKB descriptor.
    """

    def __init__(self, interface, num_tx_ring_entries, num_rx_ring_entries):


        template = Template(inspect.cleandoc('''
           ethtool --set-ring $interface
                   tx $num_tx_ring_entries
                   rx $num_rx_ring_entries'''))

        params = self._parameters(interface, num_tx_ring_entries, num_rx_ring_entries)
        data = template.substitute(params).replace('\n', '')

        super().__init__(data)



    def _parameters(self, interface, num_tx_ring_entries, num_rx_ring_entries):
        parameters = {}
        parameters['interface'] = interface
        parameters['num_tx_ring_entries'] = num_tx_ring_entries
        parameters['num_rx_ring_entries'] = num_rx_ring_entries

        return parameters




class QdiscConfigurator:

    def __init__(self):
        pass


    def run(self, command):
        # print(command)
        cmd = command.split()
        result = subprocess.run(cmd, capture_output=True, check=True)


    def setup(self, interface, mapping, scheduler):
        # FIXME: provide a mechanism to pass base-time
        base_time = self._calculate_base_time(scheduler.schedule.period)
        schedule = self._extract_schedule(scheduler)
        cmd = CommandStringTcTaprioOffloadSet(interface.name, mapping.soprio_to_tc, mapping.tc_to_hwq, base_time, schedule)
        self.run(str(cmd))


    def unset(self, interface):
        cmd = CommandStringTcTaprioOffloadUnset(interface.name)
        self.run(str(cmd))


    def _calculate_base_time(self, period):
        # XXX: evil trick to run on python3 < 3.9...
        # The hardcoded 11 (taken from /usr/include/linux/time.h) must be
        # replaced by time.CLOCK_TAI
        # now = time.clock_gettime_ns(time.CLOCK_TAI)
        CLOCK_TAI = 11
        now = time.clock_gettime_ns(CLOCK_TAI)
        ns_until_next_cycle = period - (now % period)
        # We add a safety margin of two cycles
        # FIXME: base time has to be provided by network planning
        safety_margin = 2 * period
        return (now + ns_until_next_cycle) + safety_margin


    def _extract_schedule(self, scheduler):
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




class VlanConfigurator:

    def __init__(self):
        pass


    def run(self, command):
        # print(command)
        cmd = command.split()
        result = subprocess.run(cmd, capture_output=True, check=True)


    def setup(self, interface, stream, mapping):
        cmd = CommandStringIpLinkSet(interface.name, stream.vid, mapping.soprio_to_pcp)
        self.run(str(cmd))


    def unset(self, interface, stream):
        cmd = CommandStringIpLinkUnset(interface.name, stream.vid)
        self.run(str(cmd))




class DeviceConfigurator:

    def __init__(self):
        pass


    def run(self, command):
        # print(command)
        cmd = command.split()
        result = subprocess.run(cmd, capture_output=True)

        # ethtool returns 80 when the configuration does not change
        # so we need to handle this case manually because check=True
        # will just interpret any return code different than 0 as error
        success_codes = [0, 80]
        if result.returncode not in [0, 80]:
            raise subprocess.CalledProcessError(result.returncode, command, stdout=result.stdout, stderr=result.stderr)


    def setup(self, interface, eee="off"):

        cmd = CommandStringEthtoolSetEee(interface.name, eee)
        self.run(str(cmd))

        cmd = CommandStringEthtoolFeatures(interface.name, interface.device.features)
        self.run(str(cmd))

        cmd = CommandStringEthtoolSetChannels(interface.name, interface.device.num_tx_queues, interface.device.num_rx_queues)
        self.run(str(cmd))

        cmd = CommandStringEthtoolSetRing(interface.name, interface.device.num_rx_ring_entries, interface.device.num_rx_ring_entries)
        self.run(str(cmd))




class SystemConfigurator:

    """
    SystemConfigurator

    Translates between domain classes and specific implementations
    """

    def __init__(self):
        self.qdisc = QdiscConfigurator()
        self.vlan = VlanConfigurator()
        self.device = DeviceConfigurator()


    def args_valid(self, interface, mapping, scheduler, stream):

        if not Check.is_interface(interface.name):
            return False

        if interface.device is None:
            return False


        soprio_to_tc = mapping.soprio_to_tc
        if soprio_to_tc is None:
            return False
        for tc in soprio_to_tc:
            if not Check.is_natural(tc):
                return False

        tc_to_hwq = mapping.tc_to_hwq
        if tc_to_hwq is None:
            return False
        for item in tc_to_hwq:
            if not Check.is_natural(item['offset']):
                return False
            if not Check.is_natural(item['num_queues']):
                return False

        soprio_to_pcp = mapping.soprio_to_pcp
        if soprio_to_pcp is None:
            return False
        for pcp in soprio_to_pcp:
            if not Check.is_natural(pcp):
                return False

        if scheduler is None:
            return False

        if stream is None:
            return False
        if not Check.is_natural(stream.vid):
            return False


        return True


    def setup(self, interface, mapping, scheduler, stream):

        if not self.args_valid(interface, mapping, scheduler, stream):
            raise TypeError

        # FIXME: consider other exceptions, e.g. TypeError
        try:
            # FIXME add qdisc reset
            self.qdisc.setup(interface, mapping, scheduler)
        except subprocess.CalledProcessError:
            raise

        try:
            self.vlan.setup(interface, stream, mapping)
        except subprocess.CalledProcessError:
            self.qdisc.unset(interface)
            raise

        try:
            self.device.setup(interface, eee="off")
        except subprocess.CalledProcessError:
            self.qdisc.unset(interface)
            self.vlan.unset(interface, stream)
            raise
