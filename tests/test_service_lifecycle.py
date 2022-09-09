#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

import multiprocessing
import os
import socket
import sys
import tempfile
import time
import unittest
import unittest.mock


from detd import Service
from detd.service import _SERVICE_UNIX_DOMAIN_SOCKET


from .common import *



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



class TestServiceStartup(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        env_var = os.getenv("DETD_TESTENV")
        if env_var == "HOST":
            cls.mode = TestMode.HOST
        elif env_var == "TARGET":
            cls.mode = TestMode.TARGET
        else:
            cls.mode = TestMode.HOST

        # In order to test for security vulnerabilities, we need to implement
        # somehow "hackish" solutions to test for the given scenarios.
        # E.g. that an attacker replaces files used by the application by
        # symlinks
        # We check the security of the Service by emulating those attacks by
        # simply replacing the internal service variables to point to the
        # desired "anomalous" entity, like e.g. symlinks, relative paths, etc
        # Hence, we need to store the legit value in the setUpClass method, so
        # it is available for use between method invocations. Otherwise, that
        # value would be lost after the first overwrite in a method call.
        cls.internal_lock_file = Service._SERVICE_LOCK_FILE


    @classmethod
    def tearDownClass(cls):
        try:
            uds_address = _SERVICE_UNIX_DOMAIN_SOCKET
            os.unlink(uds_address)
        except FileNotFoundError:
            pass


    def test_service_lifecycle_init_lock_path_is_none(self):

        Service._SERVICE_LOCK_FILE = None

        with self.assertRaises(TypeError):
            log_filename = './detd-server-unittest.log'
            srv = Service(log_filename=log_filename)


    def test_service_lifecycle_init_lock_path_is_relative(self):

        with tempfile.NamedTemporaryFile() as src:
            dst = "./{}".format(src.name)
            Service._SERVICE_LOCK_FILE = dst

            with self.assertRaises(TypeError):
                log_filename = './detd-server-unittest.log'
                srv = Service(log_filename=log_filename)

            # Constructor raised an exception, hence no need to clean-up


    @unittest.skip("A solution to communicate multiprocessor server errors to the unittest client is required for assertRaises to catch the remote exception")
    def test_service_lifecycle_terminate_lock_path_is_symlink(self):

        Service._SERVICE_LOCK_FILE = self.internal_lock_file

        log_filename = './detd-server-unittest.log'
        server = setup_server(self.mode, log_filename)

        lock_file = Service._SERVICE_LOCK_FILE
        os.unlink(lock_file)
        os.symlink("/dev/null", lock_file)
        with self.assertRaises(TypeError):
            server.terminate()
        server.join()


    @unittest.skip("A solution to communicate multiprocessor server errors to the unittest client is required for assertRaises to catch the remote exception")
    def test_service_lifecycle_terminate_unix_domain_socket_is_symlink(self):

        Service._SERVICE_LOCK_FILE = self.internal_lock_file

        log_filename = './detd-server-unittest.log'
        server = setup_server(self.mode, log_filename)

        from detd import service
        uds_address = service._SERVICE_UNIX_DOMAIN_SOCKET
        os.unlink(uds_address)
        with self.assertRaises(TypeError):
            server.terminate()
        server.join()



if __name__ == '__main__':

    unittest.main()
