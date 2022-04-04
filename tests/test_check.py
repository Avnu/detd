#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

import unittest
from unittest.mock import patch
from unittest import mock

from detd import StreamConfiguration
from detd import TrafficSpecification
from detd import Interface
from detd import Configuration
from detd import SystemConfigurator

import os

from .common import *


from detd import Check


class TestChecker(unittest.TestCase):


    def setUp(self):
        env_var = os.getenv("DETD_TESTENV")
        if env_var == "HOST":
            self.mode = TestMode.HOST
        elif env_var == "TARGET":
            self.mode = TestMode.TARGET
        else:
            self.mode = TestMode.HOST



    def test_is_interface_loopback(self):

        interface_name = "lo"

        self.assertEqual(Check.is_interface(interface_name), True)


    def test_is_interface_numbers(self):

        interface_name = "9999"

        self.assertEqual(Check.is_interface(interface_name), False)


    def test_is_mac_address_unicast(self):

        addr = "AB:12:AB:23:34:54"

        self.assertEqual(Check.is_mac_address(addr), True)


    def test_is_mac_address_too_long(self):

        addr = "AB:12:AB:23:34:54:54"

        self.assertEqual(Check.is_mac_address(addr), False)


    def test_is_vlan_id_3(self):

        vid = 3

        self.assertEqual(Check.is_valid_vlan_id(vid), True)


    def test_is_vlan_id_invalid(self):

        invalid = [0, 4095]

        for vid in invalid:
            self.assertEqual(Check.is_valid_vlan_id(vid), False)


    def test_is_pcp_6(self):

        pcp = 6

        self.assertEqual(Check.is_valid_pcp(pcp), True)


    def test_is_pcp_invalid(self):

        invalid = [-1, 8]

        for pcp in invalid:
            self.assertEqual(Check.is_valid_pcp(pcp), False)

    def test_is_not_symlink(self):

        dst = "/tmp/notsorandomfilename"
        os.symlink("/dev/null", dst)

        self.assertEqual(Check.is_valid_file(dst), False)

        os.unlink(dst)



if __name__ == '__main__':
    unittest.main()
