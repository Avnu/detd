#!/bin/bash

# Define variables
# Define the location on remote for scripts and binaries to be copied.
TALKER_DEST="/home/kamber/ans_talker"
LISTENER_DEST="/home/kamber/ans_listener"
# Define the location on the host for logs to be copied.
FETCH_DEST="/home/kamber/"

# Define inventory variables
# Remote IP addresses.
SERVER1_HOST="172.28.240.76"
SERVER2_HOST="172.28.240.78"
# Remote user-name.
ANSIBLE_USER=""
# Remote login password.
ANSIBLE_PASSWORD=""
# Remote sudo password.
ANSIBLE_BECOME_PASSWORD=""

# Generate a temporary inventory file with the dynamic variables
cat > temp_inventory.ini <<EOF
[server_talker]
server1 ansible_host=$SERVER1_HOST ansible_user=$ANSIBLE_USER ansible_password=$ANSIBLE_PASSWORD ansible_become_password=$ANSIBLE_BECOME_PASSWORD

[server_listener]
server2 ansible_host=$SERVER2_HOST ansible_user=$ANSIBLE_USER ansible_password=$ANSIBLE_PASSWORD ansible_become_password=$ANSIBLE_BECOME_PASSWORD
EOF

# Run the Ansible playbook with the temporary inventory file and defined variables
ansible-playbook -i temp_inventory.ini playbook.yml \
  --extra-vars "talker_dest=$TALKER_DEST listener_dest=$LISTENER_DEST fetch_dest=$FETCH_DEST"

# Clean up the temporary inventory file
rm -f temp_inventory.ini
