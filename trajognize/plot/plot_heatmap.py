"""This script generates plots for 'heatmap'/'motionmap'/'aamap' type trajognize.stat outputs.

Usage: plot_heatmap.py projectfile inputfile(s)

where inputfile(s) is/are the output of trajognize.stat HeatMap, MotionMap or AAMap objects (.txt)

For stats vith virtual substats, use autorun.sh to create symbolic links to a
common directory before running this script in the common directory.

Output is written in subdirectories of input dir, organized according to
experiment, group, light condition, real/virtual state, depending on plotted stat.

Note that intensity distribution plot works well only if all input files are
selected for a given output directory in one run.

"""

import os, subprocess, sys, glob, re

# relative imports
import plot
import spgm

try:
    import trajognize.stat.init
    import trajognize.stat.experiments
    import trajognize.settings
    from trajognize.init import Rectangle, Circle, Point
except ImportError:
    sys.path.insert(
        0,
        os.path.abspath(
            os.path.join(os.path.dirname(sys.modules[__name__].__file__), "../..")
        ),
    )
    import trajognize.stat.init
    import trajognize.stat.experiments
    import trajognize.settings
    from trajognize.init import Rectangle, Circle, Point


# TODO: ellipse/polygon needed instead of rect because yrange reverse makes rects disappear. gnuplot bug, 4.6 version needed...
# GNUPLOT_RECTANGLE_TEMPLATE = """set obj rectangle center %d,%d size %d,%d front fs empty border rgb "%s" """
# GNUPLOT_RECTANGLE_TEMPLATE = """set obj ellipse center %d,%d size %d,%d front fs empty border rgb "%s" """
GNUPLOT_POLYGON_TEMPLATE = """set obj polygon from %(cx)d-%(w2)d,%(cy)d-%(h2)d to %(cx)d+%(w2)d,%(cy)d-%(h2)d to %(cx)d+%(w2)d,%(cy)d+%(h2)d to %(cx)d-%(w2)d,%(cy)d+%(h2)d to %(cx)d-%(w2)d,%(cy)d-%(h2)d front fs empty border rgb "%(color)s" """
GNUPLOT_CIRCLE_TEMPLATE = """set obj circle center %d,%d size %d arc [%d:%d] front fs empty border rgb "%s" """
GNUPLOT_TEMPLATE = """#!/usr/bin/gnuplot
reset
set term png size 1920, 1080 font ",20"
set xrange [0:1919]
set yrange [1079:0] # (0,0) is top-left in the data but bottom-left in gnuplot originally. Reverse needed.
unset xtics
unset ytics
unset border
unset title
unset key
set label 1 noenhanced
set lmargin at screen 0
set bmargin at screen 0
set rmargin at screen 1
set tmargin at screen 1
set size ratio -1
set colorbox front user origin .88,.05 size .04,.9
set cbtics textcolor rgbcolor "white"
set palette defined (0 0 1 1, 0.25 0 0 1, 0.5 0 0 0, 0.75 1 0 0, 1 1 1 0)
f(x) = (x==0) ? 0 : sgn(x)*log10(abs(x))
maxvalue = f(%(maxvalue)d)
set cbrange [-maxvalue:maxvalue]

%(objectmarkers)s

# main heatmap
set out "%(outputfile)s"
set label 1 "%(name)s\\n%(exp)s" at screen 0.07,0.3 rotate left noenhanced front textcolor rgbcolor "white" font ",28"
plot "%(inputfile)s" index %(index)d matrix using 1:2:(f($3)) every ::1:1:1920:1080 with image

# heatmap in table form
set table "%(outputfile)s.table"
splot "%(inputfile)s" index %(index)d matrix using 1:2:(f($3)) every ::1:1:1920:1080 with image
unset table

# individual intensity distribution of heatmap
bin=0.1
set table "%(outputfile)s.table2"
plot "<sed '/^$/d' %(outputfile)s.table" u 3:(1):(bin) smooth kdensity
unset table

"""

GNUPLOT_TEMPLATE_INTDIST_INDIV = (
    """"%(inputfile)s" u 1:2 w l lw 2 title "%(strid)s",\\"""
)
GNUPLOT_TEMPLATE_INTDIST = """#!/usr/bin/gnuplot
reset
set term png
set title noenhanced
set title "%(name)s\\n%(exp)s"
set xlabel "log(intensity of pixel on heatmap)"
set ylabel "log(number of pixels on heatmap)"
set log y

set out "%(outputfile)s"
plot \\
%(tabledata)s

"""


def get_gnuplot_script(
    inputfile,
    outputfile,
    name,
    index,
    exp,
    experiment,
    group,
    maxvalue,
    image_size,
    project_settings,
):
    """Return .gnu script body as string."""
    data = {
        "inputfile": inputfile,
        "outputfile": outputfile,
        "name": name,
        "index": index,
        "exp": exp,
        "maxvalue": int(maxvalue),
    }

    objectmarkers = []
    # add queuing object markers (rectangles and circles)
    if experiment is not None:
        for object in project_settings.object_types:
            if object not in experiment:
                continue
            objobj = project_settings.object_queuing_areas[object]
            if group == "all":
                grouplist = experiment[object].keys()
            else:
                grouplist = [group]
            for g in grouplist:
                for point in experiment[object][g]:
                    (ofsx, ofsy) = trajognize.stat.experiments.queuing_center_offset(
                        point, objobj, image_size
                    )
                    if isinstance(objobj, Rectangle):
                        #                        objectmarkers.append(GNUPLOT_RECTANGLE_TEMPLATE % (point.x + ofsx,
                        #                                point.y + ofsy, objobj.w, objobj.h, "dark-gray"))
                        # TODO: rectangle somehow does not appear with reverse y range...
                        objectmarkers.append(
                            GNUPLOT_POLYGON_TEMPLATE
                            % {
                                "cx": point.x + ofsx,
                                "cy": point.y + ofsy,
                                "w2": objobj.w / 2,
                                "h2": objobj.h / 2,
                                "color": "dark-gray",
                            }
                        )
                    elif isinstance(objobj, Circle):
                        # 360 - x needed because we are >0 v90 <180 ^270, gnuplot is >0 ^90 <180 v270
                        # also, gnuplot always plots CCW, so swapping of a1 and a2 is needed
                        objectmarkers.append(
                            GNUPLOT_CIRCLE_TEMPLATE
                            % (
                                point.x + ofsx,
                                point.y + ofsy,
                                objobj.r,
                                360 - point.a2,
                                360 - point.a1,
                                "dark-gray",
                            )
                        )

    # add object markers (rectangles and circles)
    if experiment is not None:
        for object in project_settings.object_types:
            if object not in experiment:
                continue
            objobj = project_settings.object_areas[object]
            if group == "all":
                grouplist = experiment[object].keys()
            else:
                grouplist = [group]
            for g in grouplist:
                for point in experiment[object][g]:
                    if isinstance(objobj, Rectangle):
                        #                        objectmarkers.append(GNUPLOT_RECTANGLE_TEMPLATE % (point.x,
                        #                                point.y, objobj.w, objobj.h, "white"))
                        # TODO: rectangle somehow does not appear with reverse y range...
                        objectmarkers.append(
                            GNUPLOT_POLYGON_TEMPLATE
                            % {
                                "cx": point.x,
                                "cy": point.y,
                                "w2": objobj.w / 2,
                                "h2": objobj.h / 2,
                                "color": "white",
                            }
                        )
                    elif isinstance(objobj, Circle):
                        # 360 - x needed because we are >0 v90 <180 ^270, gnuplot is >0 ^90 <180 v270
                        # also, gnuplot always plots CCW, so swapping of a1 and a2 is needed
                        objectmarkers.append(
                            GNUPLOT_CIRCLE_TEMPLATE
                            % (
                                point.x,
                                point.y,
                                objobj.r,
                                360 - point.a2,
                                360 - point.a1,
                                "white",
                            )
                        )

    data["objectmarkers"] = "\n".join(objectmarkers)
    return GNUPLOT_TEMPLATE % data


def get_gnuplot_script_intdist(inputs, outputfile, name, exp):
    """Return .gnu script body as string."""
    data = {
        "outputfile": outputfile,
        "name": name,
        "exp": exp,
    }
    # add lines for all individuals in the group
    tabledata = []
    for inputfile, strid in inputs:
        tabledata.append(
            GNUPLOT_TEMPLATE_INTDIST_INDIV % {"inputfile": inputfile, "strid": strid}
        )
    data["tabledata"] = ("\n".join(tabledata))[:-2]  # remove last '/,'
    return GNUPLOT_TEMPLATE_INTDIST % data


def get_categories_from_name(name):
    """Get strid, light and real/virtual from paragraph header (name), e.g.:

    heatmap.RBG_daylight_REAL
    heatmapdiff.RBO_nightlight_VIRTUAL
    motionmap.BGP_daylight_ANY
    aamap_daylight_ANY

    """
    # heatmap type object
    match = re.match(r"^heatmap.*\.(.*)_(.*)_(.*)$", name)
    if match:
        return (match.group(1), match.group(2), match.group(3))
    else:
        # motionmap type object (no real/virt)
        match = re.match(r"^motionmap.*\.(.*)_(.*)_ANY$", name)
        if match:
            return (match.group(1), match.group(2), "ANY")
        else:
            # aamap type object (no substat)
            match = re.match(r"^aamap_(.*)_ANY$", name)
            if match:
                return ("all", match.group(1), "ANY")
    return (None, None, None)


def get_minmax_from_file(inputfile):
    """Get minimum and maximum value of a file."""
    # TODO: find quicker algo with e.g. awk
    minvalue = float("Inf")
    maxvalue = -minvalue
    for line in open(inputfile, "r"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        linesplit = line.split()
        for x in linesplit:
            try:
                xx = float(x)
            except ValueError:
                continue
            if xx > maxvalue:
                maxvalue = xx
            if xx < minvalue:
                minvalue = xx
    return (minvalue, maxvalue)


def main(argv=[]):
    """Main entry point of the script."""
    if len(argv) < 2:
        print(__doc__)
        return
    projectfile = argv[0]
    if sys.platform.startswith("win"):
        inputfiles = glob.glob(argv[1])
    else:
        inputfiles = argv[1:]
    outdirs = []
    project_settings = trajognize.settings.import_trajognize_settings_from_file(
        projectfile
    )
    if project_settings is None:
        print("Could not load project settings.")
        return
    exps = project_settings.experiments

    intdistdata = []  # (outdir, name(common), input, strid, exp)
    for inputfile in inputfiles:
        print("parsing", os.path.split(inputfile)[1])
        stat = plot.get_stat_from_filename(inputfile)
        exp = plot.get_exp_from_filename(inputfile)
        headers = plot.grep_headers_from_file(inputfile, stat)
        (minvalue, maxvalue) = get_minmax_from_file(
            inputfile
        )  # TODO: this can take quite some time...
        # plot heatmaps
        for index in range(len(headers)):
            # get categories
            name = headers[index][0]
            (strid, light, realvirt) = get_categories_from_name(name)
            if exp == "exp_all":
                experiment = None
                group = "all"
            else:
                experiment = exps[exp[4:]]
                if strid == "all":
                    group = "all"
                else:
                    group = experiment["groupid"][strid]

            # define output directory and filename
            (head, tail, plotdir) = plot.get_headtailplot_from_filename(inputfile)
            outdir = os.path.join(head, plotdir, exp, group, light, realvirt)
            if not os.path.isdir(outdir):
                os.makedirs(outdir)
            # if this is a new output directory, clear SPGM descriptions
            if outdir not in outdirs:
                spgm.remove_picture_descriptions(outdir)
                outdirs.append(outdir)
            # get filenames
            outputfilecommon = os.path.join(outdir, tail + "__" + name)
            gnufile = outputfilecommon + ".gnu"
            outputfile = outputfilecommon + ".png"
            # collect data for intensity distribution plot
            if strid != "all":
                intdistdata.append(
                    (
                        outdir,  # input/output dir for intdist (common)
                        "_".join([group, light, realvirt]),  # name (common)
                        outputfile + ".table2",  # input filename for intdist
                        strid,
                        exp,
                    )
                )
            # plot
            image_size = Point(1920, 1080)  # TODO: get from project_settings somehow
            script = get_gnuplot_script(
                inputfile,
                outputfile,
                name,
                index,
                exp,
                experiment,
                group,
                maxvalue,
                image_size,
                project_settings,
            )
            with open(gnufile, "w") as f:
                f.write(script)
            try:
                subprocess.call(["gnuplot", gnufile])
            except WindowsError:
                print(
                    "  Error plotting '%s': gnuplot is not available on Windows" % name
                )
            # create SPGM picture description
            spgm.create_picture_description(outputfile, [name, exp], inputfile, gnufile)

    # plot common intensity distribution if there are individual heatmaps
    if intdistdata:
        outdirs = set([x[0] for x in intdistdata])
        print(len(outdirs), "outdirs found")
        for outdir in outdirs:
            print("Plotting heatmap intensity distribution for", outdir)
            inputs = []
            for (outdirx, namex, inputfile, strid, expx) in intdistdata:
                if outdirx == outdir:
                    inputs.append((inputfile, strid))
                    name = namex
                    exp = expx
            outputfilecommon = os.path.join(
                outdir, "__".join(["heatmapintdist", exp, name])
            )
            gnufile = outputfilecommon + ".gnu"
            outputfile = outputfilecommon + ".png"
            script = get_gnuplot_script_intdist(inputs, outputfile, name, exp)
            with open(gnufile, "w") as f:
                f.write(script)
            try:
                subprocess.call(["gnuplot", gnufile])
            except WindowsError:
                print(
                    "  Error plotting 'heatmapintdist_%s': gnuplot is not available on Windows"
                    % name
                )
            # create SPGM picture description
            spgm.create_picture_description(
                outputfile, [name, exp], None, gnufile
            )  # there are more source files...
            # delete temporary table files (they are very big)
    #                for inputfile, strid in inputs:
    #                    os.remove(inputfile)

    # create SPGM gallery descriptions
    headtail = os.path.split(head)[1]
    # avoid overwriting caption created by e.g. calc_heatmapdiff
    if headtail.startswith("statsum_"):
        spgm.create_gallery_description(
            head, "%ss of barcode occurrences" % stat.title()
        )
    if stat.startswith("heatmap"):
        spgm.create_gallery_description(
            os.path.join(head, plotdir),
            """Plotted results for barcode %(stat)ss.
            Results are organized into subdirectories according to experiments, groups,
            light conditions and real/virtual states.
            A barcode is REAL if it was found using color blob data.
            It is VIRTUAL if it was not found but was assumed to be somewhere (e.g. under shelter)
            Object definitions are plotted on all %(stat)ss.
            Coloring of the %(stat)ss is done on sgn(x)*log10(|x|)
            """
            % {"stat": stat},
        )
    elif stat.startswith("motionmap"):
        spgm.create_gallery_description(
            os.path.join(head, plotdir),
            """Plotted results for barcode %(stat)ss.
            Results are organized into subdirectories according to experiments, groups and light conditions.
            Object definitions are plotted on all %(stat)ss.
            Coloring of the %(stat)ss is done on sgn(x)*log10(|x|)
            """
            % {"stat": stat},
        )
    elif stat.startswith("aamap"):
        spgm.create_gallery_description(
            os.path.join(head, plotdir),
            """Plotted results for barcode %(stat)ss.
            Results are organized into subdirectories according to experiments and light conditions.
            Object definitions are plotted on all %(stat)ss.
            Coloring of the %(stat)ss is done on sgn(x)*log10(|x|)
            """
            % {"stat": stat},
        )


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))  # pass only real params to main
    except Exception as ex:
        print(ex, file=sys.stderr)
        import traceback

        traceback.print_exc(ex)
        sys.exit(1)
