# detd target test automation

This framework allows to automate:
* Deployment detd deb packages to talker and listener nodes
* Deployment of test talker and listener applications to talker and listener nodes
* Execution of the tests on the target talker and listener hardware
* Retrieval of experiment results and other output from talker and listener nodes


## Quick start guide

* Prepare detd package to install on the talker and listener nodes
  * Generate the deb package with the build system
  * Copy the deb file into the files directory
  * If the name differs from detd_0.1.dev0-1_all.deb, update the relevant files

* Edit run_p2ptest.sh, updating at least:
  * IP addresses for your target machines

 * Execute the script

Examples:
```bash
# To deploy the deb package, test files, run the test and retrieve the results
./run_p2ptest.sh

# To deploy the deb package and test files
./run_p2ptest.sh deploy

# To run the test and retrieve the results (after having deployed)
./run_p2ptest.sh test
```

The relevant logs will be stored in the host machine in the FETCH_DEST, e.g.:
```bash
~/detd_p2ptest/listener_node/var/log/detd.log
~/detd_p2ptest/talker_node/var/log/detd.log
```

The listener end will generate a file in the DEST directory with the NIC
timestamps for all the frames received. E.g.:

```bash
~/detd_p2ptest$ cat listener.txt
1727871741665368341
1727871741685368283
1727871741705368225

. . .

```

The timestamps can be used to generate several visualizations for the
experiments.


## Using target test script without remote automation

The execute_detd.sh script can also be used directly on target, instead of
through Ansible remote execution.

For example, a listener test can be started by calling:

```bash
$ ./execute_detd.sh listener enp2s0
```

Then execute the talker side:

```bash
$ ./execute_detd.sh talker enp1s0
```

The listener implements a timeout if no frame is received within that period.
Therefore, the execution of the talker should not be delayed too much.


## To-Do

* Check FIXMEs
* Allow to configure all the parameters from the ansible script
