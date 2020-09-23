"""This script generates plots for 'dist24h' type trajognize.stat outputs.

Usage: plot_dist24h.py projectfile inputfile(s)

where inputfile(s) is/are the output of trajognize.stat Dist24h object (.txt)

Use autorun.sh to create symbolic links to a common directory before running
this script in the common directory.

Output is written in subdirectories of input dir, organized according to
experiment and real/virt state.

"""

import os, subprocess, sys, glob

from . import plot
from . import spgm

try:
    import trajognize.stat.experiments
    import trajognize.settings
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(
        os.path.dirname(sys.modules[__name__].__file__), "../..")))
    import trajognize.stat.experiments
    import trajognize.settings


GNUPLOT_FEEDINGRECT_TEMPLATE = """set obj rect from "%02d:00:00", graph 0 to "%02d:00:00", graph 1 fc lt -1 fs transparent pattern 2 bo
"""

GNUPLOT_TEMPLATE = """#!/usr/bin/gnuplot
reset
set term png size 800, 480
set xlabel "time of day (h)"
set ylabel "percentage of presence"
set yrange [0:100]
set format y '%%3.0f%%%%'
set key outside
set xdata time
set timefmt "%%H:%%M:%%S"
set format x "%%H"

set obj rect from "06:00:00", graph 0 to "18:00:00", graph 1 fs noborder solid 0.3 fc lt -1
set label "nightlight" at "12:00:00", graph 0.95 center
set label "daylight" at "3:00:00", graph 0.95 center
set label "daylight" at "21:00:00", graph 0.95 center

%(feedingrect)s

set out "%(outputfile)s"
set title "%(name)s.indiv\\n%(exp)s"
plot for [i = 2 : %(maxcol)d : 2] "%(inputfile)s" index %(index)d u 1:(column(i)*100.0) title columnhead(i) lc (i/2) with lines

set out "%(outputfileall)s"
set title "%(name)s.all\\n%(exp)s"
plot "%(inputfile)s" index %(index)d u 1:(column(%(maxcol)d+1)*100.0) title columnhead(%(maxcol)d+1) with lines
"""


def get_gnuplot_script(inputfile, outputfile, outputfileall, name, index, maxcol,
        exp, weekday, project_settings):
    """Return .gnu script body as string."""
    data = {
        "inputfile": inputfile,
        "outputfile": outputfile,
        "outputfileall": outputfileall,
        "name": name,
        "index": index,
        "maxcol": maxcol,
        "exp": exp,
        "feedingrect": "",
    }
    if weekday in project_settings.weekly_feeding_times:
        for (start, duration) in project_settings.weekly_feeding_times[weekday]:
            data['feedingrect'] += GNUPLOT_FEEDINGRECT_TEMPLATE % (start, start + duration)
    return GNUPLOT_TEMPLATE % data


def get_categories_from_name(name):
    """Get weekday real/virtual state and group from paragraph header (name), e.g.:

    dist24h.monday_REAL
    dist24h.tuesday_VIRTUAL_group_A1

    """
    match = re.match(r'^dist24h\.(.*)_(.*)_group_(.*)$', name)
    if match:
        return (match.group(1), match.group(2), match.group(3))
    else:
        match = re.match(r'^dist24h\.(.*)_(.*)$', name)
        if match:
            return (match.group(1), match.group(2), "all")
        else:
            return (None, None, None)


def main(argv=[]):
    """Main entry point of the script."""
    if len(argv) < 2:
        print(__doc__)
        return
    projectfile = argv[0]
    if sys.platform.startswith('win'):
        inputfiles = glob.glob(argv[1])
    else:
        inputfiles = argv[1:]
    outdirs = []
    project_settings = trajognize.settings.import_trajognize_settings_from_file(projectfile)
    if project_settings is None:
        print("Could not load project settings.")
        return
    for inputfile in inputfiles:
        print("parsing", os.path.split(inputfile)[1])
        headers = plot.grep_headers_from_file(inputfile, "dist24h")
        exp = plot.get_exp_from_filename(inputfile)
        for index in range(len(headers)):
            maxcol = len(headers[index])-3 # _avg, _std, but all is _avg, _std, _num
            # get categories
            name = headers[index][0]
            (weekday, realvirt, group) = get_categories_from_name(name)

            # define output directory
            (head, tail, plotdir) = plot.get_headtailplot_from_filename(inputfile)
            outdir = os.path.join(head, plotdir, exp, group, realvirt)
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
            script = get_gnuplot_script(inputfile, outputfile, outputfileall,
                    name, index, maxcol, exp, weekday, project_settings)
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
    spgm.create_gallery_description(head, "24h distribution of barcode occurrences")
    spgm.create_gallery_description(os.path.join(head, plotdir), """Plotted results for 24h barcode distribution.
        Results are organized into subdirectories according to experiments, groups and real/virtual state.
        A barcode is REAL if it was found using color blob data.
        It is VIRTUAL if it was not found but was assumed to be somewhere (e.g. under shelter)
        Two output types exist: one plot for individual distributions together,
        one for averaged distribution of all pateks in the group.
        """)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:])) # pass only real params to main
    except Exception as ex:
        print(ex, file=sys.stderr)
        import traceback
        traceback.print_exc(ex)
        sys.exit(1)
