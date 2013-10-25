import logging
import re

ELF_FORMAT = r'%h %l %u %t \"%r\" %>s %B \"%{Referer}i\" \"%{User-Agent}i\" %{JK_LB_FIRST_NAME}n %{JK_LB_LAST_NAME}n %{JK_LB_LAST_STATE}n %I %O %D'

DAEMON_PID_DIR = '/var/run/elfstatsd'
DAEMON_LOG_DIR = '/var/log/elfstatsd'

# Time interval in seconds between two daemon invocations
INTERVAL = 300

# If latency in milliseconds exceeds this value, a call is considered stalled and is reported in an additional metric.
STALLED_CALL_THRESHOLD = 4000

# A list of tuples containing input and output data files
# The first element - path to the file with actual access log. May contain date and time specification,
# you should define them in Python datetime format then.
# The second element - path to the file with previous part of the log. Is only used when the logs are rotated
# in-place. This setting is not taking into account if the log file names are generated using datetime parameters.
# If this setting is omitted for in-place rotating logs, some records in the end of file may be not processed by daemon.
# The third element - path to a file where you want to store aggregated data.
# Munin plugins should read and parse this file.
#
# Example:
# DATA_FILES = [
#     ('/srv/log/httpd/apache.access.log-%Y-%m-%d-%H', '', '/tmp/elfstatsd-apache.data'),
#     ('/srv/log/httpd/tomcat.log', 'tomcat.1.log', '/tmp/elfstatsd-tomcat.data'),
# ]
DATA_FILES = []

# List of regular expressions to be matched when parsing the request. Each expression should contain
# 'method' named group and optionally 'group' named group that will be parsed and displayed in Munin.
# Example: for '/content/service/call' req. that is checked against r'^/content/(?P<group>\w+)/(?P<method>\w+)[/?%&]',
# you will get 'service' as group, 'call' as method name.
# Methods without group are put into 'nogroup' group.
# As soon as first match is found, matching stops.
#
# Example:
# VALID_REQUESTS = [
#     re.compile(r'^/content/(?P<group>[\w.]+)/(?P<method>[\w.]+)[/?%&]?'),
#     re.compile(r'^/content/(?P<method>[\w.]+)[/?%&]?'),
# ]
VALID_REQUESTS = [
    re.compile(r'^/(?P<group>[\w.]+)/(?P<method>[\w.]+)/[/?%&]?'),
    re.compile(r'^/(?P<method>[\w.]+)/[/?%&]?'),
]

# Requests matching at least one of regexes in this list are not reflected in statistics and logs.
# Only requests that did not pass VALID_REQUESTS validation are tested here. If a request is considered
# valid after getting through VALID_REQUESTS, it is never checked against this list.
#
# Example:
# REQUESTS_TO_SKIP = [
#   re.compile(r'^/$'),
#   re.compile(r'^/skip'),
# ]
REQUESTS_TO_SKIP = []

# Additional aggregation for valid requests for more flexibility.
# After a request matches a regex in VALID_REQUESTS and is considered valid,
# it gets through this list of regexes and if it matches any, its group and method name initially derived from URL
# by VALID_REQUEST regex, are discarded and replaced with this values
# Records are tuples in form (group, method, regex)
#
# Example:
# REQUESTS_AGGREGATION = [
#     ('group', 'method', re.compile(r'/service/call/to/aggregate')),
#     ]
REQUESTS_AGGREGATION = []

# Symbols to be removed from method names (Munin cannot process them in field names)
FORBIDDEN_SYMBOLS = re.compile(r'[.-]')

# Response codes to track in all rounds, even if they are not found in logs
RESPONSE_CODES = [200, 404, 500]

# Apache and most other servers write logs with latencies in microseconds (10^-6).
# Tomcat, however, works with milliseconds (10^-3). This setting specifies what latency
# resolution is used. If set to False, microseconds are assumed, otherwise milliseconds.
LATENCY_IN_MILLISECONDS = False

#List of percentiles to be calculated for the requests' latencies. A list of int entries with values between 0 and 100.
LATENCY_PERCENTILES = [50, 90, 99]

#
# Settings for internal logging
#

# Maximum size of a single log file, in bytes
MAX_LOG_FILE_SIZE = 10000000

# Maximum number of log files to keep (meaning log files reporting about elfstatsd state, not target logs to be parsed)
MAX_LOG_FILES = 5

# Maximal number of calls in traceback
TRACEBACK_LENGTH = 5

LOGGING_LEVEL = logging.INFO