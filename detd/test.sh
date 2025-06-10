#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine
#
# ./test.sh
#
# Generates the protobuf code based in the ipc.proto declaration, runs the unit
# tests and deletes the generated code.

protoc ipc.proto --python_out=.
if [ "$#" -eq 0 ]; then
   python3 -m unittest discover .. --verbose
elif [ "$#" -eq 1 ]; then
   cd ..
   python3 -m unittest "$1" --verbose
   cd -
else
   echo "Usage: $0 [unit test to execute]"
fi
rm ipc_pb2.py

echo -e "\nUnit testing logs available in detd-server-unittest.log"
