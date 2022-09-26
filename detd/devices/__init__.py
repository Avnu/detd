#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

""" Package devices

This package contains the classes to handle networking devices.

An abstract Device class is defined in the device module. Each concrete device
should have its own class derived from that, implemented in its own module.

The function from_pci_id, exported by the device module, selects the specific
concrete class by matching the pci_ids enumerated by each.

The implementation of the class for each device should be kept as platform
independent as possible.

The number of dependencies on other modules should also be kept as reduced as
possible.

A commented example about how to support a new device is contained in module
intel_mgbeehl

To include your new device in the host testing environment, some changes are
required. You may need to modify RunContext locally to reference the specific
PCI ID, add support for a DETD_PCI_ID environment variable, or extend the
mocking infrastructure to iterate through all the available classes when
running host based tests.
"""




from importlib import import_module
from pathlib import Path




# Import all the modules in the devices directory
parent = Path(__file__).parent
sources = parent.rglob('*.py')
module_names = [f'.{source.stem}' for source in sources if source.stem != '__init__']

for module_name in module_names:
    import_module(module_name, __package__)

del parent, sources, module_names
del import_module, Path
