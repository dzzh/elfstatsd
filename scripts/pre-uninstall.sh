#!/bin/sh
if [ "$1" = 0  ]; then
    /sbin/service elfstatsd stop
    rm -rf /var/log/elfstatsd
    rm -rf /var/run/elfstatsd
    rm /var/sysconfig/elfstatsd
fi