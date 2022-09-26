#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

""" Module intel_i210

"""




from ..logger import get_logger

from .device import Device


logger = get_logger(__name__)




class IntelI210(Device):

    PCI_IDS_VALID = ['8086:1533', '8086:1536', '8086:1537', '8086:1538', '8086:157B',
                     '8086:157C', '8086:15F6']

    # Hardware default. Empty Flash Image (or NVM configuration loading failed)
    PCI_IDS_UNPROGRAMMED = ['8086:1531']

    PCI_IDS = PCI_IDS_VALID + PCI_IDS_UNPROGRAMMED

    def __init__(self, pci_id):

        logger.info(f"Initializing {__class__.__name__}")

        raise NotImplementedError("Handler class for i210 Ethernet controller not yet implemented")
