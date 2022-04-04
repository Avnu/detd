#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2020-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine

Gbps_to_bps = 1000 * 1000 * 1000




class Device:

    def __init__(self, num_tx_queues, num_rx_queues):
        self.num_tx_queues = num_tx_queues
        self.num_rx_queues = num_rx_queues
        self.features = {}

        self.available_queues = list(range(0, num_tx_queues-1))
        self.best_effort_queue = 0
        self.available_queues.remove(self.best_effort_queue)

        # FIXME: this should be done in runtime and not hardcoded
        # FIXME: runtime changes in rate need to be managed
        self.rate = 1 * Gbps_to_bps # bits per second


    def assign_queue(self):
        # FIXME handle case when only one queue is available, that should be
        #       reserved for best effort traffic
        # FIXME i210 requires a more sophisticate queue allocation
        return self.available_queues.pop(0)




class IntelMgbe(Device):

    # FIXME support for listener stream
    # If the stream is time aware, flows should be configured for PTP traffic
    # e.g. ethtool -N $IFACE flow-type ether proto 0x88f7 queue $PTP_RX_Q
    # For Rx redirection:
    # ethtool --set-rxfh-indir ${INTERFACE} equal 2

    def __init__(self):
        super().__init__(8, 8)

        self.features['rxvlan'] = 'off'
        self.features['hw-tc-offload'] = 'on'
        self.num_tx_ring_entries = 1024
        self.num_rx_ring_entries = 1024
