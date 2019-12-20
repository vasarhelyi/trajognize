"""This script generates correlation outputs for 'fqwhilef' type trajognize.stat outputs.

TODO: generate plot as well...

Usage: plot_fqwhilef.py inputfile(s)

where inputfile(s) is/are the output of trajognize.stat fqwhilef_t object (.txt)

Output is written in subdirectories of input dir, organized according to
experiment, group, light and object.

"""

import os, subprocess, sys, glob
from plot import *
import plot_matrixmap
import trajognize.parse
import trajognize.calc.reorder_matrixfile_eades
import spgm
import trajognize.corr.util


def get_categories_from_name(name):
    """Get light, object and group from paragraph header (name), e.g.:

    fqwhilef_daylight_home
    fqwhilef_daylight_entrance_group_G3S

    """
    match = re.match(r'^fqwhilef_([a-z]*)_([a-zA-Z]*)', name)
    if match:
        light = match.group(1)
        object = match.group(2)
    else:
        return (None, None, None)
    match = re.match(r'.*group_([0-9A-Z]*)', name)
    if match:
        group = match.group(1)
    else:
        group = 'all'
    return (light, object, group)


def main(argv=[]):
    """Main entry point of the script."""
    if not argv:
        print __doc__
        return
    if sys.platform.startswith('win'):
        inputfiles = glob.glob(argv[0])
    else:
        inputfiles = argv
    outdirs = []
    corrfiles = []
    for inputfile in inputfiles:
        print "parsing", os.path.split(inputfile)[1]
        alldata = trajognize.parse.parse_stat_output_file(inputfile)
        (head, tail, plotdir) = get_headtailplot_from_filename(inputfile)
        exp = get_exp_from_filename(inputfile)
        for index in xrange(len(alldata)):
            # get categories
            name = alldata[index][0][0]
            (light, object, group) = get_categories_from_name(name)
            # define output directory
            outdir = os.path.join(head, plotdir, exp, group, light, object)
            # if this is a new output directory, clear SPGM descriptions
            if outdir not in outdirs:
                spgm.remove_picture_descriptions(outdir)
                outdirs.append(outdir)

            # TODO: add plot if needed
                os.makedirs(outdir)

            tokens = ['0', 'avg', 'std', 'num']
            indices = [1, -3, -2, -1]
            # save avg output for correlation analysis
            headerline = trajognize.corr.util.strids2headerline(alldata[index][0][1:], False)
            corrfile = trajognize.corr.util.get_corr_filename(exp, group, False)
            if corrfile not in corrfiles:
                if os.path.isfile(corrfile):
                    os.remove(corrfile)
                corrfiles.append(corrfile)
            for j,s in enumerate(tokens):
                i = indices[j]
                if alldata[index][i][0] != s:
                    raise ValueError("ERROR: alldata[index][%d][0] should be '%s', but it is '%s'" % (i, s, alldata[index][i][0]))
                corrline = "\t".join([alldata[index][0][0] + "_" + s] + alldata[index][i][1:]) # num line
                trajognize.corr.util.add_corr_line(corrfile, headerline, corrline)


    # create SPGM gallery descriptions
    headhead = os.path.split(inputfile)[0]
    spgm.create_gallery_description(headhead, "How many are around when feeding?")
    spgm.create_gallery_description(head, "Generalized FQwhileF matrices")
    spgm.create_gallery_description(os.path.join(head, plotdir), """TODO: no plot yet. Call 1-800-makeplot if you need one.
        Plotdir is only made to store corr results
        Results are organized into subdirectories according to experiments, groups, light and object type.
        """)

if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:])) # pass only real params to main
    except Exception as ex:
        print >>sys.stderr, ex
        import traceback
        traceback.print_exc(ex)
        sys.exit(1)
