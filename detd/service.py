#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

""" Module service

This module implements the server and client side for the system service
dealing with the application requests to guarantee deterministic QoS.

   * Server-side
     * class Service
     * class ServiceRequestHandler


   * Client-side
     * class ServiceProxy

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

from .manager import StreamConfiguration
from .manager import TrafficSpecification
from .manager import Interface
from .manager import Configuration
from .manager import Manager

from .systemconf import Check
from .systemconf import QdiscConfigurator
from .systemconf import DeviceConfigurator
from .systemconf import SystemInformation
from .systemconf import CommandIp




_SERVICE_UNIX_DOMAIN_SOCKET='/var/run/detd/detd_service.sock'




class Service(socketserver.UnixDatagramServer):

    _SERVICE_LOCK_FILE='/var/lock/detd'

    def __init__(self, test_mode=False):

        # We create the lock file even before calling parent's constructor
        self.setup_lock_file()

        self.setup_unix_domain_socket()

        super().__init__(_SERVICE_UNIX_DOMAIN_SOCKET, ServiceRequestHandler)

        self.test_mode = test_mode

        self.manager = Manager()

        signal.signal(signal.SIGINT, self.terminate)
        signal.signal(signal.SIGTERM, self.terminate)


    def setup_lock_file(self):

        if not Check.is_valid_path(Service._SERVICE_LOCK_FILE):
            raise TypeError

        with open(Service._SERVICE_LOCK_FILE, "x") as lock_file:
            pid = os.getpid()
            lock_file.write(str(pid))

        os.chmod(Service._SERVICE_LOCK_FILE, stat.S_IRUSR)


    def setup_unix_domain_socket(self):

        basedir = Path(_SERVICE_UNIX_DOMAIN_SOCKET).parent.parent
        if not Check.is_valid_path(basedir):
            raise TypeError

        parent = Path(_SERVICE_UNIX_DOMAIN_SOCKET).parent
        # FIXME: set the right permissions, user, etc
        parent.mkdir()


    def terminate(self, signum, frame):
        threading.Thread(target=self.shutdown, daemon=True).start()


    def run(self):

        try:
            self.serve_forever()
        finally:
            self.server_close()
            self.cleanup()


    def cleanup(self):

        # Clean-up UNIX domain socket and parent directory
        if not Check.is_valid_unix_domain_socket(self.server_address):
            raise TypeError

        try:
            os.unlink(self.server_address)
        except OSError:
            if os.path.exists(self.server_address):
                raise

        try:
            parent = Path(self.server_address).parent
            parent.rmdir()
        except OSError:
            if os.path.exists(self.server_address):
                raise


        # Clean-up lock file
        if not Check.is_valid_file(Service._SERVICE_LOCK_FILE):
            raise TypeError

        try:
            os.unlink(Service._SERVICE_LOCK_FILE)
        except OSError:
            if os.path.exists(Service._SERVICE_LOCK_FILE):
                raise




class ServiceRequestHandler(socketserver.DatagramRequestHandler):


    def setup(self):

        super().setup()

        if self.server.test_mode:
            self.setup_talker = self._mock_setup_talker
            self.setup_talker_socket = self._mock_setup_talker_socket
        else:
            self.setup_talker = self._setup_talker
            self.setup_talker_socket = self._setup_talker_socket


    def send(self, msg):
        addr = self.client_address
        return self.socket.sendto(msg, addr)


    def send_fd(self, msg, fd):
        fds = [fd.fileno()]
        ancdata = [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array("i", fds))]
        addr = self.client_address

        return self.socket.sendmsg([msg], ancdata, 0, addr)


    def receive_qos_request(self):

        data = self.packet
        request = StreamQosRequest()
        request.ParseFromString(data)

        return request


    def build_qos_response(self, fd=None, vlan_interface=None, soprio=None):
        response = StreamQosResponse()

        # Setup succeeded if we have either a socket or the parameters initialized
        success = fd is not None or (vlan_interface is not None and soprio is not None)

        if success:
            response.ok = True
            if fd is None:
                response.vlan_interface = vlan_interface
                response.socket_priority = soprio
        else:
            response.ok = False

        message = response.SerializePartialToString()
        return message



    def send_qos_response(self, vlan_interface, soprio):

        message = self.build_qos_response(None, vlan_interface, soprio)
        self.send(message)


    def send_qos_socket_response(self, fd):

        message = self.build_qos_response(fd)
        self.send_fd(message, fd)


    def _setup_talker(self, request):
        addr = request.dmac
        vid = request.vid
        pcp = request.pcp
        txoffset = request.txmin
        interval = request.period
        size = request.size
        interface_name = request.interface

        interface = Interface(interface_name)
        stream = StreamConfiguration(addr, vid, pcp, txoffset)
        traffic = TrafficSpecification(interval, size)

        config = Configuration(interface, stream, traffic)

        vlan_interface, soprio = self.server.manager.add_talker(config)

        return vlan_interface, soprio


    def _mock_setup_talker(self, request):

        with mock.patch.object(QdiscConfigurator,  'setup', return_value=None), \
             mock.patch.object(CommandIp,   'run', return_value=None), \
             mock.patch.object(DeviceConfigurator, 'setup', return_value=None), \
             mock.patch.object(SystemInformation,  'get_pci_id', return_value=('8086:4B30')):

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


    def _setup_talker_socket(self, request):
        # FIXME: complete once manager implements setup socket
        raise


    def _mock_setup_talker_socket(self, request):
        # FIXME: modify once manager implements setup socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_PRIORITY, 6)
        s.bind(("127.0.0.1", 20001))
        return s


    def mock_socket_cleanup(self, socket):
        socket.close()


    def handle(self):

        request = self.receive_qos_request()
        if request.setup_socket == True:
            # FIXME: perform actual configuration
            # Currently manager only supports non-socket config
            sock = self.setup_talker_socket(request)
            self.send_qos_socket_response(sock)
            self.mock_socket_cleanup(sock)
        elif request.setup_socket == False:
            vlan_interface, soprio = self.setup_talker(request)
            self.send_qos_response(vlan_interface, soprio)




class ServiceProxy:

    def __init__(self):

        if not Check.is_valid_unix_domain_socket(_SERVICE_UNIX_DOMAIN_SOCKET):
            raise TypeError

        self.uds_address = _SERVICE_UNIX_DOMAIN_SOCKET

        self.setup_socket()


    def __del__(self):
        self.sock.close()


    def setup_socket(self):

        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.sock.bind("")


    def send(self, message):

        foobar = StreamQosRequest()
        foobar.ParseFromString(message)

        try:
            self.sock.sendto(message, self.uds_address)

        except:
            raise

#        finally:
#            self.sock.close()


    def recv(self):

        message, addr = self.sock.recvfrom(1024)

        return message


    def recv_fd(self, msglen):
        fds = array.array("i")   # Array of ints
        maxfds = 1
        msg, ancdata,flags, addr = self.sock.recvmsg(msglen, socket.CMSG_LEN(maxfds * fds.itemsize))
        for cmsg_level, cmsg_type, cmsg_data in ancdata:
            if cmsg_level == socket.SOL_SOCKET and cmsg_type == socket.SCM_RIGHTS:
                # Append data, ignoring any truncated integers at the end.
                fds.frombytes(cmsg_data[:len(cmsg_data) - (len(cmsg_data) % fds.itemsize)])
        return msg, list(fds)



    def send_qos_request(self, configuration, setup_socket):
        request = StreamQosRequest()
        request.interface = configuration.interface.name
        request.period = configuration.traffic.interval
        request.size = configuration.traffic.size
        request.dmac = configuration.stream.addr
        request.vid = configuration.stream.vid
        request.pcp = configuration.stream.pcp
        request.txmin = configuration.stream.txoffset
        request.txmax = configuration.stream.txoffset
        request.setup_socket = setup_socket

        message = request.SerializeToString()
        self.send(message)


    def receive_qos_response(self):
        message = self.recv()

        response = StreamQosResponse()
        response.ParseFromString(message)

        return response


    def receive_qos_socket_response(self):
        sock = self.sock

        message, fds = self.recv_fd(1024)
        response = StreamQosResponse()
        response.ParseFromString(message)

        s = socket.socket(fileno=fds[0])

        return response, s


    def setup_talker_socket(self, configuration):

        self.send_qos_request(configuration, setup_socket=True)
        status, sock = self.receive_qos_socket_response()

        if not status.ok:
            # FIXME handle error
            return None

        return sock


    def setup_talker(self, configuration):

        self.send_qos_request(configuration, setup_socket=False)
        response = self.receive_qos_response()

        if not response.ok:
            # FIXME handle error
            return None

        vlan_interface = response.vlan_interface
        soprio = response.socket_priority

        return vlan_interface, soprio
