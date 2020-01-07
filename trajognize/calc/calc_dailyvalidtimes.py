"""This script calculates total length of valid time periods for all days and all experiments.

Usage: calc_dailyvalidtime.py

Output is written to calc_dailyvalidtime.txt

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


def main(argv=[]):
    """Main entry point of the script."""
    exps = trajognize.stat.experiments.get_initialized_experiments()
    entrytimes = trajognize.parse.parse_entry_times("../../misc/entrytimes.dat")
    f = open(__file__ + ".txt", 'w')
    for exp in exps:
        start = exps[exp]['start']
        stop = exps[exp]['stop']
        for date in [start.date() +  datetime.timedelta(i) for i in range((stop.date()-start.date()).days+1)]:
            t = 0
            for i in range(86400):
                datetimeatsec = datetime.datetime(date.year, date.month, date.day) + datetime.timedelta(0,i)
                if datetimeatsec >= start and datetimeatsec <= stop and not trajognize.util.is_entry_time(entrytimes, datetimeatsec):
                    t += 1
            print exps[exp]['number'], exp, date, t
            print >>f, exps[exp]['number'], exp, date, t

if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:])) # pass only real params to main
    except Exception as ex:
        print >>sys.stderr, ex
        import traceback
        traceback.print_exc(ex)
        sys.exit(1)
