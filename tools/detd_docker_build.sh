#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2024 Intel Corporation
# Authors:
#   Kumar Amber
#
# ./detd_docker_build.sh
#
# Script automates the detd build in a container, then
# copies the .deb package back to the host.

IMAGE_NAME="detd_builder"
CONTAINER_NAME="detd_build_container"
DEB_DIRECTORY="/tmp/detd"

# Temporary folder to copy data to container
# Due to security access reasons, the ADD command is not able to access any other folder.
# Please make sure to use the same folder in the ADD command in the Dockerfile.

TMP_DIRECTORY="tmp_detd"

function build_detd_deb {


    # Clean up old directory
    rm -rf $TMP_DIRECTORY
    # Copy detd to local folder
    echo "Copying detd to $TMP_DIRECTORY"
    rsync -av --exclude 'tmp_detd' ../ $TMP_DIRECTORY

    # Build Docker image.
    echo "Building Docker"
    docker build -f Dockerfile . -t $IMAGE_NAME

    # Run the container.
    echo "Container run"
    docker run --name $CONTAINER_NAME $IMAGE_NAME


    # Clean-up files from previous runs.
    echo "Cleaning up previous outputs"
    rm -f $DEB_DIRECTORY/*.deb

    # Copy build .deb file to host.
    echo "Copying Debian package from container to host"
    docker cp $CONTAINER_NAME:/tmp/ $DEB_DIRECTORY

    # Clean up container and temporary detd folder.
    echo "Removing Docker container"
    docker rm $CONTAINER_NAME
    echo "Debian package located in $DEB_DIRECTORY"
    rm -rf $TMP_DIRECTORY
}

build_detd_deb
