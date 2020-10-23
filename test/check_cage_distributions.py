#!/usr/bin/python
# vim: ts=4 sw=4 sts=4 et
"""
This is a small script that calculates cage center distributions and time curves.

Input is taken from all log files from [inputpath]*/OUT/*.log, where inputpath
is an optional path where subdirectories with ratognize output data can be found.
Default value is defined in util.py

Results are printed to standard output.
"""

import os, sys, time, argparse, subprocess
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
argparser.add_argument("-i", "--inputpath", dest="inputpath", help="define blob input path to have blob files at [PATH]*/OUT/*.blobs", metavar="PATH")
args = argparser.parse_args()

# get input path
path = trajognize.util.get_path_as_first_arg((None, args.inputpath))
path += '*/OUT/*.log'
print("# Using data: %s" % path)

# list files and check for error
files = glob(path)
if not files:
    exit('ERROR: No files found on input path', 1)

#initialize variables
cagecenter_all_n = 0
cagecenter_all_avg = [0.0, 0.0, 0.0, 0.0]
cagecenter_all_std = [0.0, 0.0, 0.0, 0.0]

# print filenames and good lines
ii = 0
for inputfile in files:
    try:
        ii += 1
        # get file name
        head, tail = os.path.split(inputfile)
        start = time.clock()

        print("\nParsing input file #%d: '%s'..." % (ii, tail))
        (light_log, cage_log) = trajognize.parse.parse_log_file(inputfile)
        if light_log is None and cage_log is None: continue
        light_at_frame = trajognize.util.param_at_frame(light_log)
        cage_at_frame = trajognize.util.param_at_frame(cage_log)
        print("  %d LED switches parsed" % len(light_log))
        print("  %d CAGE coordinates parsed" % len(cage_log))
        lastframe = int(subprocess.run(['tail', '-1', inputfile], 
            capture_output=True, text=True, check=True).stdout.split(None, 1)[0])
        print("  %d frames will be iterated" % (lastframe+1))

        print("Calculating cage center distribution...")
        light_at_frame.reset()
        cage_at_frame.reset()
        cagecenter_this_n = 0
        cagecenter_this_avg = [0.0, 0.0, 0.0, 0.0]
        cagecenter_this_std = [0.0, 0.0, 0.0, 0.0]

        for currentframe in range(lastframe+1):
            # get cage
            cagecenter = cage_at_frame(currentframe)
            # check for nan
            cont = False
            for i in range(4):
                if cagecenter[i] != cagecenter[i]:
                    cont = True
            if cont: continue

            # get light
            lightstr = light_at_frame(currentframe)
            if lightstr in ('DAYLIGHT', 'EXTRALIGHT'):
                light = 0
            elif lightstr in ('NIGHTLIGHT', 'STRANGELIGHT'):
                light = 1
            else:
                raise ValueError("unknown lightstr: {}".format(lightstr))

            # avg and std based on this method:
            # http://en.wikipedia.org/wiki/Standard_deviation#Rapid_calculation_methods
            # num
            cagecenter_this_n += 1
            cagecenter_all_n += 1
            for i in range(4):
                # prev avg
                this_prevavg = cagecenter_this_avg[i]
                all_prevavg = cagecenter_all_avg[i]
                # avg
                cagecenter_this_avg[i] = this_prevavg + (cagecenter[i] - this_prevavg)/cagecenter_this_n
                cagecenter_all_avg[i] = all_prevavg + (cagecenter[i] - all_prevavg)/cagecenter_all_n
                # std * n
                cagecenter_this_std[i] += (cagecenter[i] - this_prevavg)*(cagecenter[i] - cagecenter_this_avg[i])
                cagecenter_all_std[i] += (cagecenter[i] - all_prevavg)*(cagecenter[i] - cagecenter_all_avg[i])
        # print results
        if not cagecenter_this_n: cagecenter_this_n = 1 # avoid division by zero
        print("  cage coordinates for this file:\n"  \
              "    center_x:         %g +- %g\n"     \
              "    center_y:         %g +- %g\n"     \
              "    horizontal_angle: %g +- %g\n"     \
              "    vertical_angle:   %g +- %g" % ( \
                cagecenter_this_avg[0],sqrt(cagecenter_this_std[0]/cagecenter_this_n),
                cagecenter_this_avg[1],sqrt(cagecenter_this_std[1]/cagecenter_this_n),
                cagecenter_this_avg[2],sqrt(cagecenter_this_std[2]/cagecenter_this_n),
                cagecenter_this_avg[3],sqrt(cagecenter_this_std[3]/cagecenter_this_n)))

        print("  time elapsed: %gs" % (time.clock()-start))
        sys.stdout.flush()

    except KeyboardInterrupt:
        print("Keyboard Interrupt detected: printing actual results before exit.")
        break

# print global results
if not cagecenter_all_n: cagecenter_all_n = 1 # avoid division by zero
print("\nCage coordinates for all files:\n"  \
      "  center_x:         %g +- %g\n"     \
      "  center_y:         %g +- %g\n"     \
      "  horizontal_angle: %g +- %g\n"     \
      "  vertical_angle:   %g +- %g" % ( \
        cagecenter_all_avg[0],sqrt(cagecenter_all_std[0]/cagecenter_all_n),
        cagecenter_all_avg[1],sqrt(cagecenter_all_std[1]/cagecenter_all_n),
        cagecenter_all_avg[2],sqrt(cagecenter_all_std[2]/cagecenter_all_n),
        cagecenter_all_avg[3],sqrt(cagecenter_all_std[3]/cagecenter_all_n)))
