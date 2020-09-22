#!/usr/bin/python
# vim: ts=4 sw=4 sts=4 et
"""
This is a small script that calculates the blob distance distribution for
all blobs that are closer than a given threshold. It is important for
determining the max inrat distance for color blobs.

Added: distance distribution between blobs of same color on consecutive frames.

Added: noise distribution of tdist with diffcolor and sdist with same color.

Added: heatmap of all color, md and rat blobs, separated for day/night light conditions.

Added: distance distribution of motion blobs

Added: check size distribution of blobs

Input is taken from all blob files from [inputpath]*/OUT/*.blobs and [inputpath]*/OUT/*.log,
where inputpath is an optional path where subdirectories with ratognize output data can be found.
Note that a single blob file can also be given instead of a path.
Default value is defined in util.py.

Results are printed to standard output.
"""

import os, sys, time, argparse
from glob import glob
from math import cos, acos, pi, sqrt

try:
    import trajognize
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(
        os.path.dirname(sys.modules[__name__].__file__), "..")))
    import trajognize

# parse command line arguments
argparser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=__doc__)
argparser.add_argument("-nd", "--nodist", dest="nodist", action="store_true", default=False, help="do not calculate distribution of color blobs")
argparser.add_argument("-nm", "--nomotiondist", dest="nomotiondist", action="store_true", default=False, help="do not calculate distribution of motion blobs")
argparser.add_argument("-nh", "--noheatmap", dest="noheatmap", action="store_true", default=False, help="do not calculate heatmaps")
argparser.add_argument("-cc", "--correctcage", dest="correctcage", action="store_true", default=False, help="correct for cage center dislocations")
argparser.add_argument("-i", "--inputpath", required=True, dest="inputpath", help="define individual blob input file, or a path that has blob files at [PATH]*/OUT/*.blobs", metavar="PATH")
argparser.add_argument("-p", "--projectfile", metavar="FILE", required=True, dest="projectfile", help="define project settings file that contains a single TrajectorySettings class instantiation.")
args = argparser.parse_args()

# project settings
project_settings = trajognize.settings.import_trajognize_settings_from_file(args.projectfile)
print("Current project is: %s\n" % project_settings.project_name)

# init distance distribution matrices
max_sdist = 150 # [pixel]
max_tdist = 150 # [pixel]
max_sizedist = 150 # [pixel]

if not args.nodist:
    sdists = [0 for x in range(max_sdist + 1)]
    sdists_samecolor = [0 for x in range(max_sdist + 1)]
    tdists = [0 for x in range(max_tdist + 1)]
    tdists_diffcolor = [0 for x in range(max_tdist + 1)]
    sizedists = [0 for x in range(max_sizedist + 1)]
    axisAdists = [0 for x in range(max_sizedist + 1)]
    axisABdists = [0 for x in range(max_sizedist + 1)]
    eccentrdists = [0 for x in range(max_sizedist + 1)]

if not args.nomotiondist:
    sdists_md = [0 for x in range(max_sdist + 1)]
    tdists_md = [0 for x in range(max_tdist + 1)]
    delta_o_avg_md = [0 for x in range(max_tdist + 1)] # avg orientation change
    delta_o_std_md = [0 for x in range(max_tdist + 1)] # std orientation change

# init blob occurrence heatmaps
if not args.noheatmap:
    heatmap_bin_size = 1 # [pixel]
    heatmaps = [[[[0 for y in range(int(project_settings.image_size.y/heatmap_bin_size)) ] for x in range(int(project_settings.image_size.x/heatmap_bin_size))] for c in range(5)] for light in range(2)] # [light][color][x][y]
    heatmap_md = [[[0 for y in range(int(project_settings.image_size.y/heatmap_bin_size)) ] for x in range(int(project_settings.image_size.x/heatmap_bin_size))] for light in range(2)] # [light][x][y]
    heatmap_rat = [[[0 for y in range(int(project_settings.image_size.y/heatmap_bin_size)) ] for x in range(int(project_settings.image_size.x/heatmap_bin_size))] for light in range(2)] # [light][x][y]

# get input path
path = trajognize.util.get_path_as_first_arg((None, args.inputpath))
if not os.path.isfile(path):
    path += '*/OUT/*.blobs'
    print("# Using data: %s" % path)
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
        inputfile_log = inputfile[:-6] # remove '.blobs'
        inputfile_log += '.log'
        start = time.clock()

        print("\nParsing input file #%d: '%s'..." % (ii, tail))
        color_blobs, md_blobs, rat_blobs = trajognize.parse.parse_blob_file(inputfile)
        if color_blobs is None and md_blobs is None and rat_blobs is None: continue
        print("  %d BLOB lines parsed" % len(color_blobs))
        sys.stdout.flush()

        if not args.noheatmap:
            print("\nParsing input log file from same path...")
            (light_log, cage_log) = trajognize.parse.parse_log_file(inputfile_log)
            if not light_log or not cage_log: continue
            light_at_frame = trajognize.util.param_at_frame(light_log)
            cage_at_frame = trajognize.util.param_at_frame(cage_log)
            print("  %d LED switches parsed" % len(light_log))
            print("  %d CAGE coordinates parsed" % len(cage_log))
            sys.stdout.flush()

        if not args.nodist:
            print("Calculating size distribution...")
            good = 0
            for currentframe in range(len(color_blobs)):
                for blob in color_blobs[currentframe]:
                    d = int(blob.radius * 2)
                    if d > max_sizedist: continue
                    sizedists[d] += 1
                    good += 1
            print("  %d blobs added with diameter <= %d" % (good, max_sizedist))
            sys.stdout.flush()

            try:
                print("Calculating axisA distribution...")
                good = 0
                for currentframe in range(len(color_blobs)):
                    for blob in color_blobs[currentframe]:
                        d = int(blob.axisA)
                        if d > max_sizedist: continue
                        axisAdists[d] += 1
                        good += 1
                print("  %d blobs added with axisA <= %d" % (good, max_sizedist))
                sys.stdout.flush()

                print("Calculating 10*axisA/axisB distribution...")
                good = 0
                for currentframe in range(len(color_blobs)):
                    for blob in color_blobs[currentframe]:
                        d = int(10*blob.axisA/blob.axisB)
                        if d > max_sizedist: continue
                        axisABdists[d] += 1
                        good += 1
                print("  %d blobs added with 10*axisA/axisB <= %d" % (good, max_sizedist))
                sys.stdout.flush()

                print("Calculating eccentricity distribution...")
                good = 0
                for currentframe in range(len(color_blobs)):
                    for blob in color_blobs[currentframe]:
                        d = int(max_sizedist*sqrt(blob.axisA*blob.axisA-blob.axisB*blob.axisB)/blob.axisA)
                        if d > max_sizedist: continue
                        eccentrdists[d] += 1
                        good += 1
                print("  %d blobs added with eccentricity <= %d" % (good, max_sizedist))
                sys.stdout.flush()

            except AttributeError:
                print("  ERROR: no axis is defined in blob data")
                sys.stdout.flush()


            print("Calculating spatial distance distribution...")
            good = 0
            good_samecolor = 0
            for currentframe in range(len(color_blobs)):
                for i in range(len(color_blobs[currentframe])):
                    for j in range(i):
                        # get distance and skip ones that are far away
                        d = int(trajognize.algo.get_distance(color_blobs[currentframe][i], color_blobs[currentframe][j]))
                        if d > max_sdist: continue
                        # same color
                        if color_blobs[currentframe][i].color == color_blobs[currentframe][j].color:
                            sdists_samecolor[d] += 1
                            good_samecolor += 1
                        else:
                            sdists[d] += 1
                            good += 1
            print("  %d blob pairs added with diff color and distance <= %d on the same frame" % (good, max_sdist))
            print("  %d blob pairs added with same color and distance <= %d on the same frame" % (good_samecolor, max_sdist))
            sys.stdout.flush()

            print("Calculating temporal distance distribution...")
            good = 0
            good_diffcolor = 0
            for currentframe in range(1, len(color_blobs)):
                for i in range(len(color_blobs[currentframe])):
                    for j in range(len(color_blobs[currentframe-1])):
                        # get distance and skip ones that are far away
                        d = int(trajognize.algo.get_distance(color_blobs[currentframe][i], color_blobs[currentframe-1][j]))
                        if d > max_tdist: continue
                        # if same color
                        if color_blobs[currentframe][i].color == color_blobs[currentframe-1][j].color:
                            tdists[d] += 1
                            good += 1
                        else:
                            tdists_diffcolor[d] += 1
                            good_diffcolor += 1
            print("  %d blob pairs added with same color and distance <= %d on consecutive frames" % (good, max_tdist))
            print("  %d blob pairs added with diff color and distance <= %d on consecutive frames" % (good_diffcolor, max_tdist))
            sys.stdout.flush()

        if not args.nomotiondist:
            print("Calculating spatial distance distribution of motion blobs...")
            good = 0
            for currentframe in range(len(md_blobs)):
                for i in range(len(md_blobs[currentframe])):
                    for j in range(i):
                        # get distance and skip ones that are far away
                        d = int(trajognize.algo.get_distance(md_blobs[currentframe][i], md_blobs[currentframe][j]))
                        if d > max_sdist: continue
                        sdists_md[d] += 1
                        good += 1
            print("  %d blob pairs added with distance <= %d on the same frame" % (good, max_sdist))
            sys.stdout.flush()

            print("Calculating temporal distance distribution of motion blobs...")
            good = 0
            good_diffcolor = 0
            for currentframe in range(1, len(md_blobs)):
                for i in range(len(md_blobs[currentframe])):
                    for j in range(len(md_blobs[currentframe-1])):
                        # assign temporary pointers
                        blobi = md_blobs[currentframe][i]
                        blobj = md_blobs[currentframe-1][j]
                        # get distance and skip ones that are far away
                        d = int(trajognize.algo.get_distance(blobi, blobj))
                        if d > max_tdist: continue
                        # store distance
                        tdists_md[d] += 1
                        # store orientation change
                        (delta_o_avg_md[d], delta_o_std_md[d]) = trajognize.algo.calculate_running_avg(
                                acos(abs(cos(blobi.orientation - blobj.orientation))) * 180/pi,
                                tdists_md[d],
                                delta_o_avg_md[d],
                                delta_o_std_md[d])
                        good += 1
            print("  %d blob pairs added with distance <= %d on consecutive frames" % (good, max_tdist))
            sys.stdout.flush()

        if not args.noheatmap:
            print("Calculating color blob heatmaps...")
            good = [0, 0]
            light_at_frame.reset()
            cage_at_frame.reset()
            for currentframe in range(len(color_blobs)):
                # get light
                lightstr = light_at_frame(currentframe)
                if lightstr in ('DAYLIGHT', 'EXTRALIGHT'):
                    light = 0
                elif lightstr in ('NIGHTLIGHT', 'STRANGELIGHT'):
                    light = 1
                else:
                    raise ValueError("unknown lightstr: {}".format(lightstr))
                # get cage
                cagecenter = cage_at_frame(currentframe)
                # store blobs on heatmap
                for i in range(len(color_blobs[currentframe])):
                    # get center and skip bad ones: nan or outside image area
                    centerx = color_blobs[currentframe][i].centerx
                    centery = color_blobs[currentframe][i].centery
                    if args.correctcage:
                        centerx += project_settings.cage_center_x - cagecenter[0]
                        centery += project_settings.cage_center_y - cagecenter[1]
                    if centerx != centerx or centerx >= project_settings.image_size.x or centerx < 0: continue
                    if centery != centery or centery >= project_settings.image_size.y or centery < 0: continue
                    # store good ones on heatmap
                    heatmaps[light][color_blobs[currentframe][i].color][int(centerx/heatmap_bin_size)][int(centery/heatmap_bin_size)] += 1
                    good[light] += 1
            print("  %d blobs added to daylight color blob heatmaps" % good[0])
            print("  %d blobs added to nightlight color blob heatmaps" % good[1])
            sys.stdout.flush()

            print("Calculating motion blob heatmap...")
            good = [0, 0]
            light_at_frame.reset()
            cage_at_frame.reset()
            for currentframe in range(len(md_blobs)):
                # get light
                lightstr = light_at_frame(currentframe)
                if lightstr in ('DAYLIGHT', 'EXTRALIGHT'):
                    light = 0
                elif lightstr in ('NIGHTLIGHT', 'STRANGELIGHT'):
                    light = 1
                else:
                    raise ValueError("unknown lightstr: {}".format(lightstr))
                # get cage
                cagecenter = cage_at_frame(currentframe)
                # store blobs on heatmap
                for i in range(len(md_blobs[currentframe])):
                    # get center and skip bad ones: nan or outside image area
                    centerx = md_blobs[currentframe][i].centerx
                    centery = md_blobs[currentframe][i].centery
                    if args.correctcage:
                        centerx += project_settings.cage_center_x - cagecenter[0]
                        centery += project_settings.cage_center_y - cagecenter[1]
                    if centerx != centerx or centerx >= project_settings.image_size.x or centerx < 0: continue
                    if centery != centery or centery >= project_settings.image_size.y or centery < 0: continue
                    # store good ones on heatmap
                    heatmap_md[light][int(centerx/heatmap_bin_size)][int(centery/heatmap_bin_size)] += 1
                    good[light] += 1
            print("  %d blobs added to daylight motion blob heatmap" % good[0])
            print("  %d blobs added to nightlight motion blob heatmap" % good[1])
            sys.stdout.flush()

            print("Calculating rat blob heatmap...")
            good = [0, 0]
            light_at_frame.reset()
            cage_at_frame.reset()
            for currentframe in range(len(rat_blobs)):
                # get light
                lightstr = light_at_frame(currentframe)
                if lightstr in ('DAYLIGHT', 'EXTRALIGHT'):
                    light = 0
                elif lightstr in ('NIGHTLIGHT', 'STRANGELIGHT'):
                    light = 1
                else:
                    raise ValueError("unknown lightstr: {}".format(lightstr))
                # get cage
                cagecenter = cage_at_frame(currentframe)
                # store blobs on heatmap
                for i in range(len(rat_blobs[currentframe])):
                    # get center and skip bad ones: nan or outside image area
                    centerx = rat_blobs[currentframe][i].centerx
                    centery = rat_blobs[currentframe][i].centery
                    if args.correctcage:
                        centerx += project_settings.cage_center_x - cagecenter[0]
                        centery += project_settings.cage_center_y - cagecenter[1]
                    if centerx != centerx or centerx >= project_settings.image_size.x or centerx < 0: continue
                    if centery != centery or centery >= project_settings.image_size.y or centery < 0: continue
                    # store good ones on heatmap
                    heatmap_rat[light][int(centerx/heatmap_bin_size)][int(centery/heatmap_bin_size)] += 1
                    good[light] += 1
            print("  %d blobs added to daylight rat blob heatmap" % good[0])
            print("  %d blobs added to nightlight rat blob heatmap" % good[1])
            sys.stdout.flush()

        print("  time elapsed: %gs" % (time.clock()-start))
        sys.stdout.flush()

    except KeyboardInterrupt:
        print("Keyboard Interrupt detected: printing actual results before exit.")
        break

# print color blob distributions
if not args.nodist:
    print("\n\n# size distribution of blobs")
    print("diameter\tnum")
    for i in range(max_sizedist + 1):
        print("%d\t%d" % (i, sizedists[i]))

    print("\n\n# axisA distribution of blobs")
    print("axisA\tnum")
    for i in range(max_sizedist + 1):
        print("%d\t%d" % (i, axisAdists[i]))

    print("\n\n# 10*axisA/axisB distribution of blobs")
    print("axisAB\tnum")
    for i in range(max_sizedist + 1):
        print("%d\t%d" % (i, axisABdists[i]))

    print("\n\n# %d*eccentricity distribution of blobs" % max_sizedist)
    print("%d*eccentricity\tnum" % max_sizedist)
    for i in range(max_sizedist + 1):
        print("%d\t%d" % (i, eccentrdists[i]))

    print("\n\n# distance distribution on a frame between blobs of difference color")
    print("sdist\tnum")
    for i in range(max_sdist + 1):
        print("%d\t%d" % (i, sdists[i]))

    print("\n\n# distance distribution on a frame between blobs of same color (as noise reference)")
    print("sdist_samecolor\tnum")
    for i in range(max_sdist + 1):
        print("%d\t%d" % (i, sdists_samecolor[i]))

    print("\n\n# distance distribution on consecutive frames between blobs of same color")
    print("tdist\tnum")
    for i in range(max_tdist + 1):
        print("%d\t%d" % (i, tdists[i]))

    print("\n\n# distance distribution on consecutive frames between blobs of different color (as noise reference)")
    print("tdist_diffcolor\tnum")
    for i in range(max_tdist + 1):
        print("%d\t%d" % (i, tdists[i]))

# print motion blob distributions
if not args.nomotiondist:
    print("\n\n# distance distribution on a frame between motion blobs")
    print("sdist_md\tnum")
    for i in range(max_sdist + 1):
        print("%d\t%d" % (i, sdists_md[i]))

    print("\n\n# distance distribution on consecutive frames between motion blobs")
    print("tdist_md\tnum\tdelta_o_avg\tdelta_o_std")
    for i in range(max_tdist + 1):
        print("%d\t%d\t%f\t%f" % (i, tdists_md[i], delta_o_avg_md[i],
            sqrt(delta_o_std_md[i]/tdists_md[i]) if tdists_md[i] else float('nan'))
        )

# print heatmaps
if not args.noheatmap:
    for light in range(len(project_settings.good_light)):
        for k in range(5):
            print("\n\n# heatmap of %s %s blobs" % (project_settings.good_light[light], project_settings.color_names[k]))
            print("heatmap_%s_%s" % (project_settings.good_light[light], project_settings.color_names[k]), end=" ")
            for x in range(int(project_settings.image_size.x/heatmap_bin_size)):
                print("\t%d" % (x * heatmap_bin_size), end=" ")
            print("")
            for y in range(int(project_settings.image_size.y/heatmap_bin_size)):
                print("%d" % (y * heatmap_bin_size), end=" ")
                for x in range(int(project_settings.image_size.x/heatmap_bin_size)):
                    print("\t%d" % heatmaps[light][k][x][y], end=" ")
                print("")

    for light in range(len(project_settings.good_light)):
        print("\n\n# heatmap of %s motion blobs" % project_settings.good_light[light])
        print("heatmap_%s_md" % project_settings.good_light[light], end=" ")
        for x in range(int(project_settings.image_size.x/heatmap_bin_size)):
            print("\t%d" % (x * heatmap_bin_size), end=" ")
        print("")
        for y in range(int(project_settings.image_size.y/heatmap_bin_size)):
            print("%d" % (y * heatmap_bin_size), end=" ")
            for x in range(int(project_settings.image_size.x/heatmap_bin_size)):
                print("\t%d" % heatmap_md[light][x][y], end=" ")
            print("")

    for light in range(len(project_settings.good_light)):
        print("\n\n# heatmap of %s rat blobs" % project_settings.good_light[light])
        print("heatmap_%s_rat" % project_settings.good_light[light], end=" ")
        for x in range(int(project_settings.image_size.x/heatmap_bin_size)):
            print("\t%d" % (x * heatmap_bin_size), end=" ")
        print("")
        for y in range(int(project_settings.image_size.y/heatmap_bin_size)):
            print("%d" % (y * heatmap_bin_size), end=" ")
            for x in range(int(project_settings.image_size.x/heatmap_bin_size)):
                print("\t%d" % heatmap_rat[light][x][y], end=" ")
            print("")
