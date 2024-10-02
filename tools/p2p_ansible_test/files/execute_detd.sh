#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2024 Intel Corporation
# Authors:
#   Kumar Amber
#   Hector Blanco Alcaine


ROLE=
INTERFACE="enp2s0"
CYCLE=20000000
OFFSET=0
SIZE=1522
ADDRESS="00:C0:FF:EE:FF:4E"
VID=3
PCP=6

DETD_DEB="detd_0.1.dev0-1_all.deb"


function usage () {

   echo "Usage: $0 [talker|listener] interface (e.g.: $0 talker enp2s0)"

}


function parse_args () {

   # Check the number of arguments supplied
   if [ $# -ne 2 ]; then
      echo "Wrong number of arguments"
      usage
      exit 1
   fi

   if [ "$1" == "talker" ]; then
      ROLE="talker"
   elif [ "$1" == "listener" ]; then
      ROLE="listener"
   else
      echo "Invalid argument"
      usage
      exit 1
   fi

   INTERFACE="$2"

}


function reinstall_deb () {
   SILENT_APT="-qqq -o Dpkg::Use-Pty=\"0\" -o Dpkg::Progress-Fancy=\"0\""
   sudo bash -c "DEBIAN_FRONTEND=noninteractive apt-get --assume-yes ${SILENT_APT} purge detd"
   sudo bash -c "DEBIAN_FRONTEND=noninteractive apt-get --assume-yes ${SILENT_APT} install ./${DETD_DEB}"
}


function cleanup () {

  sudo tc qdisc del dev ${INTERFACE} root
  sleep 2
  sudo ip maddress del ${STREAM_MAC} dev ${INTERFACE}
  sudo ip link del ${INTERFACE}.3

}


parse_args "$@"
reinstall_deb
cleanup

if [ "${ROLE}" == "talker" ]; then
   echo "Running talker..."
   sudo phc_ctl ${INTERFACE} set
   sudo taskset --cpu-list 2 chrt --fifo 98 ./detd_apps.py talker --interface ${INTERFACE}
elif [ "${ROLE}" == "listener" ]; then
   echo "Running listener..."
   # Enable Rx hardware timestamping
   sudo hwstamp_ctl -r 1 -t 0 -i ${INTERFACE} > /dev/null
   sudo ./detd_apps.py listener --interface ${INTERFACE}
else
      echo "Invalid role: ${ROLE}"
      usage
      exit 1
fi

exit 0
