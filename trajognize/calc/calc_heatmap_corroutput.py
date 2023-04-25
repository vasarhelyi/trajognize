"""This script summarizes heatmap results into correlation files.

Usage: calc_heatmap_corroutput.py projectfile inputdir [experiment]

where inputdir is/are the location where the .zipped python object outputs of
trajognize.statsum with options "-s heatmap" are located

Output is written into the correlation dir according to experiments and groups.

Note that proper output can be generated only if all substat results are available!

"""

import os, sys, glob, re
from collections import defaultdict

try:
    import trajognize.settings
    import trajognize.stat.experiments
    import trajognize.stat.init
    import trajognize.util
    import trajognize.corr.util
except ImportError:
    sys.path.insert(
        0,
        os.path.abspath(
            os.path.join(os.path.dirname(sys.modules[__name__].__file__), "../..")
        ),
    )
    import trajognize.settings
    import trajognize.stat.experiments
    import trajognize.stat.init
    import trajognize.util
    import trajognize.corr.util


def get_categories_from_filename(filename):
    """Get strid and experiement from filename, e.g.:

    stat_heatmap.ROG__exp_fifth_G1_G4_large_G2_G3_small.zip

    """
    match = re.match(r"^stat_heatmap\.(.*)__exp_(.*)\.zip$", filename)
    if match:
        strid = match.group(1)
        exp = match.group(2)
        return (strid, exp)
    else:
        return (None, None)


def main(argv=[]):
    """Main entry point of the script."""
    if len(argv) not in [2, 3]:
        print(__doc__)
        return
    projectfile = argv[0]
    inputdir = argv[1]
    statsum_basedir = os.path.split(inputdir)[0]
    if len(argv) == 3:
        experiment = argv[2]
    else:
        experiment = "*"
    inputfiles = glob.glob(
        os.path.join(inputdir, "stat_heatmap.*__exp_%s.zip" % experiment)
    )
    project_settings = trajognize.settings.import_trajognize_settings_from_file(
        projectfile
    )
    if project_settings is None:
        print("Could not load project settings.")
        return
    exps = project_settings.experiments
    corrfiles = []

    # create full database of all data
    database = defaultdict(defaultdict)
    # parse all data to create the full database
    keys = None
    for inputfile in inputfiles:
        tail = os.path.split(inputfile)[1]
        (strid, exp) = get_categories_from_filename(tail)
        if exp == "all" or strid == "all":
            print("skipping", tail)
            continue
        print("gathering info from", tail)
        # initialize empty object
        heatmaps = trajognize.stat.init.HeatMap(
            project_settings.good_light, project_settings.image_size
        )
        # add new object (so that we have latest methods from latest version)
        heatmaps += trajognize.util.load_object(inputfile)
        # calculate simplified statistics (like in dailyoutput)
        days = (
            trajognize.stat.experiments.get_days_since_start(
                exps[exp], exps[exp]["stop"]
            )
            + 1
        )
        area = exps[exp]["areaall"][exps[exp]["groupid"][strid]]
        database[exp][strid] = heatmaps.get_simplified_statistics(days, area)
        if keys is None:
            keys = sorted(database[exp][strid].keys())
    # write results (assuming that all substats are available)
    print("Writing results to corr files...")
    for exp in database:
        print(exp)
        allnames = []
        for group in list(exps[exp]["groups"].keys()) + ["all"]:
            if group == "all":
                names = sorted(allnames)
            else:
                names = sorted(exps[exp]["groups"][group])
                allnames += names
            headerline = trajognize.corr.util.strids2headerline(names, False)
            corrfile = trajognize.corr.util.get_corr_filename(
                statsum_basedir, "exp_%s" % exp, group, False
            )
            if corrfile not in corrfiles:
                if os.path.isfile(corrfile):
                    os.remove(corrfile)
                corrfiles.append(corrfile)
            for key in keys:
                corrline = "\t".join(
                    ["heatmap_%s" % ("_".join(key))]
                    + ["%g" % database[exp][strid][key] for strid in names]
                )
                trajognize.corr.util.add_corr_line(corrfile, headerline, corrline)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))  # pass only real params to main
    except Exception as ex:
        print(ex, file=sys.stderr)
        import traceback

        traceback.print_exc(ex)
        sys.exit(1)
