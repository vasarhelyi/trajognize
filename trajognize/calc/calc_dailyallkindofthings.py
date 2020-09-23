"""
This script outputs weekdays for all days for all experiments.

Usage: __file__ projectfile
"""

# external imports
import os, sys, datetime

#inport from other modules
try:
    import trajognize.stat.experiments
    import trajognize.parse
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(
        os.path.dirname(sys.modules[__name__].__file__), "../..")))
    import trajognize.stat.experiments
    import trajognize.parse


def days_since_last_paint(paintdates, sometime):
    """Get number of days since last paint."""
    tt = paintdates[0]
    for t in paintdates:
        if t.date() > sometime.date():
            break
        tt = t
    return (sometime.date()-tt.date()).days


def main(argv=[]):
    """Main entry point of the script."""
    if len(argv) < 1:
        print(__doc__)
        return
    projectfile = argv[0]

    project_settings = trajognize.settings.import_trajognize_settings_from_file(projectfile)
    if project_settings is None:
        print("Could not load project settings.")
        return
    exps = project_settings.experiments

    # initialize objects
    expnames = sorted(exps.keys(), lambda a,b: exps[a]['number'] - exps[b]['number'])
    expnames = [exp for exp in expnames if exps[exp]['number'] < 10]
    paintdates = trajognize.parse.parse_paintdates(os.path.join(
            os.path.dirname(trajognize.__file__), '../misc/paintdates.dat'))
    entrytimes = trajognize.parse.parse_entry_times(os.path.join(
            os.path.dirname(trajognize.__file__), "../misc/entrytimes.dat"))

    # write data
    outfile = open(os.path.splitext(__file__)[0] + ".dat", 'w')
    outfile.write("allday\tdate\tweekday\texp_number\texp_day\tday_since_last_paint\tdaily_valid_seconds\n")
    # get dayrange of all experiments
    firstday = exps[expnames[0]]['start'].date()
    lastday = exps[expnames[-1]]['stop'].date()
    dayrange = [firstday + datetime.timedelta(n) for n in range(int((lastday - firstday).days) + 1)]
    # go through all days
    for allday, day in enumerate(dayrange):
        print(allday, sep=", ")

        # exp params
        date = datetime.datetime(day.year, day.month, day.day)
        explist = trajognize.stat.experiments.get_experiment(exps, date, True)
        explist = [x for x in explist if exps[x]['number'] < 10]
        if explist:
            experiment = exps[explist[-1]]
            exp_number = experiment['number']
            exp_day = trajognize.stat.experiments.get_days_since_start(experiment, date)
        else:
            exp_number = -1
            exp_day = -1

        # daily valid seconds
        dvs = 0
        start = experiment['start']
        stop = experiment['stop']
        for i in range(86400):
            datetimeatsec = datetime.datetime(date.year, date.month, date.day) + datetime.timedelta(0,i)
            if datetimeatsec >= start and datetimeatsec <= stop and not trajognize.util.is_entry_time(entrytimes, datetimeatsec):
                dvs += 1

        # write out everything
        outfile.write("%d\t%s\t%d\t%d\t%d\t%d\t%d\n" % (allday, str(day), day.weekday(),
                exp_number, exp_day, days_since_last_paint(paintdates, date), dvs))

    outfile.close()


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:])) # pass only real params to main
    except Exception as ex:
        print(ex, file=sys.stderr)
        import traceback
        traceback.print_exc(ex)
        sys.exit(1)
