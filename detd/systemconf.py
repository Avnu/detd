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
import sys
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



class SystemInformation:

    """ Provides read-only information about the system"""


    def __init__(self):
        pass


    def get_pci_dbdf(self, interface):
        ethtool = CommandEthtool()
        output = ethtool.get_driver_information(interface)
        # E.g.:
        # bus-info: 0000:00:1d.1
        regex = re.compile("^bus-info: ([0-9a-fA-F]{4}):([0-9a-fA-F]{2}):([0-9a-fA-F]{2}).([0-9a-fA-F])$")
        for line in output:
            m = regex.match(line)
            if m:
                domain = m.groups()[0]
                bus = m.groups()[1]
                device = m.groups()[2]
                function = m.groups()[3]
                return domain, bus, device, function

        raise RuntimeError("ethtool output does not include correct bus-info".format(interface))



    def get_hex(self, filename):

        # E.g.:
        # 0x8086
        regex = re.compile("0x([0-9a-fA-F]{4})")

        with open(filename, 'r') as f:
            line = f.read()
            m = regex.match(line)
            if m:
                vendor = m.groups()[0]
            else:
                raise RuntimeError("Corrupted PCI entry for {}".format(interface))

        return vendor.upper()


    def get_pci_id(self, interface):
        """
        Returns the PCI ID string for a give network interface

        The PCI ID string returned contains vendor and product ids in uppercase,
        separated by a semicolon. E.g. "8086:4BA0"

        Raises a RuntimeError if it is not able to find which PCI ID is
        associated to the interface.
        """

        domain, bus, device, function = self.get_pci_dbdf(interface)
        base = "/sys/bus/pci/devices/{}:{}:{}.{}".format(domain, bus, device, function)

        filename = "{}/vendor".format(base)
        vendor = self.get_hex(filename)

        filename = "{}/device".format(base)
        product = self.get_hex(filename)

        return "{}:{}".format(vendor, product)




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

class CommandStringIpLinkSetVlan (collections.UserString):

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


class CommandStringIpLinkUnsetVlan (collections.UserString):

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




class CommandStringEthtoolSetSplitChannels(collections.UserString):

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




class CommandStringEthtoolSetCombinedChannels(collections.UserString):

    def __init__(self, interface, num_queues):

        template = Template(inspect.cleandoc('''
           ethtool --set-channels $interface
                   combined $num_queues'''))

        params = self._parameters(interface, num_queues)
        data = template.substitute(params).replace('\n', '')

        super().__init__(data)



    def _parameters(self, interface, num_queues):
        parameters = {}
        parameters['interface'] = interface
        parameters['num_queues'] = num_queues

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




class CommandStringEthtoolGetDriverInformation(collections.UserString):

    def __init__(self, interface):

        self.check_args(interface)

        template = Template(inspect.cleandoc('''
           ethtool --driver $interface'''))

        params = self._parameters(interface)
        data = template.substitute(params).replace('\n', '')

        super().__init__(data)


    def check_args(self, interface):
        pass


    def _parameters(self, interface):
        parameters = {}
        parameters['interface'] = interface

        return parameters


class CommandStringEthtoolGetChannelInformation(collections.UserString):

    def __init__(self, interface):

        self.check_args(interface)

        template = Template(inspect.cleandoc('''
           ethtool --show-channels $interface'''))

        params = self._parameters(interface)
        data = template.substitute(params).replace('\n', '')

        super().__init__(data)


    def check_args(self, interface):
        pass


    def _parameters(self, interface):
        parameters = {}
        parameters['interface'] = interface

        return parameters




class CommandIp:

    def __init__(self):
        pass


    def run(self, command):
        cmd = command.split()
        result = subprocess.run(cmd, capture_output=True, text=True)

        success_codes = [0]
        if result.returncode not in success_codes:
            raise subprocess.CalledProcessError(result.returncode, command, result.stdout, result.stderr)

        return result


    def set_vlan(self, interface, stream, mapping):
        cmd = CommandStringIpLinkSetVlan(interface.name, stream.vid, mapping.soprio_to_pcp)

        self.run(str(cmd))


    def unset_vlan(self, interface, stream):
        cmd = CommandStringIpLinkUnsetVlan(interface.name, stream.vid)

        self.run(str(cmd))



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

        schedule = self._extract_schedule(scheduler)
        cmd = CommandStringTcTaprioOffloadSet(interface.name, mapping.soprio_to_tc, mapping.tc_to_hwq, base_time, schedule)

        self.run(cmd)


    def unset_taprio_offload(self, interface):

        cmd = CommandStringTcTaprioOffloadUnset(interface.name)

        self.run(str(cmd))


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




class CommandEthtool:

    def __init__(self):
        pass

    def run(self, command):
        cmd = command.split()
        result = subprocess.run(cmd, capture_output=True, text=True)

        # ethtool returns 80 when the configuration does not change
        # so we need to handle this case manually because check=True
        # will just interpret any return code different than 0 as error
        success_codes = [0, 80]
        if result.returncode not in [0, 80]:
            raise subprocess.CalledProcessError(result.returncode, command, result.stdout, result.stderr)

        return result


    def get_driver_information(self, interface):
        cmd = CommandStringEthtoolGetDriverInformation(interface)

        result = self.run(cmd)

        return result.stdout.splitlines()


    def set_eee(self, interface, eee):
        cmd = CommandStringEthtoolSetEee(interface, eee)

        self.run(cmd)


    def set_ring(self, interface, num_tx_ring_entries, num_rx_ring_entries):
        cmd = CommandStringEthtoolSetRing(interface, num_tx_ring_entries, num_rx_ring_entries)

        self.run(cmd)


    def set_split_channels(self, interface, num_tx_queues, num_rx_queues):
        cmd = CommandStringEthtoolSetSplitChannels(interface, num_tx_queues, num_rx_queues)

        self.run(cmd)


    def set_combined_channels(self, interface, num_queues):
        cmd = CommandStringEthtoolSetCombinedChannels(interface, num_queues)

        self.run(cmd)


    def set_features(self, interface, features):
        cmd = CommandStringEthtoolFeatures(interface, features)

        self.run(cmd)





class QdiscConfigurator:

    def __init__(self):
        pass


    def setup(self, interface, mapping, scheduler, base_time):
        tc = CommandTc()

        tc.set_taprio_offload(interface, mapping, scheduler, base_time)

    def unset(self, interface):
        tc = CommandTc()

        tc.unset_taprio_offload(interface)



class VlanConfigurator:

    def __init__(self):
        pass


    def setup(self, interface, stream, mapping):
        ip = CommandIp()

        ip.set_vlan(interface, stream, mapping)


    def unset(self, interface, stream):
        ip = CommandIp()

        ip.unset_vlan(interface, stream)




class DeviceConfigurator:

    def __init__(self):
        pass


    def setup(self, interface, eee="off"):

        ethtool = CommandEthtool()

        ethtool.set_eee(interface.name, eee)
        ethtool.set_features(interface.name, interface.device.features)
        if interface.device.supports_split_channels:
            ethtool.set_split_channels(interface.name, interface.device.num_tx_queues, interface.device.num_rx_queues)
        else:
            ethtool.set_combined_channels(interface.name, interface.device.num_tx_queues)
        ethtool.set_ring(interface.name, interface.device.num_tx_ring_entries, interface.device.num_rx_ring_entries)




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

        try:
            self.device.setup(interface, eee="off")
        except subprocess.CalledProcessError:
            # FIXME add device restore
            raise

        # FIXME: consider other exceptions, e.g. TypeError
        try:
            # FIXME add qdisc reset
            self.qdisc.setup(interface, mapping, scheduler, stream.base_time)
        except subprocess.CalledProcessError:
            raise

        try:
            self.vlan.setup(interface, stream, mapping)
        except subprocess.CalledProcessError:
            self.qdisc.unset(interface)
            raise


