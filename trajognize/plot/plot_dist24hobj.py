"""This script generates plots for 'dist24hobj' type trajognize.stat outputs.

Usage: plot_dist24hobj.py projectfile inputfile(s)

where inputfile(s) is/are the output of trajognize.stat Dist24hObj object (.txt)

Use autorun.sh to create symbolic links to a common directory before running
this script in the common directory.

Output is written in subdirectories of input dir, organized according to
experiment and real/virt state.

"""

import os, subprocess, sys, glob, re

# relative imports
import plot
import spgm

try:
    import trajognize.stat.experiments
    import trajognize.stat.project
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(
        os.path.dirname(sys.modules[__name__].__file__), "../..")))
    import trajognize.stat.experiments
    import trajognize.stat.project



GNUPLOT_FEEDINGRECT_TEMPLATE = """set obj rect from "%02d:00:00", graph 0 to "%02d:00:00", graph 1 fc lt -1 fs transparent pattern 2 bo
"""

GNUPLOT_TEMPLATE = """#!/usr/bin/gnuplot
reset
set term png size 800, 480
set ylabel "percentage of presence (csplined)"
set yrange [0:]
set format y '%%3.0f%%%%'
set key outside
set xdata time
set timefmt "%%H:%%M:%%S"

set obj rect from "06:00:00", graph 0 to "18:00:00", graph 1 fs noborder solid 0.3 fc lt -1
set label "nightlight" at "12:00:00", graph 0.95 center
set label "daylight" at "3:00:00", graph 0.95 center
set label "daylight" at "21:00:00", graph 0.95 center

%(feedingrect)s

set format x "%%H"
set xlabel "time of day (h)"
set xrange ["00:00:00":"24:00:00"]

set out "%(outputfile)s"
set title "%(name)s.indiv_00_24\\n%(exp)s"
plot for [i = 2 : %(maxcol)d : 2] "%(inputfile)s" index %(index)d u 1:(column(i)*100.0) title columnhead(i) lc (i/2) with lines smooth csplines

set out "%(outputfileall)s"
set title "%(name)s.all_00_24\\n%(exp)s"
plot "%(inputfile)s" index %(index)d u 1:(column(%(maxcol)d+1)*100.0) title columnhead(%(maxcol)d+1) with lines smooth csplines

set format x "%%H:%%M"
set xlabel "time of day around feeding time (hh:mm)"

set out "%(outputfile_05_07)s"
set title "%(name)s.indiv_05_07\\n%(exp)s"
set xrange ["05:00:00":"07:00:00"]
plot for [i = 2 : %(maxcol)d : 2] "%(inputfile)s" index %(index)d u 1:(column(i)*100.0) title columnhead(i) lc (i/2) with lines smooth csplines

set out "%(outputfile_11_13)s"
set title "%(name)s.indiv_11_13\\n%(exp)s"
set xrange ["11:00:00":"13:00:00"]
plot for [i = 2 : %(maxcol)d : 2] "%(inputfile)s" index %(index)d u 1:(column(i)*100.0) title columnhead(i) lc (i/2) with lines smooth csplines

set out "%(outputfile_17_19)s"
set title "%(name)s.indiv_17_19\\n%(exp)s"
set xrange ["17:00:00":"19:00:00"]
plot for [i = 2 : %(maxcol)d : 2] "%(inputfile)s" index %(index)d u 1:(column(i)*100.0) title columnhead(i) lc (i/2) with lines smooth csplines
"""


def get_gnuplot_script(inputfile, outputfiles, outputfileall, name, index, maxcol,
        exp, weekday, project_settings):
    """Return .gnu script body as string."""
    data = {
        "inputfile": inputfile,
        "outputfile": outputfiles[0],
        "outputfileall": outputfileall,
        "outputfile_05_07": outputfiles[1],
        "outputfile_11_13": outputfiles[2],
        "outputfile_17_19": outputfiles[3],
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
    """Get weekday, object type and group from paragraph header (name), e.g.:

    dist24hobj.monday_wheel
    dist24hobj.tuesday_home_group_B2

    """
    match = re.match(r'^dist24hobj\.(.*)_(.*)_group_(.*)$', name)
    if match:
        return (match.group(1), match.group(2), match.group(3))
    else:
        match = re.match(r'^dist24hobj\.(.*)_(.*)$', name)
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
        headers = plot.grep_headers_from_file(inputfile, "dist24hobj")
        exp = plot.get_exp_from_filename(inputfile)
        for index in range(len(headers)):
            maxcol = len(headers[index])-3 # _avg, _std, but all is _avg, _std, _num
            # get categories
            name = headers[index][0]
            (weekday, object, group) = get_categories_from_name(name)

            # define output directory
            (head, tail, plotdir) = plot.get_headtailplot_from_filename(inputfile)
            outdir = os.path.join(head, plotdir, exp, group, object)
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
            outputfiles = []
            outputfiles.append(outputfilecommon + ".indiv_00_24.png")
            outputfiles.append(outputfilecommon + ".indiv_05_07.png")
            outputfiles.append(outputfilecommon + ".indiv_11_13.png")
            outputfiles.append(outputfilecommon + ".indiv_17_19.png")
            outputfileall = outputfilecommon + ".all_00_24.png"
            script = get_gnuplot_script(inputfile, outputfiles, outputfileall,
                    name, index, maxcol, exp, weekday, project_settings)
            with open(gnufile, 'w') as f:
                f.write(script)
            try:
                subprocess.call(["gnuplot", gnufile])
            except WindowsError:
                print("  Error plotting '%s': gnuplot is not available on Windows" % name)
            # create SPGM picture description
            spgm.create_picture_description(outputfiles[0],
                    [name, "individual data 00-24h", exp], inputfile, gnufile)
            spgm.create_picture_description(outputfiles[1],
                    [name, "individual data 05-07h", exp], inputfile, gnufile)
            spgm.create_picture_description(outputfiles[2],
                    [name, "individual data 11-13h", exp], inputfile, gnufile)
            spgm.create_picture_description(outputfiles[3],
                    [name, "individual data 17-19h", exp], inputfile, gnufile)
            spgm.create_picture_description(outputfileall,
                    [name, "averaged data", exp], inputfile, gnufile)

    # create SPGM gallery descriptions
    spgm.create_gallery_description(head, "24h distribution of barcode occurrences around objects")
    spgm.create_gallery_description(os.path.join(head, plotdir), """Plotted results for 24h barcode distribution around objects.
        Results are organized into subdirectories according to experiments, groups and objects.
        Two output types exist: one plot for individual distributions together,
        one for averaged distribution of all pateks in the given group.
        """)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:])) # pass only real params to main
    except Exception as ex:
        print(ex, file=sys.stderr)
        import traceback
        traceback.print_exc(ex)
        sys.exit(1)
