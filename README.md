Merge206
========

Small web log util which parses web logs such as apache or nginx and will attempt
to find 206 requests which are likely related to an original 200 or 206 request
and aggregate them into a single request.

- The combined request will be first request encountered except for the response
  bytes which will be a total.
- The combined request will take the place of the last request to be combined.
  This means that log data will not be output in chronological order according
  to the timestamps

Usage
=====

Usage:
  merge206.py [-d SECONDS] [-p PATTERN] [-i FILE]

Options:
  -i FILE, --input FILE             Logfile to read
  -p PATTERN, --pattern PATTERN     Apache log format specification
  -d SECONDS, --delay SECONDS       The max time between 206 partial requests [default: 600]
  -h --help                         Show this screen.
  --version                         Show version.
