# elfstatsd

A daemon process to aggregate statistics from access logs of different HTTP servers (Apache, Tomcat, Nginx, etc.) for visualizing these data later with [Munin](http://munin-monitoring.org) or similar tools. Elfstatsd parses logs in Extended Log Format (ELF) and reports such metrics as total number of calls, number of calls per method, aggregated latencies and response codes. Has a large number of settings that make it a flexible solution for monitoring web servers configured in many different ways.

Daemon code is written at Python programming language and requires Python 2.6 or 2.7 to run. Migration to Python 3 and addition of Python 2.4+ support are in plans.

## Test, build and run

### Building the code from sources

This code was originally written for Linux RHEL 6 and contains scripts to build RPMs for this OS. Packaging scripts for other Linux flavors are not yet implemented. Let me know if you are interested in having a package for your Linux version.

#### Installation from source codes

It is recommended to setup [a virtual environment](http://www.virtualenv.org) to run this daemon. Procedures to install daemon code with and without this environment will be described later.

#### Building and insalling RPM for RHEL 6

* `cd elfstatsd`

* If you plan to run `elfstatsd` from a virtual environment, switch to it: `source /path/to/virtualenv/bin/activate`

* Build rpm: `python setup.py bdist_rpm`

* Install rpm: `rpm -Uvh dist/elfstatsd-XX.XX.rpm`



### Running unit tests:

Elfstatsd uses `py.test` as its testing framework. It is not defined as requirement for a project and you don't need in it to build the daemon code. However, in case you want to make changes to the code and run the available tests, install `py.test` with `pip install pytest` and run `py.test` from `elfstatsd` directory.

## Configuration

### Rotating log files

Daemon is able to work with log files that rotate in-place or are re-created on schedule and contain timestamps in their file names. Use `DATA_FILES` option in `settings.py` to define any number of log file name templates that you need to process and specify an output file for each of them.


## Data visualization with Munin

To show data aggregated with `elfstatsd` in Munin, a set of plugins parsing aggregated data and sending it to Munin are needed. They will be published at Github soon with the integration guide.

**This readme is incomplete so far. It will be updated soon.**

## License

`elfstatsd` is available under the terms of MIT License.

Copyright © 2013 [Źmicier Žaleźničenka][me]

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