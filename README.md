# Elfstatsd

A daemon process to aggregate statistics from access logs of different HTTP servers (Apache, Tomcat, Nginx, etc.) for visualizing these data later with monitoring tools ([Munin](http://munin-monitoring.org) is the only tool supported by now). Elfstatsd parses logs in Extended Log Format (ELF) and reports such metrics as number of requests per method, aggregated latencies (min, max, avg, percentiles) per request and response codes. The results are written to files that are updated with each new run of daemon's execution. 

An advantage of this tool over the other existing scripts and utilities for monitoring web servers with access log files is its flexibility that allows to solve a various range of monitoring tasks. Such tasks usually require a lot of configuration effort from network administrators, as a foundation of proper visual monitoring is fine-grained tuning of the tracked requests. Elfstatsd parses the requests found in the access logs and associates them to different categories (later becoming different charts) automatically using simple regex-based rules and provides settings for advanced control over the distribution of requests into groups, if such measures are needed. It works with any ELF-based log file; it is only needed to copy access log format setting from your web server config to elfstasd.

Daemon code is written in Python programming language and requires Python 2.6.x/2.7.x to run. Adding Python 2.4-3.x support is in plans.

In order to display data aggregated by this daemon in Munin, a number of plugins for it are needed. These plugins are distributed separately and are available in [elfstats-munin][] repository. To simplify daemon's installation, you can check out [elfstats-env][] repository containing environment setup for the daemon (RHEL6 OS is only supported so far by elfstats-env).

## Build and install

Unfortunately, the installation procedure is a bit more complicated than usual for Python packages. This happens because elfstatsd is a Linux daemon requiring some more permissions than average Python package does. I did my best to simplify installation as much as possible, and you are welcome to share your thoughts on making it even simpler. However, if you install elfstatsd not from the sources, but from an RPM using [a provided environment][elfstats-env], all you need to do is to install the packages with `yum`.

Elfstatsd is distributed via source code and RPM packages. It is planned to add elfstatsd to PyPi in future. RPM files for RHEL6_x64 can be found in [Releases](https://github.com/dzzh/elfstatsd/releases). Packaging scripts for other POSIX flavors are not yet implemented. Let me know if you are interested in having a package for your OS distribution. Also, if you need in a distribution in a different format, you can build elfstatsd from the sources as explained below.

It is recommended, though not required, to setup [a virtual environment](http://www.virtualenv.org) for running this daemon. An RPM with such an environment set up and ready to go is maintained in [elfstats-env][] repository. If the provided package does not suit you, you can use default Python installation or create a virtual environment yourself. Instructions to do so are provided below. 

### Installing elfstatsd from source codes

* Clone the repository: `git clone https://github.com/dzzh/elfstatsd.git` and enter it with `cd elfstatsd`.

* Switch to the virtual environment by issuing `source /path/to/virtualenv/bin/activate` if you want to use it. If you want to install elfstatsd using your default Python, you can skip this step. Just make sure that your Python version is either 2.6.x or 2.7.x by running `python --version`.

* Install dependencies. Daemon requires a number of other Python modules to operate. They are listed in `requirements.txt` and can easily be installed with [pip](www.pip-installer.org). To do this, install pip and run `pip install -r requirements.txt`. (If you work with the virtual environment, pip is pre-installed there.)

* Install module using its setup script: `python setup.py install`. Daemon will need in write access to `/etc/sysconfig/` for correct installation.

* Run post-install script as a root: `sudo sh scripts/post-install.sh`. This simple script will create directories for internal process logging and `.pid` file storing as well as will perform some other necessary post-installation procedures. 

* If you work with a virtual environment or install elfstatsd to a location different for the default for Python packages, make necessary adjustments to `/etc/sysconfig/elfstatsd` to help the launcher to locate the code.

### Building and installing RPM for RHEL 6

* Clone the repository: `git clone https://github.com/dzzh/elfstatsd.git` and enter it with `cd elfstatsd`.

* If you want the resulting RPM to install elfstatsd to a virtual environment, you have to switch to it with `source /path/to/virtualenv/bin/activate`. To set up such an environment, you can install an RPM from [elfstats-env][] repository. Pre-built RPMs for RHEL6 are available in its [Releases](https://github.com/dzzh/elfstats-env/releases).

* Build RPM: `python setup.py bdist_rpm`. After this step, the RPMs will be put in `dist/` directory.

* Install rpm: `sudo yum install dist/elfstatsd-XX.XX.noarch.rpm`. This RPM can later be installed to the other machines without being re-built, but these machines should have virtual environment located at the same path as at the build machine or have to use default Python with installed dependencies. You can read about installing the dependencies in _Installing elfstatsd from source codes_ section.

* If you work with a virtual environment or install elfstatsd to a location different for the default for Python packages, make necessary adjustments to `/etc/sysconfig/elfstatsd` to help the launcher to locate the code. 

## Configure

Elfstatsd can be configured using `settings.py` file in `elfstatsd` directory. This file contains all the settings supported by the daemon as well as documentation to them. Please refer to the file for more information.

When updating elfstatsd to the newer version, make sure to review the changes in the configuration file. The daemon is in its early development stage, thus full backward compatibility of the settings is not guaranteed. However, all the changes will be documented in the configuration file.

### Rotating log files

Daemon is able to work with log files that rotate in-place or are re-created on schedule and contain timestamps in their file names. Use `DATA_FILES` option in `settings.py` to define any number of log file name templates that you need to process and specify an output file for each of them.

More information about different configuration settings available will follow.

## Run

elfstatsd can be run using a launcher that is installed into `/etc/init.d/elfstatsd`. To start the daemon, run `sudo /etc/init.d/elfstatsd start`; to stop the daemon, run `sudo /etc/init.d/elfstatsd stop`. 

To find location of daemon's main file, the launcher uses a configuration file placed in `/etc/sysconfig/elfstats`. By default, it is assumed that elfstatsd is run using default Python and is located in default place for Python packages. If you work with virtual environment or have elfstatsd installed in a location where Python cannot find it, adjust the settings in `/etc/sysconfig/elfstats` as needed.

When running, daemon needs in write access to the following directories:

* `/tmp`: to store files with aggregated data

* `/var/log/elfstatsd`: for internal logging

* `/var/run/elfstatsd`: for `.pid` file

All of these paths can be changed in `settings.py`. Make sure that a user launching daemon has write access to all of them.

## Test

### Running unit tests:

Elfstatsd uses `py.test` as its testing framework. It is not defined as requirement for a project and you don't need in it to build and run the daemon. However, in case you want to make changes to the code and run the available tests to make sure your changes didn't break the available functionality, you can execute `python setup.py test`. If `py.test` is not installed at your machine, it will be downloaded automatically.


## Data visualization with Munin

To show data aggregated with elfstatsd in Munin, a set of plugins parsing aggregated data and sending it to Munin are needed. These plugins can be installed from [elfstats-munin][] repository.

## Troubleshooting

If you face problems with the daemon, start troubleshooting with inspecting its logs (they are located in `/var/log/elfstatsd` by default). If the logs do not contain any significant information to help you detecting the cause of failures, you may try to run the daemon after changing its stdout and stderr paths in `elfstatsd_daemon.py` from `/dev/null` to `/dev/tty`. This will add console logging for its initial launching stage that is not covered by the internal logging. Also, feel free to contact me or raise an issue if you have a problem you cannot resolve yourself.

## License

Elfstatsd is available under the terms of MIT License.

Copyright © 2013 [Źmicier Žaleźničenka][me] & Andriy Yakovlev.

Developed at [TomTom](http://tomtom.com). Inspired by [Oleg Sigida](http://linkedin.com/in/olegsigida/).

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

[me]: https://github.com/dzzh
[elfstats-munin]: https://github.com/dzzh/elfstats-munin
[elfstats-env]: https://github.com/dzzh/elfstats-env