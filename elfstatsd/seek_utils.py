import logging
import os
import apachelog
import settings
import utils

logger = logging.getLogger("elfstatsd")


def get_seek(file_path, period_start):
    """Given a file path, find a position in it where the records for a tracked period start."""

    try:
        f = open(file_path, 'r')
    except IOError as e:
        logger.error('Could not open file %s' % file_path)
        logger.error('I/O error({0}): {1}'.format(e.errno, e.strerror))
        return

    log_parser = apachelog.parser(settings.ELF_FORMAT)
    size = os.stat(file_path).st_size
    approximate_seek = _find_approximate_seek_before_period_by_moving_back(f, size, log_parser, period_start)
    exact_seek = _find_exact_seek_before_period_by_moving_forward(f, log_parser, approximate_seek, period_start)
    f.close()
    return exact_seek


def _find_approximate_seek_before_period_by_moving_back(f, size, log_parser, period_start):
    """
    Return a position in a file that is guaranteed to start a record that is earlier than period start or 0.
    @param FileIO f: file to seek
    @param long size: file size
    @param log_parser: instance of a log parser
    @return long seek
    """
    positions = _get_seek_positions(size)
    for position in positions:
        f.seek(position)
        f.readline()  # setting seek to the beginning of the next line
        candidate = f.tell()
        record = _read_record(f, log_parser)
        if _is_record_valid(record) and _is_record_before_time(record, period_start):
            return candidate
    return 0


def _get_seek_positions(size):
    """
    Return array of suggested positions to seek for a record before start of a tracked period.

    @param long size: file size
    """

    current = size - 1
    result = []

    #No need to jump back for smaller distance as it can be easily covered by forward scan
    jump_size = int(current / 100.0 * utils.SEEK_BACKWARD_PERCENTS)
    if not jump_size or jump_size < utils.BYTES_IN_MB:
        jump_size = utils.BYTES_IN_MB

    while current > 0:
        current -= jump_size
        if current > 0:
            result.append(current)
        else:
            return result


def _find_exact_seek_before_period_by_moving_forward(f, log_parser, start_position, period_start):
    """
    Return position of a first record within tracked period or end of file if no satisfying records are found.

    @param FileIO f: file to seek
    @param log_parser: instance of a log parser
    @param long start_position: position to start seeking from
    """

    seek_candidate = start_position
    f.seek(seek_candidate)
    while True:
        seek_candidate = f.tell()
        record = _read_record(f, log_parser)
        if _is_record_valid(record):
            if _is_record_before_time(record, period_start):
                continue
            else:
                return seek_candidate
        else:
            if record == utils.END_OF_FILE:
                return f.tell()
            else:
                continue


def _read_record(f, log_parser):
    line = f.readline()
    if not line:
        return utils.END_OF_FILE
    return utils.parse_line(line, log_parser)


def _is_record_before_time(record, time):
    dt = record.get_time()
    if dt < time:
        return True
    return False


def _is_record_valid(record):
    return True if record and not record == utils.END_OF_FILE and record.get_time() else False