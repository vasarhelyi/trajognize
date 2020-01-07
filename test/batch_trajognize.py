#!/usr/bin/python
# vim: ts=4 sw=4 sts=4 et
"""
This is a small script that calls trajognize main for all blob files from [param1]*/OUT/*.blobs

param1: optional path where subdirectories with ratognize output data can be found
        default value is defined in util.py
"""

import os, sys, time
from glob import glob

try:
    import trajognize
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(
        os.path.dirname(sys.modules[__name__].__file__), "..")))
    import trajognize

# check bad arguments
if len(sys.argv) > 2 or (len(sys.argv)>1 and sys.argv[1] == '--help'):
    exit(__doc__, 2)

# get input path
path = trajognize.util.get_path_as_first_arg(sys.argv)
path += '*/OUT/*.blobs'
print("# Using data: %s" % path)

# list files and check for error
files = glob(path)
if not files:
    exit('ERROR: No files found on input path', 1)

# print filenames and good lines
i = 0
start = time.clock()
for inputfile in files:
    i += 1
    # get file name
    head, tail = os.path.split(inputfile)
    print("\n\nParsing input file #%d: '%s'...\n" % (i, tail))
    # TODO: to force overwrite of output files, add '-f' to params
    trajognize.main('--inputfile=%s' % inputfile)
end = time.clock()
print("\n\nTotal time elapsed parsing %d files: %f hours" % (len(files), (end-start)/3600))
