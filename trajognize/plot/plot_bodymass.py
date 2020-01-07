"""This script generates plots for individual bodymass measurement data.

Usage: plot_bodymass.py inputfile(s)

where inputfile(s) is/are the output of trajognize.calc.calc_bodymass.py

Output is written in subdirectories of input dir, according to experiments
and groups.

"""

import os, subprocess, sys, glob, re, numpy
from plot import *
import spgm
try:
    import trajognize.stat.init
    import trajognize.stat.experiments
    import trajognize.corr.util
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(
        os.path.dirname(sys.modules[__name__].__file__), "../..")))
    import trajognize.stat.init
    import trajognize.stat.experiments
    import trajognize.corr.util


GNUPLOT_TEMPLATE = """#!/usr/bin/gnuplot
reset
set term png size 800, 480
set xlabel "Days of the experiment"
set ylabel "Average %(basename)s"
set title "%(name)s\\n%(exp)s"
set key outside autotitle columnhead
set autoscale fix
%(paintdates)s

%(dailyvalidtimes_init)s

set out "%(outputfile)s"
plot %(dailyvalidtimes_plot)s, \\
for [i = 2 : %(maxcol)d] "%(inputfile)s" index %(index)d u 0:i lc (i-1) with lines
"""


def get_gnuplot_script(inputfile, outputfile, basename, name, maxcol, exp, index,
        pdstr, dvt_init, dvt_plot):
    """Return .gnu script body as string."""
    data = {
        "inputfile": inputfile,
        "outputfile": outputfile,
        "basename": basename,
        "name": name,
        "maxcol": maxcol,
        "exp": exp,
        "index": index,
        "paintdates": pdstr,
        "dailyvalidtimes_init": dvt_init,
        "dailyvalidtimes_plot": dvt_plot,
    }
    return GNUPLOT_TEMPLATE % data


def get_categories_from_name(name):
    """Get basename and group from paragraph header (name), e.g.:

    bodymass_group_A1
    wounds_group_A2

    """
    match = re.match(r'(.*)_group_(.*)', name)
    if match:
        return (match.group(1), match.group(2))
    else:
        return (None, None)


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
    corrfiles = []
    exps = trajognize.stat.experiments.get_initialized_experiments()
    paintdates = trajognize.parse.parse_paintdates(os.path.join(
        os.path.dirname(trajognize.__file__), '../misc/paintdates.dat'))
    for inputfile in inputfiles:
        print("parsing", os.path.split(inputfile)[1])
        alldata = trajognize.parse.parse_stat_output_file(inputfile)
        (head, tail, plotdir) = get_headtailplot_from_filename(inputfile)
        exp = get_exp_from_filename(inputfile)
        for index in range(len(alldata)):
            # get categories
            headerline = alldata[index][0]
            name = headerline[0]
            (basename, group) = get_categories_from_name(name)
            # create output directory
            outdir = os.path.join(head, plotdir, exp, group)
            if not os.path.isdir(outdir): os.makedirs(outdir)
            # if this is a new output directory, clear SPGM descriptions
            if outdir not in outdirs:
                spgm.remove_picture_descriptions(outdir)
                outdirs.append(outdir)
            outputfilecommon = os.path.join(outdir, tail + '__' + name)
            gnufile = outputfilecommon + ".gnu"
            outputfile = outputfilecommon + ".png"
            maxcol = len(headerline)
            script = get_gnuplot_script(inputfile, outputfile, basename, name,
                    maxcol, exp, index,
                    get_gnuplot_paintdate_str(exps, exp[4:], paintdates),
                    *get_gnuplot_dailyvalidtimes_strs(exps, exp[4:]))
            with open(gnufile, 'w') as f:
                f.write(script)
            try:
                subprocess.call(["gnuplot", gnufile])
            except WindowsError:
                print("  Error plotting '%s': gnuplot is not available on Windows" % name)
            # create SPGM picture description
            spgm.create_picture_description(outputfile, [name, exp], inputfile, gnufile)

            # calculate correlation output of allday averages
            # calculate correlation output of (last week - first week) weight
            names = sorted(exps[exp[4:]]['groups'][group])
            corrdata = [name + "_alldays"] # [name[:name.find("_group")]]
            corrdata2 = [name + "_lastminusfirstweek"] # [name[:name.find("_group")]]
            maxday = len(alldata[index])
            for strid in names:
                # calculate allday average
                nums = [float(alldata[index][x][headerline.index(strid)]) \
                        for x in range(1, maxday)]
                corrdata.append("%.1f" % numpy.mean(nums))
                corrdata2.append("%.1f" % (numpy.mean(nums[-7:]) - numpy.mean(nums[:7])))
            # write it out
            corrfile = trajognize.corr.util.get_corr_filename(exp, group, False)
            if corrfile not in corrfiles:
                if os.path.isfile(corrfile):
                    os.remove(corrfile)
                corrfiles.append(corrfile)
            headerline = trajognize.corr.util.strids2headerline(names, False)
            corrline = "\t".join(corrdata)
            trajognize.corr.util.add_corr_line(corrfile, headerline, corrline)
            corrline = "\t".join(corrdata2)
            trajognize.corr.util.add_corr_line(corrfile, headerline, corrline)


    # create SPGM gallery description
    spgm.create_gallery_description(os.path.join(head, plotdir), """Plotted %s statistics.
    Paint dates are indicated by gray vertical boxes in the background.
    Days and dailyvalidtimes are indicated at the top of the daily plots.
    """ % basename)

if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:])) # pass only real params to main
    except Exception as ex:
        print(ex, file=sys.stderr)
        import traceback
        traceback.print_exc(ex)
        sys.exit(1)
