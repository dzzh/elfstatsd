**This readme is by far incomplete. I plan to significantly improve the documentation in near future.**

# elfstatsd

A daemon process to aggregate statistics from access logs of different HTTP servers (Apache, Tomcat, Nginx, etc.) for visualizing these data later with [Munin](http://munin-monitoring.org) or similar tools. `elfstatsd` parses logs in Extended Log Format (ELF) and reports such metrics as total number of calls, number of calls per method, aggregated latencies (min, max, avg, percentiles) and response codes. It has a large number of settings that make it a flexible solution for monitoring web servers configured in many different ways.

Daemon code is written at Python programming language and requires Python 2.6 or 2.7 to run. Adding Python 2.4-3.x support is in plans.

In order to display data aggregated by this daemon in Munin, a number of plugins for it are needed. These plugins are distributed separately and will soon be available here at Github.

## Build

### Building the code from sources

This code was originally written for Linux RHEL 6 and contains scripts to build RPMs for this OS. Packaging scripts for other Linux flavors are not yet implemented. Let me know if you are interested in having a package for your Linux version.

It is recommended, though not required, to setup [a virtual environment](http://www.virtualenv.org) to run this daemon. 

#### Common operations

* At first, clone the repository: `git clone https://github.com/dzzh/elfstatsd`.

* Build a source distribution: `cd elfstatsd; python setup.py sdist`. After this step, an archive will be placed in `elfstatsd/dist` directory.

* Extract the distribution at a target machine: `tar xvzf elfstatsd-XX.XX.tar.gz`.

* Switch to the virtual environment by issuing `source /path/to/virtualenv/bin/activate` if you want to use it. If you want to install `elfstatsd` using your default Python, you can skip this step. Just make sure that your Python version is either 2.6.x or 2.7.x by running `python --version`.

* Install dependencies. Daemon requires a number of other Python modules to operate. They are listed in `requirements.txt`. You can easily install all the required modules with [`pip`](www.pip-installer.org). To do this, install pip and run `pip install -r requirements.txt`. (If you work with the virtual environment, pip is pre-installed there.)

#### Building and installing RPM for RHEL 6

* Perform the common operations.

* Build rpm: `python setup.py bdist_rpm`. After this step, an RPM will be put in `elfstatsd/dist` directory.

* Install rpm: `rpm -Uvh dist/elfstatsd-XX.XX.rpm`. This RPM can later be installed to the other machines without being re-built, but these machines should have virtual environment located at the same path as at the build machine or have to use default Python with installed dependencies.


#### Installation from source codes

* Perform the common operations.

* If you do not use a virtual environment, install module using default Python: `cd elfstatsd-XX.XX; python setup.py install`. 

* Run post-install script as root: `sudo sh scripts/post-install.sh`. This script will create directories for internal process logging and `.pid` file storing as well as will perform some other necessary post-installation procedures.

## Run

`elfstatsd` can be run using a launcher that is installed into `/etc/init.d/elfstatsd`. To start the daemon, run `/etc/init.d/elfstatsd start` as root; to stop the daemon, run `/etc/init.d/elfstatsd stop`. 

If you want use elfstatsd with default Python, a path to `elfstatsd` directory containing `elfstatsd.py` file has to be added to your `PYTHONPATH` (e.g. `export PYTHONPATH=$PYTHONPATH:/usr/local/lib/Python2.7/dist-packages`). 

Otherwise, if you use a virtual environment, you have to set `ELFSTATSD_VIRTUALENV_PATH` variable and point it to the root of the environment you had created (e.g. `export ELFSTATSD_VIRTUALENV_PATH=/srv/virtualenvs/munin`).

Daemon needs in write access to the following directories:

* `/tmp`: to store files with aggregated data

* `/var/log/elfstatsd`: for internal logging

* `/var/run/elfstatsd`: for `.pid` file

All of these paths can be re-declared in `settings.py`. Make sure that a user launching daemon has write access to all of them.

## Test

### Running unit tests:

`elfstatsd` uses `py.test` as its testing framework. It is not defined as requirement for a project and you don't need in it to build and run the daemon. However, in case you want to make changes to the code and run the available tests, you can execute `python setup.py test`. If `py.test` is not installed at your machine, it will be downloaded automatically.


## Configuration

`elfstatsd` can be configured using `settings.py` file in `elfstatsd` directory. This file contains all the settings supported by the daemon as well as documentation to them. Please refer to the file for more information.

When updating `elfstatsd` to the newer version, make sure to review the changes in the configuration file. The daemon is in its early development stage, thus full backward compatibility of the settings is not guaranteed. However, all the changes are documented in the configuration file.

### Rotating log files

Daemon is able to work with log files that rotate in-place or are re-created on schedule and contain timestamps in their file names. Use `DATA_FILES` option in `settings.py` to define any number of log file name templates that you need to process and specify an output file for each of them.


## Data visualization with Munin

To show data aggregated with `elfstatsd` in Munin, a set of plugins parsing aggregated data and sending it to Munin are needed. They will be published at Github soon with the integration guide.

## Troubleshooting

If you face problems with the daemon, start troubleshooting with inspecting its logs (`/var/log/elfstatsd` by default). If the logs do not contain any records, you may try to run the daemon after changing its stdout and stderr paths in `elfstatsd_class.py` from `/dev/null` to `/dev/tty`. This will add console logging for its initial launching stage that is not covered by the internal logging. Feel free to contact me or raise an issue if you have a problem you cannot resolve yourself.

## License

`elfstatsd` is available under the terms of MIT License.

Copyright © 2013 [Źmicier Žaleźničenka][me] & Andriy Yakovlev

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