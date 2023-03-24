#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

import multiprocessing
import os
import socket
import sys
import time
import unittest
import unittest.mock

from pathlib import Path

from detd import *

from .common import *

from detd import setup_root_logger
from detd import get_logger





# We rely on systemd to create the directory during normal operation
# but the test suite does not run with enough privileges to create
# the directory /var/run/detd
# Hence we change the location of the UDS to /var/tmp/detd/ and handle
# its creation and removal in the tearUp and tearDown functions
UNIX_DOMAIN_SOCKET = "/var/tmp/detd/detd_service.sock"
service._SERVICE_UNIX_DOMAIN_SOCKET = UNIX_DOMAIN_SOCKET
proxy._SERVICE_UNIX_DOMAIN_SOCKET   = UNIX_DOMAIN_SOCKET


def setup_configuration(mode):

    interface_name = "eth1"
    interval = 20 * 1000 * 1000 # ns
    size = 1522                 # Bytes

    txoffset = 250 * 1000       # ns
    addr = "03:C0:FF:EE:FF:AB"
    vid = 3
    pcp = 6

    with RunContext(mode):
        interface = Interface(interface_name)
        stream = StreamConfiguration(addr, vid, pcp, txoffset)
        traffic = TrafficSpecification(interval, size)

        config = Configuration(interface, stream, traffic)

    return config


def setup_proxy():

    proxy = ServiceProxy()

    return proxy


def run_server(test_mode, log_filename):

    if test_mode == TestMode.TARGET:
        with Service(log_filename=log_filename) as srv:
            srv.run()
    elif test_mode == TestMode.HOST:
        with Service(test_mode=True, log_filename=log_filename) as srv:
            srv.run()


def setup_server(test_mode, log_filename):
    uds_address = service._SERVICE_UNIX_DOMAIN_SOCKET
    # We rely on systemd to create the directory during normal operation
    # so we need to create it manually for the test suite to run
    parent = Path(uds_address).parent
    parent.mkdir()
    server = multiprocessing.Process(target=run_server, args=(test_mode,log_filename,))
    server.start()
    while not os.path.exists(uds_address):
        time.sleep(0.2)

    return server

def mock_setup(self, message):
    vlan_interface = "{}.{}".format(message.interface, message.vid)
    soprio = 6
    return vlan_interface, soprio



class TestService(unittest.TestCase):

    def setUp(self):

        setup_root_logger('./detd-server-unittest.log')

        env_var = os.getenv("DETD_TESTENV")
        if env_var == "HOST":
            self.mode = TestMode.HOST
        elif env_var == "TARGET":
            self.mode = TestMode.TARGET
        else:
            self.mode = TestMode.HOST

        log_filename = './detd-server-unittest.log'
        self.server = setup_server(self.mode, log_filename)
        self.proxy = setup_proxy()


    def tearDown(self):
        self.server.terminate()
        self.server.join()
        try:
            uds_address = service._SERVICE_UNIX_DOMAIN_SOCKET
            os.unlink(uds_address)
        except FileNotFoundError:
            pass
        # We rely on systemd to remove the directory during normal operation
        # so we need to remove it manually to leave the system as we found it
        parent = Path(uds_address).parent
        parent.rmdir()


    def assertSoprioEqual(self, sock, soprio):
        actual = sock.getsockopt(socket.SOL_SOCKET, socket.SO_PRIORITY)
        self.assertEqual(actual, soprio)


    def test_service_add_talker_socket(self):

        configuration = setup_configuration(self.mode)

        sock = self.proxy.add_talker_socket(configuration)

        # XXX currently this is just testing that the socket priority
        # configured by the server is correctly propagated with SCM_RIGHTS
        self.assertSoprioEqual(sock, 6)

        sock.close()


    def test_service_add_talker(self):

        configuration = setup_configuration(self.mode)

        vlan_interface, soprio, txoffsetmin, txoffsetmax = self.proxy.add_talker(configuration)

        self.assertEqual(vlan_interface, "eth1.3")
        self.assertEqual(soprio, 7)
        self.assertEqual(txoffsetmin, configuration.stream.txoffset-configuration.interface.device.hardware_delay_max)
        self.assertEqual(txoffsetmax, configuration.stream.txoffset-configuration.interface.device.hardware_delay_min)




if __name__ == '__main__':

    unittest.main()
