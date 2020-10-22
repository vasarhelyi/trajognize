"""
This script collects good params for main correlation analysis.
"""

# external imports
import os, sys, numpy
from collections import defaultdict

# imports from this module
from . import util
from .good_params import good_params, all_params

# import from other modules
try:
    import trajognize.stat.experiments
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(
        os.path.dirname(sys.modules[__name__].__file__), "../..")))
    import trajognize.stat.experiments


def main(argv=[]):
    """Main entry point of the script."""

    basedir = input("Enter base directory of statsum correlation outputs: ")
    projectfile = input("Enter the project settings file: ")

    # initialize some variables
    corrfile = os.path.join(basedir, 'collected_good_params.txt')
    outfile = os.path.splitext(corrfile)[0] + '__groupified.txt'
    project_settings = trajognize.settings.import_trajognize_settings_from_file(projectfile)
    if project_settings is None:
        print("Could not load project settings.")
        return
    exps = project_settings.experiments
    expnames = sorted(exps.keys(), lambda a,b: exps[a]['number'] - exps[b]['number'])

    # parse all data first
    if not os.path.isfile(corrfile):
        print("Correlation file does not exist:", corrfile)
        return
    print("Parsing corr file to collect data...")
    headers, data = util.parse_corr_file(corrfile)

    # open output file
    if os.path.isfile(outfile):
        print("Group descriptor file exists, overwriting it...")
    print("Writing group descriptors to", outfile)
    outfile = open(outfile, 'w')
    outfile.write("exp_number\tparam_name\tgroup\tavg\tstd\tmax\tmin\tmax-min\n")

    # parse params
    for exp in expnames:
        expdir = "exp_%s" % exp
        for key in data.keys():
            if not key.startswith(expdir): continue
            for group in exps[exp]['groups']:
                print(exp, key, group)
                groupids = exps[exp]['groups'][group]
                gi = [headers.index(strid) for strid in groupids]
                # excluding 'nan'
                qq = [data[key][i] for i in gi]
                pp = [data[key][i] for i in gi if data[key][i] == data[key][i]]
                if qq != pp:
                    if not pp:
                        print("WARNING: looks like there are no usable values in", qq)
                        pp = [float('nan')]
                    else:
                        print("WARNING:", len(qq)-len(pp), "invalid numbers excluded from", qq)
                outfile.write("%s\t%s\t%s\t%g\t%g\t%g\t%g\t%g\n" % (exps[exp]['number'], key, group,
                        numpy.mean(pp),
                        numpy.std(pp),
                        numpy.max(pp),
                        numpy.min(pp),
                        numpy.max(pp) - numpy.min(pp)))


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:])) # pass only real params to main
    except Exception as ex:
        print(ex, file=sys.stderr)
        import traceback
        traceback.print_exc(ex)
        sys.exit(1)
