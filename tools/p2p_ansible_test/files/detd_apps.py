#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2024 Intel Corporation
# Authors:
#   Kumar Amber
#   Hector Blanco Alcaine


""" Module detd_apps

Auxiliary module that implements:
    * Classes for Frame, Metadata and Timer
    * Simple talk and listen functions based on the above

This module provides a compact way to:
    * Call detd to perform a local configuration
    * Use the result to trigger a talker or listener application

The parameters for the reservation can be provided as arguments to the function.

The talker and listener applications are implemented in Python and not
optimized for real-time at lower cycle times. However, they can be used to
achieve nanosecond range Tx jitter with relaxed application cycle times, e.g.
in the tens of milliseconds.

The applications can be re-implemented in C and interoperate with detd as
demonstrated in this file. For that, replace the Proxy implementation by the
equivalent C code, and include the protobuf C code generated from ipc.proto
"""



import argparse
import binascii
import time
import struct
import socket

from ctypes import *
from fcntl import ioctl

from detd import *

ETH_HLEN = 14

# From net_stamp.h
SO_TIMESTAMPING = 37
SCM_TIMESTAMPING = SO_TIMESTAMPING

SOF_TIMESTAMPING_RX_HARDWARE = 4
SOF_TIMESTAMPING_RAW_HARDWARE = 64

# From time.h
TIMER_ABSTIME = 0x01

# From sockios.h
SIOCGIFHWADDR=0x8927


class Metadata:

    def __init__(self, rxts):
        self.rxts = rxts

    @classmethod
    def from_ancillary(cls, ancillary):

        for item in ancillary:

            cmsg_level = item[0]
            cmsg_type = item[1]
            cmsg_data = item[2]

            if(item[0]!=socket.SOL_SOCKET or item[1]!=SCM_TIMESTAMPING):
                continue

            # There are 3 timespec values (sec, nsec)
            # The HW timestamp comes in the third pair
            _, _, _, _, sec, nsec = struct.unpack("6q", item[2])

            rxts = int(sec * 1e9) + int(nsec)
            break

        return cls(rxts)


# MAC destination (6B)
# MAC source      (6B)
# 802.1Q tag (optional) (4B)
# Ethertype (Ethernet II) (2B)
# Payload
# FIXME: add vlan support
class Frame:

    def __init__(self, dmac, smac, ethertype, payload, vlan=None, rxts=None):
        self.dmac = dmac
        self.smac = smac
        self.ethertype = ethertype
        self.payload = payload

    @classmethod
    def from_binary(cls, binary, metadata=None):

        header = binary[:ETH_HLEN]
        payload = binary[ETH_HLEN:]

        dmac, smac, ethertype = struct.unpack('!6s6sH', header)
        vlan = None

        return cls(dmac, smac, ethertype, payload, vlan)

    def __repr__(self):
        dmac = ":".join('%02x' % byte for byte in self.dmac)
        smac = ":".join('%02x' % byte for byte in self.smac)
        ethertype = hex(self.ethertype)

        return f"|{smac}|{dmac}|{ethertype}|"



class Timer:

    def __init__(self, period):
        self.period = int(period)
        self.start = None
        self.next = None

        cdll.LoadLibrary("libc.so.6")
        libc = CDLL("libc.so.6")

        self.clock_nanosleep = libc.clock_nanosleep


    def sleep_until_next(self):

        if self.start is None:
            now = int(time.clock_gettime_ns(time.CLOCK_TAI))
            elapsed = now % self.period
            remaining = self.period - elapsed
            safety_margin = 4000000000
            self.start = now + remaining + int(self.period/2) + safety_margin

            self.next = self.start
        else:
            self.next = self.next + self.period

        sec = int(self.next * 1e-9)
        nsec = int(self.next - (sec*1e9))
        timespec = struct.pack("qq", sec, nsec)

        clockid = time.CLOCK_TAI
        flags = TIMER_ABSTIME

        self.clock_nanosleep(clockid, flags, timespec)


def listen(interface, socket_priority, cycle, samples):

    # FIXME add ioctl equivalent to hwstamp_ctl -r 1 -t 1 -i <iface>

    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(socket.ETH_P_ALL))

    flags = SOF_TIMESTAMPING_RX_HARDWARE | SOF_TIMESTAMPING_RAW_HARDWARE
    s.setsockopt(socket.SOL_SOCKET, SO_TIMESTAMPING, flags)

    s.setsockopt(socket.SOL_SOCKET, socket.SO_PRIORITY, socket_priority) 

    # Timeout in milliseconds, set to 10 seconds
    timeout = 10000
    s.settimeout(timeout)

    s.bind((interface, 0))

    log_file = open("listener.txt", "w")

    prev_rxts = 0
    maxts = 0
    received = 0

    while received < samples:

        try:
            f, ancdata, _, _ = s.recvmsg(64, 1024)
        except socket.timeout:
            print("recvmsg timed out. Aborting...")
            break
        except:
            print("recvmsg error. Aborting...")
            break

        frame = Frame.from_binary(f)
        meta = Metadata.from_ancillary(ancdata)

        rxts = meta.rxts
        if prev_rxts != 0:
            delta = cycle - (rxts - prev_rxts)

            if delta > maxts:
                maxts = delta


        received = received + 1
        
        prev_rxts = rxts

        log_file.write(f"{rxts}\n")

    log_file.close()

    print(f"Received [frames]: {received}")
    print(f"Max jitter [nanoseconds]: {maxts}")


def talk(interface, dest_mac, socket_priority, cycle, samples):

    # Create and bind socket to interface
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(socket.ETH_P_ALL))
    s.setsockopt(socket.SOL_SOCKET, socket.SO_PRIORITY, socket_priority) 
    s.bind((interface, 0))

    # Convert the destination MAC string to insert it in the frame
    dst = binascii.unhexlify(dest_mac.replace(':', ''))

    # Extract source MAC from provided interface
    ret = ioctl(s.fileno(), SIOCGIFHWADDR,  struct.pack('256s', bytes(interface, 'utf-8')[:15]))
    src = ret[18:24]

    ethertype = 0xb62c
    payload = 'RightInTime!'.encode()

    # Network order
    # 6 x char (6B)
    # 6 x char (6B)
    # 1 x unsigned short (2B)
    # 2 x char (2B)
    pkt = struct.pack('!6s6sH2s',
                      dst,
                      src,
                      ethertype,
                      payload)


    timer = Timer(cycle)

    for i in range(samples):
        timer.sleep_until_next()
        s.sendall(pkt)

    s.close()


if __name__ == "__main__":

    def setup_stream_config(args):

        interface = Interface(args.interface)
        stream = StreamConfiguration(args.addr, args.vid, args.pcp, args.txoffset)
        stream.base_time = 0
        traffic = TrafficSpecification(args.cycle, args.size)

        hints = None

        return interface, stream, traffic, hints

    parser = argparse.ArgumentParser(description='Configure and add a talker to the network.')
    parser.add_argument('role', type=str, choices=["talker", "listener"], help='Role of the application')
    parser.add_argument('--interface', type=str, help='Name of the network interface to use')
    parser.add_argument('--cycle', type=int, default=20000000, help='Cycle time in nanoseconds')
    parser.add_argument('--txoffset', type=int, default=0, help='Tx offset in nanoseconds')
    parser.add_argument('--size', type=int, default=1522, help='Bytes transmitted/received')
    parser.add_argument('--addr', type=str, default="03:C0:FF:EE:FF:4E", help='Stream address')
    parser.add_argument('--vid', type=int, default=3, help='VLAN ID')
    parser.add_argument('--pcp', type=int, default=6, help='VLAN PCP')
    parser.add_argument('--samples', type=int, default=10, help='Number of frames to send and receive')




    args = parser.parse_args()

    interface, stream, traffic, hints = setup_stream_config(args)

    proxy = ServiceProxy()

    if args.role == 'talker':
        # When testing a back-to-back scenario, if talker and listener are
        # triggered at the same time, the link down on one end may cause the
        # other end to go down as well.
        # The talker will be configured and triggered after a pre-configured
        # pause.
        time.sleep(5)
        config = Configuration(interface, stream, traffic, hints)
        vlan_interface, socket_priority = proxy.add_talker(config)
        talk(vlan_interface, args.addr, socket_priority, args.cycle, args.samples)
    elif args.role == 'listener':
        config = ListenerConfiguration(interface, stream, traffic, args.addr, hints)
        vlan_interface, socket_priority = proxy.add_listener(config)
        listen(vlan_interface, socket_priority, args.cycle, args.samples)
    else:
        print("Error!!!")
