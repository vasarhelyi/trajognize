"""This script summarizes dist24hobj food results into one table that contains
an average presence before and during feeding times. It also exports 'alldays'
results into correlation files.

Usage: calc_dist24hobj_feeding_avg.py inputdir [experiment]

where inputdir is/are the location where the .zipped python object outputs of
trajognize.statsum with options "-s dist24hobj" are located

Output is written into a subdir of input dir.
Correlation output is written into the correlation dir according to experiments
and groups.


Note that proper output can be generated only if all substat results are available!

"""

import os, sys, glob, re
import numpy
from collections import defaultdict

try:
    import trajognize.stat.project
    import trajognize.stat.experiments
    import trajognize.stat.init
    import trajognize.util
    import trajognize.corr.util
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(
        os.path.dirname(sys.modules[__name__].__file__), "../..")))
    import trajognize.stat.project
    import trajognize.stat.experiments
    import trajognize.stat.init
    import trajognize.util
    import trajognize.corr.util


def get_categories_from_filename(filename):
    """Get weekday and experiement from filename, e.g.:

    stat_dist24hobj.monday__exp_seventh_G1_G2_G3_G4_females.zip

    """
    match = re.match(r'^stat_dist24hobj\.(.*)__exp_(.*)\.zip$', filename)
    if match:
        weekday = match.group(1)
        exp = match.group(2)
        return (weekday, exp)
    else:
        return (None, None)


class avgdist24hobj_t():
    """Temporary storage class for 24h time distribution of barcodes around food
    and around feeding time.

    Object inherited from trajognize.stat.init.dist24hobj_t

    """
    def __init__(self, id_count):
        """Initialize with zero elements.

        :param id_count: Number of IDs (pateks)

        """
        #: version of the current structure. Change it every time something
        #: changes in the definition of the statistics, to see whether some
        #: already calculated data is old or not.
        #: version 0: first attempt (derived from dist24h version 5)
        self.version = 0
        #: number of minutes in a feeding period (+1h before)
        self.minutes_of_feeding = 120
        # initialize data
        #: one bin for all minutes, all objects, all colorids + sum
        self.avg = numpy.zeros(( \
                id_count+1,
                self.minutes_of_feeding),
                dtype=numpy.float)
        #: one bin for all minutes, all objects, all colorids + sum
        self.stv = numpy.zeros(( \
                id_count+1,
                self.minutes_of_feeding),
                dtype=numpy.float)
        #: one bin for all minutes, all objects, all colorids + sum
        self.num = numpy.zeros(( \
                id_count+1, # note that num is the same for all IDs, but matrix manipulation is simpler like this.
                self.minutes_of_feeding),
                dtype=numpy.int)

    def __add__(self, X):
        """Add another avgdist24hobj object to self with the '+' and '+=' operators.

        :param X: object of the same class that is added to self

        Overloading is needed here because averages and standard deviations
        are not additive. But they can be combined for non overlapping
        sets as described here (Q = sigma^2 * N, where sigma = std, Q = stv):
        http://en.wikipedia.org/wiki/Standard_deviation#Combining_standard_deviations

        """
        # get combined values
        num = self.num + X.num
        avg = numpy.where(num != 0, (self.num * self.avg + X.num * X.avg) / num, 0)
        stv = numpy.where(num != 0, (self.stv + X.stv) +
                (self.num * X.num) * ((self.avg - X.avg)**2) / num, 0)
        # store them
        self.num = num
        self.avg = avg
        self.stv = stv

        return self

    def calculate_group_sum(self, klist):
        """Calculate sum for the group and store it in the last k bin."""
        self.num[-1][:] = 0
        self.avg[-1][:] = 0
        self.stv[-1][:] = 0
        for k in klist:
            num = self.num[-1] + self.num[k]
            avg = numpy.where(num != 0, (self.num[-1] * self.avg[-1] + self.num[k] * self.avg[k]) / num, 0)
            stv = numpy.where(num != 0, (self.stv[-1] + self.stv[k]) +
                    (self.num[-1] * self.num[k]) * ((self.avg[-1] - self.avg[k])**2) / num, 0)
            # store them
            self.num[-1] = num
            self.avg[-1] = avg
            self.stv[-1] = stv
        # assuming that this is already defined...
        self.std[-1] = numpy.where(self.num[-1] != 0, numpy.sqrt(self.stv[-1] / self.num[-1]), 0)

    def write_results(self, outputfile, colorids, exps, exp, substat):
        """Saves the contents of self to a file (possibly as a summarized stat).

        :param outputfile: file object where the results are written
        :param colorids: global colorid database created by
                trajognize.parse.parse_colorid_file()
        :param exps: experiment database created by
                trajognize.stat.experiments.get_initialized_experiments()
        :param exp: name of the current experiment
        :param substat: name of the virtual subclass statistics (e.g. dist24h.monday)

        """
        # calculate standard deviation from standard variance
        self.std = numpy.where(self.num != 0, numpy.sqrt(self.stv / self.num), 0)
        # write results
        for group in exps[exp]['groups']:
            # get sorted names and colorid indices
            allnames = [colorids[k].strid for k in range(len(colorids))]
            names = sorted(exps[exp]['groups'][group])
            klist = [allnames.index(name) for name in names]
            # calculate group sum
            self.calculate_group_sum(klist)
            # write results
            obj = 'food' # hehe
            outputfile.write("# Time distribution of barcodes around 'food', before and during all feeding times averaged over days (except friday).\n")
            outputfile.write("# Output bin size is one minute, range is from 1h before feeding time (0h-1h) to end of feeding time (1h-2h) on a given day\n")
            outputfile.write("# Multiple feeding times of a day are averaged\n")
            outputfile.write("# IDs are ordered alphabetically.\n")
            outputfile.write("# this is group %s\n\n" % group)
            # write header
            s = ["%s_%s_group_%s" % (substat, obj, group)]
            for name in names:
                s.append("%s_avg\t%s_std" % (name, name))
            s.append("all_avg\tall_std\tall_num")
            outputfile.write("\t".join(s) + "\n")
            # write all minute bins (120)
            for bin in range(self.minutes_of_feeding):
                s = ["%02d:%02d:00" % (bin/60, bin%60)]
                for k in klist:
                    s.append("%g\t%g" % (self.avg[k,bin], self.std[k,bin]))
                s.append("%g\t%g\t%d" % (self.avg[-1,bin], self.std[-1,bin], self.num[-1,bin]))
                outputfile.write("\t".join(s) + "\n")
            outputfile.write("\n\n")
            outputfile.flush()

    def write_corroutput(self, statsum_basedir, colorids, exps, exp, corrfiles, substat):
        """Saves the contents of self to a correlation file.

        :param statsum_basedir: base directory where statsum results are written
                according to different statistics
        :param colorids: global colorid database created by
                trajognize.parse.parse_colorid_file()
        :param exps: experiment database created by
                trajognize.stat.experiments.get_initialized_experiments()
        :param exp: name of the current experiment
        :param corrfiles: name of corr files created already by the script
        :param substat: name of the virtual subclass statistics (e.g. avgfooddist24hobj.alldays)

        """
        for group in exps[exp]['groups']:
            # get sorted names and colorid indices
            allnames = [colorids[k].strid for k in range(len(colorids))]
            names = sorted(exps[exp]['groups'][group])
            klist = [allnames.index(name) for name in names]
            # initialize corr file
            headerline = trajognize.corr.util.strids2headerline(names, False)
            corrfile = trajognize.corr.util.get_corr_filename(statsum_basedir, "exp_%s" % exp, group, False)
            if corrfile not in corrfiles:
                if os.path.isfile(corrfile):
                    os.remove(corrfile)
                corrfiles.append(corrfile)
            # write cumulative average to corr file
            corrline = "\t".join([substat + "_cumul"] +
                    ["%g" % sum(self.avg[k,60:]) for k in klist])
            trajognize.corr.util.add_corr_line(corrfile, headerline, corrline)
            # write time when 1-2-3 minute feeding accumulates
            for minute in [1,2,3]:
                data = []
                for k in klist:
                    x = 0
                    for i in range(60,120):
                        x += self.avg[k,i]
                        if x >= minute:
                            data.append(i-60+1)
                            break
                    else:
                        data.append(float('inf'))
                corrline = "\t".join([substat + "_t%dmin" % minute] +
                        ["%g" % data[i] for i in range(len(data))])
                trajognize.corr.util.add_corr_line(corrfile, headerline, corrline)


def main(argv=[]):
    """Main entry point of the script."""
    if not argv:
        print(__doc__)
        return
    inputdir = argv[0]
    statsum_basedir = os.path.split(inputdir)[0]
    if len(argv) == 2:
        experiment = argv[1]
    else:
        experiment = '*'
#    inputfiles = glob.glob(os.path.join(inputdir, "statsum_dist24hobj.*", "stat_dist24hobj.*__exp_%s.zip" % experiment))
    inputfiles = glob.glob(os.path.join(inputdir, "stat_dist24hobj.*__exp_%s.zip" % experiment))
    exps = trajognize.stat.experiments.get_initialized_experiments()
    colorids = trajognize.parse.parse_colorid_file('../../misc/5-3_28patek.xml')
    id_count = len(colorids)
    # create full database of all data
    database = defaultdict(defaultdict)
    corrfiles = []

    # parse all data to create the full database
    for inputfile in inputfiles:
        tail = os.path.split(inputfile)[1]
        (weekday, exp) = get_categories_from_filename(tail)
        if exp == 'all' or weekday == 'friday' or weekday == 'alldays':
            print("  skipping", tail)
            continue
        print("  gathering info from", tail)
        # initialize empty object
        dist24hobj = trajognize.stat.init.dist24hobj_t(id_count)
        # add new object (so that we have latest methods from latest version)
        dist24hobj += trajognize.util.load_object(inputfile)
        database[exp][weekday] = dist24hobj
    # write results (assuming that all substats are available)
    if not database:
        print("No input files found.")
        return
    outputdir = os.path.join(inputdir, os.path.splitext(os.path.split(__file__)[1])[0])
    print("Writing results to .txt files in", outputdir)
    food_index = trajognize.stat.project.object_types.index('food')
    if not os.path.isdir(outputdir):
        os.makedirs(outputdir)
    for exp in database:
        print(' ', exp)
        alltemp = avgdist24hobj_t(id_count)
        for weekday in database[exp]:
            print('   ', weekday)
            data = database[exp][weekday]
            wft = trajognize.stat.project.weekly_feeding_times[weekday]
            temp = avgdist24hobj_t(id_count)
            temp2 = avgdist24hobj_t(id_count)
            outputfile = open(os.path.join(outputdir,
                    "calc_avgfooddist24hobj.%s__exp_%s.txt" % (weekday, exp)), 'w')
            if temp.version != data.version:
                raise TypeError("Version mismatch (temp.version=%d, data.version=%d)" %
                        (temp.version, data.version))
            for x in wft:
                # start is 1 hour before feeding ([hour] -> [minute])
                start = x[0]*60 - 60
                # end is feeding end
                end = x[0]*60 + x[1]*60
                # get data from original database
                temp2.avg = data.avg[:,food_index,start:end]
                temp2.stv = data.stv[:,food_index,start:end]
                temp2.num = data.num[:,food_index,start:end]
                # add to daily average
                temp += temp2
                # add to allday average
                alltemp += temp2
            substat = "avgfooddist24hobj.%s" % weekday
            temp.write_results(outputfile, colorids, exps, exp, substat)
        print('    alldays')
        substat = "avgfooddist24hobj.alldays"
        outputfile = open(os.path.join(outputdir,
                "calc_avgfooddist24hobj.alldays__exp_%s.txt" % exp), 'w')
        alltemp.write_results(outputfile, colorids, exps, exp, substat)
        alltemp.write_corroutput(statsum_basedir, colorids, exps, exp, corrfiles, substat.replace('.', '_'))


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:])) # pass only real params to main
    except Exception as ex:
        print(ex, file=sys.stderr)
        import traceback
        traceback.print_exc(ex)
        sys.exit(1)
