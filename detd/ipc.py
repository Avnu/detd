#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2025 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

""" Module ipc

This module implements helper classes to encode and decode the messages defined
in ipc.proto. They are implemented as class methods for a single class:

   * class Message

ipc.proto defines the interface for the different RPCs, each composed of a
request and a response.

For each of these requests and responses, this file provides the methods:

   * Encode: takes domain parameters and generates the packet to transmit
   * Decode: takes a packet received and extracts the corresponding attributes

In addition, utility methods are provided to extract the messages and their
type from the wire protocol. For example, with protocol buffers the messages
are encapsulated into a wrapper message, that has to be processed in order to
know the actual message type.

"""




from .ipc_pb2 import DetdMessage
from .ipc_pb2 import HintsMessage
from .ipc_pb2 import InitRequest
from .ipc_pb2 import InitResponse
from .ipc_pb2 import StreamQosRequest
from .ipc_pb2 import StreamQosResponse

from .manager import InterfaceConfiguration
from .manager import Interface
from .scheduler import Configuration
from .scheduler import ListenerConfiguration
from .scheduler import StreamConfiguration
from .scheduler import TrafficSpecification




class Message:

    # InitInterfaceRequest

    @classmethod
    def encode_init_interface_request(cls, interface_configuration):

        request = InitRequest()

        request.interface = interface_configuration.interface_name
        if interface_configuration.hints is not None:
            hints = HintsMessage()
            hints.hints_tx_selection = interface_configuration.hints.tx_selection.value
            hints.hints_tx_selection_offload = interface_configuration.hints.tx_selection_offload
            hints.hints_data_path = interface_configuration.hints.data_path.value
            hints.hints_preemption = interface_configuration.hints.preemption
            hints.hints_launch_time_control = interface_configuration.hints.launch_time_control

            request.hints = CopyFrom(hints)

        message = DetdMessage()
        message.init_request.CopyFrom(request)

        packet = message.SerializeToString()

        return packet

    @classmethod
    def decode_init_interface_request(cls, request):

        interface_name = request.interface

        if request.HasField("hints"):
            tx_selection = request.hints.hints_tx_selection
            tx_selection_offload = request.hints.hints_tx_selection_offload
            data_path = request.hints.hints_data_path
            preemption = request.hints.hints_preemption
            launch_time_control = request.hints.hints_launch_time_control
            hints = Hints(tx_selection, tx_selection_offload, data_path, preemption, launch_time_control)
        else:
            hints = None

        interface_config = InterfaceConfiguration(interface_name, hints)

        return interface_config

    # InitInterfaceResponse

    @classmethod
    def encode_init_interface_response(cls, ok):
        response = InitResponse()

        response.ok = ok

        message = DetdMessage()
        message.init_response.CopyFrom(response)

        packet = message.SerializeToString()

        return packet

    @classmethod
    def decode_init_interface_response(cls, response):

        ok = response.ok

        return ok


    # StreamQosRequest

    @classmethod
    def encode_stream_qos_request(cls, configuration, setup_socket):

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

        if type(configuration) is Configuration:
            request.talker = True
        elif type(configuration) is ListenerConfiguration:
            request.talker = False
            request.dmac = configuration.maddress

        message = DetdMessage()
        message.stream_qos_request.CopyFrom(request)

        packet = message.SerializeToString()

        return packet

    @classmethod
    def decode_stream_qos_request(cls, request):

        addr = request.dmac
        vid = request.vid
        pcp = request.pcp
        txoffset = request.txmin
        interval = request.period
        size = request.size
        interface_name = request.interface

        if not request.talker:
            maddr = request.dmac

        interface = Interface(interface_name)
        stream = StreamConfiguration(addr, vid, pcp, txoffset)
        traffic = TrafficSpecification(interval, size)

        if request.talker:
            config = Configuration(interface, stream, traffic)
        else:
            config = ListenerConfiguration(interface, stream, traffic, maddr)

        return config


    # StreamQosResponse

    @classmethod
    def encode_stream_qos_response(cls, ok=False, vlan_interface=None, socket_priority=None):
        response = StreamQosResponse()
        response.ok = ok
        if vlan_interface is not None and socket_priority is not None:
            response.vlan_interface = vlan_interface
            response.socket_priority = socket_priority

        message = DetdMessage()
        message.stream_qos_response.CopyFrom(response)

        packet = message.SerializeToString()

        return packet

    @classmethod
    def decode_stream_qos_response(cls, response):

        ok = response.ok
        vlan_interface = response.vlan_interface
        socket_priority = response.socket_priority

        return ok, vlan_interface, socket_priority



    # ListenerQosRequest

    @classmethod
    def encode_listener_qos_request(cls, configuration):

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
        request.maddress = configuration.maddress
        request.talker = False

        message = DetdMessage()
        message.stream_qos_request.CopyFrom(request)

        packet = message.SerializeToString()

        return packet


    #  ListenerQosResponse

    @classmethod
    def encode_listener_qos_response(cls, ok=False, vlan_interface=None, socket_priority=None, fd=None):
        response = StreamQosResponse()

        response.ok = ok
        if vlan_interface is not None and socket_priority is not None:
            response.vlan_interface = vlan_interface
            response.socket_priority = socket_priority

        message = DetdMessage()
        message.stream_qos_response.CopyFrom(response)

        packet = message.SerializeToString()

        return packet

    # Generic

    @classmethod
    def extract_request(cls, packet):

        message = DetdMessage()
        message.ParseFromString(packet)

        if message.HasField("init_request"):
            request = message.init_request
        elif message.HasField("stream_qos_request"):
            request = message.stream_qos_request
        else:
            raise Exception("Wrong request type")

        return type(request), request


    @classmethod
    def extract_response(cls, packet):

        message = DetdMessage()
        message.ParseFromString(packet)

        if message.HasField("init_response"):
            response = message.init_response
        elif message.HasField("stream_qos_response"):
            response = message.stream_qos_response
        else:
            raise Exception("Wrong response type")

        return type(response), response
