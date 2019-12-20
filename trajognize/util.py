"""
Miscellaneous utility functions.
"""

from trajognize.project import FPS, get_datetime_from_filename
from trajognize.init import MFIX_STR, MFIX_DUMMY_LAST

# external imports
import time
import sys
import os
import datetime
import cPickle
import gzip
import gc
import subprocess


def get_svn_info():
    """Get svn revision string."""
    realpath = os.path.split(os.path.realpath(__file__))[0]
    info = subprocess.Popen(['svn', 'info', realpath],
            stdout = subprocess.PIPE).communicate()[0].split('\n')
    infodict = {'revision': "unknown"}
    for line in info:
        x = line.split(':',1)
        if len(x) == 2:
            infodict[x[0].lower()] = x[1].strip()
    return infodict


# get_datetime_from_filename() is moved to project.py as it is project-specific


def get_datetime_at_frame(starttime, currentframe):
    """Return the datetime of a given frame, relative to the first frame.
    
    :param starttime: the datetime of the first frame
    :param currentframe: a given frame

    """
    return starttime + datetime.timedelta(0, currentframe/FPS)
    

def is_entry_time(entrytimes, sometime):
    """Return True if the given time is an 'entry time', i.e. someone was inside
    the patek room at that moment (with +- 1 min overhead).
    
    :param entry_times: dict of entry times created by parse.parse_entry_times()
    :param sometime: a datetime.datetime object representing the moment to check

    """
    key = sometime.date().isoformat()
    if key not in entrytimes.keys():
        return False
    onemin = datetime.timedelta(0,60)
    for times in entrytimes[key]:
        if sometime >= times['from'] - onemin and sometime <= times['to'] + onemin:
            return True
    return False
            

def get_path_as_first_arg(argv):
    """Return argv[1] as path or default path if argv[1] not defined."""
    if len(argv) < 2 or not argv[1]:
        # default on windows (gabor's laptop)
        if sys.platform.startswith('win'):
            #path = 'd:\\ubi\\ELTE\\patekok\\video\\random_sample_trial_run\\'
            path = 'd:\\ubi\\ELTE\\patekok\\video\\random_sample_trial_run__trajognize\\done\\'
        # default on non windows (linux, atlasz)
        else:
            # default path on atlasz
            path = '/h/mnt/user04/project/flocking/abeld/ratlab/results/random_sample_trial_run/done/'
            #path = '/h/mnt/user04/project/flocking/abeld/ratlab/results/random_sample_trial_run/first_trial/done/'
            #path = '/h/mnt/user04/project/flocking/abeld/ratlab/results/random_sample_trial_run/second_trial__opencv2.3/done/'
    else:
        # user defined path from first command line argument
        path = argv[1]
    return path


def exit(errorstr='', exitcode=0):
    """Exit execution with given exitcode, printing an error string."""
    if errorstr:
        print errorstr
    sys.exit(exitcode)


class phase_t(object):
    """A simple class that prints nice status info about the running scripts to
    standard output.

    """

    def __init__(self):
        """Initialize class and timers."""
        self.mainstarttime = time.clock()
        self.starttime = 0
        self.lasttime = 0
        self.phase_status = 0

    def start_phase(self, msg):
        """Start phase time counter and print phase starting message.

        Keyword parameters:
        msg -- the message to print at phase start

        """
        self.starttime = time.clock()
        self.lasttime = self.starttime
        self.phase_status = 0
        print msg
        sys.stdout.flush()

    def check_and_print_phase_status(self, direction, current, all):
        """Check status of current phase and print elapsed percentage.

        Keyword parameters:
        direction -- forward or backward (for increasing/decreasing counter)
        current   -- current interation index in the loop (e.g. currentframe)
        all       -- number of interations in the loop (e.g. frame_count)

        """
        # if too slow (>5s for one iteration)
        now = time.clock()
        if now-self.lasttime >= 1:
            print "%d:%.1fs" % (current, now-self.lasttime),
        self.lasttime = now
        # print percentage
        if direction == 'forward':
            if current * 100 >= self.phase_status * all:
                print "%d%%" % self.phase_status,
                self.phase_status += 1
        elif direction == 'backward':
            if current * 100 <= (100-self.phase_status) * all:
                print "%d%%" % (100-self.phase_status),
                self.phase_status += 1
        else:
            0/0
        sys.stdout.flush()

    def end_phase(self, userstr=None, main=False):
        """Calculate elapsed time since last start_phase() call and print it."""
        if main:
            if userstr: print "  %s" % userstr
            # print total elapsed time
            print "Total time elapsed: %gs" % (time.clock()-self.mainstarttime)
        else:
            # if status was checked while running, print 'done' to the end
            if self.phase_status:
                print 'done'
            # print userstring
            if userstr: print "  %s" % userstr
            # print elapsed time
            print "  time elapsed: %gs\n" % (time.clock()-self.starttime)
        sys.stdout.flush()


def mfix2str(mfix):
    """Convert mfix value of MFIX flags to string."""
    i = 1
    j = 0
    s = []
    while i < MFIX_DUMMY_LAST:
        if mfix & i:
            s.append(MFIX_STR[j])
        i *= 2
        j += 1
    if s:
        return "|".join(s)
    else:
        return '-'


def mfix2str_allascomment():
    """Convert all existing MFIX flags to a multi-line comment string
    used in .barcode output files."""
    i = 1
    j = 0
    s = ["# mFix value for IDs:"]
    while i < MFIX_DUMMY_LAST:
        s.append("#   %d: %s" % (i, MFIX_STR[j]))
        i *= 2
        j += 1
    return "\n".join(s) + "\n"


class param_at_frame(object):
    """Get the parameter value from param dictionary for current frame (e.g. light, cage).

    Method defined in class form to be able to return quickly from inside an
    iteration for all frames.
    
    Input dictionary must be sparse, having keys as frame numbers and values
    as some parameter for that frame and for frames until next key.

    """
    def __init__(self, param_log):
        self.param_log = param_log
        self.param_log_keys = list(sorted(param_log.keys(), key=int))
        self.reset()

    def reset(self):
        """Reset iterator variables."""
        self.lastkey = self.param_log_keys[0]
        self.startindex = 0

    def __call__(self, currentframe):
        """Get param for current frame, assuming being inside forward iteration over all frames."""
        for key in self.param_log_keys[self.startindex:]:
            if key == currentframe:
                return self.param_log[key]
            elif key > currentframe:
                return self.param_log[self.lastkey]
            self.lastkey = key
            self.startindex += 1
        return self.param_log[self.lastkey]


def strid2coloridindex(strid, colorids):
    """Get coloridindex of a given color string, return -1 on error."""
    for k in xrange(len(colorids)):
        if colorids[k].strid == strid:
            return k
    return -1


def print_underlined(string, emptylines=0, fileobj=None):
    """Prints a string and prints a line under it with same length + some empty
    lines if defined."""
    indent = len(string) - len(string.lstrip())
    print >> fileobj, string
    if indent:
        print >> fileobj, ' '*(indent-1),
    print >> fileobj, '-' * (len(string)-indent)
    if emptylines:
        print >> fileobj, '\n'*(emptylines-1)


def insert_commentchar_to_file(filename, commentchar):
    """Insert a comment character to all lines of a file."""
    with open(filename, 'r') as f:
        lines = f.readlines()
    lines = [commentchar + " " + line for line in lines]
    with open(filename, 'w') as f:
        f.writelines(lines)


def load_object(filename):
    """Load a compressed object from disk.

    :param filename: name of the .zip file to load from

    """
    gc.disable()
    if filename.endswith('.zip'):
        f = gzip.GzipFile(filename, 'rb')
    else:
        f = open(filename, 'rb')
    try:
        object = cPickle.load(f)
    except EOFError:
        print "ERROR loading", filename
        object = None
    f.close()
    gc.enable()
    return object


def save_object(object, filename, protocol = cPickle.HIGHEST_PROTOCOL):
    """Save a (compressed) object to disk.

    :param filename: name of the .zip file to save to

    """
    gc.disable()
    if filename.endswith('.zip'):
        f = gzip.GzipFile(filename, 'wb')
    else:
        f = open(filename, 'wb')
    cPickle.dump(object, f, protocol)
    f.close()
    gc.enable()


def debug_filename(level):
    """Returns the filename of a debug object at the current debug level."""
    return "trajognize_debug_environment.%d" % level
    
def add_subdir_to_filename(filename, subdir):
    """Add a subdirectory to a filename with full path."""
    head, tail = os.path.split(filename)
    return os.path.join(head, subdir, tail)
