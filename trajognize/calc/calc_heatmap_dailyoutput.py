"""This script summarizes heatmap dailyoutput results in one file.

Usage: calc_heatmap_dailyoutput.py projectfile inputdir

where inputdir is the output of trajognize.statsum with options "-s heatmap -d"

Output is written in a subdirectory of input dir.

"""

import os, subprocess, sys, glob, re, itertools, numpy

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


def get_categories_from_name(name):
    """Get group + avg/std/num from paragraph header (name), e.g.:

    heatmap.ORP_daylight_REAL

    """
    match = re.match(r"^heatmap\.(.*)_(.*)_(.*)$", name)
    if match:
        strid = match.group(1)
        light = match.group(2)
        realvirt = match.group(3)
        return (strid, light, realvirt)
    else:
        return (None, None, None)


def main(argv=[]):
    """Main entry point of the script."""
    if len(argv) < 2:
        print(__doc__)
        return
    projectfile = argv[0]
    inputdir = argv[1]
    inputfiles = glob.glob(os.path.join(inputdir, "*/stat_heatmap.*__day_*.txt"))
    project_settings = trajognize.settings.import_trajognize_settings_from_file(
        projectfile
    )
    if project_settings is None:
        print("Could not load project settings.")
        return
    exps = project_settings.experiments
    outdirs = []

    # create full database of all data
    database = {}
    lights = set()
    realvirts = set()
    datatypes = set()
    # parse all data to create the full database
    for inputfile in inputfiles:
        print("gathering info from", os.path.split(inputfile)[1])
        day = trajognize.plot.plot.get_day_from_filename(inputfile)
        alldata = trajognize.parse.parse_stat_output_file(inputfile)
        for index in range(len(alldata)):
            name = alldata[index][0][0]
            (strid, light, realvirt) = get_categories_from_name(name)
            for i in range(1, len(alldata[index])):
                datatype = alldata[index][i][0]
                # add new key entries to key sets
                lights.add(light)
                realvirts.add(realvirt)
                datatypes.add(datatype)
                # add key and data to database
                key = (strid, light, realvirt, day, datatype)
                database[key] = float(alldata[index][i][1])

    # write results
    # define output directory
    (head, tail, plotdir) = trajognize.plot.plot.get_headtailplot_from_filename(
        inputfile
    )
    head = os.path.split(head)[0]
    tail = plotdir
    outdir = os.path.join(head, plotdir)
    if not os.path.isdir(outdir):
        os.makedirs(outdir)
    # iterate all experiments and groups
    for exp in exps:
        for group in exps[exp]["groups"]:
            # save output in text format with header
            outputfile = os.path.join(
                outdir, tail + "__exp_%s__group_%s.txt" % (exp, group)
            )
            print("writing", os.path.split(outputfile)[1])
            outputfile = open(outputfile, "w")
            outputfile.write(
                trajognize.stat.experiments.get_formatted_description(exps[exp], "#")
            )
            outputfile.write("\n")
            outputfile.write(
                "# This file contains heatmap dailyoutput results arranged in blocks of strids and days for all (light, realvirt, datatype) tuples\n"
            )
            outputfile.write(
                "# Warning: due to the dailyoutput-type calculations, days at the edge of experiments contain data from neighboring experiments, too\n"
            )
            outputfile.write("\n")
            days = trajognize.stat.experiments.get_dayrange_of_experiment(exps[exp])
            strids = sorted(exps[exp]["groups"][group])
            for (light, realvirt, datatype) in itertools.product(
                lights, realvirts, datatypes
            ):
                outputfile.write(
                    "heatmap_dailyoutput_%s_%s_%s\t%s\tabsgrad_avg\tabsgrad_std\n"
                    % (light, realvirt, datatype, "\t".join(strids))
                )
                olddata = [0] * len(strids)
                for day in days:
                    absgrad = []
                    outputfile.write(day)
                    for i, strid in enumerate(strids):
                        key = (strid, light, realvirt, day, datatype)
                        try:
                            outputfile.write("\t%g" % database[key])
                            absgrad.append(abs(database[key] - olddata[i]))
                            olddata[i] = float(database[key])
                        except KeyError:
                            outputfile.write("\tnan")
                    outputfile.write(
                        "\t%g\t%g\n" % (numpy.mean(absgrad), numpy.std(absgrad))
                    )
                outputfile.write("\n\n")

    # create SPGM gallery description
    trajognize.plot.spgm.create_gallery_description(
        head,
        """
            Summarized heatmap dailyoutput statistics.
            """,
    )
    trajognize.plot.spgm.create_gallery_description(
        outdir,
        """
            Summarized heatmap dailyoutput results separated for experiments and groups
            Warning: due to the dailyoutput-type calculations,
            days at the edge of experiments contain data from neighboring experiments, too.

            Absgrad data appeneded to the end of group data.
            """,
    )


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))  # pass only real params to main
    except Exception as ex:
        print(ex, file=sys.stderr)
        import traceback

        traceback.print_exc(ex)
        sys.exit(1)
