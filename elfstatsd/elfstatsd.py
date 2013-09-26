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
from elfstatsd_class import ElfStatsDaemon
import settings

class FormatterWithLongerTraceback(logging.Formatter):
    def formatException(self, ei):
        sio = cStringIO.StringIO()
        traceback.print_exception(ei[0], ei[1], ei[2], settings.TRACEBACK_LENGTH, sio)
        s = sio.getvalue()
        sio.close()
        if s[-1:] == "\n":
            s = s[:-1]
        return s

daemon = ElfStatsDaemon()
logger = logging.getLogger("elfstatsd")
logger.setLevel(settings.LOGGING_LEVEL)
formatter = FormatterWithLongerTraceback("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler = RotatingFileHandler(os.path.join(settings.DAEMON_LOG_DIR, 'elfstatsd.log'),
    maxBytes=settings.MAX_LOG_FILE_SIZE, backupCount=settings.MAX_LOG_FILES)
handler.setFormatter(formatter)
logger.addHandler(handler)

daemon_runner = runner.DaemonRunner(daemon)
#This ensures that the logger file handle does not get closed during daemonization
daemon_runner.daemon_context.files_preserve=[handler.stream]
daemon_runner.do_action()
