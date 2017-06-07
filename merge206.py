"""Merge 206 partial requests in a log file.

Usage:
  merge206.py [-p PATTERN] [-d SECONDS] [-i FILE]

Options:
  -i FILE, --input FILE             Logfile to read
  -p PATTERN, --pattern PATTERN     Apache log format specification. see https://github.com/rory/apache-log-parser#supported-values
  -d SECONDS, --delay SECONDS       The max time between 206 partial requests [default: 600]
  -h --help                         Show this screen.
  --version                         Show version.

"""

from collections import OrderedDict
import re
import sys
import datetime

__author__ = 'dylanjay'

import apache_log_parser
from StringIO import StringIO

 # supported log file formats
APACHE_COMBINED="%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\""
APACHE_COMMON="%h %l %u %t \"%r\" %>s %b"


# similar request keys

KEYS = ['request_header_referer', 'remote_user', 'request_header_user_agent', 'request_http_ver', 'request_method', 'request_url', 'remote_host']

 #'response_bytes_clf']


from docopt import docopt

# plan:

def hash_entry(data):
    return tuple( data[key] for key in KEYS )



def merge_recent_entries(input, output, pattern=APACHE_COMBINED, delay=600):
    """
    If we get several requests in row that look like from the same user then we will merge

    >>> log = StringIO('''
    ... 1.1.1.1 - - [26/Nov/2015:04:58:59 +0000] "GET /blah HTTP/1.1" 200 2 "http://foo.com" "mybrowser"
    ... 1.1.1.1 - - [26/Nov/2015:04:59:05 +0000] "GET /blah HTTP/1.1" 206 742750 "http://foo.com" "mybrowser"
    ... 1.1.1.1 - - [26/Nov/2015:04:59:07 +0000] "GET /blah HTTP/1.1" 206 69475 "http://foo.com" "mybrowser"
    ... 1.1.1.1 - - [26/Nov/2015:04:59:08 +0000] "GET /blah HTTP/1.1" 206 3939 "http://foo.com" "mybrowser"
    ... '''.strip())
    >>> merge_recent_entries(log, sys.stdout)
    1.1.1.1 - - [26/Nov/2015:04:58:59 +0000] "GET /blah HTTP/1.1" 200 816166 "http://foo.com" "mybrowser"

    If from a different client IP then we won't merge
    >>> log = StringIO('''
    ... 1.1.1.1 - - [26/Nov/2015:04:58:59 +0000] "GET /blah HTTP/1.1" 200 2 "http://foo.com" "mybrowser"
    ... 1.1.1.2 - - [26/Nov/2015:04:59:05 +0000] "GET /blah HTTP/1.1" 206 742750 "http://foo.com" "mybrowser"
    ... '''.strip())
    >>> merge_recent_entries(log, sys.stdout)
    1.1.1.1 - - [26/Nov/2015:04:58:59 +0000] "GET /blah HTTP/1.1" 200 2 "http://foo.com" "mybrowser"
    1.1.1.2 - - [26/Nov/2015:04:59:05 +0000] "GET /blah HTTP/1.1" 206 742750 "http://foo.com" "mybrowser"

    If from a different browser then we won't merge
    >>> log = StringIO('''
    ... 1.1.1.1 - - [26/Nov/2015:04:58:59 +0000] "GET /blah HTTP/1.1" 200 2 "http://foo.com" "mybrowser"
    ... 1.1.1.1 - - [26/Nov/2015:04:59:05 +0000] "GET /blah HTTP/1.1" 206 742750 "http://foo.com" "notmybrowser"
    ... '''.strip())
    >>> merge_recent_entries(log, sys.stdout)
    1.1.1.1 - - [26/Nov/2015:04:58:59 +0000] "GET /blah HTTP/1.1" 200 2 "http://foo.com" "mybrowser"
    1.1.1.1 - - [26/Nov/2015:04:59:05 +0000] "GET /blah HTTP/1.1" 206 742750 "http://foo.com" "notmybrowser"

    A 404 or 500 won't get merged
    >>> log = StringIO('''
    ... 1.1.1.1 - - [26/Nov/2015:04:58:59 +0000] "GET /blah HTTP/1.1" 404 2 "http://foo.com" "mybrowser"
    ... 1.1.1.1 - - [26/Nov/2015:04:58:59 +0000] "GET /blah2 HTTP/1.1" 500 2 "http://foo.com" "mybrowser"
    ... 1.1.1.1 - - [26/Nov/2015:04:59:05 +0000] "GET /blah HTTP/1.1" 206 742750 "http://foo.com" "mybrowser"
    ... 1.1.1.1 - - [26/Nov/2015:04:59:05 +0000] "GET /blah2 HTTP/1.1" 206 742750 "http://foo.com" "mybrowser"
    ... '''.strip())
    >>> merge_recent_entries(log, sys.stdout)
    1.1.1.1 - - [26/Nov/2015:04:58:59 +0000] "GET /blah HTTP/1.1" 404 2 "http://foo.com" "mybrowser"
    1.1.1.1 - - [26/Nov/2015:04:59:05 +0000] "GET /blah2 HTTP/1.1" 500 742750 "http://foo.com" "mybrowser"
    1.1.1.1 - - [26/Nov/2015:04:59:05 +0000] "GET /blah HTTP/1.1" 206 742750 "http://foo.com" "mybrowser"
    1.1.1.1 - - [26/Nov/2015:04:59:05 +0000] "GET /blah2 HTTP/1.1" 206 742750 "http://foo.com" "mybrowser"
    """


    # keep last 1min worth of log entries and look them up based on if its the same
    # request repeated
    buffer = OrderedDict()

    
    if not pattern:
        pattern = APACHE_COMBINED
    line_parser=apache_log_parser.make_parser(pattern)
    for line in input.readlines():
        data = line_parser(line)
        #if '01:10:30' in line:
        #    import pdb; pdb.set_trace()
        # get rid of too old entries at the end of our buffer
        for oldline, oldtime in buffer.values():
            if data['time_received_utc_datetimeobj'] - oldtime > datetime.timedelta(seconds=delay):
                output.write(oldline)
                buffer.popitem(last=False)
            else:
                break
        hash = hash_entry(data)
        if hash not in buffer or data['status'] != '206':
            buffer[hash] = (line, data['time_received_utc_datetimeobj'])
            continue

        oldline,oldtime = buffer[hash]
        del buffer[hash]
        olddata = line_parser(oldline)
        if olddata['status'] not in ['200', '206']:
            buffer[hash] = (line, data['time_received_utc_datetimeobj'])
            continue

        # Combine the lines
        #update the response size
        oldbytes = olddata['response_bytes_clf']
        newbytes = data['response_bytes_clf']
        bytes = int(oldbytes) + int(newbytes)
        # TODO: bit of a hack, what if this occurs twice?
        line, count = re.subn(" {0} ".format(oldbytes), " {0} ".format(bytes), oldline )
        if count == 0 or count > 1:
            raise Exception("error trying to merge response bytes")
        buffer[hash] = (line, data['time_received_utc_datetimeobj'])

    for line, timestamp in buffer.values():
            output.write(line)

def main():
    arguments = docopt(__doc__, version='Merge web logs 1.0')

    if arguments['--input'] and arguments['--input'] != '-':
        input = open(arguments['--input'], "r")
    else:
        input = sys.stdin
    pat = arguments.get('--pattern', None)
    delay = int(arguments.get('--delay'))

    merge_recent_entries(input, sys.stdout, pattern=pat, delay=delay)

if __name__ == '__main__':
    main()