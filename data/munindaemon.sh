#! /bin/bash
#
# /etc/init.d/munindaemon
#
### BEGIN INIT INFO
# Provides: munindaemon
# Required-Start:
# Should-Start:
# Required-Stop:
# Should-Stop:
# Default-Start:  3 5
# Default-Stop:   0 1 2 6
# Short-Description: TomTom munin plugin daemon process
# Description:    Runs up the munindaemon process
### END INIT INFO

# Activate the python virtual environment
. /path_to_virtualenv/activate

case "$1" in
  start)
    echo "Starting server"
    # Start the daemon
    python /usr/share/munindaemon/munindaemon.py start
    ;;
  stop)
    echo "Stopping server"
    # Stop the daemon
    python /usr/share/munindaemon/munindaemon.py stop
    ;;
  restart)
    echo "Restarting server"
    python /usr/share/munindaemon/munindaemon.py restart
    ;;
  *)
    # Refuse to do other stuff
    echo "Usage: /etc/init.d/munindaemon.sh {start|stop|restart}"
    exit 1
    ;;
esac

exit 0