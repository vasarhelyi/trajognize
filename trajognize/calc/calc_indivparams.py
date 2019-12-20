"""This script separates individual parameters to experiments and groups.

Usage: calc_indivparams.py inputfile(s)

Output is written in a subdirectory of input dir.

"""

import os, subprocess, sys, glob, itertools, datetime

try:
    import trajognize.parse
    import trajognize.stat.init
    import trajognize.stat.experiments
    import trajognize.plot.plot
    import trajognize.plot.spgm
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(
        os.path.dirname(sys.modules[__name__].__file__), "../..")))
    import trajognize.parse
    import trajognize.stat.init
    import trajognize.stat.experiments
    import trajognize.plot.plot
    import trajognize.plot.spgm

nogroup = False

def main(argv=[]):
    """Main entry point of the script."""
    if not argv:
        print __doc__
        return
    if sys.platform.startswith('win'):
        inputfiles = glob.glob(argv[0])
    else:
        inputfiles = argv
    exps = trajognize.stat.experiments.get_initialized_experiments()
    # parse files
    for inputfile in inputfiles:
        print "parsing", os.path.split(inputfile)[1]
        (head, tail, plotdir) = trajognize.plot.plot.get_headtailplot_from_filename(inputfile)
        data = trajognize.parse.parse_stat_output_file(inputfile, 0)
        name = data[0][0]
        headerline = data[0]
        alldata = data[1:]

#        dates = [datetime.datetime.strptime(data[i][0],"%Y.%m.%d.").date() \
#                for i in xrange(1, len(data))]
        for exp in exps:
            # write interpolated data
            outdir = os.path.join(head, plotdir)
            if not os.path.isdir(outdir): os.makedirs(outdir)
            outputfile = os.path.join(outdir, "%s__exp_%s.txt" % (tail, exp))
            print "writing", os.path.split(outputfile)[1]
            outputfile = open(outputfile, "w")
            outputfile.write(trajognize.stat.experiments.get_formatted_description(exps[exp], "#"))
            outputfile.write("\n")
            if nogroup:
                outputfile.write("\t".join(data[0]))
                outputfile.write("\n")
                for i in xrange(len(alldata)):
                    outputfile.write("\t".join(alldata[i]))
                    outputfile.write("\n")
            else:
                for group in exps[exp]['groups']:
                    names = sorted(exps[exp]['groups'][group])
                    outputfile.write("\t".join(["%s_group_%s" % (name, group)] + names))
                    outputfile.write("\n")
                    for i in xrange(len(alldata)):
                        outputfile.write("\t".join([alldata[i][0].strip('.').replace('.', '-')] +
                                [alldata[i][headerline.index(strid)] for strid in names]))
                        outputfile.write("\n")
                    outputfile.write("\n\n")

            outputfile.close()

    # create SPGM gallery description
    trajognize.plot.spgm.create_gallery_description(outdir, """
            Daily interpolated %s data.
            """ % name)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:])) # pass only real params to main
    except Exception as ex:
        print >>sys.stderr, ex
        import traceback
        traceback.print_exc(ex)
        sys.exit(1)
