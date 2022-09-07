#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

"""

Module systemconf

This module contains a high level interface to access system level information
and perform system configuration operations.

It should remain as independent as possible from implementation-specific
detials. E.g. it should not deal directly with OS-specific commands.

It offers two interfaces, via the classes:
    * SystemConfigurator
    * SystemInformation

Internally, SystemConfigurator relies on concern-specific classes, like:
    * VlanConfigurator
    * DeviceConfigurator
    * QdiscConfigurator

Currently, only the Linux operating system is supported. However, this
architecture is intended to make it easier to support further operating systems
or variants. E.g. VlanConfigurator may become an interface and have concrete
implementations like VlanConfiguratorLinux.

The concern-specific classes then call OS-specific commands. Each of these
commands has their own module. E.g. ethtool in ethtool.py, tc in tc.py...
A more robust approach, e.g. using netlink on Linux, could also be integrated.
It just must be implemented first :)

The command modules define a set of command strings, that instantiate a set of
parameters in a template that results in the command to execute.

On top of them, a class for each command offer the externally available
features. E.g. Ethtool.set_vlan()

Input validation for system configuration is performed in two steps:
    * SystemConfigurator checks the consistency at the domain level
    * The interface for each command module (e.g. Ethtool class) should
      perform the translation from domain level to command-specific
      representations.
"""




import re
import subprocess

from .ip import CommandIp
from .ethtool import CommandEthtool
from .tc import CommandTc

from .common import Check




class SystemConfigurator:

    """
    SystemConfigurator

    Translates between domain classes and specific implementations
    """

    def __init__(self):
        self.qdisc = QdiscConfigurator()
        self.vlan = VlanConfigurator()
        self.device = DeviceConfigurator()

        # We track the VLAN ids configured. So when streams share the same VID,
        # we do not configure it again.
        self.already_configured_vids = []


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

        if stream.vid in self.already_configured_vids:
            return

        try:
            self.vlan.setup(interface, stream, mapping)
            self.already_configured_vids.append(stream.vid)
        except subprocess.CalledProcessError:
            self.qdisc.unset(interface)
            raise




class DeviceConfigurator:

    def __init__(self):
        pass


    def setup(self, interface, eee="off"):

        sysinfo = SystemInformation()

        ethtool = CommandEthtool()

        ethtool.set_eee(interface, eee)
        ethtool.set_features(interface)

        if sysinfo.interface_supports_split_channels(interface):
            ethtool.set_split_channels(interface)
        else:
            ethtool.set_combined_channels(interface)

        ethtool.set_rings(interface)







class VlanConfigurator:

    def __init__(self):
        pass


    def setup(self, interface, stream, mapping):
        ip = CommandIp()

        ip.set_vlan(interface, stream, mapping)


    def unset(self, interface, stream):
        ip = CommandIp()

        ip.unset_vlan(interface, stream)




class QdiscConfigurator:

    def __init__(self):
        pass


    def setup(self, interface, mapping, scheduler, base_time):
        tc = CommandTc()

        tc.set_taprio_offload(interface, mapping, scheduler, base_time)

    def unset(self, interface):
        tc = CommandTc()

        tc.unset_taprio_offload(interface)




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

        raise RuntimeError("ethtool output does not include correct bus-info information for {}".format(interface.name))



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
                raise RuntimeError("Corrupted PCI entry at {}".format(filename))

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


    def get_channels_information(self, interface):

        ethtool = CommandEthtool()
        output = ethtool.get_channels_information(interface)

        template = """Channel parameters for {}:
Pre-set maximums:
RX:[ \t]+([0-9]+|n/a)
TX:[ \t]+([0-9]+|n/a)
Other:[ \t]+([0-9]+|n/a)
Combined:[ \t]+([0-9]+|n/a)
Current hardware settings:
RX:[ \t]+([0-9]+|n/a)
TX:[ \t]+([0-9]+|n/a)
Other:[ \t]+([0-9]+|n/a)
Combined:[ \t]+([0-9]+|n/a)""".format(interface.name)

        regex = re.compile(template)
        m = regex.match("\n".join(output))
        if m:
            max_rx = m.groups()[0]
            if max_rx == 'n/a':
                max_rx = 0
            max_tx = m.groups()[1]
            if max_tx == 'n/a':
                max_tx = 0
            #max_other = m.groups()[2]
            #max_combined = m.groups()[3]
            return max_rx, max_tx

        raise RuntimeError("ethtool output does not include correct channels information for {}:\n{}".format(interface.name, "\n".join(output)))


    def interface_supports_split_channels(self, interface):

        max_rx, max_tx = self.get_channels_information(interface)

        if max_rx == 0 or max_tx == 0:
            return False

        return True
