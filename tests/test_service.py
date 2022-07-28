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


from detd import Configuration
from detd import Interface
from detd import Service
from detd import ServiceProxy
from detd import StreamConfiguration
from detd import TrafficSpecification


from .common import *



def setup_configuration(mode):

    interface_name = "eth0"
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


def run_server(test_mode):
    if test_mode == TestMode.TARGET:
        with Service() as srv:
            srv.run()
    elif test_mode == TestMode.HOST:
        with Service(test_mode=True) as srv:
            srv.run()


def setup_server(test_mode):
    uds_address = Service._SERVICE_LOCK_FILE
    server = multiprocessing.Process(target=run_server, args=(test_mode,))
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

        env_var = os.getenv("DETD_TESTENV")
        if env_var == "HOST":
            self.mode = TestMode.HOST
        elif env_var == "TARGET":
            self.mode = TestMode.TARGET
        else:
            self.mode = TestMode.HOST

        self.server = setup_server(self.mode)
        self.proxy = setup_proxy()


    def tearDown(self):
        self.server.terminate()
        self.server.join()
        try:
            uds_address = '/tmp/uds_detd_server.sock'
            os.unlink(uds_address)
        except FileNotFoundError:
            pass

    def assertSoprioEqual(self, sock, soprio):
        actual = sock.getsockopt(socket.SOL_SOCKET, socket.SO_PRIORITY)
        self.assertEqual(actual, soprio)


    def test_service_setup_talker_socket(self):

        configuration = setup_configuration(self.mode)

        sock = self.proxy.setup_talker_socket(configuration)

        # XXX currently this is just testing that the socket priority
        # configured by the server is correctly propagated with SCM_RIGHTS
        self.assertSoprioEqual(sock, 6)

        sock.close()


    def test_service_setup_talker(self):

        configuration = setup_configuration(self.mode)

        vlan_interface, soprio = self.proxy.setup_talker(configuration)

        self.assertEqual(vlan_interface, "eth0.3")
        self.assertEqual(soprio, 7)




if __name__ == '__main__':

    unittest.main()
