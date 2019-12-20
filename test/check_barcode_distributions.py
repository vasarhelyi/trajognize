#!/usr/bin/python
# vim: ts=4 sw=4 sts=4 et
"""
This is a small script that calculates the following distributions:

  - 24h distribution of number of barcodes

  - number of simultaneous barcodes with same ID, normal and including deleted

  - heatmap of barcodes, separated for day/night light conditions.

Input is taken from all barcode files from [inputpath]*/OUT/*ts.blobs.barcodes
and [param1]*/OUT/*ts.log, where inputpath is an optional path where
subdirectories with ratognize/trajognize output data can be found.
default value is defined in util.py

Results are printed to standard output.

"""

import os, sys, time, argparse
from glob import glob
from math import sqrt

try:
    import trajognize
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(
        os.path.dirname(sys.modules[__name__].__file__), "..")))
    import trajognize

# parse command line arguments
argparser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=__doc__)
argparser.add_argument("-ns", "--nosameiddist", dest="nosameiddist", action="store_true", default=False, help="do not calculate number distribution of simultaneous barcodes")
argparser.add_argument("-nh", "--noheatmap", dest="noheatmap", action="store_true", default=False, help="do not calculate heatmaps")
argparser.add_argument("-nt", "--notimedist", dest="notimedist", action="store_true", default=False, help="do not calculate 24h time distribution")
argparser.add_argument("-cc", "--correctcage", dest="correctcage", action="store_true", default=False, help="correct for cage center dislocations")
argparser.add_argument("-i", "--inputpath", dest="inputpath", help="define barcode input path to have barcode files at [PATH]*/OUT/*ts.blobs.barcodes", metavar="PATH")
args = argparser.parse_args()

# parse colorid file
colorids = trajognize.parse.parse_colorid_file()
if colorids is None: sys.exit(1)

# init barcode occurrence heatmaps
if not args.noheatmap:
    heatmap_bin_size = 1 # [pixel]
    heatmaps = [[[0 for y in xrange(int(trajognize.project.image_size.y/heatmap_bin_size)) ] for x in xrange(int(trajognize.project.image_size.x/heatmap_bin_size))] for light in xrange(len(trajognize.project.good_light))] # [light][x][y]

# init same id number distributions
if not args.nosameiddist:
    MAX_SAME_ID_WARN = 10
    MAX_SAME_ID = 200
    PATEK_COUNT = 28
    sameiddists = [[[[0 for x in xrange(MAX_SAME_ID + 1)] for deleted in xrange(2)] for ids in xrange(PATEK_COUNT+1)] for light in xrange(len(trajognize.project.good_light))] # [light][id/all][deleteddeleted][numsameid]

# init 24h time distributions
if not args.notimedist:
    avg_24h = [[0.0 for x in xrange(1440)] for i in xrange(len(colorids)+1)] # one bin for all minutes, for all colorids + sum
    std_24h = [[0.0 for x in xrange(1440)] for i in xrange(len(colorids)+1)] # one bin for all minutes, for all colorids + sum
    num_24h = [[0 for x in xrange(1440)] for i in xrange(len(colorids)+1)] # one bin for all minutes, for all colorids + sum

# get input path
path = trajognize.util.get_path_as_first_arg((None, args.inputpath))
path += '*/OUT/*ts.blobs.barcodes'
print "Using data: %s" % path

# check for corrected cage position
if args.correctcage:
    print "Using cage position correction on the heatmaps."

# list files and check for error
files = glob(path)
if not files:
    exit('ERROR: No files found on input path', 1)

# print filenames and good lines
ii = 0
for inputfile in files:
    try:
        ii += 1
        # get file name
        head, tail = os.path.split(inputfile)
        inputfile_log = inputfile[:-15] # remove '.blobs.barcodes'
        inputfile_log += '.log'
        start = time.clock()

        print "\nParsing input file #%d: '%s'..." % (ii, tail)
        barcodes = trajognize.parse.parse_barcode_file(inputfile, colorids)
        if barcodes is None: continue
        print "  %d barcode lines parsed" % len(barcodes)

        print "Parsing input log file from same path..."
        (light_log, cage_log) = trajognize.parse.parse_log_file(inputfile_log)
        if light_log is None and cage_log is None: continue
        light_at_frame = trajognize.util.param_at_frame(light_log)
        cage_at_frame = trajognize.util.param_at_frame(cage_log)
        print "  %d LED switches parsed" % len(light_log)
        print "  %d CAGE coordinates parsed" % len(cage_log)

        if not args.noheatmap:
            print "Calculating barcode heatmaps..."
            good = [0, 0]
            light_at_frame.reset()
            cage_at_frame.reset()
            for currentframe in xrange(len(barcodes)):
                # get light
                lightstr = light_at_frame(currentframe)
                if lightstr == 'DAYLIGHT':
                    light = 0
                elif lightstr == 'NIGHTLIGHT':
                    light = 1
                else:
                    continue
                # get cage
                cagecenter = cage_at_frame(currentframe)
                # store barcodes on heatmap
                for k in xrange(len(barcodes[currentframe])):
                    for barcode in barcodes[currentframe][k]:
                        # skip deleted
                        if barcode.mfix & trajognize.init.MFIX_DELETED: continue
                        # get center and skip bad ones: nan or outside image area
                        centerx = barcode.centerx
                        centery = barcode.centery
                        if args.correctcage:
                            centerx += trajognize.project.cage_center_x - cagecenter[0]
                            centery += trajognize.project.cage_center_y - cagecenter[1]
                        if centerx != centerx or centerx >= trajognize.project.image_size.x or centerx < 0: continue
                        if centery != centery or centery >= trajognize.project.image_size.y or centery < 0: continue
                        # store good ones on heatmap
                        heatmaps[light][int(centerx/heatmap_bin_size)][int(centery/heatmap_bin_size)] += 1
                        good[light] += 1
            print "  %d barcodes added to daylight heatmap" % good[0]
            print "  %d barcodes added to nightlight heatmap" % good[1]

        if not args.nosameiddist:
            print "Calculating simultaneous ID number distributions..."
            light_at_frame.reset()
            max_sameid_warning = [0 for k in xrange(len(colorids))]
            for currentframe in xrange(len(barcodes)):
                lightstr = light_at_frame(currentframe)
                if lightstr == 'DAYLIGHT':
                    light = 0
                elif lightstr == 'NIGHTLIGHT':
                    light = 1
                else:
                    continue
                for k in xrange(len(colorids)):
                    # clamp number of same ids to max
                    num = len(barcodes[currentframe][k])
                    if num > MAX_SAME_ID_WARN and not max_sameid_warning[k]:
                        print "  WARNING: there seems to be a lot of %s barcodes (%d) at frame %d." % (colorids[k].strid, num, currentframe)
                        max_sameid_warning[k] = 1
                    if num > MAX_SAME_ID:
                        print "  ERROR: too many %s barcodes (%d) at frame %d. TODO: increase MAX_SAME_ID." % (colorids[k].strid, num, currentframe)
                        num = MAX_SAME_ID
                    # store all (including deleted)
                    sameiddists[light][k][0][num] += 1
                    sameiddists[light][PATEK_COUNT][0][num] += 1
                    # store good ones (excluding deleted)
                    for barcode in barcodes[currentframe][k]:
                        if barcode.mfix & trajognize.init.MFIX_DELETED:
                            num -= 1
                    sameiddists[light][k][1][num] += 1
                    sameiddists[light][PATEK_COUNT][1][num] += 1
            num = 0
            for i in xrange(2,MAX_SAME_ID+1):
                num += sameiddists[0][PATEK_COUNT][1][i]
            print "  0:%d, 1:%d, 1+:%d barcodes are in (not deleted) daylight sameiddist" % (sameiddists[0][PATEK_COUNT][1][0], sameiddists[0][PATEK_COUNT][1][1], num)
            num = 0
            for i in xrange(2,MAX_SAME_ID+1):
                num += sameiddists[1][PATEK_COUNT][1][i]
            print "  0:%d, 1:%d, 1+:%d barcodes are in (not deleted) nightlight sameiddist" % (sameiddists[1][PATEK_COUNT][1][0], sameiddists[1][PATEK_COUNT][1][1], num)

        if not args.notimedist:
            print "Calculating 24h time distributions..."
            # get file name
            head, tail = os.path.split(inputfile)
            # get starting time
            # TODO: no error checking
            hour, minute, second = tail.split('_')[1].split('-')
            hour = int(hour)
            minute = int(minute)
            second = int(round(float(second[0:second.find('.ts.blob')])))
            secofday = hour * 3600 + minute * 60 + second
            # iterate for all frames
            numsumsum = 0
            for currentframe in xrange(len(barcodes)):
                # get current frame in min
                bin = ((secofday + currentframe/trajognize.project.FPS) % 86400 ) / 60
                numsum = 0
                # store number of barcodes in the proper time bin
                for k in xrange(len(colorids)):
                    # get number of not deleted barcodes
                    num = len(barcodes[currentframe][k])
                    for barcode in barcodes[currentframe][k]:
                        if barcode.mfix & trajognize.init.MFIX_DELETED:
                            num -= 1
                    # check for presense only
                    if num > 1: num = 1
                    # also check for number of barcodes present
                    numsum += num
                    # calculate avg, std, num based on this method:
                    # http://en.wikipedia.org/wiki/Standard_deviation#Rapid_calculation_methods
                    prev_avg = avg_24h[k][bin]
                    num_24h[k][bin] += 1
                    avg_24h[k][bin] += (num - prev_avg) / num_24h[k][bin]
                    std_24h[k][bin] += (num - prev_avg) * (num - avg_24h[k][bin])
                # store sum (all barcodes)
                k = len(colorids)
                prev_avg = avg_24h[k][bin]
                num_24h[k][bin] += 1
                avg_24h[k][bin] += (numsum - prev_avg) / num_24h[k][bin]
                std_24h[k][bin] += (numsum - prev_avg) * (numsum - avg_24h[k][bin])
                numsumsum += numsum
            print "  %d barcodes added" % numsumsum

        print "Time elapsed: %gs" % (time.clock()-start)
        sys.stdout.flush()

    except KeyboardInterrupt:
        print "Keyboard Interrupt detected: printing actual results before exit."
        break

# print heatmaps
if not args.noheatmap:
    for light in xrange(len(trajognize.project.good_light)):
        print"\n\n# heatmap of %s barcodes" % trajognize.project.good_light[light]
        print "heatmap_%s" % trajognize.project.good_light[light],
        for x in xrange(int(trajognize.project.image_size.x/heatmap_bin_size)):
            print "\t%d" % (x * heatmap_bin_size),
        print ""
        for y in xrange(int(trajognize.project.image_size.y/heatmap_bin_size)):
            print "%d" % (y * heatmap_bin_size),
            for x in xrange(int(trajognize.project.image_size.x/heatmap_bin_size)):
                print "\t%d" % heatmaps[light][x][y],
            print ""

# print sameiddists
if not args.nosameiddist:
    for light in xrange(len(trajognize.project.good_light)):
        for deleted in xrange(2):
            print"\n\n# same id distribution of %s barcodes (%s)" % (trajognize.project.good_light[light], "including MFIX_DELETED" if deleted == 0 else "only valid")
            print "sameiddists_%s_%s" % (trajognize.project.good_light[light], "withdeleted" if deleted == 0 else "onlyvalid"),
            for j in xrange(PATEK_COUNT):
                print "\t%s" % colorids[j].strid,
            print "\tALL"
            for i in xrange(MAX_SAME_ID+1):
                print "%d" %i,
                for j in xrange(PATEK_COUNT):
                    print "\t%d" % sameiddists[light][j][deleted][i],
                print "\t%d" % sameiddists[light][PATEK_COUNT][deleted][i]

# print 24h time distributions
if not args.notimedist:
    name = [colorids[k].strid for k in xrange(len(colorids))]
    name.append("all")
    print "\n\n# 24h time distribution of barcodes"
    print "# Input is read from %d files from %s" % (len(files), path)
    print "# Output bin size is one minute, range is from 00:00:00 to 23:59:59 (24*60 = 1440 bins)\n"
    # write header
    s = "time_bin"
    for k in xrange(len(name)):
        s += "\tavg_%s\tstd_%s\tnum_%s" % (name[k], name[k], name[k])
    print s
    # write all minute bins (1440)
    for bin in xrange(1440):
        s = "%02d:%02d:00" % (bin/60, bin%60)
        for k in xrange(len(name)):
            if num_24h[k][bin] > 0:
                std_24h[k][bin] = sqrt(std_24h[k][bin] / num_24h[k][bin])
            s += "\t%f\t%f\t%d" % (avg_24h[k][bin], std_24h[k][bin], num_24h[k][bin])
        print s
