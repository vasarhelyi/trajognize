"""This script generates plots for 'dailyfqobj', 'cumulfqobj' and 'movavgfqobj' type
trajognize.stat (reordered) outputs in the following formats:

    - daily ranks
    - dominance scores (LDI, BBS, normDS) TODO: more?

Usage: plot_dailyranks.py inputfile(s)

where inputfile(s) is/are the output of trajognize.stat dailyfqobj_t object (.txt),
containing all dailyfqobj, cumulfqobj and movavgfqobj type results.

Output is written in subdirectories of input dir, organized according to
experiment, group, light and object.

"""

import os, subprocess, sys, glob, numpy
from plot import *
import spgm
try:
    import trajognize.parse
    import trajognize.calc.hierarchy
    import trajognize.stat.experiments
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(
        os.path.dirname(sys.modules[__name__].__file__), "../.."))) 
    import trajognize.parse
    import trajognize.calc.hierarchy
    import trajognize.stat.experiments


GNUPLOT_TEMPLATE = """#!/usr/bin/gnuplot
reset
set term png size 800, 480
set xlabel "Days since start of experiment"
set ylabel "Rank / dominance index in ordered %(datatype)s matrix"
set title "%(name)s\\n%(exp)s"
set key outside autotitle columnhead
set autoscale fix
%(paintdates)s

%(dailyvalidtimes_init)s

set out "%(outputfile)s"
plot %(dailyvalidtimes_plot)s, \\
for [i = 2 : %(maxcol)d] "%(inputfile)s" index %(index)d u 1:i lc (i-1) lw 2 with lines

set xlabel "Days since start of experiment"
set ylabel "Abs(gradient) of %(datatype)s matrix"
set title "absgrad_%(name)s\\n%(exp)s"
unset key
set out "%(outputfileabsgrad)s"
plot %(dailyvalidtimes_plot)s, \\
"%(inputfile)s" index %(index)d u 1:(column(%(maxcol)d+1)):(column(%(maxcol)d+2)) lw 2 with errorlines

"""


def get_gnuplot_script(inputfile, outputfile, outputfileabsgrad, name, maxcol,
        exp, datatype, index, pdstr, dvt_init, dvt_plot):
    """Return .gnu script body as string."""
    data = {
        "inputfile": inputfile,
        "outputfile": outputfile,
        "outputfileabsgrad": outputfileabsgrad,
        "name": name,
        "maxcol": maxcol,
        "exp": exp,
        "datatype": datatype,
        "index": index,
        "paintdates": pdstr,
        "dailyvalidtimes_init": dvt_init,
        "dailyvalidtimes_plot": dvt_plot,
    }
    return GNUPLOT_TEMPLATE % data


def get_categories_from_name(name):
    """Get datatype, light, object, group and day from paragraph header (name), e.g.:

    dailyfqobj_daylight_water_group_G3S_day_1
    dailyfqobj_nightlight_food_group_G2L_day_4_F
    cumulfqobj_daylight_water_group_G3S_day_1
    cumulfqobj_nightlight_food_group_G2L_day_4_F
    movavgfqobj_daylight_water_group_G3S_day_1
    movavgfqobj_nightlight_food_group_G2L_day_4_F

    """
    match = re.match(r'^(.*)_(.*)_(.*)_group_(.*)_day_([0-9A-Z]*)', name)
    if match:
        return (match.group(1), match.group(2), match.group(3), match.group(4), int(match.group(5)))
    else:
        return (None, None, None, None, None)


def main(argv=[]):
    """Main entry point of the script."""
    def writedata(data, localname):
        # write header
        f.write("%s\t%s\tabsgrad_avg\tabsgrad_std\n" % (localname, "\t".join(strids)))
        # write data
        for i in xrange(len(data[key][strids[0]])):
            f.write("%d" % i)
            absgrad = []
            for strid in strids:
                f.write("\t%g" % data[key][strid][i])
                if i:
                    absgrad.append(abs(data[key][strid][i] - data[key][strid][i-1]))
                else:
                    absgrad.append(abs(data[key][strid][i] - 0))
            f.write("\t%g\t%g\n" % (numpy.mean(absgrad), numpy.std(absgrad)))
        f.write("\n\n")

    def writegnu(localname, index):
        # write .gnu
        (localhead, localtail) = os.path.split(outputfilecommon)
        gnufile = os.path.join(localhead, localtail.replace("dailyranks", localname) + ".gnu")
        outputfile = gnufile[:-4] + ".png"
        outputfileabsgrad = gnufile[:-4] + "_absgrad.png"
        name = "%s_%s_%s_group_%s" % (localname, datatype, object, group)
        maxcol = len(strids)+1
        script = get_gnuplot_script(txtfile, outputfile, outputfileabsgrad, name,
                    maxcol, exp, datatype, index,
                    get_gnuplot_paintdate_str(exps, exp[4:], paintdates),
                    *get_gnuplot_dailyvalidtimes_strs(exps, exp[4:]))
        with open(gnufile, 'w') as f:
            f.write(script)
        try:
            subprocess.call(["gnuplot", gnufile])
        except WindowsError:
            print("  Error plotting '%s': gnuplot is not available on Windows" % name)
        # create SPGM picture description
        spgm.create_picture_description(outputfile, [name, exp], txtfile, gnufile)
        spgm.create_picture_description(outputfileabsgrad,
                [name, "absgrad data", exp], txtfile, gnufile)



    if not argv:
        print(__doc__)
        return
    if sys.platform.startswith('win'):
        inputfiles = glob.glob(argv[0])
    else:
        inputfiles = argv
    exps = trajognize.stat.experiments.get_initialized_experiments()
    paintdates = trajognize.parse.parse_paintdates(os.path.join(
        os.path.dirname(trajognize.__file__), '../misc/paintdates.dat'))
    for inputfile in inputfiles:
        # reordered file should be the input
        (head, tail, plotdir) = get_headtailplot_from_filename(inputfile)
        exp = get_exp_from_filename(inputfile)
        # initialize daily rank database, where key is [(group, object)][strid]
        dailyranks = {}
        dailynormDS = {}
        dailyBBS = {}
        dailyLDI = {}
        # parse data file
        alldata = trajognize.parse.parse_stat_output_file(inputfile)
        for index in xrange(len(alldata)):
            # get categories
            name = alldata[index][0][0]
            (datatype, light, object, group, day) = get_categories_from_name(name)
            i = index/3 # F, C, D
            # symmetry, transitivity
            if name.startswith(datatype) and name.endswith("_F"):
                # calculate dominance indices
                datadict = convert_matrixdata_to_dict(alldata[index])
                normDS = trajognize.calc.hierarchy.deVries_modified_Davids_score(datadict)
                BBS = trajognize.calc.hierarchy.BBS_scale_score(datadict)
                LDI = trajognize.calc.hierarchy.Lindquist_dominance_index(datadict)
                # add new idorder entry for all Dominant parts
                strids = alldata[index][0][1:]
                for j in xrange(len(strids)):
                    key = (group, light, object, datatype)
                    strid = strids[j]
                    # initialize list if not present yet for a given key
                    if key not in dailyranks:
                        dailyranks[key] = {}
                        dailynormDS[key] = {}
                        dailyBBS[key] = {}
                        dailyLDI[key] = {}
                    if strid not in dailyranks[key]:
                        dailyranks[key][strid] = []
                        dailynormDS[key][strid] = []
                        dailyBBS[key][strid] = []
                        dailyLDI[key][strid] = []
                    # small error checking on correct day order
                    if day != len(dailyranks[key][strid]):
                        print("day", day, "dailyranks[key]", dailyranks[key])
                        raise ValueError("0/0")
                    # add new rank to daily list
                    dailyranks[key][strid].append(j)
                    dailynormDS[key][strid].append(normDS[strid])
                    dailyBBS[key][strid].append(BBS[strid])
                    dailyLDI[key][strid].append(LDI[strid])

        # write dailyrank database to file and plot it as well
        for key in dailyranks:
            (group, light, object, datatype) = key
            strids = sorted(dailyranks[key])
            # define output directory
            outdir = os.path.join(head, plotdir, exp, group, light, object, datatype)
            if not os.path.isdir(outdir): os.makedirs(outdir)
            outputfilecommon = os.path.join(outdir, "dailyranks__%s__%s_%s_%s_group_%s" % \
                    (exp, datatype, light, object, group))
            # write .txt
            txtfile = outputfilecommon + ".txt"
            f = open(txtfile, "w")
            # write comments
            f.write("# This is a post processed file containing dominance indices and ID ranks\n"
                    "# of Eades-ordered %s matrices for each day in the given experiment.\n" % datatype)
            f.write("# Experiment = %s\n" % exp)
            f.write("# Datatype = %s\n" % datatype)
            f.write("# Light = %s\n" % light)
            f.write("# Object = %s\n" % object)
            f.write("# Group = %s\n\n" % group)

            writedata(dailyranks, "dailyranks")
            writedata(dailynormDS, "dailynormDS")
            writedata(dailyBBS, "dailyBBS")
            writedata(dailyLDI, "dailyLDI")
            f.close()
            writegnu("dailyranks", 0)
            writegnu("dailynormDS", 1)
            writegnu("dailyBBS", 2)
            writegnu("dailyLDI", 3)

    # create SPGM gallery description
    spgm.create_gallery_description(os.path.join(head, plotdir), """Plotted daily ranks and dominance indices
        of the individuals based on the positions in the Eades-ordered matrices.
        The following dominance indices are calculated: normDS, LDI, BBS
        Results are shown for dailyfqobj, movavgfqobj and cumulfqobj.

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
