"""This script calculates difference from average heatmaps for all
experiments, groups, light conditions and real/virt states.

Usage: calc_heatmapdiff.py projectfile inputfile(s)

where inputfile(s) is/are the output of trajognize.stat HeatMap or MotionMap object (.txt)

Note that *.zip is also needed in the same directory for
quick python object reload of HeatMap or MotionMap output.

Use plot_heatmap.py before with autorun.sh to create symbolic links to a common
directory before running this script in the common directory.

Output is written in a subdirectory of input dir.

"""

import os, subprocess, sys, glob, re

try:
    import trajognize.settings
    import trajognize.parse
    import trajognize.stat.init
    import trajognize.stat.experiments
    import trajognize.plot.plot
    import trajognize.plot.spgm
except ImportError:
    sys.path.insert(
        0,
        os.path.abspath(
            os.path.join(os.path.dirname(sys.modules[__name__].__file__), "../..")
        ),
    )
    import trajognize.settings
    import trajognize.parse
    import trajognize.stat.init
    import trajognize.stat.experiments
    import trajognize.plot.plot
    import trajognize.plot.spgm


def get_strid_from_tail(tail):
    """Return strid from the input file tail that looks like e.g.:

    stat_heatmap.GBP__exp_fifth_G1_G4_large_G2_G3_small.txt

    """
    return tail[tail.find(".") + 1 : tail.find("__")]


def main(argv=[]):
    """Main entry point of the script."""
    if len(argv) < 2:
        print(__doc__)
        return
    if sys.platform.startswith("win"):
        projectfile = argv[0]
        inputfiles = glob.glob(argv[1])
    else:
        projectfile = argv[0]
        inputfiles = argv[1:]

    project_settings = trajognize.settings.import_trajognize_settings_from_file(
        projectfile
    )
    if project_settings is None:
        print("Could not load project settings.")
        return
    exps = project_settings.experiments
    outdirs = []

    # gather info for main data dictionary to know what to average
    filedict = {}  # keys are hashable (exp, group, light, realvirt) tuples
    stats = []
    for inputfile in inputfiles:
        print("gathering info from", os.path.split(inputfile)[1])
        exp = trajognize.plot.plot.get_exp_from_filename(inputfile)
        stat = trajognize.plot.plot.get_stat_from_filename(inputfile)
        if stat not in stats:
            stats.append(stat)
        strid = get_strid_from_tail(os.path.split(inputfile)[1])
        if exp == "exp_all" or strid == "all":
            continue
        experiment = exps[exp[4:]]
        group = experiment["groupid"][strid]
        key = (exp, group)
        # store inputfile (but the .zipped python object format) for later use
        if key not in filedict:
            filedict[key] = [inputfile[:-4] + ".zip"]
        else:
            filedict[key].append(inputfile[:-4] + ".zip")
    if len(stats) != 1:
        print("ERROR: wrong number of stats parsed:", stats)
        return
    stat = stats[0]

    # calculate averages, write new results
    for key in filedict:
        print("\n", key, "\n\n")
        (exp, group) = key
        experiment = exps[exp[4:]]
        # caculate average
        if stat == "heatmap":
            avgobj = trajognize.stat.init.HeatMap(
                project_settings.good_light, project_settings.image_size
            )
        elif stat == "motionmap":
            avgobj = trajognize.stat.init.MotionMap(
                project_settings.good_light, project_settings.image_size
            )
        else:
            raise NotImplementedError("unhandled stat: {}".format(stat))
        for inputfile in filedict[key]:
            print("parsing", os.path.split(inputfile)[1])
            newobj = trajognize.util.load_object(inputfile)
            if newobj:
                newobj.print_status()
                avgobj += newobj
        # no overloading for __div__ exists, we do it manually:
        for light in project_settings.good_light:
            avgobj.data[light] //= len(filedict[key])
        # write new results for all files
        print()
        for inputfile in filedict[key]:
            # calculate difference from average
            newobj = trajognize.util.load_object(inputfile)
            if newobj:
                # no overloading for __sub__ exists, we do it manually:
                for light in project_settings.good_light:
                    newobj.data[light] -= avgobj.data[light]
            # define output directory and write results
            (head, tail, plotdir) = trajognize.plot.plot.get_headtailplot_from_filename(
                inputfile
            )
            outdir = os.path.join(
                head, plotdir
            )  # calling standard heatmap plot will differentiate again...
            if not os.path.isdir(outdir):
                os.makedirs(outdir)
            # change stat to statdiff in output file name
            tail = tail.replace(stat, stat + "diff")
            outputfiletxt = os.path.join(outdir, tail + ".txt")
            outputfilezip = os.path.join(outdir, tail + ".zip")
            substat = stat + "diff." + get_strid_from_tail(tail)
            # save output in .zipped object
            print("writing", os.path.split(outputfilezip)[1])
            trajognize.util.save_object(newobj, outputfilezip)
            # save output in text format with header
            print("writing", os.path.split(outputfiletxt)[1])
            outputfile = open(outputfiletxt, "w")
            outputfile.write(
                trajognize.stat.experiments.get_formatted_description(experiment, "#")
            )
            outputfile.write("\n")
            outputfile.write(
                "# this is %sdiff, %s of difference from average in the given group,\n"
                % (stat, stat)
            )
            outputfile.write(
                "# for the given parameters, i.e. light condition and real/virtual state\n"
            )
            outputfile.write(
                "# this is not a true stat, it is only calculated from the results of %s stat\n"
                % stat
            )
            outputfile.write("\n")
            newobj.write_results(outputfile, project_settings, substat)
    # create SPGM gallery description
    trajognize.plot.spgm.create_gallery_description(
        head, "%ss of barcode occurrence differences from average" % stat.title()
    )


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))  # pass only real params to main
    except Exception as ex:
        print(ex, file=sys.stderr)
        import traceback

        traceback.print_exc(ex)
        sys.exit(1)
