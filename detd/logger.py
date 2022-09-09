#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

""" Module logger

Allows for centralized logging for all modules.

The program entry point must set up the root logger by using the function
setupRootLogger.

Then, every module requiring logging should call getLogger(__name__), and then use the
regular Python3 logging API on it.
"""




import logging

def setupRootLogger(filename=None):

    # Setup root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    if filename == None:
        handler = logging.StreamHandler()
    else:
        handler = logging.FileHandler(filename)

    formatter = logging.Formatter('[%(asctime)s - %(levelname)8s] %(name)15s %(funcName)20s() - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)




def getLogger(name):
    return logging.getLogger(name)
