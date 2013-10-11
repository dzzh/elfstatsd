#!/bin/sh
if [ "$1" = 0  ]; then
    /sbin/service elfstatsd stop
    rm -rf /var/log/elfstatsd
    rm -rf /var/run/elfstatsd
    rm -f /etc/sysconfig/elfstatsd
    rm -f /etc/init.d/elfstatsd
fi