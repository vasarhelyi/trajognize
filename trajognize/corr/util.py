"""
Miscellaneous utility functions for use with the correlation module.
"""

import itertools
import inspect
from collections import defaultdict
import os, sys

try:
    import trajognize.calc.hierarchy
except ImportError:
    sys.path.insert(
        0,
        os.path.abspath(
            os.path.join(os.path.dirname(sys.modules[__name__].__file__), "../..")
        ),
    )


def get_corr_filename(statsum_basedir, exp, group, pairwise=True, f_back=1):
    """Return name of the correlation file based on the calling plot dir,
    experiment and group."""

    caller_namespace = inspect.stack()[f_back][0]
    try:
        corrfile = inspect.getmodule(caller_namespace).__file__
    finally:
        del caller_namespace

    corrdir = os.path.join(statsum_basedir, "corr", exp, group)

    corrfile = (
        ("pairparams_" if pairwise else "params_")
        + os.path.splitext(os.path.split(corrfile)[1])[0]
        + ".txt"
    )

    if not os.path.isdir(corrdir):
        os.makedirs(corrdir)

    return os.path.join(corrdir, corrfile)


def strids2headerline(strids, pairwise=True, ID=["ID"]):
    """Convert a list of strids into a header line used for correlation analysis.

    Trailing end of line is not included.

    ID can contain extra columns if needed.

    """
    if pairwise:
        return "\t".join(
            ID + list(map("->".join, itertools.product(sorted(strids), sorted(strids))))
        )
    else:
        return "\t".join(ID + sorted(strids))


def matrix2corrline(data):
    """Convert a matrix type input into a line for pairwise correlation analysis.

    Matrix should include headers, too (first row and column).
    Trailing end of line is not included.

    """
    headers = sorted(data[0][1:])
    return "\t".join(
        [data[0][0]]
        + [
            data[data[0].index(sx)][data[0].index(sy)]
            for sx in headers
            for sy in headers
        ]
    )


def corrline2dict(headerline, corrline):
    """Parse a pairparams headerline and corrline and return it in dict format.

    e.g.: ID   X->X  X->Y  Y->X  Y->Y          data[X][X] = 0, data[X][Y] = 1, etc.
          helo 0     1     2     0      ===>

    """
    # convert list to dict
    csplit = corrline.split("\t")
    hsplit = headerline.split("\t")
    strids = sorted(list(set(hsplit[i].split("->")[0] for i in range(1, len(hsplit)))))
    n = len(strids)
    data = defaultdict(defaultdict)
    for i in range(n):
        for j in range(n):
            x = float(csplit[i * n + j + 1])
            data[strids[i]][strids[j]] = x

    return data


def add_corr_line(corrfile, headerline, corrline):
    """Add a line (and header) to a correlation file."""
    if not os.path.isfile(corrfile):
        writeheader = True
    else:
        writeheader = False
    f = open(corrfile, "a")
    if writeheader:
        print(headerline.strip(), file=f)
    print(corrline.strip(), file=f)
    f.close()


def pairparams2params(headerline, corrline):
    """Convert a pairparam correlation line into param type output.

    Outputs that are saved:

        - Eades-ordered rank
        - BBS score
        - LDI score
        - normDS score
        - simple row sum
        - winning above average
        - losing above average

    Returns params headerline and a list of corrlines.
    """

    # prepare data
    name = corrline[: corrline.find("\t")]
    datadict = corrline2dict(headerline, corrline)
    strids = sorted(datadict.keys())
    # calculate dominance indices
    normDS = trajognize.calc.hierarchy.deVries_modified_Davids_score(datadict)
    normDSline = "\t".join(
        ["%s_normDS" % name] + ["%g" % normDS[strid] for strid in strids]
    )

    BBS = trajognize.calc.hierarchy.BBS_scale_score(datadict)
    BBSline = "\t".join(["%s_BBS" % name] + ["%g" % BBS[strid] for strid in strids])

    LDI = trajognize.calc.hierarchy.Lindquist_dominance_index(datadict)
    LDIline = "\t".join(["%s_LDI" % name] + ["%g" % LDI[strid] for strid in strids])

    ROWSUM = trajognize.calc.hierarchy.row_sum(datadict)
    ROWSUMline = "\t".join(
        ["%s_rowsum" % name] + ["%g" % ROWSUM[strid] for strid in strids]
    )

    WINAA = trajognize.calc.hierarchy.win_above_average(datadict)
    WINAAline = "\t".join(
        ["%s_winaboveavg" % name] + ["%g" % WINAA[strid] for strid in strids]
    )

    LOSEAA = trajognize.calc.hierarchy.lose_above_average(datadict)
    LOSEAAline = "\t".join(
        ["%s_loseaboveavg" % name] + ["%g" % LOSEAA[strid] for strid in strids]
    )

    # write to output format
    paramsheaderline = strids2headerline(strids, False)
    paramscorrlines = "\n".join(
        [normDSline, BBSline, LDIline, ROWSUMline, WINAAline, LOSEAAline]
    )

    return (paramsheaderline, paramscorrlines)


def parse_corr_file(filename):
    """Parses a correlation file."""
    data = {}
    is_collected_corr_file = 0
    for line in open(filename, "r"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        linesplit = line.split("\t")
        # parse header
        if linesplit[0] == "ID":
            headers = linesplit[1:]
            continue
        # parse alternative header
        if linesplit[0] == "exp_number":
            headers = linesplit[2:]
            is_collected_corr_file = 1
            continue
        # parse data
        if len(linesplit) - 1 != len(headers) + is_collected_corr_file:
            raise ValueError(
                "Invalid line length (%d instead of %d values)!!!"
                % (len(linesplit) - 1),
                len(headers) + is_collected_corr_file,
            )
        data[linesplit[0 + is_collected_corr_file]] = [
            float(linesplit[i])
            for i in range(1 + is_collected_corr_file, len(linesplit))
        ]
    return (headers, data)
