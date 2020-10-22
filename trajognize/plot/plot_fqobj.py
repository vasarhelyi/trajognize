"""This script generates plots for 'fqobj' type trajognize.stat outputs.

Usage: plot_fqobj.py inputfile(s)

where inputfile(s) is/are the output of trajognize.stat FQObj object (.txt)

Output is written in subdirectories of input dir, organized according to
experiment, group, light and object.

Script calls three other scripts:

    ../calc/reorder_matrixfile_eades.py -- to have Eades-order, CD-decomposed input
    plot_matrixmap.py                   -- as a common framework for matrix plotting
    plot_graph.py                       -- as a common framework for graph plotting

"""

import os, subprocess, sys, glob, re

try:
    import trajognize.parse
    import trajognize.calc.reorder_matrixfile_eades
    import trajognize.corr.util
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(
        os.path.dirname(sys.modules[__name__].__file__), "../..")))
    import trajognize.parse
    import trajognize.calc.reorder_matrixfile_eades
    import trajognize.corr.util

# relative imports
import plot
import plot_matrixmap
import plot_graph
import spgm


def get_categories_from_name(name):
    """Get light, object and group from paragraph header (name), e.g.:

    fqobj_daylight_home
    fqobj_nightlight_home_C
    fqobj_daylight_entrance_group_G3S
    fqobj_nightlight_entrance_group_G3S_F

    """
    match = re.match(r'^fqobj_([a-z]*)_([a-zA-Z]*)', name)
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
        print(__doc__)
        return
    if sys.platform.startswith('win'):
        inputfiles = glob.glob(argv[0])
    else:
        inputfiles = argv
    outdirs = []
    corrfiles = []
    for inputfile in inputfiles:
        # create reordered file
        (orderedfile, params) = trajognize.calc.reorder_matrixfile_eades.main([inputfile])
        (head, tail, plotdir) = plot.get_headtailplot_from_filename(orderedfile)
        statsum_basedir = os.path.split(os.path.split(head)[0])[0]
        exp = plot.get_exp_from_filename(orderedfile)
        # parse data file
        alldata = trajognize.parse.parse_stat_output_file(orderedfile)
        for index in range(len(alldata)):
            # get categories
            name = alldata[index][0][0]
            (light, object, group) = get_categories_from_name(name)
            # define output directory
            outdir = os.path.join(head, plotdir, exp, group, light, object)
            # if this is a new output directory, clear SPGM descriptions
            if outdir not in outdirs:
                spgm.remove_picture_descriptions(outdir)
                outdirs.append(outdir)
            # plot file
            mmparams = ["-i", orderedfile, "-n", str(index), "-o", outdir]
            # add extra parameters to plot
            # TODO: add axis labels, etc.
            i = index // 3 # F, C, D
            # symmetry, transitivity
            if name.endswith("_D") and name.startswith(params[i]['name']):
                mmparams += ["-l", "Dominance transitivity: %1.2f" % params[i]['t_index']]
            if name.endswith("_C") and name.startswith(params[i]['name']):
                mmparams += ["-l", "Symmetry index: %1.2f" % params[i]['s_index']]
            if name.endswith("_F") and name.startswith(params[i]['name']):
                mmparams += ["-l", "S=%1.2f, T=%1.2f" % (params[i]['s_index'], params[i]['t_index'])]
            # plot graph
            if name.endswith("_D") and name.startswith(params[i]['name']):
                plot_graph.main(mmparams)
            # cbrange
            if name.startswith(params[i]['name']):
                mmparams += ["-cb"] + [str(params[i]['cbrange'][0]), str(params[i]['cbrange'][1])]
            # plot matrix
            plot_matrixmap.main(mmparams)

            # save output for correlation analysis
            headerline = trajognize.corr.util.strids2headerline(alldata[index][0][1:], True)
            corrline = trajognize.corr.util.matrix2corrline(alldata[index])
            corrfile = trajognize.corr.util.get_corr_filename(statsum_basedir, exp, group, True)
            if corrfile not in corrfiles:
                if os.path.isfile(corrfile):
                    os.remove(corrfile)
                corrfiles.append(corrfile)
            trajognize.corr.util.add_corr_line(corrfile, headerline, corrline)
            # convert pairparams to params (through calculating dominance indices) and save that as well
            if name.endswith("_F"):
                headerline, corrline = trajognize.corr.util.pairparams2params(headerline, corrline)
                corrfile = trajognize.corr.util.get_corr_filename(statsum_basedir, exp, group, False)
                if corrfile not in corrfiles:
                    if os.path.isfile(corrfile):
                        os.remove(corrfile)
                    corrfiles.append(corrfile)
                trajognize.corr.util.add_corr_line(corrfile, headerline, corrline)


    # create SPGM gallery descriptions
    headhead = os.path.split(inputfile)[0]
    spgm.create_gallery_description(headhead, "Generalized FQ matrices")
    spgm.create_gallery_description(head, "Generalized FQ matrices reordered with the Eades-heuristics")
    spgm.create_gallery_description(os.path.join(head, plotdir), """Plotted results for generalized FQ pairwise matrices.
        Results are organized into subdirectories according to experiments, groups, light and object type.
        All full (_F) matrices are ordered with the Eades-heuristics and separated into Common (_C) and Dominant (_D) parts.
        Note that igraph plots are drawn with negligible data entries removed (<0.05*max).
        """)

if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:])) # pass only real params to main
    except Exception as ex:
        print(ex, file=sys.stderr)
        import traceback
        traceback.print_exc(ex)
        sys.exit(1)
