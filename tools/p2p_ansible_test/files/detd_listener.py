import argparse
import subprocess
from detd import *

def clean_up(package_name):
    """
    Clean up the system and then re-install a specified .deb package.
    """
    commands = [
        f"sudo apt purge -y detd",
        f"sudo apt install ./{package_name}"
    ]

    for cmd in commands:
        try:
            subprocess.run(cmd.split(), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            print(f"Failed to execute: {cmd}\nError: {e.stderr.decode().strip()}")

def setup_stream_config(interface_name, interval_ns, size_bytes, txoffset_ns, addr, vid, pcp, maddress):
    """
    Set up the stream configuration.
    """
    interface = Interface(interface_name)
    stream = StreamConfiguration(addr, vid, pcp, txoffset_ns)
    traffic = TrafficSpecification(interval_ns, size_bytes)

    # Test Default Hints 
    hints = None

    config = ListenerConfiguration(interface, stream, traffic, maddress, hints)
    return config

def add_listener_to_proxy(proxy, config):
    """
    Add a listener to the service proxy.
    """
    response = proxy.add_listener(config)
    return response

def configure_and_add_listener(interface_name, txoffset_ns):
    """
    Configure and add a listener using the given interface name and txoffset_ns.
    """
    # Configuration parameters
    interval_ns = 20 * 1000 * 1000 # ns
    size_bytes= 1522                 # Bytes

    addr = "03:C0:FF:EE:FF:4E"
    vid = 3
    pcp = 6
    maddress = "00:C0:FF:EE:FF:4E"

    # Create a service proxy instance
    proxy = ServiceProxy()

    # Set up the stream configuration
    config = setup_stream_config(interface_name, interval_ns, size_bytes, txoffset_ns, addr, vid, pcp, maddress)

    # Add the listener to the service proxy and return the response
    response = add_listener_to_proxy(proxy, config)
    return response

def main():
    """
    Main function to parse command line arguments and add a talker.
    """
    parser = argparse.ArgumentParser(description='Configure and add a listener to the network.')
    parser.add_argument('interface_name', type=str, help='Name of the network interface to use')
    parser.add_argument('package_name', type=str, help='Name of the .deb package to install after cleanup')
    args = parser.parse_args()

    # Clean up previous runs
    clean_up(args.package_name)

    # Test 0 offset
    txoffset_ns = 0
    response = configure_and_add_listener(args.interface_name, txoffset_ns)
    print(response)


# Call the main function
if __name__ == "__main__":
    main()
