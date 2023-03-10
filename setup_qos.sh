#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2021-2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine
#
# ./setup_qos.sh --period <PERIOD> --bytes <BYTES> --offset <OFFSET> --interface <IFACE> --address <ADDRESS> --vid <VID> --pcp <PCP> -- <COMMAND> <ARGS>
#
# Set up an interface as a talker with the provided parameters except
# the destination MAC



function usage () {
   echo "Usage:"
   echo "$0 --period <PERIOD> --bytes <BYTES> --offset <OFFSET> --interface <IFACE> --address <ADDRESS> --vid <VID> --pcp <PCP> -- <COMMAND> <ARGS>"
   echo "Example:"
   echo "$0 --period 2000000 --bytes 1522 --offset 250000 --interface eth0 --address AB:CD:EF:FE:DC:BA --vid 3 --pcp 6 -- ping -4 -w 1 8.8.8.8"
}


function check_root () {

   if [ `id --user` -ne 0 ]; then
      echo "This script must be run as root! Aborting."
      exit 1
   fi

}

function parse_args () {

   # Check the number of arguments supplied
   if [ $# -lt 15  ]; then
      echo "Wrong number of arguments"
      usage
      exit 1
   fi

   # getopt will set name if there are options
   ARGS=`getopt --longoptions "period:,bytes:,offset:,interface:,address:,vid:,pcp:" --options "c:b:o:i:a:v:p:" -- "$@"`

   # Handle wrong parameter names
   # The case when parameters are missing is handled after the while below
   if [[ $? -ne 0 ]]; then
      usage
      exit 1
   fi

   eval set -- "${ARGS}"

   # Assign parameter values to variables
   while [ $# -ge 1 ]; do
      case "$1" in
         --)
            shift
            break
            ;;
         -c|--period)
            PERIOD="$2"
            shift
            ;;
         -b|--bytes)
            BYTES="$2"
            shift
            ;;
         -o|--offset)
            OFFSET="$2"
            shift
            ;;
         -i|--interface)
            IFACE="$2"
            shift
            ;;
         -a|--address)
            ADDRESS="$2"
            shift
            ;;
         -v|--vid)
            VID="$2"
            shift
            ;;
         -p|--pcp)
            PCP="$2"
            shift
            ;;
	 \?)
            echo "Invalid option $OPTARG"
	    usage
	    exit 1
	    ;;

      esac

      shift

   done


   COMMAND="$1"
   shift
   ARGS="$*"

}


function check_args () {

   VLAN_INTERFACE="${IFACE}.${VID}"
   OUTPUT=`ip link show ${VLAN_INTERFACE} > /dev/null 2>&1`
   if [ $? -eq 0 ]; then
      echo "VLAN interface ${VLAN_INTERFACE} already exists! Aborting."
      echo "Delete VLAN interface with: ip link del ${VLAN_INTERFACE}"
      exit 1
   fi

   OUTPUT=`which ${COMMAND}`
   if [ $? -ne 0 ] && [ ! -x ${COMMAND} ]; then
      echo "Command ${COMMAND} not found! Aborting."
      exit 1
   fi

}


function setup_talker () {

   # Call python script to do everything and return vlan iface and soprio
   cat >/tmp/call_detd.py << EOF
import sys
import traceback

from detd import StreamConfiguration
from detd import TrafficSpecification
from detd import Interface
from detd import Configuration
from detd import ServiceProxy

interface_name = "$IFACE"
interval = $PERIOD # ns
size = $BYTES      # Bytes

txoffset = $OFFSET # ns
addr = "$ADDRESS"
vid = $VID
pcp = $PCP

stream = StreamConfiguration(addr, vid, pcp, txoffset)
traffic = TrafficSpecification(interval, size)
interface = Interface(interface_name)

config = Configuration(interface, stream, traffic)


# Both Server() and ServiceProxy() point to the same UDS by default
proxy = ServiceProxy()

try:
   vlan_iface, soprio = proxy.add_talker(config)
except:
   traceback.print_exc()
   sys.exit(1)


print("{},{}".format(vlan_iface, soprio))
sys.exit(0)
EOF

   OUTPUT=`python3 /tmp/call_detd.py`
   if [ $? -ne 0 ]; then
      echo "Talker setup failed! Aborting."
      exit 1
   fi

   VIFACE=`echo $OUTPUT | cut -f1 -d','`
   SOPRIO=`echo $OUTPUT | cut -f2 -d','`
   # rm /tmp/detd.py

}


function run_command () {

   # Setup net_prio:rt control group
   if [[ ! -d /sys/fs/cgroup/net_prio ]]; then
      echo "The directory /sys/fs/cgroup/net_prio does not exist"
      echo "Creating directory /sys/fs/cgroup/net_prio"

      mkdir /sys/fs/cgroup/net_prio
   fi

   OUTPUT=`mountpoint /sys/fs/cgroup/net_prio`

   if [ $? -ne 0 ]; then
      echo "Mounting net_prio cgroup at /sys/fs/cgroup/net_prio"
      mount -t cgroup -o net_prio none /sys/fs/cgroup/net_prio
   fi
   mkdir -p /sys/fs/cgroup/net_prio/rt

   # Set socket priority SOPRIO for traffic
   # - Originating from processes belonging to rtnet_prio cgroup
   # - Outgoing on VIFACE
   # E.g.:
   # echo "eth0.3 7" > /sys/fs/cgroup/net_prio/rt/net_prio.ifpriomap
   echo "${VIFACE} ${SOPRIO}" > /sys/fs/cgroup/net_prio/rt/net_prio.ifpriomap

   # Setup cgroups for the application
   # Run command adding it to the net_prio:rt cgroup
   cgexec -g net_prio:rt ${COMMAND} ${ARGS}

}


check_root

parse_args "$@"
check_args
setup_talker
run_command

exit 0
