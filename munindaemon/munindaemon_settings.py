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

#Only the requests matching this regex qualify for further processing
VALID_REQUEST = re.compile('^/content/')

#After the request is retrieved, it is split by slash symbol and the groupings are put into a list.
#Specify the proper indices of the list to derive method group location (each group has own chart)
#and method name location (a line in the chart of the respective group) in the list.
#
#Example: for /content/csl/activation request with METHOD_GROUP_INDEX=2, METHOD_NAME_INDEX=3 you will get
# 'csl' as method group, 'activation' as method name.
METHOD_GROUP_INDEX = 2
METHOD_NAME_INDEX = 3

#Symbols to be removed from method names (Munin cannot process them in field names)
BAD_SYMBOLS = re.compile('[.-]')

#Response codes to track in all rounds, even if they are not found in logs
RESPONSE_CODES = [200,404,500]

#Maximum size of a single log file, in bytes
MAX_LOG_FILE_SIZE=10000000

#Maximum number of log files to keep
MAX_LOG_FILES=5

#Maximun number of calls in traceback
TRACEBACK_LENGTH=5