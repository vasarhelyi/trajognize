"""This script generates plots for 'dailyobj' type trajognize.stat outputs.

Usage: plot_dailyobj.py projectfile inputfile(s)

where inputfile(s) is/are the output of trajognize.stat DailyObj object (.txt)

Use autorun.sh to create symbolic links to a common directory before running
this script in the common directory.

Output is written in subdirectories of input dir, organized according to
experiment, group, light and object type.

"""

import os, subprocess, sys, glob, re

# relative imports
import plot
import spgm

try:
    import trajognize.stat.experiments
    import trajognize.corr.util
except ImportError:
    sys.path.insert(
        0,
        os.path.abspath(
            os.path.join(os.path.dirname(sys.modules[__name__].__file__), "../..")
        ),
    )
    import trajognize.stat.experiments
    import trajognize.corr.util


GNUPLOT_TEMPLATE = """#!/usr/bin/gnuplot
reset
set term png size 800, 480
set xlabel "Days since start of experiment"
set ylabel "Percentage of presence at %(obj)s"
set autoscale fix
%(paintdates)s
set key outside autotitle columnhead
set title noenhanced

%(dailyvalidtimes_init)s

set out "%(outputfile)s"
set title "%(name)s.indiv\\n%(exp)s"
plot %(dailyvalidtimes_plot)s, \\
for [i = 2 : %(maxcol)d : 2] "%(inputfile)s" index %(index)d u 1:(column(i)*100.0) title columnhead(i) lc (i/2) with lines

set out "%(outputfileall)s"
set title "%(name)s.all\\n%(exp)s"
plot %(dailyvalidtimes_plot)s, \\
"%(inputfile)s" index %(index)d u 1:(column(%(maxcol)d+1)*100.0) title columnhead(%(maxcol)d+1) with lines

set out "%(outputfileabsgrad)s"
set ylabel "Abs(gradient) of presence at %(obj)s"
unset key
set title "%(name)s.absgrad\\n%(exp)s"
plot %(dailyvalidtimes_plot)s, \\
"%(inputfile)s" index %(index)d u 1:(column(%(maxcol)d+4)):(column(%(maxcol)d+5)) title columnhead(%(maxcol)d+4) with errorlines

"""


def get_gnuplot_script(
    inputfile,
    outputfile,
    outputfileall,
    outputfileabsgrad,
    name,
    index,
    maxcol,
    exp,
    obj,
    pdstr,
    dvt_init,
    dvt_plot,
):
    """Return .gnu script body as string."""
    data = {
        "inputfile": inputfile,
        "outputfile": outputfile,
        "outputfileall": outputfileall,
        "outputfileabsgrad": outputfileabsgrad,
        "name": name,
        "index": index,
        "maxcol": maxcol,
        "exp": exp,
        "obj": obj,
        "paintdates": pdstr,
        "dailyvalidtimes_init": dvt_init,
        "dailyvalidtimes_plot": dvt_plot,
    }
    return GNUPLOT_TEMPLATE % data


def get_categories_from_name(name):
    """Get light, object type and group from paragraph header (name), e.g.:

    dailyobj_daylight_wheel
    dailyobj_nightlight_home_group_B2

    """
    match = re.match(r"^dailyobj_(.*)_(.*)_group_(.*)$", name)
    if match:
        return (match.group(1), match.group(2), match.group(3))
    else:
        match = re.match(r"^dailyobj_(.*)_(.*)$", name)
        if match:
            return (match.group(1), match.group(2), "all")
        else:
            return (None, None)


def main(argv=[]):
    """Main entry point of the script."""
    if len(argv) < 2:
        print(__doc__)
        return
    projectfile = argv[0]
    if sys.platform.startswith("win"):
        inputfiles = glob.glob(argv[1])
    else:
        inputfiles = argv[1:]
    outdirs = []
    corrfiles = []

    project_settings = trajognize.settings.import_trajognize_settings_from_file(
        projectfile
    )
    if project_settings is None:
        print("Could not load project settings.")
        return
    exps = project_settings.experiments

    paintdates = trajognize.parse.parse_paintdates(
        os.path.join(os.path.dirname(trajognize.__file__), "../misc/paintdates.dat")
    )
    for inputfile in inputfiles:
        print("parsing", os.path.split(inputfile)[1])
        alldata = trajognize.parse.parse_stat_output_file(inputfile)
        headers = plot.grep_headers_from_file(inputfile, "dailyobj")
        exp = plot.get_exp_from_filename(inputfile)
        for index in range(len(headers)):
            maxcol = (
                len(headers[index]) - 5
            )  # _avg, _std, but all is _avg, _std, _num, absgrad_avg, absgrad_std
            # get categories
            name = headers[index][0]
            (light, object, group) = get_categories_from_name(name)

            # define output directory
            (head, tail, plotdir) = plot.get_headtailplot_from_filename(inputfile)
            statsum_basedir = os.path.split(head)[0]
            outdir = os.path.join(head, plotdir, exp, group, light, object)
            if not os.path.isdir(outdir):
                os.makedirs(outdir)
            # if this is a new output directory, clear SPGM descriptions
            if outdir not in outdirs:
                spgm.remove_picture_descriptions(outdir)
                outdirs.append(outdir)

            outputfilecommon = os.path.join(outdir, tail + "__" + name)
            gnufile = outputfilecommon + ".gnu"
            outputfile = outputfilecommon + ".indiv.png"
            outputfileall = outputfilecommon + ".all.png"
            outputfileabsgrad = outputfilecommon + ".absgrad.png"
            script = get_gnuplot_script(
                inputfile,
                outputfile,
                outputfileall,
                outputfileabsgrad,
                name,
                index,
                maxcol,
                exp,
                object,
                plot.get_gnuplot_paintdate_str(exps, exp[4:], paintdates),
                *plot.get_gnuplot_dailyvalidtimes_strs(exps, exp[4:])
            )
            with open(gnufile, "w") as f:
                f.write(script)
            try:
                subprocess.call(["gnuplot", gnufile])
            except WindowsError:
                print(
                    "  Error plotting '%s': gnuplot is not available on Windows" % name
                )
            # create SPGM picture description
            spgm.create_picture_description(
                outputfile, [name, "individual data", exp], inputfile, gnufile
            )
            spgm.create_picture_description(
                outputfileall, [name, "averaged data", exp], inputfile, gnufile
            )
            spgm.create_picture_description(
                outputfileabsgrad, [name, "absgrad data", exp], inputfile, gnufile
            )

            # calculate correlation output of allday averages
            if exp == "exp_all":
                continue
            names = sorted(exps[exp[4:]]["groups"][group])
            corrdata = [name]  # [name[:name.find("_group")]]
            for strid in names:
                # calculate allday average as a weighted sum of daily averages
                avgs = [
                    float(alldata[index][x][headers[index].index("%s_avg" % strid)])
                    for x in range(1, len(alldata[index]))
                ]
                nums = [
                    float(alldata[index][x][headers[index].index("all_num")])
                    for x in range(1, len(alldata[index]))
                ]
                corrdata.append(
                    "%g"
                    % (
                        sum(avgs[x] * nums[x] for x in range(len(avgs)))
                        / max(1, sum(nums[x] for x in range(len(avgs))))
                    )
                )
            # write it out
            headerline = trajognize.corr.util.strids2headerline(names, False)
            corrline = "\t".join(corrdata)
            corrfile = trajognize.corr.util.get_corr_filename(
                statsum_basedir, exp, group, False
            )
            if corrfile not in corrfiles:
                if os.path.isfile(corrfile):
                    os.remove(corrfile)
                corrfiles.append(corrfile)
            trajognize.corr.util.add_corr_line(corrfile, headerline, corrline)

    # create SPGM gallery descriptions
    spgm.create_gallery_description(head, "Daily barcode occurrences around objects")
    spgm.create_gallery_description(
        os.path.join(head, plotdir),
        """Plotted results for daily barcode occurrence around objects.
        Results are organized into subdirectories according to experiments, groups, light type and objects.
        Two output types exist: one plot for individual distributions together,
        one for averaged distribution of all pateks in the given group.

        Paint dates are indicated by gray vertical boxes in the background.
        Days and dailyvalidtimes are indicated at the top of the daily plots.""",
    )


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))  # pass only real params to main
    except Exception as ex:
        print(ex, file=sys.stderr)
        import traceback

        traceback.print_exc(ex)
        sys.exit(1)
