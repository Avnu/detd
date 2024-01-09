#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Copyright(C) 2022 Intel Corporation
# Authors:
#   Hector Blanco Alcaine
#
# ./package_debian.sh
#
# Generates a rudimentary deb package to facilitate installations on Debian
# based distributions. The package is then copied to /tmp

set -e # exit early on errors

function usage () {
   echo "Usage:"
   echo "$0"
}



function parse_args () {

   # Check the number of arguments supplied
   if [ $# -gt 0  ]; then
      echo "Wrong number of arguments"
      usage
      exit 1
   fi

}


function check_args () {
   # Placeholder
   :
}


function create_deb () {

	cd ..


	# Create the source distribution
	python3 setup.py sdist


	# Replicate the id generated for the source distribution tarball
	# E.g. detd-0.1.dev0 (PKG: detd, VERSION: 0.1.dev0)
	PKG=$(awk '/^name/{print $3}' ./setup.cfg)
	VERSION=$(awk '/^version/{print $3}' ./setup.cfg)
	REVISION=1
	ID="${PKG}-${VERSION}"


	# Create a tempdir and extract the package there
	TMPDIR=`mktemp -d --suffix=.detd`
	cp dist/${ID}.tar.gz ${TMPDIR}
	cp detd/detd.service ${TMPDIR}
	tar xvzf ${TMPDIR}/${ID}.tar.gz -C ${TMPDIR}


	# Generate and customize the debian directory
	cd ${TMPDIR}/${ID}
	debmake --binaryspec ':py3' --email ${EMAIL} --fullname ${FULLNAME} --spec --revision ${REVISION}

	ARCHITECTURE=`grep -Po 'Architecture: \K\S+' debian/control`

	cp ${TMPDIR}/detd.service debian/

	sed -i 's/^Section:[^$]*$/Section: Networking/' debian/control
	sed -i 's/^Homepage:[^$]*$/Homepage\: https\:\/\/github.com\/Avnu\/detd/' debian/control
	sed -i 's/^X-Python3-Version:[^$]*$/X-Python3-Version: >= 3.8/' debian/control
	sed -i 's/^Build-Depends:\([^,]*\),$/Build-Depends: protobuf-compiler,\n              \1,/' debian/control
	sed -i 's/^Build-Depends:\([^,]*\),$/Build-Depends: dh-systemd,\n              \1,/' debian/control
	sed -i 's/^Depends:\(.*\)/Depends: iproute2,\n        \1/' debian/control
	sed -i 's/^Depends:\(.*\)/Depends: ethtool,\n        \1/' debian/control
	sed -i '/^Description:.*/i Recommends: cgroup-tools' debian/control

	echo -e "\tdh_installsystemd" >> debian/rules
	# Restart detd when the application is upgraded
	echo -e "\noverride_dh_installsystemd:\n\tdh_installsystemd --restart-after-upgrade" >> debian/rules
	# Force xz for compression, to prevent installation issues with Zstandard
	echo -e "\noverride_dh_builddeb:\n\tdh_builddeb -- -Zxz" >> debian/rules

	# Generate the deb, make it available and perform clean-up
	fakeroot debian/rules binary
	FILENAME=${PKG}_${VERSION}-${REVISION}_${ARCHITECTURE}.deb
	dpkg --contents ../${FILENAME}
	dpkg -I ../${FILENAME}
	cp ../${FILENAME} /tmp
	echo "The deb package is now available at /tmp/${FILENAME}"

	rm -rf ${TMPDIR}

}


# Customize name and email for the maintainer fields
EMAIL="foo@bar"
FULLNAME="Foobar"

parse_args "$@"
check_args

create_deb


exit 0
