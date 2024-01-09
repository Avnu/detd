# Time Sensitive System Service Prototype (detd)

A proof-of-concept for a developer-friendly system service to handle time-sensitive applications.


## Overview

### In a nutshell

This is a prototype of a system service to handle time-sensitive applications
* **Goal**
  * Prototype the interface between time-sensitive applications and the underlying system facilities
* **Non-goal**
  * Provide a production-grade, standard system service for that functionality


### Principles

  * Developer friendliness
    * Serve as enabling vehicle for developer ecosystem discussions
    * Hide implementation specific aspects through a high-level abstraction easy to understand for software developers
    * Decouple time-sensitive applications from platform or device specific aspects

  * Flexibility for experimentation
    * Implemented in Python. Integration with other languages via protobuf messages
    * Provide a clear separation of concerns and being easily extensible
    * Include a unit test and integration test suite
    * Allow for testing on host (i.e. without actual TSN hardware) and target environments


### Current functionality

The following snippet illustrates the add_talker interface:

```python
interface_name = "eth0"
interval = 2 * 1000 * 1000 # ns for 2 ms
size = 1522                 # Bytes

txoffset = 250 * 1000       # ns for 250 us
addr = "7a:b9:ed:d6:d2:12"
vid = 3
pcp = 6


interface = Interface(interface_name)
traffic = TrafficSpecification(interval, size)
stream = StreamConfiguration(addr, vid, pcp, txoffset)

config = Configuration(interface, stream, traffic)


manager = Manager()
manager.add_talker(config)
```

In a little bit more detail:

1. **Takes stream configuration and traffic specification as an input**
    * Interface to use
    * Stream configuration: txoffset, DMAC, VID,PCP
    * Traffic specification: Interval in nanoseconds, Bytes to transmit
2. **Detects and loads the specific network device handler based on the interface name**
3. **Integrates all the inputs and generates the gating schedule**
    * It is able to generate very complex taprio configurations with just the stream and traffic information
4. **Generates the commands implementing that configuration**
    * taprio offload mode supported
5. **Applies the configuration by running the commands**
    * When one of the commands fail, it is able to roll back the previous one to leave the system in a well-known state.
6. **Provides the stream handlers to the caller application**
    * The basic implementation provides the VLAN interface name (e.g. eth0.3) and the socket prio to use to the calling application
    * The plan is to return a fully configured socket. The included client-server example is already implementing part of that flow.

### Currently supported devices

* Intel® Ethernet Controller I225-LM
* Intel® Ethernet Controller I225-IT
* Intel Atom® x6000E Series (Elkhart Lake) integrated TSN controller



### Current limitations

See [Contributing](README.md#contributing) :)

* Only some Intel Ethernet controllers supported
  * Code ready to support additional devices
* Only Linux support
* Only talker streams
* taprio support restricted to offload mode
  * Code ready to support additional qdiscs
* Launch-Time Control not supported
  * E.g. etf qdisc
* Current support for AF_PACKET only
* Very basic local schedule calculation
  * E.g. inter-packet gap not considered, only one traffic class per slot...


## Examples

### Setup a talker from python

The following code will connect to the detd service and configure the specified stream.

```python
from detd import *



def setup_stream_config():

    interface_name = "eno1"
    interval = 20 * 1000 * 1000 # ns
    size = 1522                 # Bytes

    txoffset = 250 * 1000       # ns
    addr = "03:C0:FF:EE:FF:4E"
    vid = 3
    pcp = 6
    interface = Interface(interface_name)
    stream = StreamConfiguration(addr, vid, pcp, txoffset)
    traffic = TrafficSpecification(interval, size)

    config = Configuration(interface, stream, traffic)

    return config




proxy = ServiceProxy()

config = setup_stream_config()
response = proxy.add_talker(config)

print(response)
```

This example adds the talker and then prints the VLAN configured interface and socket priority that the calling application should use to send data through that stream:
```bash
('eno1.3', 7)
```

The behaviour can be inspected in the log file /var/log/detd.log:
```bash
[2022-09-15 18:18:29,608 -     INFO]    detd.service             __init__() -  * * * detd Service starting * * *
[2022-09-15 18:18:29,608 -     INFO]    detd.service             __init__() - Initializing Service
[2022-09-15 18:18:29,609 -     INFO]    detd.manager             __init__() - Initializing Manager
[2022-09-15 18:18:29,609 -     INFO]    detd.service                  run() - Entering Service main loop
[2022-09-15 18:18:34,173 -     INFO]    detd.service                setup() - ============================== REQUEST DISPATCHED ==================================
[2022-09-15 18:18:34,173 -     INFO]    detd.service                setup() - Setting up ServiceRequestHandler
[2022-09-15 18:18:34,173 -     INFO]    detd.service               handle() - Handling request
[2022-09-15 18:18:34,178 -     INFO]    detd.devices             __init__() - Initializing IntelMgbeEhl
[2022-09-15 18:18:34,178 -     INFO]    detd.manager           add_talker() - Adding talker to Manager
[2022-09-15 18:18:34,178 -     INFO]    detd.manager             __init__() - Initializing InterfaceManager
[2022-09-15 18:18:34,178 -     INFO]    detd.mapping             __init__() - Initializing Mapping
[2022-09-15 18:18:34,179 -     INFO] detd.systemconf             __init__() - Initializing SystemConfigurator
[2022-09-15 18:18:34,179 -     INFO]  detd.scheduler             __init__() - Initializing Scheduler
[2022-09-15 18:18:34,179 -     INFO]    detd.manager           add_talker() - Adding talker to InterfaceManager
[2022-09-15 18:18:34,179 -     INFO]    detd.mapping       assign_and_map() - Assigning and mapping resources
[2022-09-15 18:18:34,179 -     INFO]  detd.scheduler                  add() - Adding traffic to schedule
[2022-09-15 18:18:34,179 -     INFO] detd.systemconf                setup() - Setting up platform and devices
```

detd code uses high level constructs. Only in the final step it translates to specific command calls. For the example above, such commands would be:
```
tc qdisc replace
         dev       eno1
         parent    root
         taprio
         num_tc    2
         map       0 0 0 0 0 0 0 1 0 0 0 0 0 0 0
         queues    1@0 1@1 1@2 1@3 1@4 1@5 1@6 1@7
         base-time <now + 2 cycles>
         sched-entry S 01 250000
         sched-entry S 02 12176
         sched-entry S 01 19737824
         flags     0x2


ip link add
        link     eno1
        name     eno1.3
        type     vlan
        protocol 802.1Q
        id       3
        egress   0:0 1:1 2:2 3:3 4:4 5:5 6:7 7:7


ethtool --set-eee eth0 eee off
```




### Setup a talker stream for an arbitrary command, using a script that calls detd functions

The script [setup_qos.sh](./setup_qos.sh) allows for quick experimentation without modifying an existing application.

It performs the configuration using detd commands, as in the first example.

Then it uses the cgroup net_prio to automatically map the egress traffic from the command to a given socket prio. So all the queuing disciplines and PCP mapping in place works properly.

Example:
```bash
# 2ms period, 1522 bytes, TxOffset 250 microseconds, interface eth0
# stream DMAC AB:CD:EF:FE:DC:BA, stream VID 3, stream PCP 6
# Command: ping 8.8.8.8 for one second (Busybox's ping)

./setup_qos.sh --period 2000000 --bytes 1522 --offset 250000 --interface eth0 \
               --address AB:CD:EF:FE:DC:BA --vid 3 --pcp 6 \
               -- ping -w 1 8.8.8.8

```




### Setup a talker stream using detd functions from python

Although it is not the intended use case, you could also call the detd classes from ad-hoc applications. Please note that in this case there is no connection to any service.

```python
interface_name = "eth0"
interval = 20 * 1000 * 1000 # ns for 20 ms
size = 1522                 # Bytes

txoffset = 250 * 1000       # ns for 250 us
addr = "7a:b9:ed:d6:d2:12"
vid = 3
pcp = 6


interface = Interface(interface_name)
traffic = TrafficSpecification(interval, size)
stream = StreamConfiguration(addr, vid, pcp, txoffset)

config = Configuration(interface, stream, traffic)


manager = Manager()
manager.add_talker(config)
```

The only relevant change in the code above is using the class Manager instead of ServiceProxy to add the talker.




## Regression testing


### Test environments

By default, calls to system commands are mocked, so almost every code path can be exercised without TSN target hardware.

The test environment is controlled by the following environment variable.
```bash
DETD_TESTENV
```

Host testing is configured by default inside the test suite.

To override the default and setup target testing (e.g. calling actual commands):
```bash
DETD_TESTENV=TARGET
```

For integration testing, the service is spawned as a different process. This prevents regular use of patch. Hence, the Server class accepts a parameter test_mode, that when set to True will patch the required methods in order to maximize coverage. This is automatically performed when running the unittests.


### Test the example "Setup a talker stream using detd functions from python"

* With host test environment
  * Intended to be use during development to test most of the code paths on the development host
  * Does not require actual TSN hardware or the availability of the underlying system commands
    ```bash
    python3 -m unittest tests.test_manager
    ```

* With target test environment
  * Actual commands are issued to the OS
  * Requires real hardware and system environment
    ```bash
    DETD_TESTENV=TARGET python3 -m unittest tests.test_manager
    ```

### Run the complete test suite

Integration tests include a client-server example in python.

Run all unit and integration tests in the development host test environment:
```bash
python3 -m unittest discover
```

A convenience script [test.sh](detd/test.sh) is included in the detd directory, that basically runs the above command:
```bash
cd detd
./test.sh
```


## Getting involved

### Installation

* Runtime dependencies (Debian / Ubuntu)
  * ethtool
  * iproute2
  * python3-protobuf
  * python3
  * cgroup-tools (Optional)

* Build dependencies (Debian / Ubuntu)
  * protobuf-compiler
  * python3-all
  * python3-protobuf
  * python3-setuptools

* Packaging dependencies (Debian / Ubuntu)
  * debmake
  * debhelper-compat
  * dh-python


#### deb package

A convenience script [package_debian.sh](tools/package_debian.sh) is provided to generate a deb file for easier installation on Debian-based distributions. It generates a deb file and stores it in /tmp.

```bash
cd tools
./package_debian.sh
apt install /tmp/detd_*deb
```

Upon installation, the service is started by systemd, with logging redirected to /var/log/detd.log:
```bash
tail /var/log/detd.log
[2022-09-14 23:02:28,780 -     INFO]    detd.service             __init__() -  * * * detd Service starting * * *
[2022-09-14 23:02:28,780 -     INFO]    detd.service             __init__() - Initializing Service
[2022-09-14 23:02:28,780 -     INFO]    detd.manager             __init__() - Initializing Manager
[2022-09-14 23:02:28,780 -     INFO]    detd.service                  run() - Entering Service main loop
```

At this point the service is ready to receive requests.


#### Docker

To avoid installing all build dependencies locally, you can also use Docker for building the Debian package:

```
docker build -f tools/Dockerfile . -t detd_builder
docker run --name detd_build_container detd_builder
docker cp detd_build_container:/tmp/detd_0.1.dev0-1_all.deb ./
docker rm detd_build_container
```

#### pip

The release process and security checks for the current release were conducted over the following specific versions:
* python 3.8.10
* python-protobuf 3.6.1.3

To install:
```bash
git clone https://github.com/Avnu/detd.git
cd detd
python3 setup.py bdist_wheel
# Uninstall in case a previous version is there
# We install detd system wide
sudo pip3 uninstall detd
sudo pip3 install dist/detd-*.whl
sudo pip3 show detd
```

Optionally, you may want to run the test suite on host to make sure everything is in place:
```bash
python3 -m unittest discover
.....................................ss
----------------------------------------------------------------------
Ran 39 tests in 1.458s

OK (skipped=2)
```


### Contributing

**Junior tasks**

* Linux integration
  * RPM packaging
  * Add UDS ownership and permissions to packaging and documentation

* Developer Experience
  * "detd-in-a-container"
    * Containerize detd, and its associated dependencies, and offer the UDS interface to the host
    * E.g. allow to use more recent ethtool versions to configure Qbu, integrate with more recent LinuxPTP versions, etc
  * Make setup_qos.sh interface more compact
    * Instead of --address AB:CD:EF:FE:DC:BA --vid 3 --pcp 6
    * Use --stream AB:CD:EF:FE:DC:BA/3/6 and parse inside the string
  * Specialized diagnostics exception when initial configuration fails
    * Providing information about "usual suspects" in a consolidated way. E.g. time synch offsets.

* System integration
  * Rename QdiscConfigurator as NetworkQosConfigurator
  * Add Linux class providing Linux-specific operations that do not rely on a specialized system command. E.g. get_pci_id that currently relies on /sys.
  * Add support for taprio "pure software mode" in CommandTc, plus unit tests
  * Add support for taprio "txtime-assist" mode (aka txtime offload mode) in CommandTc, plus unit tests

* Device support
  * Add more constraints to the device specific checks
    * E.g. maximum cycle or slot lengths for the schedule checks.
  * Autodetect the number of Tx and Rx queues
    * So we can remove that from the device support class
  * Autodetect the availability of independent Tx and Rx channels
    * So we can remove that from the device support class
  * Split device features into rx_features and tx_features
    * So e.g. only tx_features are applied when setting up the talker
  * Add i226 support
    * For guidance and examples, please refer to [detd.devices](detd/devices/__init__.py) package documentation
  * Add support for more devices
  * Generic device support
    * E.g. just fall-back to software taprio and etf. Depends on launch-time support

* Code Quality
  * Improve pep8 style compliance
  * Use class methods in command abstraction classes (e.g. CommandEthtool)
    * E.g. simpler caller code


**Other improvements**

* Linux integration
  * Add D-BUS interface
  * Evaluate using netlink for consideration instead of e.g. just calling tc
    * E.g. a programmatic interface could improve aspects like error handling, security, etc, and could make parts of the code simpler by removing all the portions devoted to templating commands
  * XDP support
    * Dependencies with listener stream and launch-time control support items below

* Developer Experience
  * Add C library implementing protobuf interaction
    * This will make integration with C applications straighforward
    * The python3 implementation can be used as an example
  * Add profiles
    * A layer on top of the basic interface that further elevates the level of abstraction
    * E.g. IEC/IEEE 60802, 61850... that provide the right mappings abstracting the developers from that
  * Make the implementation strategies configurable
    * An implementation strategy maps traffic types to backends like mapping a time-aware stream to launch-time + Qbv, launch-time + Qbu, etc
    * detd would offer the most sane default, but still allow to override it
  * Cover basic interaction with TSN network configuration mechanisms
    * E.g. start enabling to load the configuration from a text file
  * Add diagnostics mode
    * Retrieve and collect runtime information about time synchronization, qdisc errors, etc

* System integration
  * Add launch-time control support
  * Integrate time-synchronization
    * When a time-aware stream is requested, check if time synchronization is running and otherwise start it and initialize to the right operation values
  * Integrate LLDP
  * Improve platform independence
    * Further separation of generic and platform specific details (e.g. subclassing per OS or platform)

* Device support
  * Add support for more devices
    * For guidance and examples, please refer to [detd.devices](detd/devices/__init__.py) package documentation
  * Add listener stream setup
    * VLAN tag configuration
    * DMAC subscription
    * tc and ethtool configuration

* Port PoCs
  * E.g. to VxWorks, or via MicroPython to FreeRTOS, Zephyr...
