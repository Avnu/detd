#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2025 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

""" Module proxy

This module implements the client side for the system service dealing with the
application requests to guarantee deterministic QoS.

   * class ServiceProxy

Client and server side exchange messages using the protocol defined in the
file ipc.proto
"""




import array
import socket

from .common import Check
from .ipc import *


_SERVICE_UNIX_DOMAIN_SOCKET='/var/run/detd/detd_service.sock'




class ServiceProxy:

    def __init__(self):

        if not Check.is_valid_unix_domain_socket(_SERVICE_UNIX_DOMAIN_SOCKET):
            raise TypeError

        self.uds_address = _SERVICE_UNIX_DOMAIN_SOCKET


    def __del__(self):
        self.sock.close()


    def setup_socket(self):

        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.sock.bind("")
        self.sock.connect(self.uds_address)


    def send(self, packet):

        try:
            self.sock.sendto(packet, self.uds_address)

        except:
            raise

#        finally:
#            self.sock.close()


    def recv(self):
        packet, addr = self.sock.recvfrom(1024)

        return packet


    def recv_fd(self, msglen):
        fds = array.array("i")   # Array of ints
        maxfds = 1
        msg, ancdata,flags, addr = self.sock.recvmsg(msglen, socket.CMSG_LEN(maxfds * fds.itemsize))
        for cmsg_level, cmsg_type, cmsg_data in ancdata:
            if cmsg_level == socket.SOL_SOCKET and cmsg_type == socket.SCM_RIGHTS:
                # Append data, ignoring any truncated integers at the end.
                fds.frombytes(cmsg_data[:len(cmsg_data) - (len(cmsg_data) % fds.itemsize)])
        return msg, list(fds)


    def send_init_interface_request(self, configuration):

        packet = Message.encode_init_interface_request(configuration)

        self.send(packet)


    def send_qos_request(self, configuration, setup_socket):

        packet = Message.encode_stream_qos_request(configuration, setup_socket)

        self.send(packet)


    def send_qos_listener_request(self, configuration, setup_socket):

        packet = Message.encode_stream_qos_request(configuration, setup_socket)

        self.send(packet)


    def receive_response(self):

        packet = self.recv()

        response_type, response = Message.extract_response(packet)

        return response_type, response


    def receive_response_socket(self):

        packet, fds = self.recv_fd(1024)

        response_type, response = Message.extract_response(packet)

        s = socket.socket(fileno=fds[0])

        return response_type, response, s


    def receive_init_interface_response(self):

        request_type, response = self.receive_response()

        if request_type != InitResponse:
            raise Exception("Unexpected response")

        return response


    def receive_qos_response(self):

        request_type, response = self.receive_response()

        if request_type != StreamQosResponse:
            raise Exception("Unexpected response")

        return response

    
    def receive_qos_socket_response(self):

        request_type, response, s = self.receive_response_socket()

        if request_type != StreamQosResponse:
            raise Exception("Unexpected response")

        return response, s


    def receive_listener_qos_response(self):

        request_type, response = self.receive_response()

        if request_type != StreamQosResponse:
            raise Exception("Unexpected response")

        return response


    def receive_listener_qos_socket_response(self):

        request_type, response, s = self.receive_response_socket()

        if request_type != StreamQosResponse:
            raise Exception("Unexpected response")

        return response, s


    def init_interface(self, configuration):
        self.setup_socket()
        self.send_init_interface_request(configuration)
        response = self.receive_init_interface_response()
        ok = Message.decode_init_interface_response(response)
        if ok == False:
            raise RuntimeError("Service replied with an error on interface init")
        self.sock.close()


    def add_talker_socket(self, configuration):

        self.setup_socket()
        self.send_qos_request(configuration, setup_socket=True)
        response, sock = self.receive_qos_socket_response()
        ok, _, _ = Message.decode_stream_qos_response(response)
        if ok == False:
            raise RuntimeError("Service replied with an error on add talker socket")
        self.sock.close()

        return sock


    def add_talker(self, configuration):

        self.setup_socket()
        self.send_qos_request(configuration, setup_socket=False)
        response = self.receive_qos_response()
        ok, vlan_interface, soprio = Message.decode_stream_qos_response(response)
        if ok == False:
            raise RuntimeError("Service replied with an error on add talker")
        self.sock.close()

        return vlan_interface, soprio


    def add_listener_socket(self, configuration):

        self.setup_socket()
        self.send_listener_qos_request(configuration, setup_socket=True)
        response, sock = self.receive_listener_qos_socket_response()
        ok, _, _ = Message.decode_stream_qos_response(response)
        if ok == False:
            raise RuntimeError("Service replied with an error on add listener socket")
        self.sock.close()

        return sock


    def add_listener(self, configuration):

        self.setup_socket()
        self.send_qos_listener_request(configuration, setup_socket=False)
        response = self.receive_listener_qos_response()
        ok, vlan_interface, soprio = Message.decode_stream_qos_response(response)
        if ok == False:
            raise RuntimeError("Service replied with an error on add listener")
        self.sock.close()

        return vlan_interface, soprio
