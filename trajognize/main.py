"""
Trajognize main code.
"""

import os,sys,argparse

# import definitions as they appear in file
from .init import MFix, variables_t, barcode_t
from .project import *

# import functions organized according to files
from . import algo
from . import algo_blob
from . import algo_barcode
from . import algo_conflict
from . import algo_trajectory
from . import output
from . import parse
from . import util

def main(argv=[]):
    """Main code. Execute as 'bin/trajognize [options]' or as 'trajognize.main(["option1", "value1", ...])'.

    Short descrition of the algorithms (numbering correspond to debug save/load level,
    however debug saving/loading is too slow and needs too much memory so far...):

    1.   Load colorids, entry times, calibration files, input blob files.
    2.   Find motion blobs that correspond to color blobs, spatial and temporal
         closeness matrices, chains and clusters and use these later.
    3.   Find full barcodes on each frame based on spatial closeness chains and
         chain angle change restrictions. No further error checking at this stage,
         more barcodes with the same colorid can be found.
         For more description see find_chains_in_sdistlists()
    4.   Remove smaller one of full barcodes that share id and are close and also
         remove full barcodes that are fully overlapping others when rats are close.
    5-6. Find partlyfound barcodes based on temporal blob-based closeness in IDs.
         For more description see find_partlyfound_from_tdist()
         Algo is executed both forward and backward to extrude IDs into both
         temporal directions. Again there is no error checking, many false
         positive matches can be expected, even long term, especially when there
         are many false positive color blobs or many rats close to each other.
    7.   Join partial barcodes that share id and are close and their joined bloblist
         still fits into one barcode, and remove barcodes that still share id and are close, again.
    8.   Create trajectory database, assign a score for each one.
    9.   Sort trajectories according to their overall score. Select best
         trajectory candidates for final output. Join already chosen ones
         with other trajectory chains, not used or virtual barcodes.
    10.  Cleanup: Extend chosen trajectories with not yet chosen ones, delete all
         superfluous barcodes, trajectories, resolve all shared and conflicting
         states and not connecting chosen trajectories.

    Main variable descriptions can be found in init.variable_t() class.

    """
    print("This is trajognize. Version:", util.get_version_info())
    print("Current project is: %s\n" % project_str[PROJECT])
    v = variables_t()
    phase = util.phase_t()
    # parse command line arguments
    argparser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=main.__doc__)
    argparser.add_argument("-f", "--force", dest="force", action="store_true", default=False, help="force overwrite of output file")
    argparser.add_argument("-i", "--inputfile", metavar="FILE", required=True, dest="inputfile", help="define blob input file name (.blobs)")
    argparser.add_argument("-c", "--coloridfile", metavar="FILE", required=True, dest="coloridfile", help="define colorid input file name (.xml)")
    argparser.add_argument("-k", "--calibfile", metavar="FILE", dest="calibfile", help="define space calibration input file name (.xml)")
    argparser.add_argument("-o", "--outputpath", metavar="PATH", dest="outputpath", help="define output path for .barcodes output file")
    argparser.add_argument("-n", "--framenum", metavar="NUM", dest="framenum", type=int, help="define max frames to read (used for debug reasons)")
    argparser.add_argument("-nt", "--notrajectory", dest="notrajectory", action="store_true", default=False, help="do not run trajectory analysis section")
    argparser.add_argument("-nd", "--nodeleted", dest="nodeleted", action="store_true", default=False, help="do not write deleted barcodes")
    argparser.add_argument("-dl", "--debugload", metavar="NUM", dest="debugload", type=int, default=0, help="define level of debug environment to load")
    argparser.add_argument("-ds", "--debugsave", metavar="NUM", dest="debugsave", type=int, default=0, help="define level of debug environment to save")
    argparser.add_argument("-de", "--debugend", metavar="NUM", dest="debugend", type=int, default=10, choices=[3, 4, 5, 6, 7, 9, 10], help="define level of debug environment to end processing with (including this)")
    # if arguments are passed to main(argv), parse them
    if argv:
        options = argparser.parse_args(argv)
    # else if called from command line or no arguments are passed to main,
    # parse default argument list
    else:
        options = argparser.parse_args()


    # check arguments
    phase.start_phase("Checking command line arguments...")
    # inputfile
    print("  Using inputfile: '%s'" % options.inputfile)
    # colorid file
    print("  Using colorid file: '%s'" % options.coloridfile)
    # output path
    if options.outputpath is None:
        (options.outputpath, tail) = os.path.split(options.inputfile)
        print("  WARNING! No output path is specified! Default is input file directory: '%s'" % os.path.abspath(options.outputpath))
    else:
        print("  Using output path: '%s'" % os.path.abspath(options.outputpath))
    # check output file
    outputfile = '%s.barcodes' % os.path.join(options.outputpath, os.path.split(options.inputfile)[1])
    if os.path.isfile(outputfile):
        if options.force:
            print("  WARNING: option '-f' specified, forcing overwrite of output file.")
        else:
            print("  ERROR: Output file already exists, add '-f' to force overwrite.")
            return
    # frame num
    if options.framenum is not None:
        print("  WARNING: debug option '-n' specified, reading only %d frames." % options.framenum)
    # no trajectory part
    if options.notrajectory is True:
        print("  WARNING: debug option '-nf' specified, trajectory analysis part is not executed.")
    # no deleted
    if options.nodeleted is True:
        print("  WARNING: debug option '-wt' specified, writing only good barcodes, skipping deleted ones.")
    phase.end_phase()


    ############################################################################
    ################################ phase 1 ###################################
    ############################################################################

    if options.debugload < 1:
        # parse colorid file
        phase.start_phase("Reading colorid file...")
        v.colorids = parse.parse_colorid_file(options.coloridfile)
        if v.colorids is None: return
        print("  %d colorids read, e.g. first is (%s,%s)" % (len(v.colorids), v.colorids[0].strid, v.colorids[0].symbol))
        if len(v.colorids[0].strid) != MCHIPS:
            print("  ERROR: colorids consist of %d colors, but MCHIPS is %d" % (len(v.colorids[0].strid), MCHIPS))
            return
        phase.end_phase()

        # parse calibration file
        phase.start_phase("Reading calibration file...")
        print("  WARNING: TODO - calibration is not implemented yet!!!")
        phase.end_phase()

        # parse input blob file
        phase.start_phase("Reading input blob file...")
        (v.color_blobs, v.md_blobs, v.rat_blobs) = parse.parse_blob_file(options.inputfile, options.framenum)
        if v.color_blobs is None and v.md_blobs is None and v.rat_blobs is None: return
        print("  %d BLOB frames read" % len(v.color_blobs))
        phase.end_phase()
    elif options.debugload == 1:
        phase.start_phase("Reading previously saved debug environment at level %d..." % options.debugload)
        v = util.load_object(util.debug_filename(options.debugload))
        phase.end_phase()
    if options.debugsave == 1:
        phase.start_phase("Saving debug environment at level %d..." % options.debugsave)
        util.save_object(v, util.debug_filename(options.debugsave))
        phase.end_phase()


    ############################################################################
    # initialize variables
    phase.start_phase("Initializing variables and output files...")
    framecount = len(v.color_blobs)
    v.sdistlists = [[[],[]] for x in range(framecount)] # spatial distlist (which blob is close to be neighbor/second neighbor on same rat)
    v.tdistlists = [[] for x in range(framecount)] # temporal distlist (which blob can be the same on the previous frame)
    v.clusterlists = [[] for x in range(framecount)] # cluster list containing blob indices in clusters for all frames
    v.clusterindices = [[] for x in range(framecount)] # cluster index for all blobs
    v.mdindices = [[] for x in range(framecount)] # motion blob index for all blobs (-1 if none)
    v.barcodes = [[[] for x in range(len(v.colorids))] for x in range(framecount)] # all barcodes found. First index is frame num.
    if not options.notrajectory:
        v.trajectories = [[] for x in range(len(v.colorids))] # all candidate trajectories found. First index is coloridindex.
        v.trajsonframe = [[set() for x in range(len(v.colorids))] for x in range(framecount)] # trajectory indices on each frame
    output.barcode_textfile_init(outputfile, v.barcodes)
    outputlogfile = outputfile[:-9] + '.log' # remove '.barcodes'
    output.logfile_init(outputlogfile)
    phase.end_phase()

    ############################################################################
    ################################ phase 2 ###################################
    ############################################################################

    if options.debugload < 2:
        ############################################################################
        # initialize calculated variables
        phase.start_phase("Initialize calculated variables (sdistlists, clusterlists, md blobs over blobs, etc.)...")
        for currentframe in range(framecount):
            # calculate spatial distances between blobs
            v.sdistlists[currentframe] = algo_blob.create_spatial_distlists(v.color_blobs[currentframe])
            # find blob clusters for later error checking and set clusterindex variable in all blobs
            (v.clusterlists[currentframe], v.clusterindices[currentframe]) = algo_blob.find_clusters_in_sdistlists(v.color_blobs[currentframe], v.sdistlists[currentframe])
            # set mdindex variable in all blobs
            v.mdindices[currentframe] = algo.find_md_under_blobs(v.color_blobs[currentframe], v.md_blobs[currentframe])

            # print status
            phase.check_and_print_phase_status('forward', currentframe, framecount)
        phase.end_phase()
    elif options.debugload == 2:
        phase.start_phase("Reading previously saved debug environment at level %d..." % options.debugload)
        v = util.load_object(util.debug_filename(options.debugload))
        phase.end_phase()
    if options.debugsave == 2:
        phase.start_phase("Saving debug environment at level %d..." % options.debugsave)
        util.save_object(v, util.debug_filename(options.debugsave))
        phase.end_phase()

    ############################################################################
    ################################ phase 3 ###################################
    ############################################################################

    if options.debugload < 3:
        ############################################################################
        # find full barcodes
        phase.start_phase("Find full IDs based on spatial closeness chains...")
        count = 0
        for currentframe in range(framecount):
            # find colorid chains
            chainlists = algo_blob.find_chains_in_sdistlists(
                    v.color_blobs[currentframe], v.sdistlists[currentframe], v.colorids)
            # store full IDs
            for k in range(len(v.colorids)):
                if not chainlists[k]: continue
                for chain in chainlists[k]:
                    # append to blob list
                    barcode = barcode_t(0, 0, 0, MFix.FULLFOUND, chain)
                    algo_barcode.calculate_params(barcode,  v.colorids[k].strid, v.color_blobs[currentframe])
                    v.barcodes[currentframe][k].append(barcode)
                    algo_blob.update_blob_barcodeindices(barcode, k, len(v.barcodes[currentframe][k])-1, v.color_blobs[currentframe])
                    count += 1
            # print status
            phase.check_and_print_phase_status('forward', currentframe, framecount)
        phase.end_phase("%d full barcodes found" % count)
    elif options.debugload == 3:
        phase.start_phase("Reading previously saved debug environment at level %d..." % options.debugload)
        v = util.load_object(util.debug_filename(options.debugload))
        phase.end_phase()
    if options.debugsave == 3:
        phase.start_phase("Saving debug environment at level %d..." % options.debugsave)
        util.save_object(v, util.debug_filename(options.debugsave))
        phase.end_phase()

        # debug quickcheck on barcode and blob database consistency
        algo_barcode.check_barcode_blob_consistency(v.barcodes, v.color_blobs, v.colorids)

    ############################################################################
    ################################ phase 4 ###################################
    ############################################################################

    if options.debugend > 3:
        if options.debugload < 4:
            ############################################################################
            # remove bad full barcodes
            phase.start_phase("Remove full barcodes that have shared id properties or are overlapping, set 'nocluster' prop on others...")
            count_sharesid = 0
            count_overlapped = 0
            for currentframe in range(framecount):
                # remove close sharesid ones
                count_sharesid += algo_barcode.remove_close_sharesid(
                        v.barcodes[currentframe], v.color_blobs[currentframe], v.colorids)
                # remove overlapping ones
                for cluster in v.clusterlists[currentframe]:
                    count_overlapped += algo_barcode.remove_overlapping_fullfound(
                            v.barcodes[currentframe], v.color_blobs[currentframe], cluster)
                    # set nocluster property for 'remote' barcodes
                    algo_barcode.set_nocluster_property(
                            v.barcodes[currentframe], v.color_blobs[currentframe], cluster)

                # print status
                phase.check_and_print_phase_status('forward', currentframe, framecount)
            phase.end_phase("%d sharesid barcodes deleted.\n  %d overlapped barcodes deleted." % (count_sharesid, count_overlapped))
        elif options.debugload == 4:
            phase.start_phase("Reading previously saved debug environment at level %d..." % options.debugload)
            v = util.load_object(util.debug_filename(options.debugload))
            phase.end_phase()
        if options.debugsave == 4:
            phase.start_phase("Saving debug environment at level %d..." % options.debugsave)
            util.save_object(v, util.debug_filename(options.debugsave))
            phase.end_phase()

        # debug quickcheck on barcode and blob database consistency
        algo_barcode.check_barcode_blob_consistency(v.barcodes, v.color_blobs, v.colorids)

    ############################################################################
    ################################ phase 5 ###################################
    ############################################################################

    if options.debugend > 4:
        if options.debugload < 5:
            ############################################################################
            # find partial blobs from tdist -> forward
            phase.start_phase("Find partial IDs based on full/partial IDs and temporal closeness chains...")
            count = 0
            count_adjusted = 0
            count_notused = 0
            for currentframe in range(1,framecount):
                # main algo is in algo.py, all function params are lists so they are modified in the call
                (a, b, c) = algo_barcode.find_partlyfound_from_tdist(
                        'forward', currentframe, v.tdistlists, v.color_blobs, v.barcodes, v.colorids,
                        v.sdistlists[currentframe], v.md_blobs, v.mdindices)
                count += a
                count_adjusted += b
                count_notused += c

                # write results to output text file
                # barcode_textfile_writeframe(v.barcodes[currentframe], currentframe, v.colorids)
                # print status
                phase.check_and_print_phase_status('forward', currentframe, framecount)
            phase.end_phase("%d partial barcodes found, from which %d barcodes have been appended with unused missing blobs, %d were created from them" % (count, count_adjusted, count_notused))
        elif options.debugload == 5:
            phase.start_phase("Reading previously saved debug environment at level %d..." % options.debugload)
            v = util.load_object(util.debug_filename(options.debugload))
            phase.end_phase()
        if options.debugsave == 5:
            phase.start_phase("Saving debug environment at level %d..." % options.debugsave)
            util.save_object(v, util.debug_filename(options.debugsave))
            phase.end_phase()

        # debug quickcheck on barcode and blob database consistency
        algo_barcode.check_barcode_blob_consistency(v.barcodes, v.color_blobs, v.colorids)

    ############################################################################
    ################################ phase 6 ###################################
    ############################################################################

    if options.debugend > 5:
        if options.debugload < 6:
            ############################################################################
            # find partial blobs from tdist -> backward
            phase.start_phase("Backward iteration: find partial IDs based on full/partial IDs and temporal closeness chains...")
            count = 0
            count_adjusted = 0
            count_notused = 0
            for currentframe in range(framecount-2, -1, -1):
                # main algo is in algo.py, all function params are lists so they are modified in the call
                (a, b, c) = algo_barcode.find_partlyfound_from_tdist(
                        'backward', currentframe, v.tdistlists, v.color_blobs, v.barcodes, v.colorids,
                        v.sdistlists[currentframe], v.md_blobs, v.mdindices)
                count += a
                count_adjusted += b
                count_notused += c

                # write results to output text file
                # barcode_textfile_writeframe(v.barcodes[currentframe], currentframe, v.colorids)
                # print status
                phase.check_and_print_phase_status('backward', currentframe, framecount)
            phase.end_phase("%d partial barcodes found, from which %d barcodes have been appended with unused missing blobs, %d were created from them" % (count, count_adjusted, count_notused))
        elif options.debugload == 6:
            phase.start_phase("Reading previously saved debug environment at level %d..." % options.debugload)
            v = util.load_object(util.debug_filename(options.debugload))
            phase.end_phase()
        if options.debugsave == 6:
            phase.start_phase("Saving debug environment at level %d..." % options.debugsave)
            util.save_object(v, util.debug_filename(options.debugsave))
            phase.end_phase()

        algo_barcode.print_max_barcode_count(v.barcodes, v.colorids)

        # debug quickcheck on barcode and blob database consistency
        algo_barcode.check_barcode_blob_consistency(v.barcodes, v.color_blobs, v.colorids)

    ############################################################################
    ################################ phase 7 ###################################
    ############################################################################

    if options.debugend > 6:
        if options.debugload < 7:
            ############################################################################
            # remove/concat bad partial barcodes
            phase.start_phase("Remove partial barcodes that have shared id properties...")
            count_sharesid = 0
            for currentframe in range(framecount):
                # remove close sharesid ones
                count_sharesid += algo_barcode.remove_close_sharesid(
                        v.barcodes[currentframe], v.color_blobs[currentframe], v.colorids, MFix.PARTLYFOUND_FROM_TDIST)
                # print status
                phase.check_and_print_phase_status('forward', currentframe, framecount)
            phase.end_phase("%d sharesid barcodes deleted/joined." % count_sharesid)
        elif options.debugload == 7:
            phase.start_phase("Reading previously saved debug environment at level %d..." % options.debugload)
            v = util.load_object(util.debug_filename(options.debugload))
            phase.end_phase()
        if options.debugsave == 7:
            phase.start_phase("Saving debug environment at level %d..." % options.debugsave)
            util.save_object(v, util.debug_filename(options.debugsave))
            phase.end_phase()

        # debug quickcheck on barcode and blob database consistency
        algo_barcode.check_barcode_blob_consistency(v.barcodes, v.color_blobs, v.colorids)

        ############################################################################
        # set sharesid/sharesblob mfix
        phase.start_phase("Set sharesid/sharesblob mfix flags...")
        for currentframe in range(framecount):
            # set mfix flags temporarily (we might use this info later
            algo_barcode.set_shared_mfix_flags(v.barcodes[currentframe],
                    v.color_blobs[currentframe], v.colorids)
            # print status
            #phase.check_and_print_phase_status('backward', currentframe, framecount)
        phase.end_phase()

        # debug quickcheck on barcode and blob database consistency
        algo_barcode.check_barcode_blob_consistency(v.barcodes, v.color_blobs, v.colorids)

    ############################################################################
    ################################ phase 8 ###################################
    ############################################################################

    if not options.notrajectory:
        if options.debugend > 7:
            if options.debugload < 8:
                ########################################################################
                # create trajectory database
                phase.start_phase("Creating trajectory database...")
                for currentframe in range(framecount):
                    algo_trajectory.initialize_trajectories(
                            v.trajectories, v.trajsonframe, v.barcodes, v.color_blobs, currentframe,
                            v.colorids, v.md_blobs, v.mdindices)

                    # write results to output text file
                    # barcode_textfile_writeframe(v.barcodes[currentframe], currentframe, v.colorids)
                    # print status
                    phase.check_and_print_phase_status('forward', currentframe, framecount)
                # calculate total distance (and  max velocity) for all trajectories
                # Depreciated
    #            algo_trajectory.calculate_total_distance(v.trajectories, v.barcodes, v.colorids)
                phase.end_phase("%d trajectories found with average length of %d frames" %
                        algo_trajectory.number_and_length_of_trajectories(v.trajectories))
            elif options.debugload == 8:
                phase.start_phase("Reading previously saved debug environment at level %d..." % options.debugload)
                v = util.load_object(util.debug_filename(options.debugload))
                phase.end_phase()
            if options.debugsave == 8:
                phase.start_phase("Saving debug environment at level %d..." % options.debugsave)
                util.save_object(v, util.debug_filename(options.debugsave))
                phase.end_phase()

            # debug quickcheck on barcode and blob database consistency
            algo_barcode.check_barcode_blob_consistency(v.barcodes, v.color_blobs, v.colorids)

    ############################################################################
    ################################ phase 9 ###################################
    ############################################################################

        if options.debugend > 8:
            if options.debugload < 9:
                ########################################################################
                # sort and select best trajectories
                phase.start_phase("Sort trajectories, choose and connect best, delete overlapping bad ones...")
                algo_trajectory.find_best_trajectories(
                        v.trajectories, v.trajsonframe, v.colorids, v.barcodes,
                        v.color_blobs, find_best_trajectories_settings)
                phase.end_phase()
            elif options.debugload == 9:
                phase.start_phase("Reading previously saved debug environment at level %d..." % options.debugload)
                v = util.load_object(util.debug_filename(options.debugload))
                phase.end_phase()
            if options.debugsave == 9:
                phase.start_phase("Saving debug environment at level %d..." % options.debugsave)
                util.save_object(v, util.debug_filename(options.debugsave))
                phase.end_phase()

            # debug quickcheck on barcode and blob database consistency
            algo_barcode.check_barcode_blob_consistency(v.barcodes, v.color_blobs, v.colorids)

    ############################################################################
    ################################ phase 10 ##################################
    ############################################################################

        if options.debugend > 9:
            if options.debugload < 10:
                ########################################################################
                # finalize trajectories, juhuuuuuuuu
                phase.start_phase("Finalize trajectories...")
                algo_trajectory.finalize_trajectories(
                        v.trajectories, v.trajsonframe, v.barcodes, v.color_blobs, v.colorids)
                phase.end_phase()
            elif options.debugload == 10:
                phase.start_phase("Reading previously saved debug environment at level %d..." % options.debugload)
                v = util.load_object(util.debug_filename(options.debugload))
                phase.end_phase()
            if options.debugsave == 10:
                phase.start_phase("Saving debug environment at level %d..." % options.debugsave)
                util.save_object(v, util.debug_filename(options.debugsave))
                phase.end_phase()

            # debug quickcheck on barcode and blob database consistency
            algo_barcode.check_barcode_blob_consistency(v.barcodes, v.color_blobs, v.colorids)

            ########################################################################
            # set sharesid/sharesblob mfix
            phase.start_phase("Refresh sharesid/sharesblob mfix flags...")
            for currentframe in range(framecount):
                # set mfix flags temporarily (we might use this info later
                algo_barcode.set_shared_mfix_flags(v.barcodes[currentframe],
                        v.color_blobs[currentframe], v.colorids)
                # print status
                #phase.check_and_print_phase_status('backward', currentframe, framecount)
            phase.end_phase()

            # debug quickcheck on barcode and blob database consistency
            algo_barcode.check_barcode_blob_consistency(v.barcodes, v.color_blobs, v.colorids)

            ########################################################################
            # get conflicts
            phase.start_phase("Check, list and (solve) remaining conflicts...")
            algo_conflict.create_conflict_database_and_try_resolve(v.trajectories, v.barcodes,
                    v.color_blobs, v.colorids)
            phase.end_phase()

            # debug quickcheck on barcode and blob database consistency
            algo_barcode.check_barcode_blob_consistency(v.barcodes, v.color_blobs, v.colorids)

    ############################################################################
    # write results to output text file
    phase.start_phase("Write results to output text files...")
    # barcode file
    output.barcode_textfile_writeall(v.barcodes, v.colorids, not options.nodeleted) # TODO: change nodeleted to writedeleted if that is a better default
    output.barcode_textfile_close()
    # log file
    output.logfile_writeall(v.color_blobs, v.barcodes)
    output.logfile_close()
    phase.end_phase()

    # end main and print total time elapsed
    phase.end_phase(None, True)
