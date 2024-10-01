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
python3 -m unittest discover .. --verbose
rm ipc_pb2.py
