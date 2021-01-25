""""
Arbitrary helper functions for trajognize.stat submodule.
"""

# external imports
import inspect
from math import hypot
import re
import sys

# imports from base class
import trajognize.init

# imports from self subclass
from . import init
from . import stat # this is only needed to have functions in the namespace, nothing is used directly...

def get_chosen_barcodes(barcodes, mfix=None):
    """Return list of chosen barcodes from list of barcodes on current frame.

    :param barcodes: list of barcodes of the current frame
    :param mfix: mfix to exclude

    """
    id_count = len(barcodes)
    chosen = [None for k in range(id_count)]
    for k in range(id_count):
        for barcode in barcodes[k]:
            if barcode.mfix & trajognize.init.MFix.CHOSEN:
                if mfix is None or not barcode.mfix & mfix:
                    chosen[k] = barcode
                break
    return chosen


def get_mfi(barcode):
    """Return mfix_type index for a given barcode (or -1 on error)."""
    if barcode.mfix & trajognize.init.MFix.CHOSEN:
        if barcode.mfix & trajognize.init.MFix.VIRTUAL:
            return init.mfix_types.index('VIRTUAL')
        else:
            return init.mfix_types.index('REAL')
    return -1 # which is VIRTUAL as well


def get_stat_fileext(stat, exp=None, asext=True):
    """Return string to use for stat file ending.

    :param stat: name of a statistic
    :param exp: name of an experiment (if given) - or a day
    :param asext: return string starts with a point or not?

    """
    if exp is not None:
        # if exp is possibly a day for dailyoutput, e.g. 2010-07-10
        # TODO: this is a bad ass hack I know and works for max. 1000 years only...
        if exp.startswith('2') and exp.find("-") != -1 and len(exp) == 10:
            expstr = "day"
        else:
            expstr = "exp"
    return "%sstat_%s%s" % ("." if asext else "", stat, "" if exp is None else "__%s_%s" % (expstr, exp))


def get_stat_fileext_zipped(stat):
    """Return string to use for zipped stat file ending.

    :param stat: name of a statistic

    """
    return get_stat_fileext(stat) + ".zip"


def get_stat_from_filename(inputfile):
    """Return name of stat from input file name assuming conventions.

    :param inputfile: name of an input file in the following format:
                      *.blobs.barcodes.stat_[statname].zip

    """
    match = re.match(r'.*\.blobs\.barcodes\.stat_(.*)\.zip$', inputfile)
    if match:
        return match.group(1)
    return None


def get_substat(stat, subclasses, subclassindex):
    """Return name of subclass if exists, otherwise return name of main class.

    :param stat: name of a statistic
    :param subclasses: names of all subclasses (or None)
    :param subclassindex: index of the subclass

    """
    if subclasses is None:
        return stat
    else:
        return stat + '.' + subclasses[subclassindex]


def print_stats_help(stats, statlist=None, fileobj=None):
    """Return formatted docstrings from all defined statistics.

    :param stats: dictionary of implemented statistics created by get_stat_dict()
    :param statlist: list of stat names to print help on.
            If not defined, help on all statistics are printed.
    :param fileobj: print to file instead of stdout
    :param commentchar: print character to the beginning of all line

    """
    if statlist is None:
        statlist = sorted(stats)
    for stat in statlist:
        trajognize.util.print_underlined("'%s' statistic description" % stat, 1, fileobj)
        print("init: {}".format(stats[stat]['init']), file=fileobj)
        print(getattr(sys.modules['trajognize.stat.init'], stats[stat]['init'][0]).__doc__, file=fileobj)
        if stats[stat]['subf'] is not None:
            print("subf: {}".format(stats[stat]['subf']), file=fileobj)
            print(getattr(sys.modules['trajognize.stat.stat'], stats[stat]['subf'][0]).__doc__, file=fileobj)
        print("calc: {}".format(stats[stat]['calc']), file=fileobj)
        print(getattr(sys.modules['trajognize.stat.stat'], stats[stat]['calc'][0]).__doc__, file=fileobj)


def get_stat_dict():
    """Returns the dictionary of statistics implemented so far, with some
    useful parameters to allow for automatic calling of stat init/calculation/print
    functions.

    'init' contains name of class object and its parameters
    'calc' contains name of calculating function and its parameters that do not
           have default values (the others are used for hacking statistics...)
    'write' contains name of writing function and its parameters
    'subf' contains subclassfunction name and its parameters
    'writedaily' contains name of writing dailyoutput function (if present) and its parameters

    """
    # get all corresponding functions
    def is_statfunc(f):
        return inspect.isfunction(f) and f.__module__ == 'trajognize.stat.stat' and f.__name__.startswith("calculate_")
    statfunction_list = inspect.getmembers(trajognize.stat.stat, is_statfunc)
    def is_subclassfunc(f):
        return inspect.isfunction(f) and f.__module__ == 'trajognize.stat.stat' and f.__name__.startswith("subclasses_")
    subclassfunction_list = inspect.getmembers(trajognize.stat.stat, is_subclassfunc)
    subclassfunction_names = [s[0] for s in subclassfunction_list]
    def is_statclass(c):
        return inspect.isclass(c) and c.__module__ == 'trajognize.stat.init'
    class_list = inspect.getmembers(trajognize.stat.init, is_statclass)
    # get class names
    classnames = [c[0] for c in class_list]
    classnames_lower = [c.lower() for c in classnames]
    stats = dict()
    for f in statfunction_list:
        # get stat name
        stat = f[0][len("calculate_"):]
        # get class name
        classname_lower = stat
        # get subclass names
        x = "subclasses_" + stat
        if x in subclassfunction_names:
            # get params
            y = subclassfunction_names.index(x)
            subclassfunction = [x, inspect.getargspec(subclassfunction_list[y][1])[0]]
        else:
            subclassfunction = None
        # add entry to stats dict
        if classname_lower in classnames_lower:
            i = classnames_lower.index(classname_lower)
            c = class_list[i]
            stats[stat] = {
                'init': [classnames[i], inspect.getargspec(c[1].__init__)[0][1:]],
                'calc': [f[0], inspect.getargspec(f[1])[0] if inspect.getargspec(f[1])[3] is None else inspect.getargspec(f[1])[0][:-len(inspect.getargspec(f[1])[3])]],
                'write': ["write_results", inspect.getargspec(c[1].write_results)[0][1:]],
                'writedaily': ["write_dailyoutput_results", inspect.getargspec(c[1].write_dailyoutput_results)[0][1:]],
                'subf': subclassfunction,
            }
    return stats


def init_stat(stats, stat, f_back=1):
    """Initializes an empty stat object,
    with parameter names validated in caller namespace.

    :param stats: dictionary of implemented statistics created by get_stat_dict()
    :param stat: name of a statistic
    :param f_back: number of frames to jump back in caller stack

    """
    caller_namespace = inspect.stack()[f_back][0].f_locals
    try:
        real_params = [caller_namespace[param_name] for param_name in stats[stat]['init'][1]]
    except KeyError:
        print("TODO: define parameters passed to '%s' in caller namespace with the same name as in function def!" % stats[stat]['init'][0])
        raise
    finally:
        del caller_namespace
    return getattr(sys.modules['trajognize.stat.init'], stats[stat]['init'][0])(*real_params)


def calculate_stat(stats, stat, f_back=1):
    """Executes a stat calculation function,
    with parameter names validated in caller namespace.

    :param stats: dictionary of implemented statistics created by get_stat_dict()
    :param stat: name of a statistic
    :param f_back: number of frames to jump back in caller stack

    """
    caller_namespace = inspect.stack()[f_back][0].f_locals
    try:
        real_params = [caller_namespace[param_name] for param_name in stats[stat]['calc'][1]]
    except KeyError:
        print("TODO: define parameters passed to '%s' in caller namespace with the same name as in function def!" % stats[stat]['calc'][0])
        raise
    finally:
        del caller_namespace
    return getattr(sys.modules['trajognize.stat.stat'], stats[stat]['calc'][0])(*real_params)


def subclasses_stat(stats, stat, f_back=1):
    """Returns subclass names for stat (or None),
    with parameter names validated in caller namespace.

    :param stats: dictionary of implemented statistics created by get_stat_dict()
    :param stat: name of a statistic
    :param f_back: number of frames to jump back in caller stack

    """
    if stats[stat]['subf'] is None:
        return None

    caller_namespace = inspect.stack()[f_back][0].f_locals
    try:
        real_params = [caller_namespace[param_name] for param_name in stats[stat]['subf'][1]]
    except KeyError:
        print("TODO: define parameters passed to '%s' in caller namespace with the same name as in function def!" % stats[stat]['calc'][0])
        raise
    finally:
        del caller_namespace
    return getattr(sys.modules['trajognize.stat.stat'], stats[stat]['subf'][0])(*real_params)


def write_stat(stats, stat, object, f_back=1):
    """Writes the results of a stat object to a file,
    with parameter names validated in caller namespace.

    :param stats: dictionary of implemented statistics created by get_stat_dict()
    :param stat: name of a statistic
    :param object: the stat object itself that contains the print function
    :param f_back: number of frames to jump back in caller stack

    """
    caller_namespace = inspect.stack()[f_back][0].f_locals
    try:
        real_params = [caller_namespace[param_name] for param_name in stats[stat]['write'][1]]

    except KeyError:
        print("TODO: define parameters passed to %s in caller namespace with the same name as in function def!" % stats[stat]['write'][0])
        raise
    finally:
        del caller_namespace
    return object.write_results(*real_params)


def write_dailyoutput_stat(stats, stat, object, f_back=1):
    """Writes the dailyoutput results of a stat object to a file,
    with parameter names validated in caller namespace.

    :param stats: dictionary of implemented statistics created by get_stat_dict()
    :param stat: name of a statistic
    :param object: the stat object itself that contains the print function
    :param f_back: number of frames to jump back in caller stack

    """
    caller_namespace = inspect.stack()[f_back][0].f_locals
    try:
        real_params = [caller_namespace[param_name] for param_name in stats[stat]['writedaily'][1]]
    except KeyError:
        print("TODO: define parameters passed to %s in caller namespace with the same name as in function def!" % stats[stat]['writedaily'][0])
        raise
    finally:
        del caller_namespace
    return object.write_dailyoutput_results(*real_params)


def get_subtitle_string(subtitleindex, sec, msg, color="#ffffff", x=None, y=None, imx=1920, imy=1080):
    """Return a string to write to a subtitle file."""
    lines = [""]
    # subtitleindex
    lines.append("%03d" % subtitleindex)
    # timing
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    fromtime = "%d:%02d:%02d.%03d" % (h, m, int(s), int((s-int(s))*1000))
    m, s = divmod(sec+1, 60)
    h, m = divmod(m, 60)
    totime = "%d:%02d:%02d.%03d" % (h, m, int(s), int((s-int(s))*1000))
    lines.append("%s --> %s" % (fromtime, totime))
    # pos and color
    if x is not None and y is not None:
        pos = '{\\pos(%d,%d)}' % ( \
                round( x * 384 / imx ),
                round( y * 288 / imy + 8))
    else:
        pos = ""
    lines.append('%s<font color="%s">%s</font>' % (pos, color, msg))
    lines.append("")
    #return result
    return "\n".join(lines)

def distance_from_line(p, a, b):
    """Calculate closest distance from point to a line segment.

    Sources:
    http://nodedangles.wordpress.com/2010/05/16/measuring-distance-from-a-point-to-a-line-segment/
    http://local.wasp.uwa.edu.au/~pbourke/geometry/pointline/source.vba

    :param p: coordinates of a point (.x, .y)
    :param a: coordinates of the first end of the line segment (.x, .y)
    :param b: coordinates of the second end of the line segment (.x, .y)

    """
    line_length = hypot(b.x - a.x, b.y - a.y)
    if line_length < 0.00000001:
        return 9999

    u = (p.x - a.x)*(b.x - a.x) + (p.y - a.y)*(b.y - a.y)
    u /= (line_length * line_length)

    if (u < 0.00001) or (u > 1):
        # closest point does not fall within the line segment,
        # take the shorter distance to an endpoint
        d1 = hypot(p.x - a.x, p.y - a.y)
        d2 = hypot(p.x - b.x, p.y - b.y)
        return min(d1, d2)
    else:
        # Intersecting point is on the line, use the formula
        ix = a.x + u * (b.x - a.x)
        iy = a.y + u * (b.y - a.y)
        return hypot(p.x - ix, p.y - iy)

def distance_from_polygon(pos, poly):
    """Return the closest distance between a point and
    an arbitrary polygon (consisting of points defining line segments)."""
    return min(distance_from_line(pos, poly[i-1], poly[i]) \
            for i in range(len(poly)))

def is_inside_polygon(pos, poly):
    """Return true if pos is inside poly.
    Source: http://www.ariel.com.au/a/python-point-int-poly.html
    """
    n = len(poly)
    inside = False
    p1x, p1y = poly[0]
    for i in range(n+1):
        p2x,p2y = poly[i % n]
        if pos.y > min(p1y, p2y):
            if pos.y <= max(p1y, p2y):
                if pos.x <= max(p1x, p2x):
                    if p1y != p2y:
                        xints = (pos.y - p1y)*(p2x - p1x)/(p2y - p1y) + p1x
                    if p1x == p2x or pos.x <= xints:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside
