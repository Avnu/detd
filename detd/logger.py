#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

""" Module logger

Allows for centralized logging for all modules.

The program entry point must set up the root logger by using the function
setup_root_logger.

Then, every module requiring logging should call get_logger(__name__), and then
use the regular Python3 logging API on it.
"""




import logging

def setup_root_logger(filename=None):

    # Setup root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    if filename == None:
        handler = logging.StreamHandler()
    else:
        handler = logging.FileHandler(filename)

    formatter = logging.Formatter('[{asctime} - {levelname:>8}] {name:>15} {funcName:>20}() - {message}', style='{')
    handler.setFormatter(formatter)
    logger.addHandler(handler)




def get_logger(name):
    return logging.getLogger(name)
