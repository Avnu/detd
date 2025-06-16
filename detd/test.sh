#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine
#
# ./test.sh [PATTERN]
#
# Generates the protobuf code based in the ipc.proto declaration, runs the unit
# tests and deletes the generated code.

if [ "$#" -gt 1 ]; then
   echo "Usage: $0 [unit test to execute]"
   exit 0
fi

PATTERN=""
if [ "$#" -eq 1 ]; then
   PATTERN="-k $1"
fi

protoc ipc.proto --python_out=.
python3 -m unittest discover .. --verbose ${PATTERN}
rm ipc_pb2.py

echo -e "\nUnit testing logs available in detd-unittest.log"
