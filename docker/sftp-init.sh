#!/bin/sh
set -e

echo "Initializing SFTP writable root..."

mkdir -p /home/sftpuser/s3-root
chown -R sftpuser:users /home/sftpuser/s3-root

echo "SFTP root ready."