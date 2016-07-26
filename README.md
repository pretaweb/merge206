Merge206
========

Small web log util which parses web logs such as apache or nginx and will attempt
to find 206 requests which are likely related to an original 200 or 206 request
and aggregate them into a single request.

WARNING: The resulting log will likely be inaccurate. There is no way to know
that two 206 requests from the same IP, for the same url, with the same user agent,
come from the same user, or even the same user in two different browser tabs.
Also the same user might pause for a long time before playing again.


- The combined request will be first request encountered except for the response
  bytes which will be a total.
- The combined request will take the place of the last request to be combined.
  This means that log data will not be output in chronological order according
  to the timestamps

Usage
=====

```
Usage:
  merge206.py [-p PATTERN] [-d SECONDS] [-i FILE]

Options:
  -i FILE, --input FILE             Logfile to read
  -p PATTERN, --pattern PATTERN     Apache log format specification. see https://github.com/rory/apache-log-parser#supported-values
  -d SECONDS, --delay SECONDS       The max time between 206 partial requests [default: 600]
  -h --help                         Show this screen.
  --version                         Show version.

```