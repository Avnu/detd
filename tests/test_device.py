#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

import unittest
from unittest.mock import patch
from unittest import mock

import os

from .common import *


from detd import Device


class TestDevice(unittest.TestCase):


    def setUp(self):
        env_var = os.getenv("DETD_TESTENV")
        if env_var == "HOST":
            self.mode = TestMode.HOST
        elif env_var == "TARGET":
            self.mode = TestMode.TARGET
        else:
            self.mode = TestMode.HOST


    def test_from_pci_id(self):

        for pci_id in [ '8086:4B30', '8086:4B31', '8086:4B32' ]:
            device = Device.from_pci_id(pci_id)



if __name__ == '__main__':
    unittest.main()
