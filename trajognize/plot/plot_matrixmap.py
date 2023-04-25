"""Heatmap-type plot for squared pairwise interaction matrices."""

import os, subprocess, sys, glob, argparse

# relative imports
import plot
import spgm

try:
    import trajognize.parse
except ImportError:
    sys.path.insert(
        0,
        os.path.abspath(
            os.path.join(os.path.dirname(sys.modules[__name__].__file__), "../..")
        ),
    )
    import trajognize.parse


def add_sum_to_matrix_file(inputfile, outputfile):
    """This script parses an input file and adds row and column sums to the
    end of each matrix found in it."""

    def writesumline():
        # print last matrix sum column line
        out.write("sum")  # header
        sum[0] = 0
        for i in range(1, len(data)):
            sum[0] += sum[i]
            out.write("\t%f" % sum[i])  # sum columns
        out.write("\t%f\n" % sum[0])  # sum sum

    startnewblock = True
    writesum = False
    sum = []
    data = []
    out = open(outputfile, "w")
    out.write("# This is a post-processed file created from '%s'\n" % inputfile)
    out.write(
        "# Sum values for all columns and rows are added to all matrices. Comments are unchanged.\n\n"
    )
    for line in open(inputfile, "r"):
        strippedline = line.strip()
        # copy empty and comment lines (that also start a new block in file)
        if strippedline.startswith("#") or not strippedline:
            startnewblock = True
            if writesum:
                writesumline()
                writesum = False
            # print empty or comment line
            out.write(line)
            continue
        # remove trailing newline character
        line = line.rstrip()
        # copy header lines with sum at the end
        if startnewblock:
            startnewblock = False
            out.write("%s\tsum\n" % line)
            # reset sum for new data matrix
            sum = [0 for i in range(len(line.split("\t")))]
            continue
        # parse data lines and add row sum to end
        data = line.split("\t")
        writesum = True  # set flag
        sum[0] = 0
        for i in range(1, len(data)):
            if data[i] != data[i]:
                continue  # skip nan
            sum[0] += float(data[i])
            sum[i] += float(data[i])
        out.write("%s\t%1.12g\n" % (line, sum[0]))
    # print last matrix sum column line if needed
    if writesum:
        writesumline()
    # close output file
    out.close()


GNUPLOT_TEMPLATE = """#!/usr/bin/gnuplot

# variable definitions
inputfile = "%(inputfile)s" # input file name
inputfilesum = "%(inputfilesum)s" # sum input file name
colsumfile = "%(colsumfile)s" # generated column sum file
outputfile = "%(outputfile)s" # output file name
ID(n) = word("%(headerline)s",n+1) # string ID definitions
nID = %(id_count)d

# cbrange autodetection (TODO: implement later)
# call "%(plotpath)s/gnucall_matrixmap_0_commoncbrange.gnu" %(index)d %(index)d

# initialize settings for a given index
call "%(plotpath)s/gnucall_matrixmap_1_init.gnu" %(index)d outputfile

# overwrite non default parameters (TODO: implement later)
#set palette model HSV defined ( 0 0 0 0, 0 0.65 1 1, 1 0 1 1) # HSV 0-300 degrees (300-360 excluded)
set label 1 ID(0)          # first title line
set label 2 "%(exp)s"      # second title line
#set cbrange [cbmin:cbmax] # defined in gnucall_matrixmap_0_commoncbrange.gnu
%(iscb)sset cbrange [%(rangemin)f:%(rangemax)f]

# call main plot + sum plots for given index
call "%(plotpath)s/gnucall_matrixmap_2_plot.gnu" %(index)d
"""


def get_gnuplot_script(
    inputfile,
    inputfilesum,
    colsumfile,
    outputfile,
    id_count,
    headerline,
    index,
    exp,
    cbrange,
):
    """Return .gnu script body as string."""
    data = {
        "inputfile": inputfile,
        "inputfilesum": inputfilesum,
        "colsumfile": colsumfile,
        "outputfile": outputfile,
        "id_count": id_count,
        "headerline": headerline,
        "index": index,
        "exp": exp,
        "rangemin": 0,
        "rangemax": 0,
        "plotpath": os.path.split(os.path.abspath(__file__))[0],
    }
    if cbrange is None or cbrange[0] is None or cbrange[1] is None:
        data["iscb"] = "#"
    else:
        data["iscb"] = ""
        data["rangemin"] = cbrange[0]
        data["rangemax"] = cbrange[1]
    return GNUPLOT_TEMPLATE % data


def main(argv=[]):
    """Create a heatmap-type plot for squared pairwise interaction matrices."""
    # parse arguments
    argparser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter, description=main.__doc__
    )
    argparser.add_argument(
        "-i",
        "--inputfile",
        metavar="FILE",
        dest="inputfile",
        required=True,
        help="file to plot, as output of trajognize.stat pairwise statistics (.txt), e.g. nearestneighbor, fqobj, aa",
    )
    argparser.add_argument(
        "-n",
        "--index",
        metavar="INDEX",
        dest="index",
        type=int,
        required=True,
        help="the paragraph (index) number to plot",
    )
    argparser.add_argument(
        "-o",
        "--outputpath",
        metavar="PATH",
        dest="outputpath",
        help="optional output directory to write the results to",
    )
    argparser.add_argument(
        "-l",
        "--label",
        metavar="STR",
        dest="label",
        help="optional label to put on plot as extra title line",
    )
    argparser.add_argument(
        "-cb",
        "--cbrange",
        metavar="NUM",
        dest="cbrange",
        nargs=2,
        type=float,
        help="optional data cbrange to plot",
    )
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
    if not os.path.isdir(outdir):
        os.makedirs(outdir)
    # parse name (header)
    data = trajognize.parse.parse_stat_output_file(inputfile, index)
    headerline = data[0]
    name = headerline[0]
    outputfilecommon = os.path.join(outdir, tail + "__" + name)
    # add col and row sum to inputfilesum
    inputfilesum = outputfilecommon + ".inputfilesum"
    colsumfile = outputfilecommon + ".colsumfile"
    add_sum_to_matrix_file(inputfile, inputfilesum)
    # get other variables
    exp = plot.get_exp_from_filename(inputfile)
    id_count = len(headerline) - 1
    gnufile = outputfilecommon + ".gnu"
    outputfile = outputfilecommon + ".png"
    # write gnuplot script
    script = get_gnuplot_script(
        inputfile,
        inputfilesum,
        colsumfile,
        outputfile,
        id_count,
        " ".join(headerline),
        index,
        exp,
        options.cbrange,
    )
    with open(gnufile, "w") as f:
        f.write(script)
    # call gnuplot
    try:
        subprocess.call(["gnuplot", gnufile])
    except WindowsError:
        print("  Error plotting '%s': gnuplot is not available on Windows" % name)
    # create SPGM picture description
    spgm.create_picture_description(
        outputfile,
        [name, exp] + [options.label] if options.label is not None else [],
        inputfile,
        gnufile,
    )


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))  # pass only real params to main
    except Exception as ex:
        print(ex, file=sys.stderr)
        import traceback

        traceback.print_exc(ex)
        sys.exit(1)
