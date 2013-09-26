import logging
import re

APACHE_LOG_FORMAT = r'%h %l %u %t \"%r\" %>s %B \"%{Referer}i\" \"%{User-Agent}i\" %{JK_LB_FIRST_NAME}n %{JK_LB_LAST_NAME}n %{JK_LB_LAST_STATE}n %I %O %D'

DAEMON_DIR = '/usr/share/elfstatsd'
DAEMON_PID_DIR = '/var/run/elfstatsd'
DAEMON_LOG_DIR = '/var/log/elfstatsd'

# Time interval in seconds between two daemon invocations
INTERVAL = 300

# Value in milliseconds to consider a call stalled and report it additionally
STALLED_CALL_THRESHOLD = 4000

# A list of tuples containing input and output data files
DATA_FILES = [
    ('/srv/log/httpd/community.access.log-%Y-%m-%d-%H', '/tmp/elfstatsd-community.data'),
    ('/srv/log/httpd/csharing.access.log-%Y-%m-%d-%H', '/tmp/elfstatsd-csharing.data'),
    ]

# List of regular expressions to be matched when parsing the request. Each expression should contain
# 'method' named group and optionally 'group' named group that will be parsed and displayed in Munin.
# Example: for /content/csl/activation request that is checked against r'^/content/(?P<group>\w+)/(?P<method>\w+)[/?%&]',
# you will get 'csl' as group, 'activation' as method name.
# Methods without group are put into 'nogroup' group.
# As soon as first match is found, matching process stops.
VALID_REQUESTS = [
    re.compile(r'^/content/(?P<group>[\w.]+)/(?P<method>\w+)[/?%&]?'),
    re.compile(r'^/content/(?P<method>[\w.]+)[/?%&]?'),
    ]

# Requests matching at least one of regexes in this list are not reflected in statistics and logs.
# Only requests that did not pass VALID_REQUESTS validation are tested here. If a request is considered
# valid after getting through VALID_REQUESTS, it is never checked against this list.
REQUESTS_TO_SKIP = [
    re.compile(r'^/$'),
    re.compile(r'^/helloloadbalancer'),
    ]

# Additional aggregation for valid requests for more flexibility.
# After a request matches a regex in VALID_REQUESTS and is considered valid,
# it gets through this list of regexes and if it matches any, its group and method name initially derived from URL
# by VALID_REQUEST regex, are discarded and replaced with this values
# Records are tuples in form (group, method, regex)
REQUESTS_AGGREGATION = [
    ('group', 'method', re.compile(r'')),
    ]

# Symbols to be removed from method names (Munin cannot process them in field names)
BAD_SYMBOLS = re.compile(r'[.-]')

# Response codes to track in all rounds, even if they are not found in logs
RESPONSE_CODES = [200, 404, 500]

# Maximum size of a single log file, in bytes
MAX_LOG_FILE_SIZE=10000000

# Maximum number of log files to keep (meaning log files reporting about elfstatsd state, not target logs to be parsed)
MAX_LOG_FILES = 5

# Maximal number of calls in traceback
TRACEBACK_LENGTH = 5

LOGGING_LEVEL = logging.INFO