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
    sys.path.insert(
        0,
        os.path.abspath(
            os.path.join(os.path.dirname(sys.modules[__name__].__file__), "..")
        ),
    )
    import trajognize

# parse command line arguments
argparser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter, description=__doc__
)
argparser.add_argument(
    "-i",
    "--inputfile",
    metavar="FILE",
    required=True,
    dest="inputfile",
    help="define barcode input file name (.blobs.barcodes)",
)
argparser.add_argument(
    "-p",
    "--projectfile",
    metavar="FILE",
    required=True,
    dest="projectfile",
    help="define project settings file that contains a single TrajognizeSettingsBase class instantiation.",
)
argparser.add_argument(
    "-n",
    "--framenum",
    metavar="NUM",
    dest="framenum",
    default=0,
    help="define frame to read",
)
options = argparser.parse_args()

# colorid file
print("  Using project file: '%s'" % options.projectfile)
# inputfile
print("  Using inputfile: '%s'" % options.inputfile)
# frame num
options.framenum = int(options.framenum)

# read projectfile
project_settings = trajognize.settings.import_trajognize_settings_from_file(
    args.projectfile
)
if project_settings is None:
    print("Could not parse project settings file")
    sys.exit(1)
colorids = project_settings.colorids
print("  Current project is: %s" % project_settings.project_name)

# read barcode file line
print("Reading frame", options.framenum)
barcodes = trajognize.parse.parse_barcode_file(
    options.inputfile, colorids, options.framenum, options.framenum
)
if not barcodes:
    print("barcode file empty")
    sys.exit()

# print line
for k in range(len(colorids)):
    if not barcodes[0][k]:
        print(colorids[k])
    for barcode in barcodes[0][k]:
        print(
            "%s\t%d\t%d\t%d\t%s\t%s"
            % (
                colorids[k],
                int(barcode.centerx),
                int(barcode.centery),
                int(barcode.orientation * 180 / pi),
                trajognize.util.mfix2str(barcode.mfix),
                barcode.blobindices,
            )
        )
