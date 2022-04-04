#!/usr/bin/env python3

from setuptools import setup
import setuptools.command.build_py
from distutils.spawn import find_executable
import subprocess
from subprocess import check_call




proto = 'detd/ipc.proto'

class OverrideBuildPy(setuptools.command.build_py.build_py):


    def run(self):
        self.gen_stub(proto)
        setuptools.command.build_py.build_py.run(self)


    def gen_stub(self, proto):

        protoc = find_executable("protoc")
        if protoc == None:
            raise FileNotFoundError(errno.ENOENT, "protoc not found")

        cmd = [ protoc, proto, "--python_out=." ]
        subprocess.check_call(cmd)




setup(
    cmdclass = { 'build_py': OverrideBuildPy }
)
