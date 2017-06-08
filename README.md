Merge206
========

Small web log util which parses web logs such as apache or nginx and will attempt
to find 206 requests which are likely related to an original 200 or 206 request
and aggregate them into a single request.

WARNING: The resulting log will likely be inaccurate. There is no way to know
that two 206 requests from the same IP, for the same url, with the same user agent,
come from the same user, or even the same user in two different browser tabs.
Also the same user might pause for a long time before playing again.

Adjusting ```--delay argument``` can have a big effect on the total number of requests.
If users typically pause videos for a long time, or take a long time to flip pages
in a in browser pdf viewer, then would would want a long delay. However the longer
the delay, the more chance of two different users with the same fingerprint being
wrongly merge into a single request.


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

Changes
========

1.1 (2017-6-8)
------------
- Fixed a bug that meant 404 and other error codes got merged with 206
- Fixed some perforance issues
- Put in some tests

1.0
---
Initial version

Known Issues
============

- Currently there is a bug that two 200 requests within the delay perion will get merged.
- merged requests don't get output in chronological order.