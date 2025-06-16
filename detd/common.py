#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

""" Module common

Entities used by more than a single module that cannot be fit cleanly into the
current import structure.

When possible, the entities in this file should be moved to more meaningful
modules.
"""




import collections
import enum
import inspect
import os
import re
import socket
import stat

from string import Template




Gbps_to_bps = 1000 * 1000 * 1000
Mbps_to_bps = 1000 * 1000




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



class CommandString(collections.UserString):

    def __init__(self, template, params):

        template = Template(inspect.cleandoc(template))
        data = template.substitute(params).replace('\n', '')

        super().__init__(data)




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
