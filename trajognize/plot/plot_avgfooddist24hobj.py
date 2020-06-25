"""This script generates plots for 'avgfooddist24hobj' type outputs.

Usage: plot_avgfooddist24hobj.py inputfile(s)

where inputfile(s) is/are the output of trajognize.calc.calc_dist24hobj_avgfood.py

Use autorun.sh to create symbolic links to a common directory before running
this script in the common directory.

Output is written in subdirectories of input dir, organized according to
experiment and real/virt state.

"""

import os, subprocess, sys, glob

from .plot import *

from . import spgm

try:
    import trajognize.stat.experiments
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(
        os.path.dirname(sys.modules[__name__].__file__), "../..")))
    import trajognize.stat.experiments


GNUPLOT_TEMPLATE = """#!/usr/bin/gnuplot
reset
set term png size 800, 480
set ylabel "average percentage of presence"
set yrange [0:]
set format y '%%3.0f%%%%'
set key outside
set xdata time
set timefmt "%%H:%%M:%%S"

set obj rect from "01:00:00", graph 0 to "02:00:00", graph 1 fc lt -1 fs transparent pattern 2 bo

set format x "%%H:%%M"
set xlabel "time around feeding (h)"
set xrange ["00:00:00":"02:00:00"]

# individual plot
set out "%(outputfile)s"
set title "%(name)s.indiv\\n%(exp)s"
plot for [i = 2 : %(maxcol)d : 2] "%(inputfile)s" index %(index)d u 1:(column(i)*100.0) title columnhead(i) lc (i/2) with lines

# common (all) plot)
set out "%(outputfileall)s"
set title "%(name)s.all\\n%(exp)s"
plot "%(inputfile)s" index %(index)d u 1:(column(%(maxcol)d+1)*100.0) title columnhead(%(maxcol)d+1) with lines

# cumulative plot
set ylabel "Cumulative presence at feeding (min)"
set title "%(name)s.cumul\\n%(exp)s"
set format y '%%g'
set out "%(outputfilecumul)s"
plot for [i = 2 : %(maxcol)d : 2] "%(inputfile)s" index %(index)d every ::61 u 1:(column(i)) smooth cumulative notitle lw 2 lc (i/2) with lines, \\
     for [i = 2 : %(maxcol)d : 2] "" index %(index)d every ::0::0 u 1:(NaN) title columnhead(i) lw 2 lc (i/2) with lines

"""


def get_gnuplot_script(inputfile, outputfile, outputfileall, outputfilecumul, name, index, maxcol,
        exp):
    """Return .gnu script body as string."""
    data = {
        "inputfile": inputfile,
        "outputfile": outputfile,
        "outputfileall": outputfileall,
        "outputfilecumul": outputfilecumul,
        "name": name,
        "index": index,
        "maxcol": maxcol,
        "exp": exp,
    }
    return GNUPLOT_TEMPLATE % data


def get_categories_from_name(name):
    """Get weekday, object type and group from paragraph header (name), e.g.:

    avgfooddist24hobj.monday_wheel
    avgfooddist24hobj.alldays_home_group_B2

    """
    match = re.match(r'^avgfooddist24hobj\.(.*)_(.*)_group_(.*)$', name)
    if match:
        return (match.group(1), match.group(2), match.group(3))
    else:
        match = re.match(r'^avgfooddist24hobj\.(.*)_(.*)$', name)
        if match:
            return (match.group(1), match.group(2), "all")
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
    for inputfile in inputfiles:
        print("parsing", os.path.split(inputfile)[1])
        headers = grep_headers_from_file(inputfile, "avgfooddist24hobj")
        exp = get_exp_from_filename(inputfile)
        for index in range(len(headers)):
            maxcol = len(headers[index])-3 # _avg, _std, but all is _avg, _std, _num
            # get categories
            name = headers[index][0]
            (weekday, object, group) = get_categories_from_name(name)

            # define output directory
            (head, tail, plotdir) = get_headtailplot_from_filename(inputfile)
            outdir = os.path.join(head, plotdir, exp, group)
            if not os.path.isdir(outdir): os.makedirs(outdir)
            # if this is a new output directory, clear SPGM descriptions
            if outdir not in outdirs:
                spgm.remove_picture_descriptions(outdir)
                outdirs.append(outdir)

            outputfilecommon = os.path.join(outdir, tail + '__' + name)
            if weekday in trajognize.stat.experiments.ordered_weekdays:
                outputfilecommon = outputfilecommon.replace(weekday, "%d%s" % \
                        (trajognize.stat.experiments.ordered_weekdays.index(weekday) + 1, weekday))
            gnufile = outputfilecommon + ".gnu"
            outputfile = outputfilecommon + ".indiv.png"
            outputfileall = outputfilecommon + ".all.png"
            outputfilecumul = outputfilecommon + ".cumul.png"
            script = get_gnuplot_script(inputfile, outputfile, outputfileall, outputfilecumul,
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
            spgm.create_picture_description(outputfilecumul,
                    [name, "cumulative data", exp], inputfile, gnufile)

    # create SPGM gallery descriptions
    spgm.create_gallery_description(head, "Averaged barcode distribution around food during feeding times.")
    spgm.create_gallery_description(os.path.join(head, plotdir), """Plotted results for barcode distribution around food during feeding times.
        Results are organized into subdirectories according to experiments and groups.
        Three output types exist: one plot for individual distributions together,
        one for averaged distribution of all pateks in the given group, and one
        as a cumulative feeding time for individuals.
        """)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:])) # pass only real params to main
    except Exception as ex:
        print(ex, file=sys.stderr)
        import traceback
        traceback.print_exc(ex)
        sys.exit(1)
