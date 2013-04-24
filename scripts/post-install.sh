VIRTUALENV_PATH='/srv/virtualenvs/munin'

mkdir /usr/share/munindaemon
mkdir /var/log/munindaemon
mkdir /var/run/munindaemon

source $VIRTUALENV_PATH/bin/activate
packages=`python -c "from distutils.sysconfig import get_python_lib; print get_python_lib()"`

ln -sf $packages/munindaemon/munindaemon.py /usr/share/munindaemon/munindaemon.py

chmod u+x /etc/init.d/munindaemon
chkconfig munindaemon on