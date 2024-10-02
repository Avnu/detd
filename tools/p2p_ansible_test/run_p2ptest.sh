#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2024 Intel Corporation
# Authors:
#   Kumar Amber
#   Hector Blanco Alcaine


# Remote IP addresses.
TALKER_NODE_IP="172.28.240.67"
LISTENER_NODE_IP="172.28.240.149"

# Interfaces to run the talker and listener applications
TALKER_INTERFACE="enp1s0"
LISTENER_INTERFACE="enp2s0"

# Remote user-name.
ANSIBLE_USER="$(whoami)"

# Define the location on remote for scripts and binaries to be copied.
DEST="/home/${ANSIBLE_USER}/detd_p2ptest"
# Define the location on the host for logs to be copied.
FETCH_DEST="/home/${ANSIBLE_USER}/detd_p2ptest"

# Modify inventory.ini with the variables defined above
sed -i "s|^dest=[^$]*$|dest=${DEST}|" inventory.ini
sed -i "s|^fetch_dest=[^$]*$|fetch_dest=${FETCH_DEST}|" inventory.ini
sed -i "s/^talker_node ansible_host=[^$]*$/talker_node ansible_host=${TALKER_NODE_IP}/" inventory.ini
sed -i "s/^listener_node ansible_host=[^$]*$/listener_node ansible_host=${LISTENER_NODE_IP}/" inventory.ini
sed -i "s/^talker_node interface=[^$]*$/talker_node interface=${TALKER_INTERFACE}/" inventory.ini
sed -i "s/^listener_node interface=[^$]*$/listener_node interface=${LISTENER_INTERFACE}/" inventory.ini


if [ "$1" == "deploy" ]; then

  PLAYBOOKS="deploy.yml"
  BECOME=""

elif [ "$1" == "test" ]; then

  PLAYBOOKS="test.yml"
  BECOME="--ask-become-pass"

else

  PLAYBOOKS="deploy.yml test.yml"
  BECOME="--ask-become-pass"

fi

ansible-playbook --inventory inventory.ini ${BECOME} ${PLAYBOOKS}
