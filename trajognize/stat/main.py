"""
Trajognize stat main code.
"""

# external imports
import os
import sys
import argparse
import datetime
# imports from base class
import trajognize

# imports from self subclass
from . import util
from . import experiments

def main(argv=[]):
    """Main code. Execute as 'bin/stat [options]' or as 'trajognize.stat.main(["option1", "value1", ...])'.

    Short list of the statistics implemented so far:
    0.  basic statistics about frame numbers, errors, skipped frames, etc. for
        all light conditions (including bad ones)
    1.  24h distribution of barcodes (1440 minute bins, all colorids + sum)
    2.  heatmap of barcodes (image_size.x by image_size.y images for all light
        types, containing barcode center occurrence numbers)
        This stat has one virtual subclass for all barcode types and one for 'all'
    3.  number of simultaneous id distribution of barcodes
    4.  nearest neighbor distribution (NxN matrix, where N = len(oolorids))
    5.  spatial distance distribution between different barcodes
    6.  velocity distribution of barcodes
    7.  acceleration distribution of barcodes
    8.  approach-avoidance type stats
    9.  FQ+type stats
    10. butt-head type states

    All implemented statistics get saved in binary format as a zipped python
    object to save space and to allow for quick summary of more stats on more
    files later on.

    For more details on the implemented statistics, check out stat.py and
    init.py or call util.print_stats_help()

    """
    print("This is trajognize stat. Version:", trajognize.util.get_version_info())
    phase = trajognize.util.Phase()
    # create stat dictionary from implemented stat functions and classes
    stats = util.get_stat_dict()
    # parse command line arguments
    argparser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=main.__doc__, add_help=False)
    argparser.add_argument("-h", "--help", metavar="HELP", nargs='?', const=[], choices=["stats"]+sorted(stats.keys()), help="Without arguments show this help and exit. Optional arguments for help topics: %s." % (["stats"]+sorted(stats.keys())))
    argparser.add_argument("-f", "--force", dest="force", action="store_true", default=False, help="force overwrite of output files")
    argparser.add_argument("-i", "--inputfile", metavar="FILE", dest="inputfile", required=False, help="define barcode input file name (.blobs.barcodes)")
    argparser.add_argument("-p", "--projectfile", metavar="FILE", dest="projectfile", required=False, help="define project settings file that contains a single TrajognizeSettingsBase class instantiation.")
    argparser.add_argument("-e", "--entrytimesfile", metavar="FILE", dest="entrytimesfile", help="define entry times input file name (.dat, .txt)")
    argparser.add_argument("-k", "--calibfile", metavar="FILE", dest="calibfile", help="define space calibration input file name (.xml)")
    argparser.add_argument("-o", "--outputpath", metavar="PATH", dest="outputpath", help="define output path for .barcodes.stat_*.zip output files")
    argparser.add_argument("-n", "--framenum", metavar="NUM", dest="framenum", help="define max frames to read (used for debug reasons)")
    argparser.add_argument("-s", "--statistics", metavar="stat", dest="statistics", nargs='+', choices=sorted(stats.keys()), default=sorted(stats.keys()), help="Define only some of the statistics to run. Possible values: %s" % sorted(stats.keys()))
    argparser.add_argument("-ns", "--nostatistics", metavar="stat", dest="nostatistics", nargs='+', choices=sorted(stats.keys()), default=[], help="Define some of the statistics not to run. Possible values: %s" % sorted(stats.keys()))
    argparser.add_argument("-sci", "--subclassindex", metavar="INDEX", dest="subclassindex", nargs='+', type=int, help="Define only some of the stat subclasses to run. Works bugfree only if a single stat is selected.")
    argparser.add_argument("-d", "--dailyoutput", dest="dailyoutput", action="store_true", default=False, help="Store output separated for days. This is kind of a hack and should be used only with heatmaps.")
    argparser.add_argument("-sub", "--subtitle", dest="subtitle", action="store_true", default=False, help="create subtitle output")

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
    # inputfile
    if not options.inputfile:
        print("  ERROR: inputfile not specified. Use the '-i' option")
        return
    print("  Using inputfile: '%s'" % options.inputfile)
    # project settings
    if not options.projectfile:
        print("  ERROR: projectfile not specified. Use the '-p' option.")
        return
    print("  Using project settings file: '%s'" % options.projectfile)
    # entrytimes file
    if options.entrytimesfile is None:
        print("  Not using entrytimes file.")
    else:
        print("  Using entrytimes file: '%s'" % options.entrytimesfile)
    # output path
    if options.outputpath is None:
        (options.outputpath, tail) = os.path.split(options.inputfile)
        print("  WARNING! No output path is specified! Default is input file directory: '%s'" % options.outputpath)
    else:
        print("  Using output path: '%s'" % options.outputpath)
    # dailyoutput
    if options.dailyoutput:
        print("  WARNING: option '-d' specified, output is written on a daily basis. Use -d in statsum also to parse daily output data.")
    # check output file
    outputfilecommon = os.path.join(options.outputpath, os.path.split(options.inputfile)[1])
    if options.force:
        print("  WARNING: option '-f' specified, forcing overwrite of output files.")
    # frame num
    if options.framenum is not None:
        options.framenum = int(options.framenum)
        print("  WARNING: debug option '-n' specified, reading only %d frames." % options.framenum)
    # subtitles
    if options.subtitle:
        if options.dailyoutput:
            print("  ERROR:  dailyoutput and subtitle params cannot be specified at the same time!")
            return
        print("  option -sub specified, creating subtitle files.")
    # statistics - get difference of stat and nostat
    options.statistics = sorted(list(set(options.statistics).difference(set(options.nostatistics))))
    print("  Calculating statistics:", options.statistics)
    # TODO: maybe check subclassindex
    phase.end_phase()

    phase.start_phase("Reading project settings file...")
    project_settings = trajognize.settings.import_trajognize_settings_from_file(options.projectfile)
    if project_settings is None:
        print("  ERROR parsing project settings file")
        return
    print("  Current project is: %s" % project_settings.project_name)
    exps = project_settings.experiments
    phase.end_phase()

    # parse colorid file
    phase.start_phase("Checking colorids...")
    colorids = project_settings.colorids
    if not colorids:
        print("  ERROR parsing colorids")
        return
    print("  %d colorids read, e.g. first is '%s'" % (len(colorids), colorids[0]))
    phase.end_phase()

    # parse entrytimes file
    phase.start_phase("Parsing entrytimes...")
    if options.entrytimesfile is None:
        entrytimes = {}
    else:
        entrytimes = trajognize.parse.parse_entry_times(options.entrytimesfile)
        if entrytimes is None:
            print("  ERROR parsing entrytimes file")
            return
    if entrytimes:
        print("  %d entrytime dates read, e.g. first is (%s)" % (len(entrytimes), next(iter(entrytimes.values()))))
    else:
        print("  entrytimes are empty")
    phase.end_phase()

    # parse calibration file
    phase.start_phase("Reading calibration file...")
    print("  WARNING: TODO - calibration is not implemented yet!!!")
    phase.end_phase()

    # parse input barcode file
    phase.start_phase("Reading input barcode file...")
    barcodes = trajognize.parse.parse_barcode_file(options.inputfile, colorids, 0, options.framenum)
    if barcodes is None:
        print("  empty barcode file found. Exiting.")
        return
    print("  %d barcode frames read" % len(barcodes))
    phase.end_phase()

    # parse input log file
    phase.start_phase("Reading input log file...")
    inputfile = options.inputfile # this is needed for the automatic execution of stat_calculate functions...
    head, tail = os.path.split(inputfile)
    inputfile_log = inputfile[:-15] # remove '.blobs.barcodes'
    inputfile_log += '.log'
    if len(project_settings.all_light) > 1:
        (light_log, cage_log) = trajognize.parse.parse_log_file(inputfile_log)
    else:
        # in most projects we use only a single lighting condition, let it be NIGHTLIGHT
        # in most projects we do not use cage correction, let it be the center value
        light_log = {0: 'NIGHTLIGHT'}
        cage_log = {0: [project_settings.image_size.x/2, project_settings.image_size.y/2, 0, 90]}
    if light_log is None and cage_log is None:
        print("  reading input log file failed. Exiting.""")
        return
    print("  %d LED switches parsed" % len(light_log))
    print("  %d CAGE coordinates parsed" % len(cage_log))
    # get current experiment name (assuming that it will remain the same on the whole video)
    starttime = project_settings.get_datetime_from_filename(inputfile)
    # get days for dailyoutput (current and next if we are around midnight)
    if options.dailyoutput:
        dailyoutput = True
        days = [str(starttime.date()), str((starttime + datetime.timedelta(days=1)).date())]
    else:
        dailyoutput = False
        days = [""]
    # get current experiment as well (name 'experiment' should be defined for stat calculation)
    explist = experiments.get_experiment(exps, starttime)
    if not explist:
        exp = None
        experiment = None
    else:
        # first one in list is the main one (we always calculate stat with that)
        exp = explist[0]
        experiment = exps[exp]
    print("  current experiment is '%s'" % exp)
    phase.end_phase()

    ############################################################################
    # stats
    for stat in options.statistics:
        subclasses = util.subclasses_stat(stats, stat)
        if options.subclassindex is None:
            if subclasses is None:
                subclassindices = [0]
            else:
                subclassindices = range(len(subclasses))
        else:
            subclassindices = options.subclassindex
        for subclassindex in subclassindices:
            substat = util.get_substat(stat, subclasses, subclassindex)
            phase.start_phase("Calculating %s statistic..." % substat)
            outputfiles = [trajognize.util.add_subdir_to_filename(outputfilecommon +
                    util.get_stat_fileext_zipped(substat), day) for day in days]
            breakit = False
            for outputfile in outputfiles:
                if os.path.isfile(outputfile) and not options.force:
                    print("  Output file '%s' already exists, add '-f' to force overwrite. Now skipping.\n" % util.get_stat_fileext_zipped(substat))
                    breakit = True
            if breakit: continue
            # prepare subtitle file
            if options.subtitle:
                outputdir = os.path.split(outputfiles[0])[0]
                if not os.path.isdir(outputdir): os.mkdir(outputdir)
                subtitlefile = open(outputfilecommon + util.get_stat_fileext(substat) + '.srt', 'w')
            else:
                subtitlefile = None
            # do the actual stat calculation
            statobjects = util.calculate_stat(stats, stat)
            # close subtitle file if applicable
            if options.subtitle:
                subtitlefile.close()
            if not dailyoutput: statobjects = [statobjects]
            for i, statobject in enumerate(statobjects):
                if not statobject.files:
                    continue
                print("  %s stat%s version: %d" % (stat, " (%s)" % days[i] if days[i] else "", statobject.version))
                statobject.print_status()
                outputdir = os.path.split(outputfiles[i])[0]
                if not os.path.isdir(outputdir): os.mkdir(outputdir)
                trajognize.util.save_object(statobject, outputfiles[i])
            phase.end_phase()

    # end main and print total time elapsed
    phase.end_phase(None, True)
