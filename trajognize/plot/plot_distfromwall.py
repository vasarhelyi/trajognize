"""This script generates plots for '-s distfromwall' type trajognize.stat outputs.

Usage: plot_distfromwall.py inputfile(s)

where inputfile(s) is/are the output of trajognize.statsum

Output is written in subdirectories of input dir, organized according to
experiment, group, light condition, real/virtual state.

"""

import os, subprocess, sys, glob, re

from .plot import *

from . import spgm

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

GNUPLOT_TEMPLATE_AVG = """#!/usr/bin/gnuplot
reset
set term png size 800, 480
set xlabel "Days of the experiment"
set ylabel "Average distance from wall (px)"
set title "%(name)s\\n%(exp)s"
set key outside autotitle columnhead
set autoscale fix
%(paintdates)s

%(dailyvalidtimes_init)s

set out "%(outputfile)s"
# old with [avg, std]:
# plot %(dailyvalidtimes_plot)s, \\
# for [i = 2 : %(maxcol)d : 2] "%(inputfile)s" index %(index)d u 0:i:(i+1) lc (i/2 + 1) with yerrorlines
# new with [avg, std, num]:
plot %(dailyvalidtimes_plot)s, \\
for [i = 2 : %(maxcol)d : 3] "%(inputfile)s" index %(index)d u 0:i:(i+1) lc (i/3 + 1) with yerrorlines

set out "%(outputfileabsgrad)s"
set ylabel "Abs(gradient) of distfromwall"
unset key
set title "%(name)s.absgrad\\n%(exp)s"
plot %(dailyvalidtimes_plot)s, \\
"%(inputfile)s" index %(index)d u 0:(column(%(maxcol)d+1)):(column(%(maxcol)d+2)) title columnhead(%(maxcol)d+1) with errorlines


"""

GNUPLOT_TEMPLATE_DIST = """#!/usr/bin/gnuplot
reset
set term pngcairo
set xlabel "Days of the experiment"
set ylabel "Distance from wall (px)"
set cblabel "log(weight)
set title "%(name)s\\n%(exp)s"
set key autotitle columnhead
set autoscale fix
%(paintdates)s
set palette rgbformulae 7,5,15
f(x) = (x==0) ? 0 : log10(x)
set out "%(outputfile)s"
plot "%(inputfile)s" index %(index)d matrix using ($1-1):($2-1):(f($3)) every ::1:1 with image
"""

GNUPLOT_TEMPLATE_PAINTDATE_DST = """set obj rect from %d, graph 0 to %d, graph 1 fc lt 2 fs transparent solid 0.2 noborder front"""

def get_gnuplot_script_avg(inputfile, outputfile, outputfileabsgrad, name,
        maxcol, exp, index, pdstr, dvt_init, dvt_plot):
    """Return .gnu script body as string for _avg plot."""
    data = {
        "inputfile": inputfile,
        "outputfile": outputfile,
        "outputfileabsgrad": outputfileabsgrad,
        "name": name,
        "maxcol": maxcol,
        "exp": exp,
        "index": index,
        "paintdates": pdstr,
        "dailyvalidtimes_init": dvt_init,
        "dailyvalidtimes_plot": dvt_plot,
    }
    return GNUPLOT_TEMPLATE_AVG % data


def get_gnuplot_script_dist(inputfile, outputfile, name, maxcol, exp, index, pdstr):
    """Return .gnu script body as string for _avg plot."""
    data = {
        "inputfile": inputfile,
        "outputfile": outputfile,
        "name": name,
        "maxcol": maxcol,
        "exp": exp,
        "index": index,
        "paintdates": pdstr,
    }
    return GNUPLOT_TEMPLATE_DIST % data


def get_categories_from_name(name):
    """Get avg/dist, light, allspeed/onlymoving, real/virt and group/strid from paragraph header (name), e.g.:

    distfromwall_avg_daylight_allspeed_REAL_group_A1
    distfromwall_dist_nightlight_onlymoving_VIRTUAL_patek_ORG

    """
    match = re.match(r'^distfromwall_(avg|dist)_([a-z]*)_(allspeed|onlymoving)_([A-Z]*)_(group|patek)_(.*)', name)
    if match:
        return (match.group(1), match.group(2), match.group(3), match.group(4), match.group(6))
    else:
        return (None, None, None, None, None)


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
        headers = grep_headers_from_file(inputfile, "distfromwall_")
        (head, tail, plotdir) = get_headtailplot_from_filename(inputfile)
        exp = get_exp_from_filename(inputfile)
        # plot all indices
        for index in range(len(headers)):
            # get categories
            name = headers[index][0]
            (avgdist, light, mot, realvirt, groupstrid) = get_categories_from_name(name)
            if avgdist == "avg":
                group = groupstrid
            elif avgdist == "dist":
                strid = groupstrid
                if exp == "exp_all":
                    experiment = None
                    group = "all"
                else:
                    experiment = exps[exp[4:]]
                    if strid == "all":
                        group = "all"
                    else:
                        group = experiment['groupid'][strid]
            else:
                0/0
            # create output directory
            outdir = os.path.join(head, plotdir, exp, group, light, realvirt)
            if not os.path.isdir(outdir): os.makedirs(outdir)
            # if this is a new output directory, clear SPGM descriptions
            if outdir not in outdirs:
                spgm.remove_picture_descriptions(outdir)
                outdirs.append(outdir)
            outputfilecommon = os.path.join(outdir, tail + '__' + name)
            gnufile = outputfilecommon + ".gnu"
            outputfile = outputfilecommon + ".png"
            if avgdist == "avg":
                maxcol = len(headers[index])-2 # absgrad_avg, absgrad_std
                outputfileabsgrad = outputfilecommon + ".absgrad.png"
                script = get_gnuplot_script_avg(inputfile, outputfile,
                        outputfileabsgrad, name, maxcol, exp, index,
                        get_gnuplot_paintdate_str(exps, exp[4:], paintdates),
                        *get_gnuplot_dailyvalidtimes_strs(exps, exp[4:]))
            elif avgdist == "dist":
                maxcol = len(headers[index])
                script = get_gnuplot_script_dist(inputfile, outputfile, name,
                        maxcol, exp, index,
                        get_gnuplot_paintdate_str(exps, exp[4:], paintdates,
                        GNUPLOT_TEMPLATE_PAINTDATE_DST))
            with open(gnufile, 'w') as f:
                f.write(script)
            try:
                subprocess.call(["gnuplot", gnufile])
            except WindowsError:
                print("  Error plotting '%s': gnuplot is not available on Windows" % name)
            # create SPGM picture description
            spgm.create_picture_description(outputfile, [name, exp], inputfile, gnufile)
            if avgdist == "avg":
                spgm.create_picture_description(outputfileabsgrad,
                        [name, "absgrad data", exp], inputfile, gnufile)

            # calculate correlation output of allday averages
            if avgdist != "avg" or exp == "exp_all": continue
            names = sorted(exps[exp[4:]]['groups'][group])
            corrdata = [name] # [name[:name.find("_group")]]
            for strid in names:
                # calculate allday average as a weighted sum of daily averages
                avgs = [float(alldata[index][x][headers[index].index("%s.avg" % strid)]) \
                        for x in range(1, len(alldata[index]))]
                nums = [float(alldata[index][x][headers[index].index("%s.num" % strid)]) \
                        for x in range(1, len(alldata[index]))]
                corrdata.append("%.1f" % (sum(avgs[x]*nums[x] for x in range(len(avgs))) /
                        max(1, sum(nums[x] for x in range(len(avgs)))) ))
            # write it out
            headerline = trajognize.corr.util.strids2headerline(names, False)
            corrline = "\t".join(corrdata)
            corrfile = trajognize.corr.util.get_corr_filename(exp, group, False)
            if corrfile not in corrfiles:
                if os.path.isfile(corrfile):
                    os.remove(corrfile)
                corrfiles.append(corrfile)
            trajognize.corr.util.add_corr_line(corrfile, headerline, corrline)


    # create SPGM gallery description
    spgm.create_gallery_description(head, """Distance-from-wall statistics""")
    spgm.create_gallery_description(os.path.join(head, plotdir), """Plotted distfromwall statistics.
            There are three types of outputs:
            _avg  - average and standard deviation of the daily distance-from-wall distribution is plotted
            _dist - the whole distribution for each day is plotted for all strid-s separately as a heatmap
            _absgrad - the daily abs(gradient), i.e. change of averaged group distance-from-wall

            Paint dates are indicated by gray vertical boxes in the background.
            Days and dailyvalidtimes are indicated at the top of the daily plots.

            Distance from wall is actually the distance from walls, home or wheel, not over the latter objects.
            """)

if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:])) # pass only real params to main
    except Exception as ex:
        print(ex, file=sys.stderr)
        import traceback
        traceback.print_exc(ex)
        sys.exit(1)
