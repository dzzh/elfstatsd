import logging
import re

APACHE_LOG_FORMAT = r'%h %l %u %t \"%r\" %>s %B \"%{Referer}i\" \"%{User-Agent}i\" %{JK_LB_FIRST_NAME}n %{JK_LB_LAST_NAME}n %{JK_LB_LAST_STATE}n %I %O %D'

DAEMON_DIR = '/usr/share/munindaemon'
DAEMON_PID_DIR = '/var/run/munindaemon'
DAEMON_LOG_DIR = '/var/log/munindaemon'

#Time interval in seconds between two daemon invocations
INTERVAL = 300

#Value in milliseconds to consider a call stalled and report it additionally
STALLED_CALL_THRESHOLD = 4000

#A list of tuples containing input and output data files
DATA_FILES = [
    ('/srv/log/httpd/community.access.log-%Y-%m-%d-%H', '/tmp/munindaemon-community.data'),
    ('/srv/log/httpd/csharing.access.log-%Y-%m-%d-%H', '/tmp/munindaemon-csharing.data'),
]

#List of regular expressions to be matched when parsing the request. Each expression should contain
#'group' and 'method' named groups that will be parsed and displayed in Munin.
#Example: for /content/csl/activation request that is checked against r'^/content/(?P<group>\w+)/(?P<method>\w+)[/?%&]',
# you will get 'csl' as group, 'activation' as method name.
VALID_REQUESTS = [
    re.compile(r'^/content/(?P<group>\w+)/(?P<method>\w+)[/?%&]?'),
                 ]

#Symbols to be removed from method names (Munin cannot process them in field names)
BAD_SYMBOLS = re.compile(r'[.-]')

#Response codes to track in all rounds, even if they are not found in logs
RESPONSE_CODES = [200, 404, 500]

#Maximum size of a single log file, in bytes
MAX_LOG_FILE_SIZE=10000000

#Maximum number of log files to keep
MAX_LOG_FILES=5

#Maximun number of calls in traceback
TRACEBACK_LENGTH=5

LOGGING_LEVEL = logging.INFO