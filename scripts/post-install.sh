#!/bin/sh
mkdir -p /var/log/elfstatsd
mkdir -p /var/run/elfstatsd

chmod +x /etc/init.d/elfstatsd
chkconfig elfstatsd on