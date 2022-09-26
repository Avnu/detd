#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

""" Module intel_mgbetgl

"""




from ..logger import get_logger

from .device import Device


logger = get_logger(__name__)




class IntelMgbeTgl(Device):

    PCI_IDS = ['8086:A0AC']

    def __init__(self, pci_id):

        logger.info(f"Initializing {__class__.__name__}")

        raise NotImplementedError("Handler class for Tiger Lake UP3's integrated TSN controller not yet implemented")
