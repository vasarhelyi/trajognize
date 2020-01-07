#!/usr/bin/python
# vim: ts=4 sw=4 sts=4 et
"""
This is a small script that prints a single line of a barcode file in
human readable format.

Input is taken from default barcode file or file specified.

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
    argparser.add_argument("-i", "--inputfile", metavar="FILE", dest="inputfile", help="define barcode input file name (.blobs.barcodes)")
    argparser.add_argument("-c", "--coloridfile", metavar="FILE", dest="coloridfile", help="define colorid input file name (.xml)")
    argparser.add_argument("-n", "--framenum", metavar="NUM", dest="framenum", default=0, help="define frame to read")
    options = argparser.parse_args()

    # colorid file
    if options.coloridfile is None:
        options.coloridfile = 'misc/5-3_28patek.xml'
        print("  WARNING! No colorid file is specified! Default is: '%s'" % options.coloridfile)
    else:
        print("  Using colorid file: '%s'" % options.coloridfile)

    # inputfile
    if options.inputfile is None:
        # default on windows (gabor's laptop)
        if sys.platform.startswith('win'):
            options.inputfile = 'd:\\ubi\\Visual Studio 2010\\Projects\\ratognize_svn\\OUT\\2011-08-30_12-42-09.588960.ts.blobs.barcodes'
        # default on non windows (linux, atlasz)
        else:
            options.inputfile = '/h/mnt/user04/project/flocking/abeld/ratlab/results/random_sample_trial_run/done/random_sample_trial_run_2011-06-10_13-15-29.335159.ts/OUT/2011-06-10_13-15-29.335159.ts.blobs.barcodes'
        print("  WARNING! No input file is specified! Default for %s is: '%s'" % (sys.platform, options.inputfile))
    else:
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
            print colorids[k].strid
        for barcode in barcodes[0][k]:
            print("%s\t%d\t%d\t%d\t%s\t%s" % (colorids[k].strid, int(barcode.centerx),
                    int(barcode.centery), int(barcode.orientation*180/pi),
                    trajognize.util.mfix2str(barcode.mfix), barcode.blobindices))
