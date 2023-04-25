#!/usr/bin/python
# vim: ts=4 sw=4 sts=4 et
"""
This is a small script that calls parse_blob.py to print all possible errors
in blob files from [param1]*/OUT/*.blobs

param1: optional path where subdirectories with ratognize output data can be found
        default value is defined in util.py
"""

import os, sys, time
from glob import glob

try:
    import trajognize
except ImportError:
    sys.path.insert(
        0,
        os.path.abspath(
            os.path.join(os.path.dirname(sys.modules[__name__].__file__), "..")
        ),
    )
    import trajognize

# check bad arguments
if len(sys.argv) > 2 or (len(sys.argv) > 1 and sys.argv[1] == "--help"):
    exit(__doc__, 2)

# get input path
path = trajognize.util.get_path_as_first_arg(sys.argv)
path += "*/OUT/*.blobs"
print("# Using data: %s" % path)

# list files and check for error
files = glob(path)
if not files:
    exit("ERROR: No files found on input path", 1)

# print filenames and good lines
i = 0
for inputfile in files:
    i += 1
    # get file name
    head, tail = os.path.split(inputfile)
    print("Parsing input file #%d: '%s'..." % (i, tail))
    start = time.perf_counter()
    color_blobs, md_blobs, rat_blobs = trajognize.parse.parse_blob_file(inputfile)
    if color_blobs is None and md_blobs is None and rat_blobs is None:
        continue
    end = time.perf_counter()
    print("  time elapsed: %.2gs" % (end - start))
    print("  %d BLOB lines" % len(color_blobs))
    print("  %d MD lines" % len(rat_blobs))
    print("  %d RAT lines" % len(md_blobs))
