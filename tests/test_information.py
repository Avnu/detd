#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

import unittest
import subprocess
from unittest.mock import patch
from unittest import mock
from unittest.mock import mock_open
from subprocess import CalledProcessError

from detd import Interface
from detd import SystemInformation

import os

from .common import *


class TestSystemInformation(unittest.TestCase):


    def setUp(self):

        env_var = os.getenv("DETD_TESTENV")
        if env_var == "HOST":
            self.mode = TestMode.HOST
        elif env_var == "TARGET":
            self.mode = TestMode.TARGET
        else:
            self.mode = TestMode.HOST


    def test_getpciid_success(self):

        sysinfo = SystemInformation()

        interface = "eth0"

        uevent = """
DRIVER=stmmaceth
PCI_CLASS=20018
PCI_ID=8086:4BA0
PCI_SUBSYS_ID=8086:7270
PCI_SLOT_NAME=0000:00:1d.1
MODALIAS=pci:v00008086d00004BA0sv00008086sd00007270bc02sc00i18"""

        mocked_open = mock.mock_open(read_data=uevent)
        with mock.patch('builtins.open', mocked_open):
            pci_id = sysinfo.get_pci_id(interface)
            self.assertEqual(pci_id, "8086:4BA0")


    def test_getpciid_parse_error(self):

        sysinfo = SystemInformation()

        interface = "eth0"

        uevent = """
DRIVER=stmmaceth
PCI_CLASS=20018
PCI_SUBSYS_ID=8086:7270
PCI_SLOT_NAME=0000:00:1d.1
MODALIAS=pci:v00008086d00004BA0sv00008086sd00007270bc02sc00i18"""

        mocked_open = mock.mock_open(read_data=uevent)
        with mock.patch('builtins.open', mocked_open):
            self.assertRaises(RuntimeError, sysinfo.get_pci_id, interface)


if __name__ == '__main__':
    unittest.main()
