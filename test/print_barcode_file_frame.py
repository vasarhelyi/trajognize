#!/usr/bin/python
# vim: ts=4 sw=4 sts=4 et
"""
This is a small script that prints a single line of a barcode file in
human readable format.

Input is taken from file specified.

Results are printed to standard output.

"""

import os, sys, argparse
from math import pi

try:
    import trajognize
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(
        os.path.dirname(sys.modules[__name__].__file__), "..")))
    import trajognize

# parse command line arguments
argparser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=__doc__)
argparser.add_argument("-i", "--inputfile", metavar="FILE", required=True, dest="inputfile", help="define barcode input file name (.blobs.barcodes)")
argparser.add_argument("-c", "--coloridfile", metavar="FILE", required=True, dest="coloridfile", help="define colorid input file name (.xml)")
argparser.add_argument("-n", "--framenum", metavar="NUM", dest="framenum", default=0, help="define frame to read")
options = argparser.parse_args()

# colorid file
print("  Using colorid file: '%s'" % options.coloridfile)
# inputfile
print("  Using inputfile: '%s'" % options.inputfile)
# frame num
options.framenum = int(options.framenum)

# read coloridfile
colorids = trajognize.parse.parse_colorid_file(options.coloridfile)
if colorids is None:
    print("colorids file bad")
    sys.exit()

# read barcode file line
print("Reading frame", options.framenum)
barcodes = trajognize.parse.parse_barcode_file(options.inputfile, colorids, options.framenum, options.framenum)
if not barcodes:
    print("barcode file empty")
    sys.exit()

# print line
for k in range(len(colorids)):
    if not barcodes[0][k]:
        print(colorids[k].strid)
    for barcode in barcodes[0][k]:
        print("%s\t%d\t%d\t%d\t%s\t%s" % (colorids[k].strid, int(barcode.centerx),
                int(barcode.centery), int(barcode.orientation*180/pi),
                trajognize.util.mfix2str(barcode.mfix), barcode.blobindices))
