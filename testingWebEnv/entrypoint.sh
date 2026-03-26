#!/bin/sh

# Generate SSH host keys if they don't exist
ssh-keygen -A

# Start SSH daemon in the background
/usr/sbin/sshd

# Start Nginx in the foreground
nginx -g "daemon off;"
