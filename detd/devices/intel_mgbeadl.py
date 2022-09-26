#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

""" Module intel_mgbeadl

"""




from ..logger import get_logger

from .device import Device


logger = get_logger(__name__)




class IntelMgbeAdl(Device):

    PCI_IDS = ['8086:7AAC', '8086:7AAD', '8086:54AC']

    def __init__(self, pci_id):

        logger.info(f"Initializing {__class__.__name__}")

        raise NotImplementedError("Handler class for Alder Lake's integrated TSN controller not yet implemented")
