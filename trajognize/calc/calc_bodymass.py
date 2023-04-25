"""This script inpterpolates bodymass.txt (or wounds.txt) and separates output
on a daily basis for all experiments and groups.

Usage: calc_bodymass.py projectfile inputfile(s)

Output is written in a subdirectory of input dir.

"""

import os, subprocess, sys, glob, itertools, datetime

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

nogroup = False


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

    project_settings = trajognize.settings.import_trajognize_settings_from_file(
        projectfile
    )
    if project_settings is None:
        print("Could not load project settings.")
        return
    exps = project_settings.experiments
    # parse files
    for inputfile in inputfiles:
        print("parsing", os.path.split(inputfile)[1])
        (head, tail, plotdir) = trajognize.plot.plot.get_headtailplot_from_filename(
            inputfile
        )
        data = trajognize.parse.parse_stat_output_file(inputfile, 0)
        name = data[0][0]
        headerline = data[0]
        dates = [
            datetime.datetime.strptime(data[i][0], "%Y.%m.%d.").date()
            for i in range(1, len(data))
        ]
        for exp in exps:
            firstday = exps[exp]["start"].date()
            lastday = exps[exp]["stop"].date()
            alldata = []
            index = 0
            # interpolate all data
            for date in [
                firstday + datetime.timedelta(i)
                for i in range((lastday - firstday).days + 1)
            ]:
                while index < len(dates) and dates[index] < date:
                    lastindex = index
                    index += 1
                # no more data available, push the last one again
                if index >= len(dates):
                    alldata.append(list(alldata[-1]))
                    continue
                # if first measurement date is already over day in experiment,
                # we store the first entry
                if index == 0:
                    alldata.append(list(data[1]))
                    continue
                # exact match, store original
                if dates[index] == date:
                    alldata.append(list(data[index + 1]))
                    continue
                # between two dates, interpolate
                before = data[lastindex + 1]
                after = data[index + 1]
                beforedate = dates[lastindex]
                afterdate = dates[index]
                n = (afterdate - beforedate).days
                i = (date - beforedate).days
                alldata.append(
                    [str(date)]
                    + [
                        "%g"
                        % (
                            float(before[j])
                            + i * (float(after[j]) - float(before[j])) / n
                        )
                        for j in range(1, len(before))
                    ]
                )
            # write interpolated data
            outdir = os.path.join(head, plotdir)
            if not os.path.isdir(outdir):
                os.makedirs(outdir)
            outputfile = os.path.join(outdir, "meas_%s__exp_%s.txt" % (tail, exp))
            print("writing", os.path.split(outputfile)[1])
            outputfile = open(outputfile, "w")
            outputfile.write(
                "# This file contains interpolated data of %s\n" % inputfile
            )
            outputfile.write("\n")
            outputfile.write(
                trajognize.stat.experiments.get_formatted_description(exps[exp], "#")
            )
            outputfile.write("\n")
            if nogroup:
                outputfile.write("\t".join(data[0]))
                outputfile.write("\n")
                for i in range(len(alldata)):
                    outputfile.write("\t".join(alldata[i]))
                    outputfile.write("\n")
            else:
                for group in exps[exp]["groups"]:
                    names = sorted(exps[exp]["groups"][group])
                    outputfile.write("\t".join(["%s_group_%s" % (name, group)] + names))
                    outputfile.write("\n")
                    for i in range(len(alldata)):
                        outputfile.write(
                            "\t".join(
                                [alldata[i][0].strip(".").replace(".", "-")]
                                + [
                                    alldata[i][headerline.index(strid)]
                                    for strid in names
                                ]
                            )
                        )
                        outputfile.write("\n")
                    outputfile.write("\n\n")

            outputfile.close()

    # create SPGM gallery description
    trajognize.plot.spgm.create_gallery_description(
        outdir,
        """
            Daily interpolated %s data.
            """
        % name,
    )


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))  # pass only real params to main
    except Exception as ex:
        print(ex, file=sys.stderr)
        import traceback

        traceback.print_exc(ex)
        sys.exit(1)
