#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

""" Module service

This module implements the server side for the system service dealing with the
application requests to guarantee deterministic QoS.

   * class Service
   * class ServiceRequestHandler

Client and server side exchange messages using the protocol defined in the
file ipc.proto
"""




import array
import os
import signal
import socket
import socketserver
import stat
import threading

from pathlib import Path
from unittest import mock

from .ipc_pb2 import StreamQosRequest
from .ipc_pb2 import StreamQosResponse


from .manager import Interface
from .manager import Manager

from .scheduler import Configuration
from .scheduler import StreamConfiguration
from .scheduler import TrafficSpecification
from .scheduler import Hints

from .systemconf import Check
from .systemconf import QdiscConfigurator
from .systemconf import DeviceConfigurator
from .systemconf import SystemInformation
from .systemconf import CommandIp
from .sysctl import CommandSysctl

from .logger import setup_root_logger
from .logger import get_logger


_SERVICE_UNIX_DOMAIN_SOCKET='/var/run/detd/detd_service.sock'


logger = get_logger(__name__)




class Service(socketserver.UnixDatagramServer):

    _SERVICE_LOCK_FILE='/var/lock/detd'

    def __init__(self, test_mode=False, log_filename=None):

        setup_root_logger(log_filename)

        logger.info(" * * * detd Service starting * * *")
        logger.info("Initializing Service")

        # We create the lock file even before calling parent's constructor
        self.setup_lock_file()

        try:
            self.setup_unix_domain_socket()

            # Create directory for the socket file
            try:
               os.makedirs(os.path.dirname(_SERVICE_UNIX_DOMAIN_SOCKET))
            except FileExistsError:
               # directory already exists
               pass

            super().__init__(_SERVICE_UNIX_DOMAIN_SOCKET, ServiceRequestHandler)

            self.test_mode = test_mode

            self.manager = Manager()

            signal.signal(signal.SIGINT, self.terminate)
            signal.signal(signal.SIGTERM, self.terminate)
        except Exception as ex:
            self.cleanup_lock_file()
            logger.exception("Exception while initializing service")
            raise


    def setup_lock_file(self):

        if not Check.is_valid_path(Service._SERVICE_LOCK_FILE):
            logger.error(f"{Service._SERVICE_LOCK_FILE} is not a valid path")
            raise TypeError

        with open(Service._SERVICE_LOCK_FILE, "x") as lock_file:
            pid = os.getpid()
            lock_file.write(str(pid))

        os.chmod(Service._SERVICE_LOCK_FILE, stat.S_IRUSR)


    def setup_unix_domain_socket(self):

        basedir = Path(_SERVICE_UNIX_DOMAIN_SOCKET).parent.parent
        if not Check.is_valid_path(basedir):
            logger.error(f"{basedir} is not a valid path")
            raise TypeError


    def terminate(self, signum, frame):

        logger.info("Terminating Service")

        threading.Thread(target=self.shutdown, daemon=True).start()


    def run(self):

        logger.info("Entering Service main loop")

        try:
            self.serve_forever()
        except Exception as ex:
            logger.exception("Exception while in Server main loop")
            raise
        finally:
            self.server_close()
            self.cleanup()


    def cleanup(self):

        logger.info("Cleaning up Service")

        # Clean-up UNIX domain socket
        if not Check.is_valid_unix_domain_socket(self.server_address):
            logger.error(f"{self.server_address} is not a valid UNIX domain socket")
            raise TypeError

        try:
            os.unlink(self.server_address)
        except OSError:
            logger.error(f"Removing UNIX domain socket {self.server_address} failed")
            if os.path.exists(self.server_address):
                raise

        self.cleanup_lock_file()

    def cleanup_lock_file(self):
        # Clean-up lock file
        if not Check.is_valid_file(Service._SERVICE_LOCK_FILE):
            logger.error(f"{Service.SERVICE_LOCK_FILE} is not a valid file")
            raise TypeError

        try:
            os.unlink(Service._SERVICE_LOCK_FILE)
        except OSError:
            logger.error(f"Removing file {Service._SERVICE_LOCK_FILE} failed")
            if os.path.exists(Service._SERVICE_LOCK_FILE):
                raise




class ServiceRequestHandler(socketserver.DatagramRequestHandler):


    def setup(self):

        logger.info("============================== REQUEST DISPATCHED ==================================")
        logger.info("Setting up ServiceRequestHandler")

        super().setup()

        if self.server.test_mode:
            self.add_talker = self._mock_add_talker
            self.add_talker_socket = self._mock_add_talker_socket
            self.add_listener = self._mock_add_listener
            self.add_listener_socket = self._mock_add_listener_socket
        else:
            self.add_talker = self._add_talker
            self.add_talker_socket = self._add_talker_socket
            self.add_listener = self._add_listener
            self.add_listener_socket = self._add_listener_socket


    def send(self, msg):
        addr = self.client_address
        return self.socket.sendto(msg, addr)


    def send_fd(self, msg, fd):
        fds = [fd.fileno()]
        ancdata = [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array("i", fds))]
        addr = self.client_address

        return self.socket.sendmsg([msg], ancdata, 0, addr)


    def build_qos_response(self, vlan_interface=None, soprio=None, fd=None):
        response = StreamQosResponse()

        if fd is None:
            response.vlan_interface = vlan_interface
            response.socket_priority = soprio

        message = response.SerializePartialToString()
        return message

    def receive_qos_request(self):

        data = self.packet
        request = StreamQosRequest()
        request.ParseFromString(data)

        return request


    def send_qos_response(self, vlan_interface, soprio):

        message = self.build_qos_response(vlan_interface, soprio)
        self.send(message)


    def send_qos_socket_response(self, fd):

        message = self.build_qos_response(fd=fd)
        self.send_fd(message, fd)

    def build_listener_qos_response(self, vlan_interface=None, soprio=None, fd=None):
        response = StreamQosResponse()

        if fd is None:
            response.vlan_interface = vlan_interface
            response.socket_priority = soprio

        message = response.SerializePartialToString()
        return message



    def send_listener_qos_response(self, vlan_interface, soprio):

        message = self.build_listener_qos_response(vlan_interface, soprio)
        self.send(message)


    def send_listener_qos_socket_response(self, fd):

        message = self.build_listener_qos_response(fd=fd)
        self.send_fd(message, fd)


    def _add_talker(self, request):
        addr = request.dmac
        vid = request.vid
        pcp = request.pcp
        txoffset = request.txmin
        interval = request.period
        size = request.size
        interface_name = request.interface
        if request.hints_available == True:
            tx_selection = request.hints_tx_selection
            tx_selection_offload = request.hints_tx_selection_offload
            data_path = request.hints_data_path
            preemption = request.hints_preemption
            launch_time_control = request.hints_launch_time_control
            hints = Hints(tx_selection, tx_selection_offload, data_path, preemption, launch_time_control)
        else:
            hints = None


        interface = Interface(interface_name)
        stream = StreamConfiguration(addr, vid, pcp, txoffset)
        traffic = TrafficSpecification(interval, size)

        config = Configuration(interface, stream, traffic, hints)

        vlan_interface, soprio = self.server.manager.add_talker(config)

        return vlan_interface, soprio


    def _mock_add_talker(self, request):

        with mock.patch.object(QdiscConfigurator,  'setup', return_value=None), \
             mock.patch.object(CommandIp,   'run', return_value=None), \
             mock.patch.object(DeviceConfigurator, 'setup_talker', return_value=None), \
             mock.patch.object(CommandSysctl, 'run', return_value=None), \
             mock.patch.object(SystemInformation,  'get_pci_id', return_value=('8086:4B30')), \
             mock.patch.object(SystemInformation,  'get_rate', return_value=1000 * 1000 * 1000), \
             mock.patch.object(Check,  'is_interface', return_value=True):

            addr = request.dmac
            vid = request.vid
            pcp = request.pcp
            txoffset = request.txmin
            interval = request.period
            size = request.size
            interface_name = request.interface

            stream = StreamConfiguration(addr, vid, pcp, txoffset)
            traffic = TrafficSpecification(interval, size)
            interface = Interface(interface_name)

            config = Configuration(interface, stream, traffic)

            vlan_interface, soprio = self.server.manager.add_talker(config)

        return vlan_interface, soprio


    def _add_talker_socket(self, request):
        # FIXME: complete once manager implements setup socket
        raise


    def _mock_add_talker_socket(self, request):
        # FIXME: modify once manager implements setup socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_PRIORITY, 6)
        s.bind(("127.0.0.1", 20001))
        return s

    def _add_listener(self, request):
        addr = request.dmac
        vid = request.vid
        pcp = request.pcp
        txoffset = request.txmin
        interval = request.period
        size = request.size
        interface_name = request.interface
        hints = None

        interface = Interface(interface_name)
        stream = StreamConfiguration(addr, vid, pcp, txoffset)
        traffic = TrafficSpecification(interval, size)

        config = Configuration(interface, stream, traffic, hints)

        vlan_interface, soprio = self.server.manager.add_listener(config)

        return vlan_interface, soprio

    def _add_listener_socket(self, request):
        # FIXME: complete once manager implements setup socket
        raise


    def _mock_add_listener(self, request):

        with mock.patch.object(QdiscConfigurator,  'setup', return_value=None), \
             mock.patch.object(CommandIp,   'run', return_value=None), \
             mock.patch.object(CommandSysctl, 'run', return_value=None), \
             mock.patch.object(DeviceConfigurator, 'setup_listener', return_value=None), \
             mock.patch.object(SystemInformation,  'get_pci_id', return_value=('8086:4B30')), \
             mock.patch.object(SystemInformation,  'get_rate', return_value=1000 * 1000 * 1000), \
             mock.patch.object(Check,  'is_interface', return_value=True):

            addr = request.dmac
            vid = request.vid
            pcp = request.pcp
            txoffset = request.txmin
            interval = request.period
            size = request.size
            interface_name = request.interface

            stream = StreamConfiguration(addr, vid, pcp, txoffset)
            traffic = TrafficSpecification(interval, size)
            interface = Interface(interface_name)

            config = Configuration(interface, stream, traffic)

            vlan_interface, soprio = self.server.manager.add_listener(config)

        return vlan_interface, soprio

    def _mock_add_listener_socket(self, request):
        # FIXME: modify once manager implements setup socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_PRIORITY, 6)
        s.bind(("127.0.0.1", 20001))
        return s

    def mock_socket_cleanup(self, socket):
        socket.close()

    def handle(self):
        logger.info("Handling request")

        request = self.receive_qos_request()

        if request.talker == True:
            if request.setup_socket == True:
            # FIXME: perform actual configuration
            # Currently manager only supports non-socket config
                try:
                    sock = None
                    sock = self.add_talker_socket(request)
                    if sock is None:
                        raise ValueError("Failed to create a talker, socket is None.")
                except Exception as ex:
                    logger.exception("Exception raised while setting up a talker socket")

                try:
                    self.send_qos_socket_response(sock)
                except Exception as ex:
                    logger.exception("Exception raised while sending the QoS response after setting up a talker socket")

                self.mock_socket_cleanup(sock)


            elif request.setup_socket == False:
                try:
                    vlan_interface = None
                    soprio = None
                    vlan_interface, soprio = self.add_talker(request)
                    if vlan_interface is None or soprio is None:
                         raise ValueError("Failed to create a talker, vlan_interface or soprio is None.")
                except Exception as ex:
                    logger.exception("Exception raised while setting up a talker")

                try:
                    self.send_qos_response(vlan_interface, soprio)
                except Exception as ex:
                    logger.exception("Exception raised while sending the QoS response after setting up a talker")

        elif request.talker == False:
            if request.setup_socket == True:
            # FIXME: perform actual configuration
            # Currently manager only supports non-socket config
                try:
                    sock = None
                    sock = self.add_listener_socket(request)
                    if sock is None:
                        raise ValueError("Failed to create a listener, socket is None.")
                except Exception as ex:
                    logger.exception("Exception raised while setting up a listener socket")

                try:
                    self.send_listener_qos_socket_response(sock)
                except Exception as ex:
                    logger.exception("Exception raised while sending the QoS response after setting up a  socket")

                self.mock_socket_cleanup(sock)


            elif request.setup_socket == False:
                try:
                    vlan_interface = None
                    soprio = None
                    vlan_interface, soprio = self.add_listener(request)
                    if vlan_interface is None or soprio is None:
                        raise ValueError("Failed to create a listener, vlan_interface or soprio is None.")
                except Exception as ex:
                    logger.exception("Exception raised while setting up a listener")
                
                try:
                    self.send_listener_qos_response(vlan_interface, soprio)
                except Exception as ex:
                    logger.exception("Exception raised while sending the QoS response after setting up a listener")
