"""
Trajognize stat summary code.
"""

# external imports
import os
import sys
import argparse
import datetime
import glob

# imports from base class
import trajognize

# imports from self subclass
from . import init
from . import util
from . import experiments


def write_results(
    outputfilename,
    stats,
    stat,
    substat,
    statobject,
    exps,
    exp,
    day,
    dailyoutput,
    project_settings,
):
    """Helper function to write results to file."""
    outputfile = open(outputfilename, "w")
    # print other parameters to file
    outputfile.write("trajognize version = %s\n" % trajognize.util.get_version_info())
    outputfile.write("%s_t object version = %d\n" % (stat, statobject.version))
    outputfile.write("results written on %s\n\n" % str(datetime.datetime.now()))
    # print stat help to file
    util.print_stats_help(stats, [stat], outputfile)
    outputfile.close()
    trajognize.util.insert_commentchar_to_file(outputfilename, "#")
    # print experiment definition to file
    outputfile = open(outputfilename, "a")
    outputfile.write("\n")
    if exp == "dailyoutput":
        outputfile.write(
            "# This file contains data from all files on day %s, regardless of experiment definitions.\n"
            % day
        )
    elif exp == "all":
        outputfile.write(
            "# This file contains data from all files, regardless of experiment definitions.\n"
        )
    else:
        outputfile.write(experiments.get_formatted_description(exps[exp], "#"))
    outputfile.write("\n\n")
    # print results to file
    if dailyoutput:
        # next line is needed for heatmap simplified stat only...
        exp = [
            e
            for e in trajognize.stat.experiments.get_experiment(
                exps, datetime.datetime.strptime(day, "%Y-%m-%d"), True
            )
            if exps[e]["number"] < 10
        ][-1]
        util.write_dailyoutput_stat(stats, stat, statobject)
    else:
        util.write_stat(stats, stat, statobject)
    outputfile.close()


def main(argv=[]):
    """Main stat summary code. Execute as 'bin/statsum [options]'
    or as 'trajognize.stat.sum.main(["options1", "value1", ...])'.

    This module loads previously saved statistics for single barcode files
    and summarizes them to get global statistics.

    """
    print("This is trajognize statsum. Version:", trajognize.util.get_version_info())
    phase = trajognize.util.Phase()
    # create stat dictionary from implemented stat functions and classes
    stats = util.get_stat_dict()
    # parse command line arguments
    argparser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=main.__doc__,
        add_help=False,
    )
    argparser.add_argument(
        "-h",
        "--help",
        metavar="HELP",
        nargs="?",
        const=[],
        choices=["stats"] + sorted(stats.keys()),
        help="Without arguments show this help and exit. Optional arguments for help topics: %s."
        % (["stats"] + sorted(stats.keys())),
    )
    argparser.add_argument(
        "-i",
        "--inputpath",
        metavar="PATH",
        required=False,
        dest="inputpath",
        help="define input path to have stat files at [PATH]/*/OUT/*.blobs.barcodes.stat_*.zip",
    )
    argparser.add_argument(
        "-p",
        "--projectfile",
        metavar="FILE",
        required=False,
        dest="projectfile",
        help="define project settings file that contains a single TrajognizeSettingsBase class instantiation.",
    )
    argparser.add_argument(
        "-k",
        "--calibfile",
        metavar="FILE",
        dest="calibfile",
        help="define space calibration input file name (.xml)",
    )
    argparser.add_argument(
        "-o",
        "--outputpath",
        metavar="PATH",
        dest="outputpath",
        help="define output path for summarized results",
    )
    argparser.add_argument(
        "-s",
        "--statistics",
        metavar="stat",
        dest="statistics",
        nargs="+",
        choices=sorted(stats.keys()),
        default=sorted(stats.keys()),
        help="Define only some of the statistics to run. Possible values: %s"
        % sorted(stats.keys()),
    )
    argparser.add_argument(
        "-ns",
        "--nostatistics",
        metavar="stat",
        dest="nostatistics",
        nargs="+",
        choices=sorted(stats.keys()),
        default=[],
        help="Define some of the statistics not to run. Possible values: %s"
        % sorted(stats.keys()),
    )
    argparser.add_argument(
        "-e",
        "--experiments",
        metavar="exp",
        dest="experiments",
        nargs="+",
        help="Define only some of the experiments to process.",
    )
    argparser.add_argument(
        "-ne",
        "--noexperiments",
        metavar="exp",
        dest="noexperiments",
        nargs="+",
        default=[],
        help="Define some of the experiments not to process.",
    )
    argparser.add_argument(
        "-sci",
        "--subclassindex",
        metavar="INDEX",
        dest="subclassindex",
        nargs="+",
        type=int,
        help="Define only some of the stat subclasses to run. Works bugfree only if a single stat is selected.",
    )
    argparser.add_argument(
        "-d",
        "--dailyoutput",
        dest="dailyoutput",
        action="store_true",
        default=False,
        help="Write results separated for days. This is kind of a hack and should be used only with heatmaps so far.",
    )
    argparser.add_argument(
        "-u",
        "--uniqueoutput",
        dest="uniqueoutput",
        action="store_true",
        default=False,
        help="Write results separated for each input file uniquely.",
    )
    # if arguments are passed to main(argv), parse them
    if argv:
        options = argparser.parse_args(argv)
    # else if called from command line or no arguments are passed to main, parse default argument list
    else:
        options = argparser.parse_args()
    # handle help option with help topics
    if options.help == []:
        print("\n")
        argparser.print_help()
        return
    elif options.help == "stats":
        print("\n")
        util.print_stats_help(stats)
        return
    elif options.help:
        print("\n")
        util.print_stats_help(stats, [options.help])
        return

    # check arguments
    phase.start_phase("Checking command line arguments...")
    # input path
    if not options.inputpath:
        print("  ERROR: inputpath not specified. Use the '-i' option")
        return
    print("  Using input path: '%s'" % options.inputpath)
    inputdirs = glob.glob(os.path.join(options.inputpath, "*" + os.sep))

    # project settings file
    if not options.projectfile:
        print("  ERROR: projectfile not specified. Use the '-p' option.")
        return
    print("  Using project file: '%s'" % options.projectfile)

    # output path
    if options.outputpath is None:
        options.outputpath = options.inputpath
        print(
            "  WARNING! No output path is specified! Default is input path: '%s'"
            % options.outputpath
        )
    else:
        print("  Using output path: '%s'" % options.outputpath)

    # dailyoutput
    # get input files for daily output
    if options.dailyoutput:
        print("  WARNING: option '-d' specified, output is written on a daily basis.")
        dailyoutput = True
    # get standard inputfiles
    else:
        dailyoutput = False

    # uniqueoutput
    # get input files for unique output
    if options.uniqueoutput:
        print(
            "  WARNING: option '-u' specified, output is written for every input file separately."
        )
        uniqueoutput = True
    # get standard inputfiles
    else:
        uniqueoutput = False

    phase.end_phase()

    # parse project settings file
    phase.start_phase("Reading project settings file...")
    project_settings = trajognize.settings.import_trajognize_settings_from_file(
        options.projectfile
    )
    if project_settings is None:
        print("  ERROR: Could not load project settings.")
        return
    # define some variables directly to be present in caller namespace for stats
    good_light = project_settings.good_light
    all_light = project_settings.all_light
    image_size = project_settings.image_size
    MBASE = project_settings.MBASE
    exps = project_settings.experiments
    aa_settings = project_settings.stat_aa_settings
    object_types = project_settings.object_types
    max_day = project_settings.max_day
    print("  Current project is: %s" % project_settings.project_name)
    phase.end_phase()

    # parse colorid file
    phase.start_phase("Checking colorids...")
    colorids = project_settings.colorids
    if not colorids:
        print("  ERROR: Could not get colorids.")
        return
    id_count = len(colorids)
    print("  %d colorids read, e.g. first is '%s'" % (id_count, colorids[0]))
    phase.end_phase()

    # parse calibration file
    phase.start_phase("Reading calibration file...")
    print("  WARNING: TODO - calibration is not implemented yet!!!")
    phase.end_phase()

    # experiments and statistics
    phase.start_phase("Initializing statistics for all experiments...")
    if options.experiments is None:
        options.experiments = list(exps.keys())
    # replace number to experiment name
    for i, exp in enumerate(options.experiments):
        if exp not in exps:
            for e in exps:
                if exp.isdigit() and exps[e]["number"] == int(exp):
                    options.experiments[i] = e
                    break
            else:
                print("  ERROR: invalid experiment '{}'".format(exp))
                return
    for i, exp in enumerate(options.noexperiments):
        if exp not in exps:
            for e in exps:
                if exp.isdigit() and exps[e]["number"] == int(exp):
                    options.noexperiments[i] = e
                    break
            else:
                print("  ERROR: invalid experiment '{}'".format(exp))
                return
    # get difference of exp and noexp
    options.experiments = sorted(
        list(set(options.experiments).difference(set(options.noexperiments)))
    )
    if len(options.experiments) == len(exps):
        options.experiments += ["all"]
    # get difference of stat and nostat
    options.statistics = sorted(
        list(set(options.statistics).difference(set(options.nostatistics)))
    )
    # initialize subclassdict
    subclassdict = dict()
    for stat in options.statistics:
        subclassdict[stat] = util.subclasses_stat(stats, stat)

    phase.end_phase()

    ############################################################################
    # parse (sub)stats
    for day in (
        experiments.get_dayrange_of_all_experiments(exps) if dailyoutput else [None]
    ):
        inputfiles = glob.glob(
            os.path.join(
                options.inputpath,
                "*",
                "OUT",
                "%s*.blobs.barcodes.stat_*.zip" % ("%s/" % day if day else ""),
            )
        )
        print(
            "  %sparsing %d input .zip files from %d directories"
            % ("%s: " % day if day else "", len(inputfiles), len(inputdirs))
        )
        if not inputfiles:
            continue
        # initialize statobjects
        statobjects = dict()
        for exp in ["dailyoutput"] if dailyoutput else options.experiments:
            statobjects[exp] = dict()
            if dailyoutput:
                print("  dailyoutput for", day)
            else:
                print("  experiment '%s':" % exp)
            for stat in options.statistics:
                if options.subclassindex is None:
                    if subclassdict[stat] is None:
                        subclassindices = [0]
                    else:
                        subclassindices = range(len(subclassdict[stat]))
                else:
                    subclassindices = options.subclassindex
                for subclassindex in subclassindices:
                    substat = util.get_substat(stat, subclassdict[stat], subclassindex)
                    statobjects[exp][substat] = util.init_stat(stats, stat)
                    print("    %s" % substat)
        print()
        # parse files
        for filenum in range(len(inputfiles)):
            inputfile = inputfiles[filenum]
            statobject = None
            if dailyoutput:
                explist = ["dailyoutput"]
            else:
                # get current experiment name (TODO: assuming that it will remain the same on the whole video)
                explist = experiments.get_experiment(
                    exps, project_settings.get_datetime_from_filename(inputfile)
                )
                # if current experiment is not in list, add next object to summarized result
                if "all" in options.experiments and (
                    not explist or explist[0] not in options.experiments
                ):
                    # calculate summarized result only if all experiments are to be calculated
                    explist.append("all")
            # do things twice for cut-up first experiment
            for exp in explist:
                if not dailyoutput and exp not in options.experiments:
                    continue
                substat = util.get_stat_from_filename(inputfile)
                if substat is None or substat not in statobjects[exp].keys():
                    continue
                statobject = statobjects[exp][substat]
                phase.start_phase(
                    "Reading file #%d (%1.1f%%): %s"
                    % (
                        filenum,
                        100.0 * filenum / len(inputfiles),
                        os.path.split(inputfile)[1],
                    )
                )
                newobj = trajognize.util.load_object(inputfile)
                if newobj:
                    newobj.print_status()
                    if newobj.version != statobject.version:
                        print(
                            "  WARNING: object version is %d instead of %d. Skipping it!"
                            % (newobj.version, statobject.version)
                        )
                    else:
                        statobject += newobj
                    if uniqueoutput:
                        # print results to stdout
                        print("  writing unique output...")
                        uniqueoutputfilename = (
                            project_settings.get_unique_output_filename(
                                options.outputpath, inputfile
                            )
                        )
                        write_results(
                            uniqueoutputfilename,
                            stats,
                            stat,
                            substat,
                            newobj,
                            exps,
                            exp,
                            day,
                            dailyoutput,
                            project_settings,
                        )

                phase.end_phase()

        ############################################################################
        # write results
        phase.start_phase("Writing results to files...")
        for exp in ["dailyoutput"] if dailyoutput else options.experiments:
            for substat in statobjects[exp]:
                statobject = statobjects[exp][substat]
                # parse 'substat' and 'subclassindex'
                i = substat.find(".")
                if i == -1:
                    stat = substat
                    subclassindex = 0
                else:
                    stat = substat[:i]
                    subclassindex = subclassdict[stat].index(substat[i + 1 :])
                # if this is the summary, add all others before printing result
                if exp == "all":
                    for tempexp in options.experiments:
                        if tempexp == "all" or "part" in tempexp:
                            continue
                        statobject += statobjects[tempexp][substat]
                # print results to stdout
                tailcommon = util.get_stat_fileext(
                    substat, day if dailyoutput else exp, False
                )
                print()
                trajognize.util.print_underlined(tailcommon)
                statobject.print_status()
                # print results to .txt file
                outputfilecommon = os.path.join(options.outputpath, tailcommon)
                outputfilename = outputfilecommon + ".txt"
                write_results(
                    outputfilename,
                    stats,
                    stat,
                    substat,
                    statobject,
                    exps,
                    exp,
                    day,
                    dailyoutput,
                    project_settings,
                )
                # save output in object format as well for later analysis, post processing, etc.
                trajognize.util.save_object(statobject, outputfilecommon + ".zip")
        phase.end_phase("\n")

    # end main and print total time elapsed
    phase.end_phase(None, True)
