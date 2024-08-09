#!/bin/bash

# Define paths
DETD_CONFIG="detd_listener.py"
TX_RX="txrx"
INTERFACE="enp3s0"
DETD_DEB="detd_0.1.dev0-1_all.deb"
TARGET_DEV_MAC="00:a0:c9:00:00:00"

# Make Python script executable
chmod +x $DETD_CONFIG

# Make the executable
chmod +x $TX_RX

tc qdisc del dev $INTERFACE root
sleep 2
ip link del $INTERFACE.3
sleep 2

# Run Detd Configuration
# Execute the script and capture the output
output=$(python3 $DETD_CONFIG $INTERFACE $DETD_DEB)

sleep 10
# Parse the output using shell parameter expansion

VLAN_INTERFACE=$(echo $output | sed -n "s/('\([^']*\)', .*)/\1/p")
SOCKET_PRIO=$(echo $output | sed -n "s/(.*, \([0-9]*\))/\1/p")

echo "Vlan Interface = $VLAN_INTERFACE"
echo "Socket Prio = $SOCKET_PRIO"

sleep 2
# Set up Interface
ip link set $VLAN_INTERFACE up

sleep 2

# Run Tx_RX
./$TX_RX --interface=$VLAN_INTERFACE --afpkt --verbose --socket-prio=$SOCKET_PRIO -r > list_out.txt
