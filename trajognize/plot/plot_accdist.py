"""This script generates plots for 'accdist' type trajognize.stat outputs.

Usage: plot_accdist.py inputfile(s)

where inputfile(s) is/are the output of trajognize.stat accdist_t object (.txt)

Output is written in subdirectories of input dir categorized according to
experiments.

"""

import os, subprocess, sys, glob

from .plot import *

from . import spgm

GNUPLOT_TEMPLATE = """#!/usr/bin/gnuplot
reset
set term png
set logscale y
set xlabel "acceleration (pixel/frame^2)"
set ylabel "number of frames"
set title "%(name)s\\n%(exp)s"
set key autotitle columnhead
set out "%(outputfile)s"
plot for [i = 2 : %(maxcol)d] "%(inputfile)s" index %(index)d u 1:i lc (i-1) with lines
set out "%(outputfileall)s"
plot "%(inputfile)s" index %(index)d u 1:(column(%(maxcol)d+1)) with lines
"""


def get_gnuplot_script(inputfile, outputfile, outputfileall, name, index, maxcol,
        exp):
    """Return .gnu script body as string."""
    data = {
        "inputfile": inputfile,
        "outputfile": outputfile,
        "outputfileall": outputfileall,
        "name": name,
        "index": index,
        "maxcol": maxcol,
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
        headers = grep_headers_from_file(inputfile, "accdist_")
        exp = get_exp_from_filename(inputfile)
        # define output directory
        (head, tail, plotdir) = get_headtailplot_from_filename(inputfile)
        outdir = os.path.join(head, plotdir, exp)
        if not os.path.isdir(outdir): os.makedirs(outdir)
        # if this is a new output directory, clear SPGM descriptions
        if outdir not in outdirs:
            spgm.remove_picture_descriptions(outdir)
            outdirs.append(outdir)
        # plot all indices
        for index in range(len(headers)):
            name = headers[index][0]
            maxcol = len(headers[index])-1
            outputfilecommon = os.path.join(outdir, tail + '__' + name)
            gnufile = outputfilecommon + ".gnu"
            outputfile = outputfilecommon + ".indiv.png"
            outputfileall = outputfilecommon + ".all.png"
            script = get_gnuplot_script(inputfile, outputfile, outputfileall,
                    name, index, maxcol, exp)
            with open(gnufile, 'w') as f:
                f.write(script)
            try:
                subprocess.call(["gnuplot", gnufile])
            except WindowsError:
                print("  Error plotting '%s': gnuplot is not available on Windows" % name)
            # create SPGM picture description
            spgm.create_picture_description(outputfile,
                    [name, "individual data", exp], inputfile, gnufile)
            spgm.create_picture_description(outputfileall,
                    [name, "averaged data", exp], inputfile, gnufile)

    # create SPGM gallery descriptions
    spgm.create_gallery_description(head, "Distribution of acceleration")
    spgm.create_gallery_description(os.path.join(head, plotdir), """Plotted results for acceleration distribution.
        Results are categorized in subdirectories according to experiments.
        Two output types exist: one plot for individual distributions together,
        one for averaged distribution of all pateks.
        """)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:])) # pass only real params to main
    except Exception as ex:
        print(ex, file=sys.stderr)
        import traceback
        traceback.print_exc(ex)
        sys.exit(1)
