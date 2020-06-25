"""This script generates plots for '-s heatmap -d' type trajognize.stat outputs.

Usage: plot_heatmap_dailyoutput.py inputfile(s)

where inputfile(s) is/are the output of trajognize.calc.calc_heatmap_dailyoutput.py

Output is written in subdirectories of input dir, organized according to
experiment, group, light condition, real/virtual state, depending on plotted stat.

"""

import os, subprocess, sys, glob, re

from .plot import *

from . import spgm

try:
    import trajognize.stat.init
    import trajognize.stat.experiments
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(
        os.path.dirname(sys.modules[__name__].__file__), "../..")))
    import trajognize.stat.init
    import trajognize.stat.experiments

GNUPLOT_TEMPLATE = """#!/usr/bin/gnuplot
reset
set term png
set datafile missing "nan"
set xlabel "Days of the experiment"
set ylabel "%(datatype)s"
set title "%(name)s\\n%(expgroup)s"
set key autotitle columnhead
set autoscale fix
%(paintdates)s

%(dailyvalidtimes_init)s

set out "%(outputfile)s"
plot %(dailyvalidtimes_plot)s, \\
for [i = 2 : %(maxcol)d] "%(inputfile)s" index %(index)d u 0:i lc (i-1) with lines

set out "%(outputfileabsgrad)s"
set ylabel "Abs(gradient) of %(name)s"
unset key
set title "%(name)s.absgrad\\n%(expgroup)s"
plot %(dailyvalidtimes_plot)s, \\
"%(inputfile)s" index %(index)d u 0:(column(%(maxcol)d+1)):(column(%(maxcol)d+2)) title columnhead(%(maxcol)d+1) with errorlines

"""


def get_gnuplot_script(inputfile, outputfile, outputfileabsgrad, name, maxcol,
        expgroup, datatype, index, pdstr, dvt_init, dvt_plot):
    """Return .gnu script body as string."""
    data = {
        "inputfile": inputfile,
        "outputfile": outputfile,
        "outputfileabsgrad": outputfileabsgrad,
        "name": name,
        "maxcol": maxcol,
        "expgroup": expgroup,
        "datatype": datatype,
        "index": index,
        "paintdates": pdstr,
        "dailyvalidtimes_init": dvt_init,
        "dailyvalidtimes_plot": dvt_plot,
    }
    return GNUPLOT_TEMPLATE % data


def get_categories_from_name(name):
    """Get light, realvirt and datatype from paragraph header (name), e.g.:

    heatmap_dailyoutput_daylight_REAL_mean_all
    heatmap_dailyoutput_nightlight_VIRTUAL_std_nonzero

    """
    match = re.match(r'^heatmap_dailyoutput_([a-z]*)_([A-Z]*)_(.*)', name)
    if match:
        return (match.group(1), match.group(2), match.group(3), )
    else:
        return (None, None, None)


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
    exps = trajognize.stat.experiments.get_initialized_experiments()
    paintdates = trajognize.parse.parse_paintdates(os.path.join(
        os.path.dirname(trajognize.__file__), '../misc/paintdates.dat'))
    for inputfile in inputfiles:
        print("parsing", os.path.split(inputfile)[1])
        # calc_heatmap_dailyoutput.py output file should be the input
        headers = grep_headers_from_file(inputfile, "heatmap_dailyoutput_")
        (head, tail, plotdir) = get_headtailplot_from_filename(inputfile)
        expgroup = get_exp_from_filename(inputfile)
        (exp, group) = expgroup.split("__")
        group = group[6:] # remove 'group_'
        # plot all indices
        for index in range(len(headers)):
            # get categories
            name = headers[index][0]
            (light, realvirt, datatype) = get_categories_from_name(name)
            name = name[20:] # remove 'heatmap_dailyoutput_'
            outdir = os.path.join(head, plotdir, exp, group, light, realvirt)
            if not os.path.isdir(outdir): os.makedirs(outdir)

            # if this is a new output directory, clear SPGM descriptions
            if outdir not in outdirs:
                spgm.remove_picture_descriptions(outdir)
                outdirs.append(outdir)
            outputfilecommon = os.path.join(outdir, tail + '__' + name)
#            print("length of filename:", len(outputfilecommon))
            gnufile = outputfilecommon + ".gnu"
            outputfile = outputfilecommon + ".png"
            outputfileabsgrad = outputfilecommon + ".absgrad.png"
            maxcol = len(headers[index])-2 # absgrad_avg, absgrad_std
            script = get_gnuplot_script(inputfile, outputfile, outputfileabsgrad,
                    name, maxcol, expgroup, datatype, index,
                    get_gnuplot_paintdate_str(exps, exp[4:], paintdates),
                    *get_gnuplot_dailyvalidtimes_strs(exps, exp[4:]))
            with open(gnufile, 'w') as f:
                f.write(script)
            try:
                subprocess.call(["gnuplot", gnufile])
            except WindowsError:
                print("  Error plotting '%s': gnuplot is not available on Windows" % name)
            # create SPGM picture description
            spgm.create_picture_description(outputfile, [name, expgroup], inputfile, gnufile)
            spgm.create_picture_description(outputfileabsgrad,
                    [name, "absgrad data", expgroup], inputfile, gnufile)

    # create SPGM gallery description
    spgm.create_gallery_description(os.path.join(head, plotdir), """Plotted heatmap dailyoutput statistics:
            mean_all      - mean value of all pixels on the heatmap
            std_all       - standard deviation of all pixels on the heatmap
            sum_all       - weighted sum of all pixel values on the heatmap
            count_nonzero - number of nonzero pixels on the heatmap
            percent_nonzero - number of nonzero pixels on the heatmap as a percentage of experiment area
            mean_nonzero  - mean value of all nonzero pixels on the heatmap
            std_nonzero   - standard deviation of all nonzero pixels on the heatmap
            count_territory - number of pixels on the heatmap that are larger than territory threshold
            percent_territory - number of pixels on the heatmap that are larger than territory threshold as a percentage of experiment area
            mean_territory  - mean value of all pixels on the heatmap that are larger than territory threshold
            std_territory   - standard deviation of all pixels on the heatmap that are larger than territory threshold

            and all of the above normalized with the number of frames used for the heatmap (REAL and VIRT together)

            Paint dates are indicated by gray vertical boxes in the background.
            Days and dailyvalidtimes are indicated at the top of the daily plots.""")

if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:])) # pass only real params to main
    except Exception as ex:
        print(ex, file=sys.stderr)
        import traceback
        traceback.print_exc(ex)
        sys.exit(1)
