import re

#Munindaemon assumes that Apache log file is in the following format:
#Field 4 - time
#Field 8 - request
#Field 9 - response code
#Last field - latency
#In next versions of a daemon it will be possible to specify Apache log format in this config file.

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
VALID_REQUEST = re.compile('^(/content|/serv)/')

#Symbols to be removed from method names (Munin cannot process them in field names)
BAD_SYMBOLS = re.compile('[.-]')

#Response codes to track in all rounds, even if they are not found in logs
RESPONSE_CODES = [200,204,301,302,303,304,307,404,500,501,502,503,504]

#Maximum size of a single log file, in bytes
MAX_LOG_FILE_SIZE=10000000

#Maximum number of log files to keep
MAX_LOG_FILES=5
