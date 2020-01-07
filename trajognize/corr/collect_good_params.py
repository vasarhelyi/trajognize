"""
This script collects good params for main correlation analysis.
"""

# external imports
import os, sys, re, glob
from collections import defaultdict
# imports from this module
import util
from good_params import good_params, all_params
#inport from other modules
try:
    import trajognize.stat.experiments
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(
        os.path.dirname(sys.modules[__name__].__file__), "../..")))
    import trajognize.stat.experiments


corrfile = os.path.join(util.get_corr_basedir(), 'collected_good_params.txt')
corrfileall = os.path.join(util.get_corr_basedir(), 'collected_all_params.txt')
exps = trajognize.stat.experiments.get_initialized_experiments()

def main(argv=[]):
    """Main entry point of the script."""
    if os.path.isfile(corrfile):
        print("Correlation file already exists, remove it first:", corrfile)
        os.remove(corrfile)
    if os.path.isfile(corrfileall):
        print("Correlation file already exists, remove it first:", corrfileall)
        os.remove(corrfileall)
    # parse all data first
    print("\nParsing all corr files to collect data...\n")
    alldata = defaultdict(lambda: defaultdict(dict)) # [exp][paramname][strid] = value
    alldataall = defaultdict(lambda: defaultdict(dict)) # [exp][paramname][strid] = value
    basedir = util.get_corr_basedir()
    # get all experiment dirs
    expdirs = os.listdir(basedir)
    for expdir in expdirs:
        if expdir == 'exp_all' or os.path.isfile(os.path.join(basedir, expdir)): continue
        print(expdir)
        # get all group dirs
        groupdirs = os.listdir(os.path.join(basedir, expdir))
        for groupdir in groupdirs:
            if groupdir == 'all' or os.path.isfile(os.path.join(basedir, expdir, groupdir)): continue
            print(' ', groupdir)
            # get all param files
            paramfiles = glob.glob(os.path.join(basedir, expdir, groupdir, "param*.txt"))
            for paramfile in paramfiles:
                tail = os.path.split(paramfile)[1]
                print('   ', tail)
                headers, data = util.parse_corr_file(paramfile)
                for paramname in data.keys():
                    # remove group entry from paramname if there is one in it
                    i = paramname.find('_group_')
                    if i == -1:
                        goodparamname = paramname
                    else:
                        goodparamname = paramname[:i]
                        j = paramname[i+7:].find('_')
                        if j != -1:
                            goodparamname += paramname[j+i+7:]
                    # collect good params
                    for s in good_params[tail]:
                        if re.match(s, paramname):
                            print('     (good)', paramname)
                            # this is a good param, parse it into a common dict for all groups in that experiment
                            for i in range(len(headers)):
                                alldata[expdir][goodparamname][headers[i]] = data[paramname][i]
                            break
                    # collect all params
                    for s in all_params[tail]:
                        if re.match(s, paramname):
                            print('     (all)', paramname)
                            # this is a good param, parse it into a common dict for all groups in that experiment
                            for i in range(len(headers)):
                                alldataall[expdir][goodparamname][headers[i]] = data[paramname][i]
                            break

    # write summarized data to common file
    print("\nWriting summarized good data to", corrfile)
    print("Writing summarized all data to", corrfileall)
    expnames = sorted(exps.keys(), lambda a,b: exps[a]['number'] - exps[b]['number'])
    for exp in expnames:
        print(" ", exp)
        expdir = "exp_%s" % exp
        if expdir not in alldata: continue
        # add group line
        strids = []
        for group in exps[exp]['groups']:
            strids.extend(exps[exp]['groups'][group])
        strids.sort()
        groups = [exps[exp]['groupid'][strid] for strid in strids]
        headerline = util.strids2headerline(strids, False, ["exp_number", "param_name"])
        corrline = "\t".join(["#%d" % exps[exp]['number'], "%s__groupids" % expdir] + groups)
        util.add_corr_line(corrfile, headerline, "")
        util.add_corr_line(corrfile, headerline, corrline)
        util.add_corr_line(corrfileall, headerline, "")
        util.add_corr_line(corrfileall, headerline, corrline)
        # add good params
        for paramname in sorted(alldata[expdir].keys()):
            # check if all strids have been parsed...
            parsed_strids = sorted(alldata[expdir][paramname].keys())
            if parsed_strids != strids:
                print("(good)", expdir, paramname, "is not complete, only %d entries found instead of %d!" % (len(parsed_strids), len(strids)))
                continue
            corrline = "\t".join(["%d" % exps[exp]['number'], "%s__%s" % (expdir, paramname)] + \
                    ["%g" % alldata[expdir][paramname][strid] for strid in strids])
            util.add_corr_line(corrfile, headerline, corrline)
        # add all params
        for paramname in sorted(alldataall[expdir].keys()):
            # check if all strids have been parsed...
            parsed_strids = sorted(alldataall[expdir][paramname].keys())
            if parsed_strids != strids:
                print("(all)", expdir, paramname, "is not complete, only %d entries found instead of %d!" % (len(parsed_strids), len(strids)))
                continue
            corrline = "\t".join(["%d" % exps[exp]['number'], "%s__%s" % (expdir, paramname)] + \
                    ["%g" % alldataall[expdir][paramname][strid] for strid in strids])
            util.add_corr_line(corrfileall, headerline, corrline)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:])) # pass only real params to main
    except Exception as ex:
        print(ex, file=sys.stderr)
        import traceback
        traceback.print_exc(ex)
        sys.exit(1)
