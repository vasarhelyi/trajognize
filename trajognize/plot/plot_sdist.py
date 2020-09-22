"""This script generates plots for 'sdist' type trajognize.stat outputs.

Usage: plot_sdist.py inputfile(s)

where inputfile(s) is/are the output of trajognize.stat sdist_t object (.txt)

Output is written in subdirectories of input dir categorized according to
experiments.

"""

import os, subprocess, sys, glob

from . import plot
from . import spgm

GNUPLOT_TEMPLATE = """#!/usr/bin/gnuplot
reset
set term png
#set logscale y
set xlabel "distance between barcodes (pixel)"
set ylabel "number of frames"
set title "%(name)s\\n%(exp)s"
unset key
set out "%(outputfile)s"
plot "%(inputfile)s" index %(index)d u 1:2 with boxes
"""


def get_gnuplot_script(inputfile, outputfile, name, index, exp):
    """Return .gnu script body as string."""
    data = {
        "inputfile": inputfile,
        "outputfile": outputfile,
        "name": name,
        "index": index,
        "exp": exp,
    }
    return GNUPLOT_TEMPLATE % data


def main(argv=[]):
    """Main entry point of the script."""
    if not argv:
        print(__doc__)
        return
    if sys.platform.startswith('win'):
        inputfiles = glob.glob(argv[0])
    else:
        inputfiles = argv
    outdirs = []
    for inputfile in inputfiles:
        print("parsing", os.path.split(inputfile)[1])
        headers = plot.grep_headers_from_file(inputfile, "sdist_")
        exp = plot.get_exp_from_filename(inputfile)
        # define output directory
        (head, tail, plotdir) = plot.get_headtailplot_from_filename(inputfile)
        outdir = os.path.join(head, plotdir, exp)
        if not os.path.isdir(outdir): os.makedirs(outdir)
        # if this is a new output directory, clear SPGM descriptions
        if outdir not in outdirs:
            spgm.remove_picture_descriptions(outdir)
            outdirs.append(outdir)
        # plot all indices
        for index in range(len(headers)):
            name = headers[index][0]
            outputfilecommon = os.path.join(outdir, tail + '__' + name)
            gnufile = outputfilecommon + ".gnu"
            outputfile = outputfilecommon + ".png"
            script = get_gnuplot_script(inputfile, outputfile, name, index, exp)
            with open(gnufile, 'w') as f:
                f.write(script)
            try:
                subprocess.call(["gnuplot", gnufile])
            except WindowsError:
                print("  Error plotting '%s': gnuplot is not available on Windows" % name)
            # create SPGM picture description
            spgm.create_picture_description(outputfile, [name, exp], inputfile, gnufile)

    # create SPGM gallery descriptions
    spgm.create_gallery_description(head, "Distribution of spatial distance between barcodes")
    spgm.create_gallery_description(os.path.join(head, plotdir), """Plotted results for spatial distance distribution between barcodes.
        Results are categorized in subdirectories according to experiments.
        """)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:])) # pass only real params to main
    except Exception as ex:
        print(ex, file=sys.stderr)
        import traceback
        traceback.print_exc(ex)
        sys.exit(1)
