#!/usr/bin/env python
"""Plots a graph using either the Sugiyama layout or the reaching centrality
based layout of Enys."""

import os, sys, glob, argparse, igraph, numpy

# relative imports
import plot
import spgm

try:
    import trajognize.parse
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(
        os.path.dirname(sys.modules[__name__].__file__), "../..")))
    import trajognize.parse

def create_ncol_file(data, outputfile):
    """Create .ncol file that is compatible with igraph."""
    count = 0
    f = open(outputfile, 'w')
    for i in range(1, len(data[0])):
        for j in range(1, len(data)):
            value = float(data[i][j])
            if value and value == value:
                count += 1
                f.write("%s\t%s\t%s\n" % (data[0][i], data[j][0], data[i][j]))
    f.flush()
    f.close()
    return count


def remove_negligible_data(data):
    """Remove elements for data that are negligible, i.e.
    their value is smaller than 5% of max value"""
    x = [[float(d) for d in data[i][1:]] for i in range(1, len(data))]
    removed = []
    dmean = numpy.mean(x)
    dmax = numpy.max(x)
    dthreshold = dmax*0.05
    for i in range(1, len(data)):
        for j in range(1, len(data)):
            if x[i-1][j-1] and x[i-1][j-1] < dmax*0.05:
                data[i][j] = "0"
                removed.append(x[i-1][j-1])
    if removed:
        print(len(removed), "elements -", removed, "- removed from matrix for igraph plot, " \
                "based on the following criteria: value < 0.05 * max " \
                "(mean=%g, max=%g, threshold=%g)" % (dmean, dmax, dthreshold))


def main(argv=[]):
    # parse arguments
    argparser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=main.__doc__)
    argparser.add_argument("-i", "--inputfile", metavar="FILE", dest="inputfile", required=True, help="file to plot, as output of trajognize.stat pairwise statistics (.txt), e.g. nearestneighbor, fqobj, aa")
    argparser.add_argument("-n", "--index", metavar="INDEX", dest="index", type=int, required=True, help="the paragraph (index) number to plot")
    argparser.add_argument("-o", "--outputpath", metavar="PATH", dest="outputpath", help="optional output directory to write the results to")
    argparser.add_argument("-l", "--label", metavar="STR", dest="label", help="optional label to put on plot as extra title line")
    options = argparser.parse_args(argv)
    # check arguments
    inputfile = options.inputfile
    index = options.index
    # define output directory and filename
    (head, tail, plotdir) = plot.get_headtailplot_from_filename(inputfile)
    if options.outputpath is None:
        outdir = os.path.join(head, plotdir)
    else:
        outdir = options.outputpath
    if not os.path.isdir(outdir): os.makedirs(outdir)
    # parse name (header)
    data = trajognize.parse.parse_stat_output_file(inputfile, index)
    remove_negligible_data(data)
    headerline = data[0]
    name = headerline[0]
    outputfilecommon = os.path.join(outdir, tail + '__' + name)
    # add col and row sum to inputfilesum
    inputfilencol = outputfilecommon + ".ncol"
    if not create_ncol_file(data, inputfilencol): return
    # get other variables
    exp = plot.get_exp_from_filename(inputfile)
    id_count = len(headerline) - 1
    outputfile = outputfilecommon + ".graph.png"

    ############################################################################
    # igraph specific part starts here

    g = igraph.load(inputfilencol)

#    print("Removing loop edges...")
#    g.es([x for x, l in enumerate(g.is_loop()) if l]).delete()

    lo, extd_graph = g.layout_sugiyama(weights=g.es["weight"], return_extended_graph=True)

    # vertex parameters
    extd_graph.vs["shape"] = "none"
    extd_graph.vs[:g.vcount()]["shape"] = "rectangle"
    extd_graph.vs[:g.vcount()]["label"] = g.vs["name"]
    extd_graph.vs[:g.vcount()]["label_size"] = 14
    extd_graph.vs[:g.vcount()]["color"] = "#FF0000"
    # vertex size TODO: rectangle with width and height
    extd_graph.vs["width"] = extd_graph.vs["size"] = [extd_graph.vs["label_size"][i] * \
            len(extd_graph.vs[i]["label"]) for i in range(g.vcount())]
    extd_graph.vs["height"] = extd_graph.vs["label_size"]
    extd_graph.vs[g.vcount():]["size"] = 0

    # edge parameters
    extd_graph.es["curved"] = False
    extd_graph.es["color"] = "#228B22D0"
    # edge_weight
    has_original_eid = extd_graph != g
    for edge in extd_graph.es:
        if has_original_eid:
            orig_edge = g.es[edge["_original_eid"]]
        else:
            orig_edge = edge
        edge["weight"] = orig_edge["weight"]
    # edge width
    normalized_weights = extd_graph.es["weight"]
    wmin = min(normalized_weights)
    wmax = max(normalized_weights)
    if wmax != wmin:
        normalized_weights = [5 * (x - wmin) / (wmax - wmin) + 5 for x in normalized_weights] # 5-10
        extd_graph.es["width"] = normalized_weights
    else:
        extd_graph.es["width"] = 5
    # edge arrow size
    extd_graph.es["arrow_size"] = [max(1, x/3) for x in extd_graph.es["width"]]

    # other params
    params = dict(
            bbox=(800, 600),
            layout=lo,
            margin=20,
            autocurve=False,
    )

    # plot it
    igraph.plot(extd_graph, outputfile, **params)

    # create SPGM picture description
    spgm.create_picture_description(outputfile,
           [name, exp] + [options.label] if options.label is not None else [],
           inputfile, None)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:])) # pass only real params to main
    except Exception as ex:
        print(ex, file=sys.stderr)
        import traceback
        traceback.print_exc(ex)
        sys.exit(1)
