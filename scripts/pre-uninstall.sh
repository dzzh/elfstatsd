if [ "$1" = 0  ]; then
/sbin/service munindaemon stop
rm -rf /var/log/munindaemon
rm -rf /var/run/munindaemon
fi