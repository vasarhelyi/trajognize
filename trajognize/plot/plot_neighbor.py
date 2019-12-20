"""This script generates plots for 'neighbor' type trajognize.stat outputs.

Usage: plot_neighbor.py inputfile(s)

where inputfile(s) is/are the output of trajognize.stat neighbor_t object (.txt)

Output is written in subdirectories of input dir, according to experiment, group
and light.

Script calls another scripts for the network type output:

    plot_matrixmap.py -- as a common framework for matrix plotting

"""

import os, subprocess, sys, glob, numpy
from plot import *
import plot_matrixmap
import trajognize.parse
import spgm
import trajognize.corr.util


GNUPLOT_TEMPLATE = """#!/usr/bin/gnuplot
reset
set term png
set xlabel "Number of neighbors"
set ylabel "Number of frames"
set title "%(name)s\\n%(exp)s"
set autoscale fix
set key autotitle columnhead
set out "%(outputfile)s"
plot for [i = 2 : %(maxcol)d] "%(inputfile)s" index %(index)d u 1:i lc (i-1) with lines
"""


def get_gnuplot_script(inputfile, outputfile, name, index, maxcol, exp):
    """Return .gnu script body as string."""
    data = {
        "inputfile": inputfile,
        "outputfile": outputfile,
        "name": name,
        "index": index,
        "maxcol": maxcol,
        "exp": exp,
    }
    return GNUPLOT_TEMPLATE % data


def get_categories_from_name(name):
    """Get networknumber, light and group from paragraph header (name), e.g.:

    neighbor_network_daylight_group_G3S
    neighbor_number_nightlight_group_G3S
    neighbor_network_daylight
    neighbor_number_nightlight

    """
    match = re.match(r'^neighbor_([a-zA-Z]*)_([a-zA-Z]*)', name)
    if match:
        networknumber = match.group(1)
        light = match.group(2)
    else:
        return (None, None, None)
    match = re.match(r'.*group_([0-9A-Z]*)', name)
    if match:
        group = match.group(1)
    else:
        group = 'all'
    return (networknumber, light, group)


def main(argv=[]):
    """Main entry point of the script."""
    if not argv:
        print __doc__
        return
    if sys.platform.startswith('win'):
        inputfiles = glob.glob(argv[0])
    else:
        inputfiles = argv
    outdirs = []
    corrfiles = []
    for inputfile in inputfiles:
        (head, tail, plotdir) = get_headtailplot_from_filename(inputfile)
        exp = get_exp_from_filename(inputfile)
        # parse data file
        alldata = trajognize.parse.parse_stat_output_file(inputfile)
        # TODO: common cbrange for F, C, D
        for index in xrange(len(alldata)):
            # get categories
            name = alldata[index][0][0]
            (networknumber, light, group) = get_categories_from_name(name)
            # define output directory
            outdir = os.path.join(head, plotdir, exp, group, light)
            # if this is a new output directory, clear SPGM descriptions
            if outdir not in outdirs:
                spgm.remove_picture_descriptions(outdir)
                outdirs.append(outdir)
            # plot file
            if networknumber == "network":
                plot_matrixmap.main(["-i", inputfile, "-n", str(index), "-o", outdir])
            elif networknumber == "number":
                maxcol = len(alldata[index][0])
                outputfilecommon = os.path.join(outdir, tail + '__' + name)
                gnufile = outputfilecommon + ".gnu"
                outputfile = outputfilecommon + ".png"
                script = get_gnuplot_script(inputfile, outputfile, name, index, maxcol, exp)
                print >>open(gnufile, 'w'), script
                try:
                    subprocess.call(["gnuplot", gnufile])
                except WindowsError:
                    print "  Error plotting '%s': gnuplot is not available on Windows" % name
                # create SPGM picture description
                spgm.create_picture_description(outputfile, [name, exp], inputfile, gnufile)
            else:
                0/0

            # save output for correlation analysis
            if networknumber == "network":
                headerline = trajognize.corr.util.strids2headerline(alldata[index][0][1:], True)
                corrline = trajognize.corr.util.matrix2corrline(alldata[index])
                corrfile = trajognize.corr.util.get_corr_filename(exp, group, True)
                if corrfile not in corrfiles:
                    if os.path.isfile(corrfile):
                        os.remove(corrfile)
                    corrfiles.append(corrfile)
                trajognize.corr.util.add_corr_line(corrfile, headerline, corrline)
                # convert pairparams to params (through calculating dominance indices) and save that as well
                headerline, corrline = trajognize.corr.util.pairparams2params(headerline, corrline)
                corrfile = trajognize.corr.util.get_corr_filename(exp, group, False)
                if corrfile not in corrfiles:
                    if os.path.isfile(corrfile):
                        os.remove(corrfile)
                    corrfiles.append(corrfile)
                trajognize.corr.util.add_corr_line(corrfile, headerline, corrline)
            elif networknumber == "number":
                headerline = trajognize.corr.util.strids2headerline(alldata[index][0][1:], False)
                # calculate correlation output as weighted avg number of neighbors
                corrdata = [name] # [name[:name.find("_group")]]
                for j in xrange(1, len(alldata[index][0])):
                    try:
                        corrdata.append("%g" % numpy.average(range(len(alldata[index])-1),
                                weights=[float(alldata[index][i][j]) for i in xrange(1, len(alldata[index]))]))
                    except ZeroDivisionError:
                        corrdata.append("nan") # TODO: or 0 ?
                corrline = "\t".join(corrdata)
                corrfile = trajognize.corr.util.get_corr_filename(exp, group, False)
                if corrfile not in corrfiles:
                    if os.path.isfile(corrfile):
                        os.remove(corrfile)
                    corrfiles.append(corrfile)
                trajognize.corr.util.add_corr_line(corrfile, headerline, corrline)



    # create SPGM gallery descriptions
    spgm.create_gallery_description(head, "Neighbor networks and neighbor number distibutions")
    spgm.create_gallery_description(os.path.join(head, plotdir), """Plotted results for neighbor matrices and neighbor number distributions.
        Results are organized into subdirectories according to experiments, groups and light conditions.
        """)

if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:])) # pass only real params to main
    except Exception as ex:
        print >>sys.stderr, ex
        import traceback
        traceback.print_exc(ex)
        sys.exit(1)
