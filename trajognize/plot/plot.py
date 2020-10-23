"""This is a file for some common functions for plotting."""

import subprocess, os, sys, re, inspect, collections
try:
    import trajognize.stat.experiments
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(
        os.path.dirname(sys.modules[__name__].__file__), "../..")))
    import trajognize.stat.experiments


GNUPLOT_TEMPLATE_PAINTDATE = """set obj rect from %g, graph 0 to %g, graph 1 fc lt -1 fs solid 0.2 noborder"""

GNUPLOT_TEMPLATE_DAILYVALIDTIMES_INIT = """
days(x) = word("Mon Tue Wed Thu Fri Sat Sun", int(x+1))
startDayOfExp=%d
endDayOfExp=%d
set boxwidth 0.8 absolute
set style fill solid 0.5 border
set style data boxes
set y2range [] reverse	#### This plot is y-reversed
set xrange [0:endDayOfExp-startDayOfExp]  ### TODO: start from 0 or 1 ?
set y2range [0:500000] #### To have a smaller plot for y2 (max value is 84600)
"""

GNUPLOT_TEMPLATE_DAILYVALIDTIMES_PLOT = """"%s"  u ($1-startDayOfExp):7 axes x1y2 notitle lt rgb "gray",\\
     "" u ($1-startDayOfExp):(10000):(days($3)) with labels axes x1y2 rotate right"""


def get_gnuplot_paintdate_str(exps, exp, paintdates, template=GNUPLOT_TEMPLATE_PAINTDATE):
    """Prepare paintdate strings for gnuplot."""
    pdlist = []
    for t in paintdates:
        if t >= exps[exp]['start'] and t <= exps[exp]['stop']:
            day = trajognize.stat.experiments.get_days_since_start(exps[exp], t)
            pdlist.append(template % (day-0.5, day+0.5))
    return "\n".join(pdlist)


def get_gnuplot_dailyvalidtimes_strs(exps, exp):
    """Prepare paintdate strings for gnuplot."""
    startDayOfExp = (exps[exp]['start'].date() - exps['first_A1_A2_B1_B2']['start'].date()).days
    endDayOfExp = (exps[exp]['stop'].date() - exps['first_A1_A2_B1_B2']['start'].date()).days
    init_str = GNUPLOT_TEMPLATE_DAILYVALIDTIMES_INIT % (startDayOfExp, endDayOfExp)
    plot_str = GNUPLOT_TEMPLATE_DAILYVALIDTIMES_PLOT % os.path.join(
            os.path.dirname(trajognize.__file__), '../misc/dailyallkindofthings.dat')
    return (init_str, plot_str)


def grep_headers_from_file(inputfile, headerstart):
    """Get header lines from trajognize.stat output .txt files."""
    headerlines = subprocess.run(["grep", "^%s" % headerstart, inputfile],
        stdout=subprocess.PIPE, encoding="utf-8", check=True).stdout.split('\n')
    return [line.split('\t') for line in headerlines if line]


def get_exp_from_filename(inputfile):
    """Get experiment from trajognize.stat output .txt/.dat files."""
    match = re.match(r'^(stat|calc|meas)_.*__(exp_.*)\.(txt|dat)$',
            os.path.split(inputfile)[1])
    if match:
        return match.group(2)
    else:
        return "exp_unknown"


def get_day_from_filename(inputfile):
    """Get experiment from trajognize.statsum dailyoutput .txt/.dat files."""
    match = re.match(r'^stat_.*__day_(.*)\.(txt|dat)$',
            os.path.split(inputfile)[1])
    if match:
        return match.group(1)
    else:
        return None


def get_stat_from_filename(inputfile):
    """Get stat name from trajognize.stat output .txt/.dat files, e.g.:

    stat_motionmap.all__exp_third_merge_A1A2B1B2.txt
    stat_aa__exp_all.txt

    """
    match = re.match(r'^stat_(.*)__.*\.(txt|dat)$',
            os.path.split(inputfile)[1])
    if match:
        substat = match.group(1)
        i = substat.find('.')
        if i > 0:
            return substat[:i]
        else:
            return substat
    else:
        return None


def get_headtailplot_from_filename(inputfile, f_back=1):
    """Return head, tail and plotdir for input file."""

    (head, tail) = os.path.split(inputfile)
    tail = os.path.splitext(tail)[0]
    caller_namespace = inspect.stack()[f_back][0]
    try:
        plotdir = inspect.getmodule(caller_namespace).__file__
    finally:
        del caller_namespace
    plotdir = os.path.splitext(os.path.split(plotdir)[1])[0]

    return (head, tail, plotdir)


def convert_matrixdata_to_dict(strdata):
    """Parse a data matrix with header row and column and return it in dict format.

    e.g.: helo  X  Y             data[X][X] = 1, data[X][Y] = 2, etc.
          X     1  2     ===>
          Y     3  4

    """
    # convert list to dict
    name = strdata[0][0]
    strids = strdata[0][1:]
    n = len(strids)
    data = collections.defaultdict(collections.defaultdict)
    for i in range(n):
        for j in range(n):
            x = float(strdata[i+1][j+1])
            data[strids[i]][strids[j]] = x
    return data

