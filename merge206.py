"""Merge 206 partial requests in a log file.

Usage:
  merge206.py [-p PATTERN] [-d SECONDS] [-i FILE]

Options:
  -i FILE, --input FILE             Logfile to read
  -p PATTERN, --pattern PATTERN     Apache log format specification. see https://github.com/rory/apache-log-parser#supported-values
  -d SECONDS, --delay SECONDS       The max time between 206 partial requests [default: 600]
  -k KEYS, --keys KEYS              Request keys [default: 'request_header_referer remote_user request_header_user_agent request_http_ver request_method request_url remote_host']
  -h --help                         Show this screen.
  --version                         Show version.

"""

from collections import OrderedDict
import re
import sys
import datetime
import apache_log_parser
from StringIO import StringIO
from docopt import docopt

__author__ = 'dylanjay'


 # supported log file formats
APACHE_COMBINED="%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\""
APACHE_COMMON="%h %l %u %t \"%r\" %>s %b"

# similar request keys

KEYS = ['request_header_referer', 'remote_user', 'request_header_user_agent', 'request_http_ver', 'request_method', 'request_url', 'remote_host']


def merge_recent_entries(
        input, output, pattern=APACHE_COMBINED, delay=600, keys=''):
    """
    If we get several requests in row that look like from the same user then we will merge

    >>> merge_recent_entries(StringIO('''
    ... 1.1.1.1 - - [26/Nov/2015:04:58:59 +0000] "GET /blah HTTP/1.1" 200 2 "http://foo.com" "mybrowser"
    ... 1.1.1.1 - - [26/Nov/2015:04:59:05 +0000] "GET /blah HTTP/1.1" 206 742750 "http://foo.com" "mybrowser"
    ... 1.1.1.1 - - [26/Nov/2015:04:59:07 +0000] "GET /blah HTTP/1.1" 206 69475 "http://foo.com" "mybrowser"
    ... 1.1.1.1 - - [26/Nov/2015:04:59:08 +0000] "GET /blah HTTP/1.1" 206 3939 "http://foo.com" "mybrowser"
    ... '''.strip()), sys.stdout)
    1.1.1.1 - - [26/Nov/2015:04:58:59 +0000] "GET /blah HTTP/1.1" 200 816166 "http://foo.com" "mybrowser"

    Interleving requests will get merged
    >>> merge_recent_entries(StringIO('''
    ... 1.1.1.1 - - [26/Nov/2015:04:58:59 +0000] "GET /blah HTTP/1.1" 200 2 "http://foo.com" "mybrowser"
    ... 1.1.1.2 - - [26/Nov/2015:04:59:05 +0000] "GET /blah HTTP/1.1" 200 742750 "http://foo.com" "mybrowser"
    ... 1.1.1.1 - - [26/Nov/2015:04:59:07 +0000] "GET /blah HTTP/1.1" 206 69475 "http://foo.com" "mybrowser"
    ... 1.1.1.2 - - [26/Nov/2015:04:59:08 +0000] "GET /blah HTTP/1.1" 206 3939 "http://foo.com" "mybrowser"
    ... '''.strip()), sys.stdout)
    1.1.1.1 - - [26/Nov/2015:04:58:59 +0000] "GET /blah HTTP/1.1" 200 69477 "http://foo.com" "mybrowser"
    1.1.1.2 - - [26/Nov/2015:04:59:05 +0000] "GET /blah HTTP/1.1" 200 746689 "http://foo.com" "mybrowser"

    If from a different client IP then we won't merge
    >>> merge_recent_entries(StringIO('''
    ... 1.1.1.1 - - [26/Nov/2015:04:58:59 +0000] "GET /blah HTTP/1.1" 200 2 "http://foo.com" "mybrowser"
    ... 1.1.1.2 - - [26/Nov/2015:04:59:05 +0000] "GET /blah HTTP/1.1" 206 742750 "http://foo.com" "mybrowser"
    ... '''.strip()), sys.stdout)
    1.1.1.1 - - [26/Nov/2015:04:58:59 +0000] "GET /blah HTTP/1.1" 200 2 "http://foo.com" "mybrowser"
    1.1.1.2 - - [26/Nov/2015:04:59:05 +0000] "GET /blah HTTP/1.1" 206 742750 "http://foo.com" "mybrowser"

    If from a different browser then we won't merge
    >>> merge_recent_entries(StringIO('''
    ... 1.1.1.1 - - [26/Nov/2015:04:58:59 +0000] "GET /blah HTTP/1.1" 200 2 "http://foo.com" "mybrowser"
    ... 1.1.1.1 - - [26/Nov/2015:04:59:05 +0000] "GET /blah HTTP/1.1" 206 742750 "http://foo.com" "notmybrowser"
    ... '''.strip()), sys.stdout)
    1.1.1.1 - - [26/Nov/2015:04:58:59 +0000] "GET /blah HTTP/1.1" 200 2 "http://foo.com" "mybrowser"
    1.1.1.1 - - [26/Nov/2015:04:59:05 +0000] "GET /blah HTTP/1.1" 206 742750 "http://foo.com" "notmybrowser"

    A 404 or 500 won't get merged
    >>> merge_recent_entries(StringIO('''
    ... 1.1.1.1 - - [26/Nov/2015:04:58:59 +0000] "GET /blah HTTP/1.1" 404 2 "http://foo.com" "mybrowser"
    ... 1.1.1.1 - - [26/Nov/2015:04:59:01 +0000] "GET /blah2 HTTP/1.1" 500 2 "http://foo.com" "mybrowser"
    ... 1.1.1.1 - - [26/Nov/2015:04:59:05 +0000] "GET /blah HTTP/1.1" 206 742750 "http://foo.com" "mybrowser"
    ... 1.1.1.1 - - [26/Nov/2015:04:59:06 +0000] "GET /blah2 HTTP/1.1" 206 742750 "http://foo.com" "mybrowser"
    ... '''.strip()), sys.stdout)
    1.1.1.1 - - [26/Nov/2015:04:58:59 +0000] "GET /blah HTTP/1.1" 404 2 "http://foo.com" "mybrowser"
    1.1.1.1 - - [26/Nov/2015:04:59:01 +0000] "GET /blah2 HTTP/1.1" 500 2 "http://foo.com" "mybrowser"
    1.1.1.1 - - [26/Nov/2015:04:59:05 +0000] "GET /blah HTTP/1.1" 206 742750 "http://foo.com" "mybrowser"
    1.1.1.1 - - [26/Nov/2015:04:59:06 +0000] "GET /blah2 HTTP/1.1" 206 742750 "http://foo.com" "mybrowser"

    If they are too far apart then it won't get merged
    >>> merge_recent_entries(StringIO('''
    ... 1.1.1.1 - - [26/Nov/2015:04:41:59 +0000] "GET /blah HTTP/1.1" 200 2 "http://foo.com" "mybrowser"
    ... 1.1.1.1 - - [26/Nov/2015:04:59:05 +0000] "GET /blah HTTP/1.1" 206 742750 "http://foo.com" "mybrowser"
    ... '''.strip()), sys.stdout)
    1.1.1.1 - - [26/Nov/2015:04:41:59 +0000] "GET /blah HTTP/1.1" 200 2 "http://foo.com" "mybrowser"
    1.1.1.1 - - [26/Nov/2015:04:59:05 +0000] "GET /blah HTTP/1.1" 206 742750 "http://foo.com" "mybrowser"

    Two 200 requests won't get merged
    >>> merge_recent_entries(StringIO('''
    ... 1.1.1.1 - - [26/Nov/2015:04:58:59 +0000] "GET /blah HTTP/1.1" 200 2 "http://foo.com" "mybrowser"
    ... 1.1.1.1 - - [26/Nov/2015:04:59:05 +0000] "GET /blah HTTP/1.1" 200 742750 "http://foo.com" "mybrowser"
    ... '''.strip()), sys.stdout)
    1.1.1.1 - - [26/Nov/2015:04:58:59 +0000] "GET /blah HTTP/1.1" 200 2 "http://foo.com" "mybrowser"
    1.1.1.1 - - [26/Nov/2015:04:59:05 +0000] "GET /blah HTTP/1.1" 200 742750 "http://foo.com" "mybrowser"

    The merged request should be in the right order when output
    >>> merge_recent_entries(StringIO('''
    ... 2.2.2.2 - - [26/Nov/2015:04:51:05 +0000] "GET /1 HTTP/1.1" 206 742750 "http://foo.com" "mybrowser"
    ... 1.1.1.1 - - [26/Nov/2015:04:52:59 +0000] "GET /blah HTTP/1.1" 200 2 "http://foo.com" "mybrowser"
    ... 3.3.3.3 - - [26/Nov/2015:04:53:05 +0000] "GET /2 HTTP/1.1" 206 742750 "http://foo.com" "mybrowser"
    ... 1.1.1.1 - - [26/Nov/2015:04:54:05 +0000] "GET /blah HTTP/1.1" 206 742750 "http://foo.com" "mybrowser"
    ... 3.3.3.3 - - [26/Nov/2015:04:55:05 +0000] "GET /3 HTTP/1.1" 206 742750 "http://foo.com" "mybrowser"
    ... '''.strip()), sys.stdout)
    2.2.2.2 - - [26/Nov/2015:04:51:05 +0000] "GET /1 HTTP/1.1" 206 742750 "http://foo.com" "mybrowser"
    1.1.1.1 - - [26/Nov/2015:04:52:59 +0000] "GET /blah HTTP/1.1" 200 742752 "http://foo.com" "mybrowser"
    3.3.3.3 - - [26/Nov/2015:04:53:05 +0000] "GET /2 HTTP/1.1" 206 742750 "http://foo.com" "mybrowser"
    3.3.3.3 - - [26/Nov/2015:04:55:05 +0000] "GET /3 HTTP/1.1" 206 742750 "http://foo.com" "mybrowser"    """


    if not pattern:
        pattern = APACHE_COMBINED
    delay = datetime.timedelta(seconds=delay)
    
    keys_list = KEYS
    if keys:
        keys_list = keys.split()

    line_parser=apache_log_parser.make_parser(pattern)

    # keep last 1min worth of log entries and look them up based on if its the same
    # request repeated
    buffer = OrderedDict()


    def hash_entry(data, keys_entry):
        # we need to make sure we only have a single mergable item in the buffer at anyone time
        # We can only merge 200 and 206 so they get the same hash.

        #TODO currently this allows a 200 to be merged with a 200 which isn't right
        # To fix have to have some way to make the new 200 have a different hash from
        # the old one?
        keys = keys_entry + (['status'] if data['status'] not in ['200','206'] else [])
        return tuple( data[key] for key in  keys)



    #import pdb; pdb.set_trace()
    for line in input.readlines():
        data = line_parser(line)
        # get rid of too old entries at the end of our buffer
        for oldline, oldtime, _ in buffer.itervalues():
            if data['time_received_utc_datetimeobj'] - oldtime > delay:
                output.write(oldline)
                buffer.popitem(last=False)
            else:
                break

        hash = hash_entry(data, keys_list)
        if hash not in buffer:
            buffer[hash] = (line, data['time_received_utc_datetimeobj'], data)
            continue

        # we have a line in the buffer we can merge with
        oldline, oldtime, olddata = buffer[hash]
        del buffer[hash]

        # Combine the lines
        #update the response size
        oldbytes = olddata['response_bytes_clf']
        newbytes = data['response_bytes_clf']
        bytes = int(oldbytes) + int(newbytes)
        data['response_bytes_clf'] = str(bytes)
        # TODO: bit of a hack, what if this occurs twice?
        line, count = re.subn(" {0} ".format(oldbytes), " {0} ".format(bytes), oldline )
        if count == 0 or count > 1:
            raise Exception("error trying to merge response bytes")
        # Important we add this back in with the timestamp of the latest in the merge
        # not the original.
        buffer[hash] = (line, data['time_received_utc_datetimeobj'], data)
        #TODO: this puts the merged line out of sequence which can cause problems

    for line, _, _ in buffer.itervalues():
            output.write(line)

def main():
    arguments = docopt(__doc__, version='Merge web logs 1.0')

    if arguments['--input'] and arguments['--input'] != '-':
        input = open(arguments['--input'], "r")
    else:
        input = sys.stdin
    pat = arguments.get('--pattern', None)
    delay = int(arguments.get('--delay'))
    keys = arguments.get('--keys', '')

    merge_recent_entries(input, sys.stdout, pattern=pat, delay=delay, keys=keys)

if __name__ == '__main__':
    main()