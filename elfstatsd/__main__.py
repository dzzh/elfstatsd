"""
A daemon parsing Apache access logs and dumping aggregated results to the specified files.
These dump files can later be used by Munin or other clients to monitor server behavior in near-real-time.
"""
import logging
import cStringIO
import traceback
import os
from daemon import runner
from logging.handlers import RotatingFileHandler
from elfstats_daemon import ElfStatsDaemon
import settings

DEFAULT_TRACEBACK_LENGTH = 5
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_DIR = '/var/log/elfstatsd'
DEFAULT_MAX_LOG_SIZE = 10000000
DEFAULT_MAX_LOG_FILES = 5


class FormatterWithLongerTraceback(logging.Formatter):
    def formatException(self, ei):
        sio = cStringIO.StringIO()
        traceback.print_exception(ei[0], ei[1], ei[2],
                                  getattr(settings, 'TRACEBACK_LENGTH', DEFAULT_TRACEBACK_LENGTH), sio)
        s = sio.getvalue()
        sio.close()
        if s[-1:] == '\n':
            s = s[:-1]
        return s


daemon = ElfStatsDaemon()
logger = logging.getLogger('elfstatsd')
logger.setLevel(getattr(settings, 'LOGGING_LEVEL', DEFAULT_LOG_LEVEL))
formatter = FormatterWithLongerTraceback('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler = RotatingFileHandler(os.path.join(getattr(settings, 'DAEMON_LOG_DIR', DEFAULT_LOG_DIR), 'elfstatsd.log'),
                              maxBytes=getattr(settings, 'MAX_LOG_FILE_SIZE', DEFAULT_MAX_LOG_SIZE),
                              backupCount=getattr(settings, 'MAX_LOG_FILES', DEFAULT_MAX_LOG_FILES))
handler.setFormatter(formatter)
logger.addHandler(handler)

daemon_runner = runner.DaemonRunner(daemon)
#This ensures that the logger file handle does not get closed during daemonization
daemon_runner.daemon_context.files_preserve = [handler.stream]
daemon_runner.do_action()
