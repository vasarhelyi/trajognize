"""This script reads in a full file with squared matrices inside and
writes a similar output containing the following data for all input matrices:

    - original full matrix reordered with the Eades heuristics
    - Common part of the reordered matrix (symmetry index included)
    - Dominant part of the reordered matrix (transitivity index included)

Usage: reorder_matrixfile_eades.py inputfile

where inputfile is the output of trajognize.stat objects (.txt) that
are in squared matrix format (e.g. nearestneighbour, fq, aa, etc.)

Output is written in a subdirectory of input dir.

Main script returns name of outputfile and corresponding param dictionary.

"""

import os, sys, glob, datetime, collections


try:
    import trajognize.plot.plot
    import trajognize.parse
    import trajognize.calc.hierarchy as hierarchy
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(
        os.path.dirname(sys.modules[__name__].__file__), "../..")))
    import trajognize.plot.plot
    import trajognize.parse
    import trajognize.calc.hierarchy as hierarchy


def main(argv=[]):
    """Main entry point of the script."""
    if len(argv) != 1:
        print(__doc__)
        return
    inputfile = argv[0]
    params = []

    (head, tail, plotdir) = trajognize.plot.plot.get_headtailplot_from_filename(inputfile)
    print("parsing", os.path.split(inputfile)[1])
    # define output directory and write results (filenames remain the same)
    outdir = os.path.join(head, plotdir) # calling standard heatmap will differentiate again...
    if not os.path.isdir(outdir): os.makedirs(outdir)
    outputfile = os.path.join(outdir, tail + ".txt")
    out = open(outputfile, "w")
    out.write("# This is a post-processed file created from '%s'\n" % inputfile)
    out.write("# It contains original data reordered with the Eades-heuristic, and separated into Common and Dominant part.\n")
    out.write("# Results written on %s\n\n" % str(datetime.datetime.now()))
    alldata = trajognize.parse.parse_stat_output_file(inputfile)
    for index in range(len(alldata)):
        # convert list to dict
        n = len(alldata[index][0])-1
        name = alldata[index][0][0]
        strids = alldata[index][0][1:]
        data = collections.defaultdict(collections.defaultdict)
        minvalue = float('Inf')
        maxvalue = -minvalue
        for i in range(n):
            for j in range(n):
                x = float(alldata[index][i+1][j+1])
                if x < minvalue: minvalue = x
                if x > maxvalue: maxvalue = x
                data[strids[i]][strids[j]] = x
        # reorder IDs with Eades heuristics and separate into C-D parts
        idorder = hierarchy.feedback_arc_set_eades(data)
        (dataC, dataD, s_index, dataR) = hierarchy.decompose_CD(data, idorder)
        t_index = hierarchy.dominance_transitivity(dataD, idorder)
        # save params
        params.append({
                'name': name,
                't_index': t_index,
                's_index': s_index,
                'cbrange': [minvalue, maxvalue]})
        # write full matrix
        out.write("# original file index %d, Eades-order, full matrix\n" % index)
        out.write("# S=%1.3f, T=%1.3f\n\n" % (s_index, t_index))
        trajognize.output.matrixfile_write(out, data, name + "_F", idorder)
        out.write("\n\n")
        # write Common part
        out.write("# original file index %d, Eades-order, Common part\n" % index)
        out.write("# Symmetry-index: %f\n\n" % s_index)
        trajognize.output.matrixfile_write(out, dataC, name + "_C", idorder)
        out.write("\n\n")
        # write Dominant part
        out.write("# original file index %d, Eades-order, Dominant part\n" % index)
        out.write("# Transitivity-index: %f\n\n" % t_index)
        trajognize.output.matrixfile_write(out, dataD, name + "_D", idorder)
        out.write("\n\n")
    out.close()
    return (outputfile, params)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:])) # pass only real params to main
    except Exception as ex:
        print(ex, file=sys.stderr)
        import traceback
        traceback.print_exc(ex)
        sys.exit(1)
