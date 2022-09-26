#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

""" Module intel_i226

"""




from ..logger import get_logger

from .device import Device


logger = get_logger(__name__)




class IntelI226(Device):

    # Devices supporting TSN: i226-LM, i226-IT
    PCI_IDS_VALID = ['8086:125B', '8086:125D']

    # Hardware default. Empty Flash Image (or NVM configuration loading failed)
    PCI_IDS_UNPROGRAMMED = ['8086:125F']

    PCI_IDS = PCI_IDS_VALID + PCI_IDS_UNPROGRAMMED

    def __init__(self, pci_id):

        logger.info(f"Initializing {__class__.__name__}")

        raise NotImplementedError("Handler class for i226 TSN Ethernet controller not yet implemented")
