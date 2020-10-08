""""
Main classes for statistics are defined here, like heatmap, 24h distribution, etc.

To allow for automatic execution of all statistics, it is important to have all
Stat derived objects synhcronized with statistical functions implemented in
trajognize.stat.stat. For more info check out the description there.

All things needed when a new stat is created:

  - object definition in trajognize/stat/init.py (here)
  - statistic implementation in trajognize/stat/stat.py
  - plot for the new stat as trajognize/plot/plot_*.py
  - definition of good and all params in trajognize/corr/good_params.py
  - automatic plot implementation in trajognize/plot/autorun.sh, or on altasz,
    parallelization implementation in queue_jobs/full_run__plot.py

"""

# external imports
from functools import cmp_to_key
import sys
import numpy
from math import sqrt

# imports from base class
import trajognize.init

from . import experiments

#: generally used mfix values to differentiate in the stat outputs
#: for more info see trajognize.stat.util.get_mfi()
mfix_types = ['REAL', 'VIRTUAL']

class Stat(object):
    """Base storage class for trajognize statistic storage classes.

    All subclasses should have all methods and variables implemented
    that are defined here, but overloading is only necessary in some cases
    by default. If you do not want to mess things up, try to stick to the
    structure and format used here and in the subclasses already implemented.

    Note that the self.points and self.frames members are used everywhere for
    historical reasons but in many cases they are meaningless,
    e.g. when results are separated for groups at summary. This is not indicated
    everywhere explicitely so if you would like to use them, check their
    definition in stat.py

    """
    def __init__(self, good_light):
        """Initialize an empty class."""
        #: version of the current structure. Change it every time something
        #: changes in the definition of the statistics, to see whether some
        #: already calculated data is old or not.
        #: version 0: first attempt
        #: version 1: differentiate between mfix_types
        self.version = 1
        #: number of files that are parsed into this statistic
        self.files = 0
        #: number of frames that were used to gather info for the statistic
        self.frames = dict()
        #: number of data points in the statistic
        self.points = dict()
        #: the main data of the statistic
        self.data = dict()
        # initialize data
        for light in good_light:
            self.data[light] = numpy.zeros(( \
                    len(mfix_types),
                    1,
                    1),
                    dtype=numpy.int)
            self.frames[light] = 0
            self.points[light] = numpy.zeros((len(mfix_types)), dtype=numpy.int)
        raise NotImplementedError("TODO: overload default function with proper settings.")

    def __add__(self, X):
        """Add another object of the same class to self with the '+' and '+=' operators.

        :param X: object of the same class that is added to self

        Overload this function only when you define new data types or structures.
        Make sure to implement version checking if overloaded.

        """
        self._check_version(X)
        for light in self.data.keys():
            self.data[light] += X.data[light]
            self.frames[light] += X.frames[light]
            self.points[light] += X.points[light]
        self.files += X.files

        return self

    def _check_version(self, X):
        """Check if self is compatible with a given object's version."""
        if self.version != X.version:
            raise TypeError("Objects with different versions (%d and %d) cannot be added!" % (self.version, X.version))

    def _print_status__simple(self):
        """Template function for print_status() for simple data.

        No need to overload this function, only use it in print_status() if needed.

        """
        print("  statistic is from %d files, %d frames and %d data points" % \
                (self.files, self.frames, self.points))

    def _print_status__light(self):
        """Template function for print_status() for data with light types.

        No need to overload this function, only use it in print_status() if needed.

        """
        for light in self.frames.keys():
            print("  %s statistic is from %d files, %d frames and %d data points" % \
                    (light, self.files, self.frames[light], self.points[light]))

    def _print_status__mft(self):
        """Template function for print_status() for data with mfix types.

        No need to overload this function, only use it in print_status() if needed.

        """
        for mfi in range(len(mfix_types)):
            mft = mfix_types[mfi]
            print("  %s statistic is from %d files, %d frames and %d data points" % \
                    (mft, self. files, self.frames, self.points[mfi]))

    def _print_status__light_mft(self):
        """Template function for print_status() for data with light and mfix types.

        No need to overload this function, only use it in print_status() if needed.

        """
        for light in self.frames.keys():
            for mfi in range(len(mfix_types)):
                mft = mfix_types[mfi]
                print("  %s %s statistic is from %d files, %d frames and %d data points" % \
                        (light, mft, self.files, self.frames[light], self.points[light][mfi]))

    def print_status(self):
        """Prints status info about the data to standard output.

        Overload this function only when you define new data types or structures.

        """
        self._print_status__light()

    def write_results(self, outputfile):
        """Saves the contents of self to a file (possibly as a summarized stat).

        :param outputfile: file object where the results are written

        """
        outputfile.write("# TODO: print title, description, params\n")
        outputfile.flush()
        raise NotImplementedError("TODO: overload default function with proper settings.")

    def write_dailyoutput_results(self):
        """Saves the contents of self to a file (possibly as a summarized stat
        with daily outputs).

        This method has to be implemented only if stat can produce dailyoutput
        results, such as heatmaps.

        """
        pass


################################################################################
################################################################################
################################################################################
# storage classes for a statistic on barcodes


class HeatMap(Stat):
    """Storage class for heatmaps of barcodes for all light types and real/virt
    states.

    heatmap.data[light][real/virtual][x][y] is the number of times a patek
    barcode center was at the coordinates (x, y) in the given light condition.

    This class has one virtual subclass for each barcode and one for 'all' sum
    to avoid long execution times of stat and statsum (large memory needed for
    image matrices).

    Note that summarized results do not take into account groups, it is
    calculated for all 28 rats. However, groups are (should be) separated
    spatially on the heatmaps.

    """
    def __init__(self, good_light, image_size):
        """Initialize barcode heatmaps with zero elements.

        """
        #: version of the current structure. Change it every time something
        #: changes in the definition of the statistics, to see whether some
        #: already calculated data is old or not.
        #: version 0: first attempt
        #: version 1: entrytimes are checked and skipped
        #: version 2: subclasses + mfix_types introduced (REAL and VIRTUAL)
        #: version 2b: percentage introduced to simplified stat outputs
        #: version 3: filter_for_valid_cage introduced (2015.04.20.)
        self.version = 3
        #: number of files that are parsed into this statistic
        self.files = 0
        #: number of frames that were used to gather info for the statistic
        self.frames = dict()
        #: number of data points in the statistic
        self.points = dict()
        #: the main data of the statistic: [light][x][y]
        self.data = dict()
        #: parameter that defines nonzero values in dailyoutput
        self.nonzero_threshold = 0
        #: parameters that define lower/upper thresholds for the intensity
        #: of motional territory.
        #: values are based on real log analysis
        self.territory_intensity_per_day_min = 0.5
        self.territory_intensity_per_day_max = 15.0
        # initialize data
        for light in good_light:
            self.data[light] = numpy.zeros(
                    (len(mfix_types), image_size.x, image_size.y),
                    dtype=numpy.int)
            self.frames[light] = 0
            self.points[light] = numpy.zeros((len(mfix_types)), dtype=numpy.int)

    def print_status(self):
        """Prints status info about the data to standard output."""
        self._print_status__light_mft()

    def write_results(self, outputfile, project_settings, substat):
        """Saves the contents of self to a file (possibly as a summarized stat).

        :param outputfile: file object where the results are written
        :param project_settings: global project settings imported by
                trajognize.settings.import_trajognize_settings_from_file()
        :param substat: name of the virtual subclass statistics (e.g. heatmap.RPG)

        """
        anymft = mfix_types + ["ANY"]
        for light in project_settings.good_light:
            for mfi in range(len(anymft)):
                mft = anymft[mfi]
                if mft == "ANY":
                    points = sum(self.points[light])
                else:
                    points = self.points[light][mfi]
                outputfile.write("# %s of %s %s barcodes from %d files, %d frames, %d points\n" %
                        (substat, light.lower(), mft, self.files, self.frames[light], points))
                outputfile.write("# image size is %dx%d pixels, bin size is 1x1 pixel.\n" %
                        (project_settings.image_size.x, project_settings.image_size.y))
                outputfile.write("# filter_for_valid_cage=%s\n" % str(project_settings.filter_for_valid_cage))
                outputfile.write("# (0,0) = (top,left) corner of image.\n\n")
                outputfile.write("%s_%s_%s" % (substat, light.lower(), mft))
                for x in range(project_settings.image_size.x):
                    outputfile.write("\t%d" % x)
                outputfile.write("\n")
                if mft == "ANY":
                    data = sum(self.data[light])
                else:
                    data = self.data[light][mfi]
                for y in range(project_settings.image_size.y):
                    outputfile.write("%d" % y)
                    for x in range(project_settings.image_size.x):
                        outputfile.write("\t%d" % data[x, y])
                    outputfile.write("\n")
                outputfile.write("\n\n")
                outputfile.flush()

    def get_simplified_statistics(self, days, area, binsize=1):
        """Get simplified statistics from a heatmap.

        :param days: number of days in the given experiment. Needed for territory
                     size calculation, since intensity thresholds are defined for
                     a single day.
        :param area: the area of the experiment for a given group in pixels
        :param binsize: averaging factor for the heatmap

        """
        simplified = dict()
        anymft = mfix_types + ["ANY"]
        for light in self.data.keys():
            image_size = trajognize.init.Point(*self.data[light].shape[1:])
            for mfi in range(len(anymft)):
                mft = anymft[mfi]
                if mft == "ANY":
                    x = sum(self.data[light])
                else:
                    x = self.data[light][mfi]
                # get binned results
                if binsize > 1:
                    xbin = numpy.array([[numpy.mean(x[
                        i * binsize : i * binsize + binsize,
                        j * binsize : j * binsize + binsize])
                        for j in range(image_size.y / binsize)]
                        for i in range(image_size.x / binsize)
                    ])
                else:
                    xbin = x
                x_nonzero = xbin[xbin > self.nonzero_threshold]
                x_territory = xbin[xbin >= self.territory_intensity_per_day_min * days]
                x_territory = x_territory[x_territory <= self.territory_intensity_per_day_max * days]
                mean_all = numpy.mean(xbin)
                std_all = numpy.std(xbin)
                sum_all = numpy.sum(xbin)
                count_nonzero = len(x_nonzero)
                mean_nonzero = numpy.mean(x_nonzero)
                std_nonzero = numpy.std(x_nonzero)
                count_territory = len(x_territory)
                mean_territory = numpy.mean(x_territory)
                std_territory = numpy.std(x_territory)
                s = ["", "_framenormed"]
                n = [1., float(self.frames[light])]
                if not n[1]: n[1] = float('nan')
                for i in [0,1]:
                    simplified[(light, mft, "mean_all%s" % s[i])] = mean_all/n[i]
                    simplified[(light, mft, "std_all%s" % s[i])] = std_all/n[i]
                    simplified[(light, mft, "sum_all%s" % s[i])] = sum_all/n[i]
                    simplified[(light, mft, "count_nonzero%s" % s[i])] = count_nonzero/n[i]
                    simplified[(light, mft, "percent_nonzero%s" % s[i])] = count_nonzero/area/n[i]
                    simplified[(light, mft, "mean_nonzero%s" % s[i])] = mean_nonzero/n[i]
                    simplified[(light, mft, "std_nonzero%s" % s[i])] = std_nonzero/n[i]
                    simplified[(light, mft, "count_territory%s" % s[i])] = count_territory/n[i]
                    simplified[(light, mft, "percent_territory%s" % s[i])] = count_territory/area/n[i]
                    simplified[(light, mft, "mean_territory%s" % s[i])] = mean_territory/n[i]
                    simplified[(light, mft, "std_territory%s" % s[i])] = std_territory/n[i]
        return simplified

    def write_dailyoutput_results(self, outputfile, project_settings, exps, exp, substat):
        """Saves the contents of self to a file (possibly as a summarized stat
        of extracted statistics of the heatmaps for daily output stat).

        :param outputfile: file object where the results are written
        :param project_settings: global project settings imported by
                trajognize.settings.import_trajognize_settings_from_file()
        :param exps: experiment database created by project_settings
        :param exp: name of the current experiment
        :param substat: name of the virtual subclass statistics (e.g. heatmap.RPG)

        """
        # calculate simplified statistics for 1 day only
        # Caution: more noise in daily territory size!!!
        strid = substat.split('.')[1]
        if strid == "all":
            area = sum(exps[exp]['areaall'][group] for group in exps[exp]['areaall'].keys())
        else:
            area = exps[exp]['areaall'][exps[exp]['groupid'][strid]]
        simplified = self.get_simplified_statistics(1, area)
        keys = sorted(simplified.keys())
        anymft = mfix_types + ["ANY"]
        for light in project_settings.good_light:
            for mfi in range(len(anymft)):
                mft = anymft[mfi]
                if mft == "ANY":
                    points = sum(self.points[light])
                else:
                    points = self.points[light][mfi]
                outputfile.write("# %s of %s %s barcodes from %d files, %d frames, %d points\n" %
                        (substat, light.lower(), mft, self.files, self.frames[light], points))
                outputfile.write("# image size is %dx%d pixels, bin size is 1x1 pixel.\n" %
                        (project_settings.image_size.x, project_settings.image_size.y))
                outputfile.write("# this is an extracted statistics of the heatmap to reduce overall size.\n")
                outputfile.write("# filter_for_valid_cage=%s\n" % str(project_settings.filter_for_valid_cage))
                outputfile.write("# nonzero threshold is > %d\n" % self.nonzero_threshold)
                outputfile.write("# territory intensity thresholds (per day): %g <= x <= %g\n\n" %
                        (self.territory_intensity_per_day_min, self.territory_intensity_per_day_max))
                outputfile.write("%s_%s_%s\tvalue\n" % (substat, light.lower(), mft))
                for (keylight, keymft, keydata) in keys:
                    if keylight == light and keymft == mft:
                        outputfile.write("%s\t%g\n"% (keydata, simplified[(keylight, keymft, keydata)]))
                outputfile.write("\n\n")
                outputfile.flush()


class MotionMap(Stat):
    """Storage class for motion heatmaps of barcodes for all light types.

    motionmap.data[light][x][y] is the number of times a patek
    barcode center was at the coordinates (x, y) in the given light condition,
    with velocity over velocity threshold. Interpolated positions between
    two frames are stamped, too, so that number of interpolated points equals
    the velocity expressed in px/frame.

    This class has one virtual subclass for each barcode and one for 'all' sum
    to avoid long execution times of stat and statsum (large memory needed for
    image matrices).

    Note that summarized results does not take into account groups, it is
    calculated for all 28 rats. However, groups are (should be ) separated
    spatially on the motion heatmaps.

    """
    def __init__(self, good_light, image_size):
        """Initialize barcode motion heatmaps with zero elements.

        """
        #: version of the current structure. Change it every time something
        #: changes in the definition of the statistics, to see whether some
        #: already calculated data is old or not.
        #: version 0: first attempt, inherited from HeatMap version 2
        #: version 1: filter_for_valid_cage introduced (2015.04.20.)
        self.version = 1
        #: threshold below which we do not take barcodes into account
        self.velocity_threshold = 5 # [px/frame] = 1 cm/frame = 25 cm/s
        #: number of files that are parsed into this statistic
        self.files = 0
        #: number of frames that were used to gather info for the statistic
        self.frames = dict()
        #: number of data points in the statistic
        self.points = dict()
        #: the main data of the statistic: [light][x][y]
        self.data = dict()
        # initialize data
        for light in good_light:
            self.data[light] = numpy.zeros(
                (image_size.x, image_size.y),
                dtype=numpy.int
            )
            self.frames[light] = 0
            self.points[light] = 0

    def print_status(self):
        """Prints status info about the data to standard output."""
        self._print_status__light()

    def write_results(self, outputfile, project_settings, substat):
        """Saves the contents of self to a file (possibly as a summarized stat).

        :param outputfile: file object where the results are written
        :param project_settings: global project settings imported by
                trajognize.settings.import_trajognize_settings_from_file()
        :param substat: name of the virtual subclass statistics (e.g. heatmap.RPG)

        """
        for light in project_settings.good_light:
            outputfile.write("# %s of %s barcodes from %d files, %d frames, %d points\n" %
                    (substat, light.lower(), self.files, self.frames[light], self.points[light]))
            outputfile.write("# image size is %dx%d pixels, bin size is 1x1 pixel.\n" %
                    (project_settings.image_size.x, project_settings.image_size.y))
            outputfile.write("# velocity_threshold=%dpx/frame\n" % self.velocity_threshold)
            outputfile.write("# filter_for_valid_cage=%s\n" % str(project_settings.filter_for_valid_cage))
            outputfile.write("# (0,0) = (top,left) corner of image.\n\n")
            outputfile.write("%s_%s_ANY" % (substat, light.lower()))
            for x in range(project_settings.image_size.x):
                outputfile.write("\t%d" % x)
            outputfile.write("\n")
            for y in range(project_settings.image_size.y):
                outputfile.write("%d" % y)
                for x in range(project_settings.image_size.x):
                    outputfile.write("\t%d" % self.data[light][x, y])
                outputfile.write("\n")
            outputfile.write("\n\n")
            outputfile.flush()


class AAMap(Stat):
    """Storage class for AA heatmaps of barcodes for all light types.

    aamap.data[light][x][y] is the number of times a patek
    barcode center was at the coordinates (x, y) in the given light condition,
    when it was assumed to be in an AA type event (see AA).
    Interpolated positions between two frames are stamped, too,
    so that number of interpolated points equals the velocity expressed in px/frame.

    Note that summarized results does not take into account groups, it is
    calculated for all 28 rats. However, groups are (should be) separated
    spatially on the motion heatmaps.

    """
    def __init__(self, good_light, image_size):
        """Initialize barcode AA heatmaps with zero elements.

        """
        #: version of the current structure. Change it every time something
        #: changes in the definition of the statistics, to see whether some
        #: already calculated data is old or not.
        #: version 0: first attempt, inherited from MotionMap version 0
        #: version 1: angle thresholds introduced to aa
        #: version 2: minimum event length introduced to aa
        self.version = 2
        #: number of files that are parsed into this statistic
        self.files = 0
        #: number of frames that were used to gather info for the statistic
        self.frames = dict()
        #: number of data points in the statistic
        self.points = dict()
        #: the main data of the statistic: [light][x][y]
        self.data = dict()
        # initialize data
        for light in good_light:
            self.data[light] = numpy.zeros(
                (image_size.x, image_size.y),
                dtype=numpy.int
            )
            self.frames[light] = 0
            self.points[light] = 0

    def print_status(self):
        """Prints status info about the data to standard output."""
        self._print_status__light()

    def write_results(self, outputfile, project_settings):
        """Saves the contents of self to a file (possibly as a summarized stat).

        :param outputfile: file object where the results are written
        :param project_settings: global project settings imported by
                trajognize.settings.import_trajognize_settings_from_file()

        """
        for light in project_settings.good_light:
            outputfile.write("# AA heatmap of %s barcodes from %d files, %d frames, %d points\n" %
                    (light.lower(), self.files, self.frames[light], self.points[light]))
            outputfile.write("# image size is %dx%d pixels, bin size is 1x1 pixel.\n" %
                    (project_settings.image_size.x, project_settings.image_size.y))
            outputfile.write("# heatmap points are calculated with the 'aa' stat\n")
            outputfile.write("# filter_for_valid_cage=%s\n" % str(project_settings.filter_for_valid_cage))
            outputfile.write("# (0,0) = (top,left) corner of image.\n\n")
            outputfile.write("aamap_%s_ANY" % light.lower())
            for x in range(project_settings.image_size.x):
                outputfile.write("\t%d" % x)
            outputfile.write("\n")
            for y in range(project_settings.image_size.y):
                outputfile.write("%d" % y)
                for x in range(project_settings.image_size.x):
                    outputfile.write("\t%d" % self.data[light][x, y])
                outputfile.write("\n")
            outputfile.write("\n\n")
            outputfile.flush()


class Dist24h(Stat):
    """Storage class for 24h time distribution of barcodes.

    dist24h.avg[virtual/real][patek/all][minute] is a number between 0 and 1, indicating at what
    percentage was a patek/ all pateks (virtually) visible on that minute of the day.
    .stv is num*(standard variance) = num*(standard deviation)^2 of the distribution
    .std is the standard deviation,
    .num is the number of frames taken into account in the statistic.

    """
    def __init__(self, project_settings, id_count):
        """Initialize with zero elements.

        :param id_count: Number of IDs (pateks)

        """
        #: version of the current structure. Change it every time something
        #: changes in the definition of the statistics, to see whether some
        #: already calculated data is old or not.
        #: version 0: first attempt
        #: version 1: entrytimes are checked and skipped
        #: version 2: bugfix on 'all' normalization
        #: version 3: mfix_type introduced (REAL and VIRTUAL)
        #: version 4: weekdays introduced as virtual substats
        #: version 5: results written on group basis, structure reorganized
        #: version 6: filter_for_valid_cage introduced (2015.04.30.)
        self.version = 6
        #: number of files that are parsed into this statistic
        self.files = 0
        #: number of frames that were used to gather info for the statistic
        self.frames = 0
        #: number of data points in the statistic
        self.points = numpy.zeros((len(mfix_types)), dtype=numpy.int)
        #: number of minutes in a day (data is using minute bins over the day)
        self.minutes_per_day = 1440
        # initialize data
        #: one bin for real/virt, all minutes, all colorids + sum
        self.avg = numpy.zeros(( \
                id_count+1,
                len(mfix_types),
                self.minutes_per_day),
                dtype=numpy.float)
        #: one bin for real/virt, all minutes, all colorids + sum
        self.stv = numpy.zeros(( \
                id_count+1,
                len(mfix_types),
                self.minutes_per_day),
                dtype=numpy.float)
        #: one bin for real/virt, all minutes, all colorids + sum
        self.num = numpy.zeros(( \
                id_count+1, # note that num is the same for all IDs, but matrix manipulation is simpler like this.
                len(mfix_types),
                self.minutes_per_day),
                dtype=numpy.int)

    def __add__(self, X):
        """Add another dist24h object to self with the '+' and '+=' operators.

        :param X: object of the same class that is added to self

        Overloading is needed here because averages and standard deviations
        are not additive. But they can be combined for non overlapping
        sets as described here (Q = sigma^2 * N, where sigma = std, Q = stv):
        http://en.wikipedia.org/wiki/Standard_deviation#Combining_standard_deviations

        """
        self._check_version(X)
        # get combined values
        num = self.num + X.num
        avg = numpy.where(num != 0, (self.num * self.avg + X.num * X.avg) / num, 0)
        stv = numpy.where(num != 0, (self.stv + X.stv) +
                (self.num * X.num) * ((self.avg - X.avg)**2) / num, 0)
        # store them
        self.num = num
        self.avg = avg
        self.stv = stv
        # store other variables
        self.frames += X.frames
        self.points += X.points
        self.files += X.files

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

    def print_status(self):
        """Prints status info about the data to standard output."""
        self._print_status__mft()

    def write_results(self, outputfile, project_settings, exps, exp, substat):
        """Saves the contents of self to a file (possibly as a summarized stat).

        :param outputfile: file object where the results are written
        :param project_settings: global project settings imported by
                trajognize.settings.import_trajognize_settings_from_file()
        :param exps: experiment database created by project_settings
        :param exp: name of the current experiment
        :param substat: name of the virtual subclass statistics (e.g. dist24h.monday)

        """
        colorids = project_settings.colorids
        # calculate standard deviation from standard variance
        self.std = numpy.where(self.num != 0, numpy.sqrt(self.stv / self.num), 0)
        # write results
        if exp == "all":
            # get sorted names and colorid indices
            names = sorted([colorids[k] for k in range(len(colorids))])
            klist = range(len(colorids))
            # calculate group sum
            self.calculate_group_sum(klist)
            # write results
            for mfi in range(len(mfix_types)):
                mft = mfix_types[mfi]
                outputfile.write("# 24h time distribution of %s barcodes from %d files, %d frames, %d points\n" %
                        (mft, self.files, self.frames, self.points[mfi]))
                outputfile.write("# Output bin size is one minute, range is from 00:00:00 to 23:59:59 (24*60 = 1440 bins)\n")
                outputfile.write("# filter_for_valid_cage=%s\n" % str(project_settings.filter_for_valid_cage))
                outputfile.write("# IDs are ordered alphabetically.\n\n")
                # write header
                s = ["%s_%s" % (substat, mft)]
                for name in names:
                    s.append("%s_avg\t%s_std" % (name, name))
                s.append("all_avg\tall_std\tall_num")
                outputfile.write("\t".join(s) + "\n")
                # write all minute bins (1440)
                for bin in range(self.minutes_per_day):
                    s = ["%02d:%02d:00" % (bin/60, bin%60)]
                    for k in klist:
                        s.append("%g\t%g" % (self.avg[k,mfi,bin], self.std[k,mfi,bin]))
                    s.append("%g\t%g\t%d" % (self.avg[-1,mfi,bin], self.std[-1,mfi,bin], self.num[-1,mfi,bin]))
                    outputfile.write("\t".join(s) + "\n")
                outputfile.write("\n\n")
                outputfile.flush()
        else:
            for group in exps[exp]['groups']:
                # get sorted names and colorid indices
                allnames = [colorids[k] for k in range(len(colorids))]
                names = sorted(exps[exp]['groups'][group])
                klist = [allnames.index(name) for name in names]
                # calculate group sum
                self.calculate_group_sum(klist)
                # write results
                for mfi in range(len(mfix_types)):
                    mft = mfix_types[mfi]
                    outputfile.write("# 24h time distribution of %s barcodes from %d files, %d frames, %d points\n" %
                            (mft, self.files, self.frames, self.points[mfi]))
                    outputfile.write("# Output bin size is one minute, range is from 00:00:00 to 23:59:59 (24*60 = 1440 bins)\n")
                    outputfile.write("# filter_for_valid_cage=%s\n" % str(project_settings.filter_for_valid_cage))
                    outputfile.write("# IDs are ordered alphabetically.\n")
                    outputfile.write("# this is group %s\n\n" % group)
                    # write header
                    s = ["%s_%s_group_%s" % (substat, mft, group)]
                    for name in names:
                        s.append("%s_avg\t%s_std" % (name, name))
                    s.append("all_avg\tall_std\tall_num")
                    outputfile.write("\t".join(s) + "\n")
                    # write all minute bins (1440)
                    for bin in range(self.minutes_per_day):
                        s = ["%02d:%02d:00" % (bin/60, bin%60)]
                        for k in klist:
                            s.append("%g\t%g" % (self.avg[k,mfi,bin], self.std[k,mfi,bin]))
                        s.append("%g\t%g\t%d" % (self.avg[-1,mfi,bin], self.std[-1,mfi,bin], self.num[-1,mfi,bin]))
                        outputfile.write("\t".join(s) + "\n")
                    outputfile.write("\n\n")
                    outputfile.flush()


class Dist24hObj(Stat):
    """Storage class for 24h time distribution of barcodes around specific objects.

    dist24h.avg[patek/all][object][minute] is a number between 0 and 1, indicating at what
    percentage was a patek/ all pateks (virtually) visible on that minute of the day
    around (on/under) a given object.

    Object locations and closeness thresholds are defined in stat.experiments.py

    .stv is num*(standard variance) = num*(standard deviation)^2 of the distribution
    .std is the standard deviation,
    .num is the number of frames taken into account in the statistic.

    """
    def __init__(self, object_types, id_count):
        """Initialize with zero elements.

        :param id_count: Number of IDs (pateks)

        """
        #: version of the current structure. Change it every time something
        #: changes in the definition of the statistics, to see whether some
        #: already calculated data is old or not.
        #: version 0: first attempt (derived from dist24h version 5)
        #:            note that filter_for_valid_cage is not needed here,
        #:            since object definitions contain this check inherently
        self.version = 0
        #: number of files that are parsed into this statistic
        self.files = 0
        #: number of frames that were used to gather info for the statistic
        self.frames = 0
        #: number of data points in the statistic
        self.points = 0
        #: number of minutes in a day (data is using minute bins over the day)
        self.minutes_per_day = 1440
        # initialize data
        #: one bin for all minutes, all objects, all colorids + sum
        self.avg = numpy.zeros(( \
                id_count+1,
                len(object_types),
                self.minutes_per_day),
                dtype=numpy.float)
        #: one bin for all minutes, all objects, all colorids + sum
        self.stv = numpy.zeros(( \
                id_count+1,
                len(object_types),
                self.minutes_per_day),
                dtype=numpy.float)
        #: one bin for all minutes, all objects, all colorids + sum
        self.num = numpy.zeros(( \
                id_count+1, # note that num is the same for all IDs, but matrix manipulation is simpler like this.
                len(object_types),
                self.minutes_per_day),
                dtype=numpy.int)

    def __add__(self, X):
        """Add another dist24hobj object to self with the '+' and '+=' operators.

        :param X: object of the same class that is added to self

        Overloading is needed here because averages and standard deviations
        are not additive. But they can be combined for non overlapping
        sets as described here (Q = sigma^2 * N, where sigma = std, Q = stv):
        http://en.wikipedia.org/wiki/Standard_deviation#Combining_standard_deviations

        """
        self._check_version(X)
        # get combined values
        num = self.num + X.num
        avg = numpy.where(num != 0, (self.num * self.avg + X.num * X.avg) / num, 0)
        stv = numpy.where(num != 0, (self.stv + X.stv) +
                (self.num * X.num) * ((self.avg - X.avg)**2) / num, 0)
        # store them
        self.num = num
        self.avg = avg
        self.stv = stv
        # store other variables
        self.points += X.points
        self.frames += X.frames
        self.files += X.files

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

    def print_status(self):
        """Prints status info about the data to standard output."""
        self._print_status__simple()

    def write_results(self, outputfile, project_settings, exps, exp, substat):
        """Saves the contents of self to a file (possibly as a summarized stat).

        :param outputfile: file object where the results are written
        :param project_settings: global project settings imported by
                trajognize.settings.import_trajognize_settings_from_file()
        :param exps: experiment database created by project_settings
        :param exp: name of the current experiment
        :param substat: name of the virtual subclass statistics (e.g. dist24h.monday)

        """
        colorids = project_settings.colorids
        # calculate standard deviation from standard variance
        self.std = numpy.where(self.num != 0, numpy.sqrt(self.stv / self.num), 0)
        # write results
        if exp == "all":
            # get sorted names and colorid indices
            names = sorted([colorids[k] for k in range(len(colorids))])
            klist = range(len(colorids))
            # calculate group sum
            self.calculate_group_sum(klist)
            # write results
            for obi in range(len(project_settings.object_types)):
                obj = project_settings.object_types[obi] # hehe
                outputfile.write("# 24h time distribution of barcodes around '%s' from %d files, %d frames, %d points\n" %
                        (obj, self.files, self.frames, self.points))
                outputfile.write("# Output bin size is one minute, range is from 00:00:00 to 23:59:59 (24*60 = 1440 bins)\n")
                outputfile.write("# IDs are ordered alphabetically.\n\n")
                # write header
                s = ["%s_%s" % (substat, obj)]
                for name in names:
                    s.append("%s_avg\t%s_std" % (name, name))
                s.append("all_avg\tall_std\tall_num")
                outputfile.write("\t".join(s) + "\n")
                # write all minute bins (1440)
                for bin in range(self.minutes_per_day):
                    s = ["%02d:%02d:00" % (bin/60, bin%60)]
                    for k in klist:
                        s.append("%g\t%g" % (self.avg[k,obi,bin], self.std[k,obi,bin]))
                    s.append("%g\t%g\t%d" % (self.avg[-1,obi,bin], self.std[-1,obi,bin], self.num[-1,obi,bin]))
                    outputfile.write("\t".join(s) + "\n")
                outputfile.write("\n\n")
                outputfile.flush()
        else:
            for group in exps[exp]['groups']:
                # get sorted names and colorid indices
                allnames = [colorids[k] for k in range(len(colorids))]
                names = sorted(exps[exp]['groups'][group])
                klist = [allnames.index(name) for name in names]
                # calculate group sum
                self.calculate_group_sum(klist)
                # write results
                for obi in range(len(project_settings.object_types)):
                    obj = project_settings.object_types[obi] # hehe
                    outputfile.write("# 24h time distribution of barcodes around '%s' from %d files, %d frames, %d points\n" %
                            (obj, self.files, self.frames, self.points))
                    outputfile.write("# Output bin size is one minute, range is from 00:00:00 to 23:59:59 (24*60 = 1440 bins)\n")
                    outputfile.write("# IDs are ordered alphabetically.\n")
                    outputfile.write("# this is group %s\n\n" % group)
                    # write header
                    s = ["%s_%s_group_%s" % (substat, obj, group)]
                    for name in names:
                        s.append("%s_avg\t%s_std" % (name, name))
                    s.append("all_avg\tall_std\tall_num")
                    outputfile.write("\t".join(s) + "\n")
                    # write all minute bins (1440)
                    for bin in range(self.minutes_per_day):
                        s = ["%02d:%02d:00" % (bin/60, bin%60)]
                        for k in klist:
                            s.append("%g\t%g" % (self.avg[k,obi,bin], self.std[k,obi,bin]))
                        s.append("%g\t%g\t%d" % (self.avg[-1,obi,bin], self.std[-1,obi,bin], self.num[-1,obi,bin]))
                        outputfile.write("\t".join(s) + "\n")
                    outputfile.write("\n\n")
                    outputfile.flush()


class DailyObj(Stat):
    """Storage class for the amount of time spent around specific objects on a daily basis.

    dist24h.avg[light][patek/all][object][day] is a number between 0 and 1, indicating at what
    percentage was a patek/all pateks in the group (virtually) visible on a day
    (in that light condition, since experiment start) at (on/under) a given object.

    Object locations and closeness thresholds are defined in stat.experiments.py

    .stv is num*(standard variance) = num*(standard deviation)^2 of the distribution
    .std is the standard deviation,
    .num is the number of frames taken into account in the statistic.

    """
    def __init__(self, good_light, object_types, max_day, id_count):
        """Initialize with zero elements.

        :param id_count: Number of IDs (pateks)

        """
        #: version of the current structure. Change it every time something
        #: changes in the definition of the statistics, to see whether some
        #: already calculated data is old or not.
        #: version 0: first attempt
        #: version 1: light introduced (2013.09.25.)
        #: version 1b: absgrad introduced (to sum only) (2014.09.13.)
        #:            note that filter_for_valid_cage is not needed here,
        #:            since object definitions contain this check inherently
        self.version = 1
        #: number of files that are parsed into this statistic
        self.files = 0
        #: number of frames that were used to gather info for the statistic
        self.frames = dict()
        #: number of data points in the statistic
        self.points = dict()
        #: the main data of the statistic: [light]
        self.avg = dict()
        self.stv = dict()
        self.num = dict()
        # initialize data
        for light in good_light:
            #: one bin for all days, all objects, all colorids + group sum
            self.avg[light] = numpy.zeros(( \
                    id_count+1,
                    len(object_types),
                    max_day),
                    dtype=numpy.float)
            #: one bin for all days, all objects, all colorids + group sum
            self.stv[light] = numpy.zeros(( \
                    id_count+1,
                    len(object_types),
                    max_day),
                    dtype=numpy.float)
            #: one bin for all days, all objects, all colorids + group sum
            self.num[light] = numpy.zeros(( \
                    id_count+1, # note that num is the same for all IDs, but matrix manipulation is simpler like this.
                    len(object_types),
                    max_day),
                    dtype=numpy.int)
            self.frames[light] = 0
            self.points[light] = 0


    def __add__(self, X):
        """Add another dailyobj object to self with the '+' and '+=' operators.

        :param X: object of the same class that is added to self

        Overloading is needed here because averages and standard deviations
        are not additive. But they can be combined for non overlapping
        sets as described here (Q = sigma^2 * N, where sigma = std, Q = stv):
        http://en.wikipedia.org/wiki/Standard_deviation#Combining_standard_deviations

        """
        self._check_version(X)
        for light in self.num.keys():
            # get combined values
            num = self.num[light] + X.num[light]
            avg = numpy.where(num != 0, (self.num[light] * self.avg[light] + X.num[light] * X.avg[light]) / num, 0)
            stv = numpy.where(num != 0, (self.stv[light] + X.stv[light]) +
                    (self.num[light] * X.num[light]) * ((self.avg[light] - X.avg[light])**2) / num, 0)
            # store them
            self.num[light] = num
            self.avg[light] = avg
            self.stv[light] = stv
            # store other variables
            self.points[light] += X.points[light]
            self.frames[light] += X.frames[light]
        self.files += X.files

        return self

    def calculate_group_sum(self, klist):
        """Calculate sum for the group and store it in the last k bin."""
        for light in self.num.keys():
            self.num[light][-1][:] = 0
            self.avg[light][-1][:] = 0
            self.stv[light][-1][:] = 0
            for k in klist:
                num = self.num[light][-1] + self.num[light][k]
                avg = numpy.where(num != 0, (self.num[light][-1] * self.avg[light][-1] + self.num[light][k] * self.avg[light][k]) / num, 0)
                stv = numpy.where(num != 0, (self.stv[light][-1] + self.stv[light][k]) +
                        (self.num[light][-1] * self.num[light][k]) * ((self.avg[light][-1] - self.avg[light][k])**2) / num, 0)
                # store them
                self.num[light][-1] = num
                self.avg[light][-1] = avg
                self.stv[light][-1] = stv
                # assuming that this is already defined...
                self.std[light][-1] = numpy.where(self.num[light][-1] != 0, numpy.sqrt(self.stv[light][-1] / self.num[light][-1]), 0)

    def print_status(self):
        """Prints status info about the data to standard output."""
        self._print_status__light()

    def write_results(self, outputfile, project_settings, exps, exp):
        """Saves the contents of self to a file (possibly as a summarized stat).

        :param outputfile: file object where the results are written
        :param project_settings: global project settings imported by
                trajognize.settings.import_trajognize_settings_from_file()
        :param exps: experiment database created by project_settings
        :param exp: name of the current experiment

        """

        colorids = project_settings.colorids
        # do not save common results for all experiments,
        # since day is calculated from the beginning of each experiment...
        if exp == "all": return
        # calculate standard deviation from standard variance
        self.std = dict()
        for light in project_settings.good_light:
            self.std[light] = numpy.where(self.num[light] != 0, numpy.sqrt(self.stv[light] / self.num[light]), 0)
        # calculate max number of days in the given experiment
        maxday = experiments.get_days_since_start(exps[exp], exps[exp]['stop'])
        dayoffset = experiments.get_day_offset(exps[exp])
        # write results
        for group in exps[exp]['groups']:
            # get sorted names and colorid indices
            allnames = [colorids[k] for k in range(len(colorids))]
            names = sorted(exps[exp]['groups'][group])
            klist = [allnames.index(name) for name in names]
            # calculate group sum
            self.calculate_group_sum(klist)
            # write results
            for light in project_settings.good_light:
                for obi in range(len(project_settings.object_types)):
                    obj = project_settings.object_types[obi] # hehe
                    outputfile.write("# Daily amount of time (%s) around '%s' from %d files, %d frames, %d points\n" %
                            (light.lower(), obj, self.files, self.frames[light], self.points[light]))
                    outputfile.write("# Day number is calculated from the beginning of the given experiment.\n")
                    outputfile.write("# IDs are ordered alphabetically.\n")
                    outputfile.write("# this is group %s\n\n" % group)
                    # write header
                    s = ["dailyobj_%s_%s_group_%s" % (light.lower(), obj, group)]
                    for name in names:
                        s.append("%s_avg\t%s_std" % (name, name))
                    s.append("all_avg\tall_std\tall_num\tabsgrad_avg\tabsgrad_std")
                    outputfile.write("\t".join(s) + "\n")
                    # write all days
                    for day in range(maxday + 1):
                        s = ["%d" % day]
                        absgrad = []
                        for k in klist:
                            s.append("%g\t%g" % (self.avg[light][k,obi,day+dayoffset], self.std[light][k,obi,day+dayoffset]))
                            if day:
                                absgrad.append(abs(self.avg[light][k,obi,day+dayoffset] - self.avg[light][k,obi,day+dayoffset-1]))
                            else:
                                absgrad.append(abs(self.avg[light][k,obi,day+dayoffset] - 0))
                        s.append("%g\t%g\t%d" % (self.avg[light][-1,obi,day+dayoffset], self.std[light][-1,obi,day+dayoffset], self.num[light][-1,obi,day+dayoffset]))
                        s.append("%g\t%g" % (numpy.mean(absgrad), numpy.std(absgrad)))
                        outputfile.write("\t".join(s) + "\n")
                    outputfile.write("\n\n")
            outputfile.flush()


class SameIDDist(Stat):
    """Storage class for sameid number distributions.

    This stat is a debug stat. Final output contains 1 chosen only...

    sameiddist.data[light][patek/all][deleted/notdeleted][numsameid] is the number
    of frames when a given patek was visible numsameid times simultanelously
    in the given light condition. Two statistics are given for including/excluding
    deleted barcodes.

    """
    def __init__(self, good_light, id_count):
        """Initialize with zero elements.

        :param id_count: Number of IDs (pateks)

        """
        #: version of the current structure. Change it every time something
        #: changes in the definition of the statistics, to see whether some
        #: already calculated data is old or not.
        #: version 0: first attempt
        #: version 1: entrytimes are checked and skipped
        self.version = 1
        #: number of files that are parsed into this statistic
        self.files = 0
        #: number of frames that were used to gather info for the statistic
        self.frames = dict()
        #: number of data points in the statistic
        self.points = dict()
        #: maximum number of simultaneous ids to detect
        self.max_same_id = 200
        #: the main data of the statistic: [light][patek/all][deleted/notdeleted][numsameid]
        self.data = dict()
        # initialize data
        for light in good_light:
            self.data[light] = numpy.zeros(( \
                    id_count+1,
                    2,
                    self.max_same_id + 1),
                    dtype=numpy.int)
            self.points[light] = [0, 0] # [deleted, notdeleted]
            self.frames[light] = 0

    def __add__(self, X):
        """Add another sameiddist object of the same class to self with the '+' and '+=' operators.

        :param X: object of the same class that is added to self

        Overloading original method because the redefinition of points.

        """
        self._check_version(X)
        for light in self.data.keys():
            self.data[light] += X.data[light]
            self.frames[light] += X.frames[light]
            self.points[light][0] += X.points[light][0]
            self.points[light][1] += X.points[light][1]
        self.files += X.files

        return self

    def print_status(self):
        """Prints status info about the data to standard output."""
        for light in self.points.keys():
            print("  %s statistic is from %d files, %d frames and %d/%d data points (including/excluding deleted)" % \
                    (light, self.files, self.frames[light], self.points[light][0], self.points[light][1]))

    def write_results(self, outputfile, project_settings):
        """Saves the contents of self to a file (possibly as a summarized stat).

        :param outputfile: file object where the results are written
        :param project_settings: global project settings imported by
                trajognize.settings.import_trajognize_settings_from_file()

        """
        colorids = project_settings.colorids
        for light in project_settings.good_light:
            for deleted in range(2):
                outputfile.write("# same id distribution of %s barcodes from %d files, %d frames, %d points (%s)\n\n" % \
                        (light.lower(), self.files, self.frames[light], self.points[light][deleted],
                        "including MFix.DELETED" if deleted == 0 else "only valid"))
                # write header
                names = [colorids[k] for k in range(len(colorids))]
                names.append("all")
                outputfile.write("sameiddists_%s_%s" % (light.lower(),
                        "withdeleted" if deleted == 0 else "onlyvalid"))
                for name in names:
                    outputfile.write("\t%s" % name)
                outputfile.write("\n")
                # write data
                for i in range(self.max_same_id+1):
                    outputfile.write("%d" %i)
                    for j in range(len(names)):
                        outputfile.write("\t%d" % self.data[light][j,deleted,i])
                    outputfile.write("\n")
                outputfile.write("\n\n")
        outputfile.flush()


class NearestNeighbor(Stat):
    """Storage class for nearest neighbor occurrence matrix.

    X.data[light][real/virtual/any][i][j] is the number of frames
    where patek j is nearest neighbor of patek i in the given light condition.

    real is when both are real
    virtual is when both are virtual
    any is when there is no check on real/virtual state

    """
    def __init__(self, good_light, id_count):
        """Initialize with zero elements.

        :param id_count: Number of IDs (pateks)

        """
        #: version of the current structure. Change it every time something
        #: changes in the definition of the statistics, to see whether some
        #: already calculated data is old or not.
        #: version 0: first attempt
        #: version 1: cage wall check implemented
        #: version 2: entrytimes are checked and skipped
        #: version 3: real/virtual/any is introduced
        #: version 4: filter_for_valid_cage introduced (2015.04.30.)
        self.version = 4
        #: number of files that are parsed into this statistic
        self.files = 0
        #: number of frames that were used to gather info for the statistic
        self.frames = dict()
        #: number of data points in the statistic
        self.points = dict()
        #: the main data of the statistic: [light][id_from][id_to]
        self.data = dict()
        # initialize data
        for light in good_light:
            self.data[light] = numpy.zeros(( \
                    3, # bothreal=0/bothvirtual=1/any=2
                    id_count,
                    id_count),
                    dtype=numpy.int)
            self.frames[light] = 0
            self.points[light] = 0

    def write_results(self, outputfile, project_settings, exps, exp):
        """Saves the contents of self to a file (possibly as a summarized stat).

        String IDs are ordered alphabetically.
        Other orders should be calculated with the plot/calc submodules.

        :param outputfile: file object where the results are written
        :param project_settings: global project settings imported by
                trajognize.settings.import_trajognize_settings_from_file()
        :param exps: experiment database created by project_settings
        :param exp: name of the current experiment

        """
        colorids = project_settings.colorids
        realvirtany = ["real", "virtual", "any"]
        if exp == "all":
            for light in project_settings.good_light:
                for rva in range(len(realvirtany)):
                    outputfile.write("# nearest neighbor distribution of %s barcodes from %d files, %d frames, %d points\n" %
                            (light.lower(), self.files, self.frames[light], self.points[light]))
                    outputfile.write("# X[row][col] = number of frames when patek [col] is the nearest neighbor of patek [row].\n")
                    outputfile.write("# real is when both pateks are real, virtual is when both are virtual, any is when it doesn't matter\n")
                    outputfile.write("# filter_for_valid_cage=%s\n" % str(project_settings.filter_for_valid_cage))
                    outputfile.write("# IDs are ordered alphabetically.\n\n")
                    # write header
                    names = [colorids[k] for k in range(len(colorids))]
                    si = sorted(list(range(len(names))), key=cmp_to_key(lambda x, y: -1 if names[x] < names[y] else 1 if names[x] > names[y] else 0))
                    outputfile.write("nearestneighbor_%s_%s" % (light.lower(), realvirtany[rva]))
                    for i in range(len(si)):
                        outputfile.write("\t%s" % names[si[i]])
                    outputfile.write("\n")
                    # write data
                    for i in range(len(si)):
                        outputfile.write(names[si[i]])
                        for j in range(len(si)):
                            outputfile.write("\t%d" % self.data[light][rva][si[i],si[j]])
                        outputfile.write("\n")
                    outputfile.write("\n\n")
            outputfile.flush()
        else:
            for light in project_settings.good_light:
                for group in exps[exp]['groups']:
                    for rva in range(len(realvirtany)):
                        outputfile.write("# nearest neighbor distribution of %s barcodes from %d files, %d frames, %d points\n" %
                                (light.lower(), self.files, self.frames[light], self.points[light]))
                        outputfile.write("# X[row][col] = number of frames when patek [col] is the nearest neighbor of patek [row].\n")
                        outputfile.write("# real is when both pateks are real, virtual is when both are virtual, any is when it doesn't matter\n")
                        outputfile.write("# filter_for_valid_cage=%s\n" % str(project_settings.filter_for_valid_cage))
                        outputfile.write("# IDs are ordered alphabetically.\n")
                        outputfile.write("# this is group %s\n\n" % group)
                        # write header
                        names = exps[exp]['groups'][group]
                        si = sorted(list(range(len(names))), key=cmp_to_key(lambda x, y: -1 if names[x] < names[y] else 1 if names[x] > names[y] else 0))
                        allnames = [colorids[k] for k in range(len(colorids))]
                        outputfile.write("nearestneighbor_%s_%s_group_%s" % (light.lower(), realvirtany[rva], group))
                        for i in range(len(si)):
                            outputfile.write("\t%s" % names[si[i]])
                        outputfile.write("\n")
                        # write data
                        for i in range(len(si)):
                            outputfile.write(names[si[i]])
                            for j in range(len(si)):
                                outputfile.write("\t%d" % self.data[light][rva][allnames.index(names[si[i]]),allnames.index(names[si[j]])])
                            outputfile.write("\n")
                        outputfile.write("\n\n")
            outputfile.flush()


class Neighbor(Stat):
    """Storage class for neighbor distribution matrices and number of neighbours
    on a daily basis.

    X.data[light][0/1][day][i][j/n] is the number of frames
    where patek-j / n-pateks is neighbor of patek i in the given light condition
    on the given day.

    Being a neighbor is defined by a proper distance threshold.

    """
    def __init__(self, good_light, max_day, id_count):
        """Initialize with zero elements.

        :param id_count: Number of IDs (pateks)

        """
        #: version of the current structure. Change it every time something
        #: changes in the definition of the statistics, to see whether some
        #: already calculated data is old or not.
        #: version 0: first attempt, inherited from NearestNeighbor
        #: version 1: filter_for_valid_cage introduced (2015.04.30.)
        self.version = 1
        #:
        self.distance_threshold = 150 # [px] = 20 cm
        #: number of files that are parsed into this statistic
        self.files = 0
        #: number of frames that were used to gather info for the statistic
        self.frames = dict()
        #: number of data points in the statistic
        self.points = dict()
        #: the main data of the statistic: [light][0/1][day][id_from][id_to / n]
        self.data = dict()
        # initialize data
        for light in good_light:
            self.data[light] = numpy.zeros(( \
                    2, # 0: j (network), 1: n (number)
                    max_day,
                    id_count,
                    id_count),
                    dtype=numpy.int)
            self.frames[light] = 0
            self.points[light] = 0

    def write_results(self, outputfile, project_settings, exps, exp):
        """Saves the contents of self to a file (possibly as a summarized stat).

        String IDs are ordered alphabetically.
        Other orders should be calculated with the plot/calc submodules.

        :param outputfile: file object where the results are written
        :param project_settings: global project settings imported by
                trajognize.settings.import_trajognize_settings_from_file()
        :param exps: experiment database created by project_settings
        :param exp: name of the current experiment

        TODO: save results on a daily basis

        """
        colorids = project_settings.colorids
        if exp == "all": return
        for light in project_settings.good_light:
            outputfile.write("# neighbor networks of %s barcodes from %d files, %d frames, %d points\n" %
                    (light.lower(), self.files, self.frames[light], self.points[light]))
            outputfile.write("# network-type output: X[row][col] = number of frames when patek [col] is neighbor of patek [row].\n")
            outputfile.write("# number-type output: X[row][col] = number of frames when patek [col] has [row] neighbors.\n")
            outputfile.write("# distance threshold for being neighbors: %d pixels\n" % self.distance_threshold)
            outputfile.write("# filter_for_valid_cage=%s\n" % str(project_settings.filter_for_valid_cage))
            outputfile.write("# IDs are ordered alphabetically.\n\n")
            for group in exps[exp]['groups']:
                for nn, networknumber in enumerate(['network', 'number']):
                    # write header
                    names = exps[exp]['groups'][group]
                    si = sorted(list(range(len(names))), key=cmp_to_key(lambda x, y: -1 if names[x] < names[y] else 1 if names[x] > names[y] else 0))
                    allnames = [colorids[k] for k in range(len(colorids))]
                    outputfile.write("neighbor_%s_%s_group_%s" % (networknumber, light.lower(), group))
                    for i in range(len(si)):
                        outputfile.write("\t%s" % names[si[i]])
                    outputfile.write("\n")
                    # write data
                    # TODO: so far we only export allday results.
                    #       integrate this if daily output is needed:
                    #       dayoffset = experiments.get_day_offset(exps[exp])
                    x = sum(self.data[light][nn])
                    for i in range(len(si)):
                        if not nn:
                            outputfile.write(names[si[i]])
                            for j in range(len(si)):
                                outputfile.write("\t%d" % x[allnames.index(names[si[i]]),allnames.index(names[si[j]])])
                        else:
                            outputfile.write("%d" % i)
                            for j in range(len(si)):
                                outputfile.write("\t%d" % x[allnames.index(names[si[j]]), i])
                        outputfile.write("\n")
                    outputfile.write("\n\n")
        outputfile.flush()


class FQObj(Stat):
    """Storage class for generalized FQ matrix, i.e. pairwise OR norm
    over/queuing object relations.

    X.fandq[light][object][i][j] is the amount of frames when patek i is over
    an object while patek j is queuing it in the given light condition.

    Output is normalized with
    X.qorq[light][object][i][j], the total number of frames when patek i or j was
    around the object (on it or queuing) in the given light condition.

    Queuing is applicable only with orientation towards object center (+- 90 deg)

    """
    def __init__(self, good_light, object_types, id_count):
        """Initialize with zero elements.

        :param good_light(List[str]): list of good light types
        :param id_count: Number of IDs (pateks)

        """
        #: version of the current structure. Change it every time something
        #: changes in the definition of the statistics, to see whether some
        #: already calculated data is old or not.
        #: version 0: first attempt
        #: version 1: serious bugfix, + operator fixed, normalization is fine now
        #: version 2: light introduced (2013.09.25.)
        #:            note that filter_for_valid_cage is not needed here,
        #:            since object definitions contain this check inherently
        self.version = 2
        #: number of files that are parsed into this statistic
        self.files = 0
        #: number of frames that were used to gather info for the statistic
        self.frames = dict()
        #: number of data points in the statistic
        self.points = dict()
        #: the main data of the statistic: [object][id_from][id_to]
        #: represents number of frames
        self.fandq = dict()
        self.qorq = dict()
        for light in good_light:
            self.fandq[light] = numpy.zeros(( \
                    len(object_types),
                    id_count,
                    id_count),
                    dtype=numpy.float)
            #: represents number of frames when i or j was queuing (or feeding)
            self.qorq[light] = numpy.zeros(( \
                    len(object_types),
                    id_count,
                    id_count),
                    dtype=numpy.float)
            self.frames[light] = 0
            self.points[light] = 0

    def __add__(self, X):
        """Add another fqobj object to self with the '+' and '+=' operators."""
        self._check_version(X)
        for light in self.fandq.keys():
            self.fandq[light] += X.fandq[light]
            self.qorq[light] += X.qorq[light]
            self.frames[light] += X.frames[light]
            self.points[light] += X.points[light]
        self.files += X.files
        return self

    def print_status(self):
        """Prints status info about the data to standard output."""
        self._print_status__light()

    def write_results(self, outputfile, project_settings, exps, exp):
        """Saves the contents of self to a file (possibly as a summarized stat).

        String IDs are ordered alphabetically.
        Other orders should be calculated with the plot/calc submodules.

        :param outputfile: file object where the results are written
        :param project_settings: global project settings imported by
                trajognize.settings.import_trajognize_settings_from_file()
        :param exps: experiment database created by project_settings
        :param exp: name of the current experiment

        """
        colorids = project_settings.colorids
        # write it
        for light in project_settings.good_light:
            # OR normalize results
            ornormdata = numpy.where(self.qorq[light] > 0, self.fandq[light] / self.qorq[light], 0)
            if exp == "all":
                for obi in range(len(project_settings.object_types)):
                    obj = project_settings.object_types[obi] # hehe
                    # skip not queueable objects
                    if not experiments.is_object_queueable(project_settings.object_queuing_areas[obj]): continue
                    outputfile.write("# FQ_%s distribution of %s barcodes from %d files, %d frames, %d points\n" %
                            (obj, light.lower(), self.files, self.frames[light], sum(sum(self.fandq[light][obi]))))
                    outputfile.write("# X[row][col] = OR normalized generalized FQ value of patek [row] and [col],\n")
                    outputfile.write("# i.e. amount of [row] over %s while [col] queuing it.\n" % obj)
                    outputfile.write("# Queuing is applicable only with orientation towards %s obj center (+- 90 deg)\n" % obj)
                    outputfile.write("# IDs are ordered alphabetically.\n\n")
                    # write header
                    names = [colorids[k] for k in range(len(colorids))]
                    si = sorted(list(range(len(names))), key=cmp_to_key(lambda x, y: -1 if names[x] < names[y] else 1 if names[x] > names[y] else 0))
                    outputfile.write("fqobj_%s_%s" % (light.lower(), obj))
                    for i in range(len(si)):
                        outputfile.write("\t%s" % names[si[i]])
                    outputfile.write("\n")
                    # write data
                    for i in range(len(si)):
                        outputfile.write(names[si[i]])
                        for j in range(len(si)):
                            outputfile.write("\t%g" % ornormdata[obi,si[i],si[j]])
                        outputfile.write("\n")
                    outputfile.write("\n\n")
                outputfile.flush()
            else:
                for obi in range(len(project_settings.object_types)):
                    obj = project_settings.object_types[obi] # hehe
                    # skip not relevant and not queueable objects
                    if not experiments.is_object_queueable(project_settings.object_queuing_areas[obj]): continue
                    if obj not in exps[exp].keys(): continue
                    for group in exps[exp]['groups']:
                        outputfile.write("# FQ_%s distribution of %s barcodes from %d files, %d frames, %d points (including all groups)\n" %
                                (obj, light.lower(), self.files, self.frames[light], sum(sum(self.fandq[light][obi]))))
                        outputfile.write("# X[row][col] = OR normalized generalized FQ value of patek [row] and [col],\n")
                        outputfile.write("# i.e. amount of [row] over %s while [col] queuing it.\n" % obj)
                        outputfile.write("# Queuing is applicable only with orientation towards %s center (+- 90 deg)\n" % obj)
                        outputfile.write("# IDs are ordered alphabetically.\n")
                        outputfile.write("# this is group %s\n\n" % group)
                        # write header
                        names = exps[exp]['groups'][group]
                        si = sorted(list(range(len(names))), key=cmp_to_key(lambda x, y: -1 if names[x] < names[y] else 1 if names[x] > names[y] else 0))
                        allnames = [colorids[k] for k in range(len(colorids))]
                        outputfile.write("fqobj_%s_%s_group_%s" % (light.lower(), obj, group))
                        for i in range(len(si)):
                            outputfile.write("\t%s" % names[si[i]])
                        outputfile.write("\n")
                        # write data
                        for i in range(len(si)):
                            outputfile.write(names[si[i]])
                            for j in range(len(si)):
                                outputfile.write("\t%g" % ornormdata[obi,allnames.index(names[si[i]]),allnames.index(names[si[j]])])
                            outputfile.write("\n")
                        outputfile.write("\n\n")
                outputfile.flush()


class DailyFQObj(Stat):
    """Storage class for generalized FQ matrix, i.e. pairwise OR norm
    over/queuing object relations on a daily basis.

    X.fandq[light][object][i][j] is the amount of frames when patek i is over
    an object while patek j is queuing it in a given light condition.

    Output is normalized with
    X.qorq[light][object][i][j], the total number of frames when patek i or j was
    around the object (on it or queuing) in the given light condition.

    Queuing is applicable only with orientation towards object center (+- 90 deg)

    """
    def __init__(self, good_light, object_types, max_day, id_count):
        """Initialize with zero elements.

        :param id_count: Number of IDs (pateks)

        """
        #: version of the current structure. Change it every time something
        #: changes in the definition of the statistics, to see whether some
        #: already calculated data is old or not.
        #: version 0: first attempt, inherited from fqobj version 1
        #: version 1: light introduced (2013.09.25.)
        #:            note that filter_for_valid_cage is not needed here,
        #:            since object definitions contain this check inherently
        self.version = 1
        #: number of days to average with moving window
        self.dayavg = 3 # days
        #: number of files that are parsed into this statistic
        self.files = 0
        #: number of frames that were used to gather info for the statistic
        self.frames = dict()
        #: number of data points in the statistic
        self.points = dict()
        #: the main data of the statistic: [day][object][id_from][id_to]
        #: represents number of frames
        self.fandq = dict()
        self.qorq = dict()
        for light in good_light:
            self.fandq[light] = numpy.zeros(( \
                    len(object_types),
                    id_count,
                    id_count,
                    max_day),
                    dtype=numpy.float)
            #: represents number of frames when i or j was queuing (or feeding)
            self.qorq[light] = numpy.zeros(( \
                    len(object_types),
                    id_count,
                    id_count,
                    max_day),
                    dtype=numpy.float)
            self.frames[light] = 0
            self.points[light] = 0

    def __add__(self, X):
        """Add another fqobj object to self with the '+' and '+=' operators."""
        self._check_version(X)
        for light in self.fandq.keys():
            self.fandq[light] += X.fandq[light]
            self.qorq[light] += X.qorq[light]
            self.frames[light] += X.frames[light]
            self.points[light] += X.points[light]
        self.files += X.files
        return self

    def print_status(self):
        """Prints status info about the data to standard output."""
        self._print_status__light()

    def write_results(self, outputfile, project_settings, exps, exp):
        """Saves the contents of self to a file (possibly as a summarized stat).

        String IDs are ordered alphabetically.
        Other orders should be calculated with the plot/calc submodules.

        :param outputfile: file object where the results are written
        :param project_settings: global project settings imported by
                trajognize.settings.import_trajognize_settings_from_file()
        :param exps: experiment database created by project_settings
        :param exp: name of the current experiment

        """
        colorids = project_settings.colorids
        def writedata(datatype, data):
            """Helper function."""
            # write header
            outputfile.write("%s_%s_%s_group_%s_day_%d" % (datatype, light.lower(), obj, group, day))
            for i in range(len(si)):
                outputfile.write("\t%s" % names[si[i]])
            outputfile.write("\n")
            # write data
            for i in range(len(si)):
                outputfile.write(names[si[i]])
                for j in range(len(si)):
                    outputfile.write("\t%g" % data[obi,allnames.index(names[si[i]]),allnames.index(names[si[j]]),day+dayoffset])
                outputfile.write("\n")
            outputfile.write("\n\n")

        # do not save common results for all experiments,
        # since day is calculated from the beginning of each experiment...
        if exp == "all": return
        # calculate max number of days in the given experiment
        maxday = experiments.get_days_since_start(exps[exp], exps[exp]['stop'])
        dayoffset = experiments.get_day_offset(exps[exp])

        for light in project_settings.good_light:
            # calculate cumulative results
            cumulqorq = numpy.copy(self.qorq[light])
            cumulfandq = numpy.copy(self.fandq[light])
            movavgqorq = numpy.copy(self.qorq[light])
            movavgfandq = numpy.copy(self.fandq[light])

            # calculate cumulative and moving average data
            for obi in range(len(project_settings.object_types)):
                for i in range(len(colorids)):
                    for j in range(len(colorids)):
                        for day in range(1, maxday + 1):
                            cumulqorq[obi,i,j,day+dayoffset] += cumulqorq[obi,i,j,day+dayoffset-1]
                            cumulfandq[obi,i,j,day+dayoffset] += cumulfandq[obi,i,j,day+dayoffset-1]
                            movavgqorq[obi,i,j,day+dayoffset] = sum(self.qorq[light][obi,i,j,max(0, day+dayoffset - self.dayavg + 1):day+dayoffset + 1])
                            movavgfandq[obi,i,j,day+dayoffset] = sum(self.fandq[light][obi,i,j,max(0, day+dayoffset - self.dayavg + 1):day+dayoffset + 1])

            # OR normalize results
            ornormdata = numpy.where(self.qorq[light] > 0, self.fandq[light] / self.qorq[light], 0)
            cumuldata = numpy.where(cumulqorq > 0, cumulfandq / cumulqorq, 0)
            movavgdata = numpy.where(movavgqorq > 0, movavgfandq / movavgqorq, 0)

            # write it
            for obi in range(len(project_settings.object_types)):
                obj = project_settings.object_types[obi] # hehe
                # skip not relevant and not queueable objects
                if not experiments.is_object_queueable(project_settings.object_queuing_areas[obj]): continue
                if obj not in exps[exp].keys(): continue
                for group in exps[exp]['groups']:
                    outputfile.write("# Daily FQ_%s distribution of %s barcodes from %d files, %d frames, %d points (including all groups and all days)\n" %
                            (obj, light.lower(), self.files, self.frames[light], sum(sum(sum(self.fandq[light][obi])))))
                    outputfile.write("# X[row][col] = OR normalized generalized FQ value of patek [row] and [col],\n")
                    outputfile.write("# i.e. amount of [row] over %s while [col] queuing it.\n" % obj)
                    outputfile.write("# Queuing is applicable only with orientation towards %s center (+- 90 deg)\n" % obj)
                    outputfile.write("# IDs are ordered alphabetically.\n")
                    outputfile.write("# this is group %s, all days since start of experiment are listed separately below.\n" % group)
                    outputfile.write("# cumulative results are also written as cumulfqobj_*\n")
                    outputfile.write("# %d-day moving average results are also written as movavgfqobj_*\n\n" % self.dayavg)
                    # prepare IDs and header
                    names = exps[exp]['groups'][group]
                    si = sorted(list(range(len(names))), key=cmp_to_key(lambda x, y: -1 if names[x] < names[y] else 1 if names[x] > names[y] else 0))
                    allnames = [colorids[k] for k in range(len(colorids))]
                    for day in range(maxday + 1):
                        # daily results
                        writedata("dailyfqobj", ornormdata)
                        # moving average results
                        writedata("movavgfqobj", movavgdata)
                        # cumulative results
                        writedata("cumulfqobj", cumuldata)
            outputfile.flush()


class FQFood(Stat):
    """Storage class for the real FQ matrix, i.e. pairwise OR norm
    over/queuing relations, restricted to the time of feeding.

    X.fandq[light][i][j] is the amount of frames when patek i is feeding
    while patek j is queuing it in the given light condition.

    Output is normalized with
    X.qorq[light][i][j], the total number of frames when patek i or j was
    around the feeding area (on it or queuing) in the given light condition.

    Queuing is applicable only with orientation towards object center (+- 90 deg)

    """
    def __init__(self, good_light, id_count):
        """Initialize with zero elements.

        :param id_count: Number of IDs (pateks)

        """
        #: version of the current structure. Change it every time something
        #: changes in the definition of the statistics, to see whether some
        #: already calculated data is old or not.
        #: version 0: inherited from generalized fqobj version 2 (2013.11.22.)
        #: version 1: serious bug corrected: only 'food' object is calculated (2014.06.02.)
        #:            note that filter_for_valid_cage is not needed here,
        #:            since object definitions contain this check inherently
        self.version = 1
        #: number of files that are parsed into this statistic
        self.files = 0
        #: number of frames that were used to gather info for the statistic
        self.frames = dict()
        #: number of data points in the statistic
        self.points = dict()
        #: the main data of the statistic: [object][id_from][id_to]
        #: represents number of frames
        self.fandq = dict()
        self.qorq = dict()
        for light in good_light:
            self.fandq[light] = numpy.zeros(( \
                    id_count,
                    id_count),
                    dtype=numpy.float)
            #: represents number of frames when i or j was queuing (or feeding)
            self.qorq[light] = numpy.zeros(( \
                    id_count,
                    id_count),
                    dtype=numpy.float)
            self.frames[light] = 0
            self.points[light] = 0

    def __add__(self, X):
        """Add another fqfood object to self with the '+' and '+=' operators."""
        self._check_version(X)
        for light in self.fandq.keys():
            self.fandq[light] += X.fandq[light]
            self.qorq[light] += X.qorq[light]
            self.frames[light] += X.frames[light]
            self.points[light] += X.points[light]
        self.files += X.files
        return self

    def print_status(self):
        """Prints status info about the data to standard output."""
        self._print_status__light()

    def write_results(self, outputfile, project_settings, exps, exp):
        """Saves the contents of self to a file (possibly as a summarized stat).

        String IDs are ordered alphabetically.
        Other orders should be calculated with the plot/calc submodules.

        :param outputfile: file object where the results are written
        :param project_settings: global project settings imported by
                trajognize.settings.import_trajognize_settings_from_file()
        :param exps: experiment database created by project_settings
        :param exp: name of the current experiment

        """
        colorids = project_settings.colorids
        # write it
        for light in project_settings.good_light:
            # OR normalize results
            ornormdata = numpy.where(self.qorq[light] > 0, self.fandq[light] / self.qorq[light], 0)
            if exp == "all":
                outputfile.write("# FQfood distribution of %s barcodes from %d files, %d frames, %d points\n" %
                        (light.lower(), self.files, self.frames[light], sum(sum(self.fandq[light]))))
                outputfile.write("# X[row][col] = OR normalized FQ value of patek [row] and [col],\n")
                outputfile.write("# i.e. amount of [row] feeding while [col] queuing.\n")
                outputfile.write("# Queuing is applicable only with orientation towards feeding center (+- 90 deg)\n")
                outputfile.write("# Statistic is restricted to real feeding times, no friday\n")
                outputfile.write("# IDs are ordered alphabetically.\n\n")
                # write header
                names = [colorids[k] for k in range(len(colorids))]
                si = sorted(list(range(len(names))), key=cmp_to_key(lambda x, y: -1 if names[x] < names[y] else 1 if names[x] > names[y] else 0))
                outputfile.write("fqfood_%s" % light.lower())
                for i in range(len(si)):
                    outputfile.write("\t%s" % names[si[i]])
                outputfile.write("\n")
                # write data
                for i in range(len(si)):
                    outputfile.write(names[si[i]])
                    for j in range(len(si)):
                        outputfile.write("\t%g" % ornormdata[si[i],si[j]])
                    outputfile.write("\n")
                outputfile.write("\n\n")
            else:
                for group in exps[exp]['groups']:
                    outputfile.write("# FQfood distribution of %s barcodes from %d files, %d frames, %d points (including all groups)\n" %
                            (light.lower(), self.files, self.frames[light], sum(sum(self.fandq[light]))))
                    outputfile.write("# X[row][col] = OR normalized generalized FQ value of patek [row] and [col],\n")
                    outputfile.write("# i.e. amount of [row] feeding while [col] queuing.\n")
                    outputfile.write("# Queuing is applicable only with orientation towards feeding center (+- 90 deg)\n")
                    outputfile.write("# Statistic is restricted to real feeding times, no friday\n")
                    outputfile.write("# IDs are ordered alphabetically.\n")
                    outputfile.write("# this is group %s\n\n" % group)
                    # write header
                    names = exps[exp]['groups'][group]
                    si = sorted(list(range(len(names))), key=cmp_to_key(lambda x, y: -1 if names[x] < names[y] else 1 if names[x] > names[y] else 0))
                    allnames = [colorids[k] for k in range(len(colorids))]
                    outputfile.write("fqfood_%s_group_%s" % (light.lower(), group))
                    for i in range(len(si)):
                        outputfile.write("\t%s" % names[si[i]])
                    outputfile.write("\n")
                    # write data
                    for i in range(len(si)):
                        outputfile.write(names[si[i]])
                        for j in range(len(si)):
                            outputfile.write("\t%g" % ornormdata[allnames.index(names[si[i]]),allnames.index(names[si[j]])])
                        outputfile.write("\n")
                    outputfile.write("\n\n")


class FQWhileF(Stat):
    """Storage class for counting how many are feeding or queuing while one
    is feeding, restricted to the time of feeding, relative to any type of
    object (food, water, wheel, etc.)

    X.data[light][object][i][n] is the amount of frames when patek i is feeding
    while n other patek's are feeding or queuing in the given light condition,
    around a given object.

    Queuing is applicable only with orientation towards object center (+- 90 deg)

    """
    def __init__(self, good_light, object_types, id_count):
        """Initialize with zero elements.

        :param id_count: Number of IDs (pateks)

        """
        #: version of the current structure. Change it every time something
        #: changes in the definition of the statistics, to see whether some
        #: already calculated data is old or not.
        #: version 0: inherited from fqfood version 1 (2014.06.02.)
        #: version 1: geeralized to all objects (2014.06.04.)
        #:            note that filter_for_valid_cage is not needed here,
        #:            since object definitions contain this check inherently
        self.version = 1
        #: number of files that are parsed into this statistic
        self.files = 0
        #: number of frames that were used to gather info for the statistic
        self.frames = dict()
        #: number of data points in the statistic
        self.points = dict()
        #: the main data of the statistic: [object][id_from][id_to]
        #: represents number of frames
        self.data = dict()
        for light in good_light:
            self.data[light] = numpy.zeros(( \
                    len(object_types),
                    id_count,   # who is feeding
                    id_count),  # how many others are feeding or queuing
                    dtype=numpy.float)
            self.frames[light] = 0
            self.points[light] = 0

    def print_status(self):
        """Prints status info about the data to standard output."""
        self._print_status__light()

    def write_results(self, outputfile, project_settings, exps, exp):
        """Saves the contents of self to a file (possibly as a summarized stat).

        String IDs are ordered alphabetically.
        Other orders should be calculated with the plot/calc submodules.

        :param outputfile: file object where the results are written
        :param project_settings: global project settings imported by
                trajognize.settings.import_trajognize_settings_from_file()
        :param exps: experiment database created by project_settings
        :param exp: name of the current experiment

        """
        colorids = project_settings.colorids
        def weighted_avg_and_std(values, weights):
            """
            Return the weighted average and standard deviation.

            values, weights -- Numpy ndarrays with the same shape.
            """
            if not numpy.sum(weights):
                return (0, 0)
            average = numpy.average(values, weights=weights)
            variance = numpy.average((values-average)**2, weights=weights)  # Fast and numerically precise
            return (average, sqrt(variance))

        # write it
        for light in project_settings.good_light:
            if exp == "all":
                for obi in range(len(project_settings.object_types)):
                    obj = project_settings.object_types[obi] # hehe
                    # skip not queueable objects
                    if not experiments.is_object_queueable(project_settings.object_queuing_areas[obj]): continue
                    outputfile.write("# FQWhileF_%s distribution of %s barcodes from %d files, %d frames, %d points\n" %
                            (obj, light.lower(), self.files, self.frames[light], sum(sum(self.data[light][obi]))))
                    outputfile.write("# X[row][col] = number of frames when patek [col] is over %s obj and [row] pateks are ForQ-ing,\n" % obj)
                    outputfile.write("# Queuing is applicable only with orientation towards object center (+- 90 deg)\n")
                    outputfile.write("# In case of food, statistic is restricted to real feeding times, no friday\n")
                    outputfile.write("# IDs are ordered alphabetically.\n\n")
                    # write header
                    names = [colorids[k] for k in range(len(colorids))]
                    si = sorted(list(range(len(names))), key=cmp_to_key(lambda x, y: -1 if names[x] < names[y] else 1 if names[x] > names[y] else 0))
                    outputfile.write("fqwhilef_%s_%s" % (light.lower(), obj))
                    for i in range(len(si)):
                        outputfile.write("\t%s" % names[si[i]])
                    outputfile.write("\n")
                    # write data
                    for n in range(len(si)):
                        outputfile.write("%d" % n)
                        for i in range(len(si)):
                            outputfile.write("\t%g" % self.data[light][obi,si[i],n])
                        outputfile.write("\n")
                    # write average, standard deviation and number of frames per patek
                    avg = [0]*len(si)
                    std = [0]*len(si)
                    for i in range(len(si)):
                        avg[i], std[i] = weighted_avg_and_std(
                                range(len(self.data[light][obi,si[i]])),
                                self.data[light][obi,si[i]])
                    outputfile.write("avg")
                    for i in range(len(si)):
                        outputfile.write("\t%g" % avg[i])
                    outputfile.write("\n")
                    outputfile.write("std")
                    for i in range(len(si)):
                        outputfile.write("\t%g" % std[i])
                    outputfile.write("\n")
                    outputfile.write("num")
                    for i in range(len(si)):
                        outputfile.write("\t%g" % numpy.sum(self.data[light][obi,si[i]]))
                    outputfile.write("\n\n")
            else:
                for obi in range(len(project_settings.object_types)):
                    obj = project_settings.object_types[obi] # hehe
                    # skip non relevant and not queueable objects
                    if not experiments.is_object_queueable(project_settings.object_queuing_areas[obj]): continue
                    if obj not in exps[exp].keys(): continue
                    for group in exps[exp]['groups']:
                        outputfile.write("# FQWhileF_%s distribution of %s barcodes from %d files, %d frames, %d points (including all groups)\n" %
                                (obj, light.lower(), self.files, self.frames[light], sum(sum(self.data[light][obi]))))
                        outputfile.write("# X[row][col] = number of frames when patek [col] is over obj %s and [row] pateks are ForQ-ing,\n" % obj)
                        outputfile.write("# Queuing is applicable only with orientation towards object center (+- 90 deg)\n")
                        outputfile.write("# In case of food, statistic is restricted to real feeding times, no friday\n")
                        outputfile.write("# IDs are ordered alphabetically.\n")
                        outputfile.write("# this is group %s\n\n" % group)
                        # write header
                        names = exps[exp]['groups'][group]
                        si = sorted(list(range(len(names))), key=cmp_to_key(lambda x, y: -1 if names[x] < names[y] else 1 if names[x] > names[y] else 0))
                        allnames = [colorids[k] for k in range(len(colorids))]
                        outputfile.write("fqwhilef_%s_%s_group_%s" % (light.lower(), obj, group))
                        for i in range(len(si)):
                            outputfile.write("\t%s" % names[si[i]])
                        outputfile.write("\n")
                        # write data
                        for n in range(len(si)):
                            outputfile.write("%d" % n)
                            for i in range(len(si)):
                                outputfile.write("\t%g" % self.data[light][obi,allnames.index(names[si[i]]),n])
                            outputfile.write("\n")
                        # write average, standard deviation and number of frames per patek
                        avg = [0]*len(si)
                        std = [0]*len(si)
                        for i in range(len(si)):
                            avg[i], std[i] = weighted_avg_and_std(
                                    range(len(self.data[light][obi,allnames.index(names[si[i]])])),
                                    self.data[light][obi,allnames.index(names[si[i]])])
                        outputfile.write("avg")
                        for i in range(len(si)):
                            outputfile.write("\t%g" % avg[i])
                        outputfile.write("\n")
                        outputfile.write("std")
                        for i in range(len(si)):
                            outputfile.write("\t%g" % std[i])
                        outputfile.write("\n")
                        outputfile.write("num")
                        for i in range(len(si)):
                            outputfile.write("\t%g" % numpy.sum(self.data[light][obi,allnames.index(names[si[i]])]))
                        outputfile.write("\n\n")

class AA(Stat):
    """Storage class for AA (approach-aviodance) matrix.

    AA is defined for each pair of rats (i!=j) as the time-averaged dot product
    of i's velocity (v_i) and the direction from i to j (d_ij).
    We count AA events across all frames when i and j were within 40 cm (~200px)
    of each other and both i and j was moving at least 25 cm/s ~ 125 px/s = 5 px/frame
    and approacher points towards the avoider and avoider points away from approacher.
    AA_ij is positive if i tends to approach j and negative if i tends to avoid j.

    TODO: will work better on smoothed velocities, with less false positives.

    """
    def __init__(self, good_light, id_count, aa_settings):
        """Initialize with zero elements.

        :param id_count: Number of IDs (pateks)
        :param aa_settings: AASettings settings used for aa detection

        """
        #: version of the current structure. Change it every time something
        #: changes in the definition of the statistics, to see whether some
        #: already calculated data is old or not.
        #: version 0: first attempt
        #: version 1: velocity threshold for avoiding introduced as well
        #: version 2: angle thresholds and proper normalization introduced,
        #             therefore avg and stv not needed, we count events only!!!
        #: version 3: minimum event length introduced: events are only saved
        #             if they are long/continuous enough in time
        #             disable with min_event_length 1 (equal to version 2)
        #: version 4: minimum event count introduced to get e.g. 5/10 frames (2015.02.26.)
        #: version 5: filter_for_valid_cage introduced (2015.04.30.)
        #: version 6: settings moved to AASettings class (2018.07.26.)
        #: version 7: differentiate between appr. and avoider vel threshold
        #             and check approacher's forward motion
        self.version = 7
        #: thresholds, settings
        self.distance_threshold = aa_settings.distance_threshold
        self.approacher_velocity_threshold = aa_settings.approacher_velocity_threshold
        self.avoider_velocity_threshold = aa_settings.avoider_velocity_threshold
        self.min_event_count = aa_settings.min_event_count
        self.cos_approacher_threshold = aa_settings.cos_approacher_threshold
        self.cos_avoider_threshold = aa_settings.cos_avoider_threshold
        self.min_event_length = aa_settings.min_event_length
        #: number of files that are parsed into this statistic
        self.files = 0
        #: number of frames that were used to gather info for the statistic
        self.frames = dict()
        #: number of data points in the statistic
        self.points = dict()
        #: the main data of the statistic
        self.data = dict()
        # initialize data
        for light in good_light:
            self.data[light] = numpy.zeros(( \
                    id_count,
                    id_count),
                    dtype=numpy.int)
            self.frames[light] = 0
            self.points[light] = 0

    def print_status(self):
        """Prints status info about the data to standard output."""
        self._print_status__light()

    def write_results(self, outputfile, project_settings, exps, exp):
        """Saves the contents of self to a file (possibly as a summarized stat).

        String IDs are ordered alphabetically.
        Other orders should be calculated with the plot/calc submodules.

        :param outputfile: file object where the results are written
        :param project_settings: global project settings imported by
                trajognize.settings.import_trajognize_settings_from_file()
        :param exps: experiment database created by project_settings
        :param exp: name of the current experiment

        """
        colorids = project_settings.colorids
        # write output
        outputfile.write("# AA = <v_i(t)*d_ij(t)>_t, with the following threshold parameters:\n")
        outputfile.write("#   distance_threshold = %g px\n" % self.distance_threshold)
        outputfile.write("#   approacher_velocity_threshold = %g px/frame\n" % self.approacher_velocity_threshold)
        outputfile.write("#   avoider_velocity_threshold = %g px/frame\n" % self.avoider_velocity_threshold)
        outputfile.write("#   cos_approacher_threshold = %g\n" % self.cos_approacher_threshold)
        outputfile.write("#   cos_avoider_threshold = %g\n" % self.cos_avoider_threshold)
        outputfile.write("#   min_event_length = %g frames\n" % self.min_event_length)
        outputfile.write("#   min_event_count = %g\n\n\n" % self.min_event_count)
        if exp == "all":
            for light in project_settings.good_light:
                outputfile.write("# AA (approach-avoidance) distribution of %s barcodes from %d files, %d frames, %d points\n" %
                        (light.lower(), self.files, self.frames[light], self.points[light]))
                outputfile.write("# X[row][col] = number of frames when [row] was approaching while [col] was avoiding.\n")
                outputfile.write("# filter_for_valid_cage=%s\n" % str(project_settings.filter_for_valid_cage))
                outputfile.write("# IDs are ordered alphabetically.\n\n")
                # write header
                names = [colorids[k] for k in range(len(colorids))]
                si = sorted(list(range(len(names))), key=cmp_to_key(lambda x, y: -1 if names[x] < names[y] else 1 if names[x] > names[y] else 0))
                outputfile.write("aa_%s" % light.lower())
                for i in range(len(si)):
                    outputfile.write("\t%s" % names[si[i]])
                outputfile.write("\n")
                # write data
                for i in range(len(si)):
                    outputfile.write(names[si[i]])
                    for j in range(len(si)):
                        outputfile.write("\t%g" % self.data[light][si[i],si[j]])
                    outputfile.write("\n")
                outputfile.write("\n\n")
                outputfile.flush()
        else:
            for group in exps[exp]['groups']:
                for light in project_settings.good_light:
                    outputfile.write("# AA (approach-avoidance) distribution of %s barcodes from %d files, %d frames, %d points\n" %
                            (light.lower(), self.files, self.frames[light], self.points[light]))
                    outputfile.write("# X[row][col] = number of frames when [row] was approaching while [col] was avoiding.\n")
                    outputfile.write("# filter_for_valid_cage=%s\n" % str(project_settings.filter_for_valid_cage))
                    outputfile.write("# IDs are ordered alphabetically.\n")
                    outputfile.write("# this is group %s\n\n" % group)
                    # write header
                    names = exps[exp]['groups'][group]
                    si = sorted(list(range(len(names))), key=cmp_to_key(lambda x, y: -1 if names[x] < names[y] else 1 if names[x] > names[y] else 0))
                    allnames = [colorids[k] for k in range(len(colorids))]
                    outputfile.write("aa_%s_group_%s" % (light.lower(), group))
                    for i in range(len(si)):
                        outputfile.write("\t%s" % names[si[i]])
                    outputfile.write("\n")
                    # write data
                    for i in range(len(si)):
                        outputfile.write(names[si[i]])
                        for j in range(len(si)):
                            outputfile.write("\t%g" % self.data[light][allnames.index(names[si[i]]),allnames.index(names[si[j]])])
                        outputfile.write("\n")
                    outputfile.write("\n\n")
                    outputfile.flush()


class ButtHead(Stat):
    """Storage class for butthead occurrence matrix.

    X.data[light][i][j] is the number of frames
    where the head of patek i is close to the butt of patek j
    in the given light condition.

    """
    def __init__(self, good_light, id_count):
        """Initialize with zero elements.

        :param id_count: Number of IDs (pateks)

        """
        #: version of the current structure. Change it every time something
        #: changes in the definition of the statistics, to see whether some
        #: already calculated data is old or not.
        #: version 0: first attempt (2015.02.26.)
        #: version 1: filter_for_valid_cage introduced (2015.04.30.)
        self.version = 1
        #: thresholds
        self.patek_length = 100 # [px] = 20 cm
        self.cos_approacher_threshold = 0 # +-90 degrees
        #: number of files that are parsed into this statistic
        self.files = 0
        #: number of frames that were used to gather info for the statistic
        self.frames = dict()
        #: number of data points in the statistic
        self.points = dict()
        #: the main data of the statistic
        self.data = dict()
        # initialize data
        for light in good_light:
            self.data[light] = numpy.zeros(( \
                    id_count,
                    id_count),
                    dtype=numpy.int)
            self.frames[light] = 0
            self.points[light] = 0

    def print_status(self):
        """Prints status info about the data to standard output."""
        self._print_status__light()

    def write_results(self, outputfile, project_settings, exps, exp):
        """Saves the contents of self to a file (possibly as a summarized stat).

        String IDs are ordered alphabetically.
        Other orders should be calculated with the plot/calc submodules.

        :param outputfile: file object where the results are written
        :param project_settings: global project settings imported by
                trajognize.settings.import_trajognize_settings_from_file()
        :param exps: experiment database created by project_settings
        :param exp: name of the current experiment

        """
        colorids = project_settings.colorids
        if exp == "all":
            for light in project_settings.good_light:
                outputfile.write("# butthead distribution of %s barcodes from %d files, %d frames, %d points\n" %
                        (light.lower(), self.files, self.frames[light], self.points[light]))
                outputfile.write("# X[row][col] = number of frames when butt of patek [col] is close to head of patek [row].\n")
                outputfile.write("# IDs are ordered alphabetically.\n")
                outputfile.write("# filter_for_valid_cage=%s\n" % str(project_settings.filter_for_valid_cage))
                outputfile.write("# patek_length = %g px\n" % self.patek_length)
                outputfile.write("# cos_approacher_threshold = %g\n\n" % self.cos_approacher_threshold)
                # write header
                names = [colorids[k] for k in range(len(colorids))]
                si = sorted(list(range(len(names))), key=cmp_to_key(lambda x, y: -1 if names[x] < names[y] else 1 if names[x] > names[y] else 0))
                outputfile.write("butthead_%s" % light.lower())
                for i in range(len(si)):
                    outputfile.write("\t%s" % names[si[i]])
                outputfile.write("\n")
                # write data
                for i in range(len(si)):
                    outputfile.write(names[si[i]])
                    for j in range(len(si)):
                        outputfile.write("\t%d" % self.data[light][si[i],si[j]])
                    outputfile.write("\n")
                outputfile.write("\n\n")
            outputfile.flush()
        else:
            for light in project_settings.good_light:
                for group in exps[exp]['groups']:
                    outputfile.write("# butthead distribution of %s barcodes from %d files, %d frames, %d points\n" %
                            (light.lower(), self.files, self.frames[light], self.points[light]))
                    outputfile.write("# X[row][col] = number of frames when butt of patek [col] is close to head of patek [row].\n")
                    outputfile.write("# IDs are ordered alphabetically.\n")
                    outputfile.write("# filter_for_valid_cage=%s\n" % str(project_settings.filter_for_valid_cage))
                    outputfile.write("# patek_length = %g px\n" % self.patek_length)
                    outputfile.write("# cos_approacher_threshold = %g\n" % self.cos_approacher_threshold)
                    outputfile.write("# this is group %s\n\n" % group)
                    # write header
                    names = exps[exp]['groups'][group]
                    si = sorted(list(range(len(names))), key=cmp_to_key(lambda x, y: -1 if names[x] < names[y] else 1 if names[x] > names[y] else 0))
                    allnames = [colorids[k] for k in range(len(colorids))]
                    outputfile.write("butthead_%s_group_%s" % (light.lower(), group))
                    for i in range(len(si)):
                        outputfile.write("\t%s" % names[si[i]])
                    outputfile.write("\n")
                    # write data
                    for i in range(len(si)):
                        outputfile.write(names[si[i]])
                        for j in range(len(si)):
                            outputfile.write("\t%d" % self.data[light][allnames.index(names[si[i]]),allnames.index(names[si[j]])])
                        outputfile.write("\n")
                    outputfile.write("\n\n")
            outputfile.flush()


class SDist(Stat):
    """Storage class for (spatial) distance distribution of barcodes of different id
    on the same frame.

    X.data[light][dist] is the number of times when two pateks were
    at dist pixels from each other.

    """
    def __init__(self, good_light):
        """Initialize with zero elements."""
        #: version of the current structure. Change it every time something
        #: changes in the definition of the statistics, to see whether some
        #: already calculated data is old or not.
        #: version 0: first attempt
        #: version 1: cage wall check implemented
        #: version 2: entrytimes are checked and skipped
        #: version 3: maxdist increased from 200 to 1000
        #: version 4: filter_for_valid_cage introduced (2015.04.30.)
        self.version = 4
        #: number of files that are parsed into this statistic
        self.files = 0
        #: number of frames that were used to gather info for the statistic
        self.frames = dict()
        #: number of data points in the statistic
        self.points = dict()
        #: maximum distance to detect [pixels]
        self.maxdist = 1000
        #: the main data of the statistic: [light][dist]
        self.data = dict()
        # initialize data
        for light in good_light:
            self.data[light] = numpy.zeros(( \
                    self.maxdist))
            self.frames[light] = 0
            self.points[light] = 0

    def write_results(self, outputfile, project_settings):
        """Saves the contents of self to a file (possibly as a summarized stat).

        :param outputfile: file object where the results are written
        :param project_settings: global project settings imported by
                trajognize.settings.import_trajognize_settings_from_file()

        """
        for light in project_settings.good_light:
            outputfile.write("# distance distribution [pixel] of %s barcodes from %d files, %d frames, %d points\n" %
                    (light.lower(), self.files, self.frames[light], self.points[light]))
            outputfile.write("# filter_for_valid_cage=%s\n" % str(project_settings.filter_for_valid_cage))
            outputfile.write("# only CHOSEN barcodes are taken into account.\n\n")
            # write header
            outputfile.write("sdist_%s\tnum\n" % (light.lower()))
            # write data
            for i in range(self.maxdist):
                outputfile.write("%d\t%d\n" % (i, self.data[light][i]))
            outputfile.write("\n\n")
        outputfile.flush()


class VelDist(Stat):
    """Storage class for the velocity distribution of barcodes (calculated as the
    position change from consecutive frames).

    X.data[light][patek/all][vel] is the number of times when a patek was
    moving with velocity vel [pixels/frame].

    """
    def __init__(self, good_light, id_count):
        """Initialize with zero elements.

        :param id_count: Number of IDs (pateks)

        """
        #: version of the current structure. Change it every time something
        #: changes in the definition of the statistics, to see whether some
        #: already calculated data is old or not.
        #: version 0: first attempt
        #: version 1: entrytimes are checked and skipped
        #: version 2: filter_for_valid_cage introduced (2015.04.30.)
        self.version = 2
        #: number of files that are parsed into this statistic
        self.files = 0
        #: number of frames that were used to gather info for the statistic
        self.frames = dict()
        #: number of data points in the statistic
        self.points = dict()
        #: maximum velocity to detect [pixels/frame]
        self.maxvel = 200
        #: the main data of the statistic: [light][patek+all][dist]
        self.data = dict()
        # initialize data
        for light in good_light:
            self.data[light] = numpy.zeros(( \
                    id_count+1,
                    self.maxvel),
                    dtype=numpy.int)
            self.frames[light] = 0
            self.points[light] = 0

    def write_results(self, outputfile, project_settings):
        """Saves the contents of self to a file (possibly as a summarized stat).

        :param outputfile: file object where the results are written
        :param project_settings: global project settings imported by
                trajognize.settings.import_trajognize_settings_from_file()

        """
        colorids = project_settings.colorids
        for light in project_settings.good_light:
            outputfile.write("# velocity distribution [pixel/frame] of %s barcodes from %d files, %d frames, %d points\n" %
                    (light.lower(), self.files, self.frames[light], self.points[light]))
            outputfile.write("# filter_for_valid_cage=%s\n" % str(project_settings.filter_for_valid_cage))
            outputfile.write("# only CHOSEN barcodes are taken into account.\n\n")
            # write header
            names = [colorids[k] for k in range(len(colorids))]
            names.append("all")
            outputfile.write("veldist_%s" % (light.lower()))
            for name in names:
                outputfile.write("\t%s" % name)
            outputfile.write("\n")
            # write data
            for i in range(self.maxvel):
                outputfile.write("%d" % i)
                for k in range(len(names)):
                    outputfile.write("\t%d" % self.data[light][k,i])
                outputfile.write("\n")
            outputfile.write("\n\n")
        outputfile.flush()


class AccDist(Stat):
    """Storage class for the acceleration distribution of barcodes
    (calculated from the position of 3 consecutive frames).

    X.data[light][patek/all][acc] is the number of times when a patek was
    moving with acceleration acc [pixels/frame^2].

    """
    def __init__(self, good_light, id_count):
        """Initialize with zero elements.

        :param id_count: Number of IDs (pateks)

        """
        #: version of the current structure. Change it every time something
        #: changes in the definition of the statistics, to see whether some
        #: already calculated data is old or not.
        #: version 0: first attempt
        #: version 1: filter_for_valid_cage introduced (2015.04.30.)
        self.version = 1
        #: number of files that are parsed into this statistic
        self.files = 0
        #: number of frames that were used to gather info for the statistic
        self.frames = dict()
        #: number of data points in the statistic
        self.points = dict()
        #: maximum (absolute) acceleration to detect [pixels/frame^2]
        self.maxacc = 200
        #: the main data of the statistic: [light][patek+all][dist]
        self.data = dict()
        # initialize data
        for light in good_light:
            self.data[light] = numpy.zeros(( \
                    id_count+1,
                    self.maxacc),
                    dtype=numpy.int)
            self.frames[light] = 0
            self.points[light] = 0

    def write_results(self, outputfile, project_settings):
        """Saves the contents of self to a file (possibly as a summarized stat).

        :param outputfile: file object where the results are written
        :param project_settings: global project settings imported by
                trajognize.settings.import_trajognize_settings_from_file()

        """
        colorids = project_settings.colorids
        for light in project_settings.good_light:
            outputfile.write("# acceleration distribution [pixel/frame^2] of %s barcodes from %d files, %d frames, %d points\n" %
                    (light.lower(), self.files, self.frames[light], self.points[light]))
            outputfile.write("# filter_for_valid_cage=%s\n" % str(project_settings.filter_for_valid_cage))
            outputfile.write("# only CHOSEN barcodes are taken into account.\n\n")
            # write header
            names = [colorids[k] for k in range(len(colorids))]
            names.append("all")
            outputfile.write("accdist_%s" % (light.lower()))
            for name in names:
                outputfile.write("\t%s" % name)
            outputfile.write("\n")
            # write data
            for i in range(self.maxacc):
                outputfile.write("%d" % i)
                for k in range(len(names)):
                    outputfile.write("\t%d" % self.data[light][k,i])
                outputfile.write("\n")
            outputfile.write("\n\n")
        outputfile.flush()


class Basic(Stat):
    """Store class for basic statistics, like frame num on different lights,
    frame nums in different experiments, number of different errors, etc.

    """
    def __init__(self, all_light, MBASE):
        """Initialize an empty class."""
        #: version of the current structure. Change it every time something
        #: changes in the definition of the statistics, to see whether some
        #: already calculated data is old or not.
        #: version 0: first attempt
        #: version 1: total time of experiment added (to write results)
        #: version 2: mfix flag count results are saved
        #: version 3: stats for color comparison are introduced
        #: version 4: filter_for_valid_cage introduced (2015.04.30.)
        self.version = 4
        #: number of files that are parsed into this statistic
        self.files = 0
        #: number of frames that were used to gather info for the statistic
        self.frames = dict()
        #: number of frames with cage error (nan in any parameter)
        self.cageerror = dict()
        #: number of frames within entry times
        self.entrytime = dict()
        #: number of frames where patek is not in its valid cage
        self.nonvalidcage = dict()
        #: number of hits for all mfix flags separately
        self.mfixcount = dict()
        #: number of found blobs for each color
        self.colors_all = dict()
        self.colors_chosen = dict()
        # initialize data
        for light in all_light:
            self.frames[light] = 0
            self.cageerror[light] = 0
            self.entrytime[light] = 0
            self.nonvalidcage[light] = 0
            self.mfixcount[light] = numpy.zeros(len(trajognize.init.MFix) + 1) # last is for counting not chosens
            self.colors_all[light] = numpy.zeros(MBASE)
            self.colors_chosen[light] = numpy.zeros(MBASE)

    def __add__(self, X):
        """Add another object of the same class to self with the '+' and '+=' operators.

        :param X: object of the same class that is added to self

        """
        self._check_version(X)
        for light in self.frames.keys():
            self.frames[light] += X.frames[light]
            self.cageerror[light] += X.cageerror[light]
            self.entrytime[light] += X.entrytime[light]
            self.nonvalidcage[light] += X.nonvalidcage[light]
            self.mfixcount[light] += X.mfixcount[light]
            self.colors_all[light] += X.colors_all[light]
            self.colors_chosen[light] += X.colors_chosen[light]
        self.files += X.files

        return self

    def print_status(self):
        """Prints status info about the data to standard output."""
        for light in self.frames.keys():
            print("  %s statistic is from %d files and %d frames" % \
                    (light, self.files, self.frames[light]))

    def write_results(self, outputfile, project_settings, exps, exp):
        """Saves the contents of self to a file (possibly as a summarized stat).

        :param outputfile: file object where the results are written
        :param project_settings: global project settings imported by
                trajognize.settings.import_trajognize_settings_from_file()
        :param exps: experiment database created by project_settings
        :param exp: name of the current experiment

        """
        colorids = project_settings.colorids
        outputfile.write("# Basic statistics on video files and errors from %d files\n\n" % self.files)
        if exp != "all":
            dt = exps[exp]['stop'] - exps[exp]['start']
            if sys.hexversion < 0x02070000:
                totalframes = int(dt.seconds + dt.microseconds / 1E6 + dt.days * 86400 * project_settings.FPS)
            else:
                totalframes = int(dt.total_seconds() * project_settings.FPS)
            outputfile.write("Number of frames in %s experiment:\t%d\n" % (exp, totalframes))
            processedframes = 0
            for light in project_settings.all_light:
                processedframes += self.frames[light]
            outputfile.write("Number of not processed frames in %s experiment:\t%d\t(%1.2f%% of experiment)\n" %
                    (exp, totalframes - processedframes, 100.0*(totalframes-processedframes)/totalframes))
            outputfile.write("\n\n")

        for light in project_settings.all_light:
            outputfile.write("# Basic statistics for %s light condition\n" % light)
            outputfile.write("Total number of processed frames:\t%d" % self.frames[light])
            if exp == "all":
                outputfile.write("\n")
            else:
                outputfile.write("\t(%1.2f%% of experiment)\n" % (100.0*self.frames[light]/totalframes))
            x = self.frames[light]
            if not x: x = 1
            outputfile.write("Number of (invalid) frames due to entry times:\t%d\t(%1.2f%% of processed)\n" % \
                    (self.entrytime[light], 100.0*self.entrytime[light]/x))
            outputfile.write("Number of valid frames:\t%d\t(%1.2f%% of processed)\n" % \
                    (self.frames[light] - self.entrytime[light],
                    100.0*(self.frames[light] - self.entrytime[light])/x))
            x = self.frames[light] - self.entrytime[light]
            if not x: x = 1
            outputfile.write("Number of valid frames with cage error:\t%d\t(%1.2f%% of valid)\n" % \
                    (self.cageerror[light], 100.0*self.cageerror[light]/x))
            outputfile.write("Number of not chosen barcodes:\t%d\t(%1.2f%% of valid)\n" % \
                    (self.mfixcount[light][-1], 100.0*self.mfixcount[light][-1]/(len(colorids)*x)))
            outputfile.write("Number of chosen barcodes with the following flags:\n")
            for i in range(len(trajognize.init.MFix)):
                outputfile.write("%-22s\t%d\t(%1.2f%% of chosen)\n" % \
                        (trajognize.init.MFix(1<<i).name, self.mfixcount[light][i],
                        100.0*self.mfixcount[light][i] / max(1, len(colorids)*x - self.mfixcount[light][-1])))
            outputfile.write("Number of barcodes containing a given color:\tall_novirt\tchosen\n")
            for i in range(project_settings.MBASE):
                outputfile.write("%-6s\t%d\t%d\n" % (project_settings.color_names[i],
                        self.colors_all[light][i],
                        self.colors_chosen[light][i]))
            outputfile.write("Number of chosen barcodes with position in non valid cage:\n")
            outputfile.write("%d\t(%1.2f%% of chosen)\n" % \
                    (self.nonvalidcage[light], 100.0*self.nonvalidcage[light] / max(1, len(colorids)*x - self.mfixcount[light][-1])))

            outputfile.write("\n\n")
        outputfile.flush()


class DistFromWall(Stat):
    """Storage class for the distance-from-wall distribution of barcodes
    for all light types and real/virt states, for all days separately.

    distfromwall.data[light][patek][0=all/1=moving][real/virtual][day][dist] is
    the number of frames a patek barcode center was at 'dist' distance from the
    closest wall of territory, home or wheel, not over these objects.

    This class has no virtual subclasses, all data fit in approximately the
    same amount of memory than one subclass of a HeatMap object.

    """
    def __init__(self, good_light, image_size, max_day, id_count):
        """Initialize distfromwall distributions with zero elements.

        :param id_count: Number of IDs (pateks)

        """
        #: version of the current structure. Change it every time something
        #: changes in the definition of the statistics, to see whether some
        #: already calculated data is old or not.
        #: version 0: first attempt
        #: version 1: motion type data introduced
        #: version 1b: absgrad introduced (to sum only) (2014.12.19.)
        #:            note that filter_for_valid_cage is not needed here,
        #:            since object definitions contain this check inherently
        self.version = 1
        #: velocity threshold for motion type data
        self.velocity_threshold = 5 # [px/frame] = 1 cm/frame = 25 cm/s
        self.motion_types = ["allspeed", "onlymoving"]
        #: number of files that are parsed into this statistic
        self.files = 0
        #: number of frames that were used to gather info for the statistic
        self.frames = dict()
        #: number of data points in the statistic
        self.points = dict()
        #: the main data of the statistic: [light][x][y]
        self.data = dict()
        # initialize data
        for light in good_light:
            self.data[light] = numpy.zeros(( \
                    id_count,
                    len(self.motion_types),
                    len(mfix_types),
                    max_day,
                    int(image_size.y / 4)),
                    dtype=numpy.int)
            self.frames[light] = 0
            self.points[light] = 0

    def print_status(self):
        """Prints status info about the data to standard output."""
        self._print_status__light()

    def write_results(self, outputfile, project_settings, exps, exp):
        """Saves the contents of self to a file (possibly as a summarized stat).

        :param outputfile: file object where the results are written
        :param project_settings: global project settings imported by
                trajognize.settings.import_trajognize_settings_from_file()
        :param exps: experiment database created by project_settings
        :param exp: name of the current experiment

        """
        colorids = project_settings.colorids
        def weighted_avg_and_std(values, weights):
            """
            Return the weighted average and standard deviation.

            values, weights -- Numpy ndarrays with the same shape.
            """
            if not numpy.sum(weights):
                return (0, 0)
            average = numpy.average(values, weights=weights)
            variance = numpy.average((values-average)**2, weights=weights)  # Fast and numerically precise
            return (average, sqrt(variance))

        # do not save common results for all experiments,
        # since day is calculated from the beginning of each experiment...
        if exp == "all": return
        # calculate max number of days in the given experiment
        maxday = experiments.get_days_since_start(exps[exp], exps[exp]['stop'])
        dayoffset = experiments.get_day_offset(exps[exp])
        dayrange = experiments.get_dayrange_of_experiment(exps[exp])
        anymft = mfix_types + ["ANY"]
        for light in project_settings.good_light:
            for group in exps[exp]['groups']:
                # get sorted names and colorid indices
                allnames = [colorids[k] for k in range(len(colorids))]
                names = sorted(exps[exp]['groups'][group])
                klist = [allnames.index(name) for name in names]
                outputfile.write("# daily distance-from-wall distribution of %s barcodes of group %s from %d files, %d frames, %d points\n" %
                        (light.lower(), group, self.files, self.frames[light], self.points[light]))
                outputfile.write("# velocity threshold for 'onlymoving' type data: %d [pixels/frame]\n\n" % self.velocity_threshold)
                for mfi, mft in enumerate(anymft):
                    for moi, mot in enumerate(self.motion_types):
                        # write daily avg and std for the group
                        # header
                        outputfile.write("distfromwall_avg_%s_%s_%s_group_%s" % \
                                (light.lower(), mot, mft, group))
                        for name in names:
                            outputfile.write("\t%s.avg\t%s.std\t%s.num" % (name, name, name))
                        outputfile.write("\tabsgrad_avg\tabsgrad_std\n")
                        # data
                        lastdayavg = [0] * len(klist)
                        for day in range(maxday + 1):
                            absgrad = []
                            outputfile.write(dayrange[day])
                            for i, k in enumerate(klist):
                                if mft == "ANY":
                                    x = sum(self.data[light][k][moi])
                                else:
                                    x = self.data[light][k][moi][mfi]
                                avg, std = weighted_avg_and_std(range(len(x[day+dayoffset])), x[day+dayoffset])
                                num = numpy.sum(x[day+dayoffset])
                                outputfile.write("\t%g\t%g\t%g" % (avg, std, num))
                                absgrad.append(abs(avg - lastdayavg[i]))
                                lastdayavg[i] = avg
                            outputfile.write("\t%g\t%g\n" % (numpy.mean(absgrad), numpy.std(absgrad)))
                        outputfile.write("\n\n")

                        # write the whole distribution for all IDs
                        for k in klist:
                            name = colorids[k]
                            outputfile.write("distfromwall_dist_%s_%s_%s_patek_%s\t%s\n" % \
                                    (light.lower(), mot, mft, name, "\t".join(dayrange)))
                            if mft == "ANY":
                                x = sum(self.data[light][k][moi])
                            else:
                                x = self.data[light][k][moi][mfi]
                            for i in range(len(x[0])):
                                outputfile.write("%d" % i)
                                for day in range(maxday + 1):
                                    outputfile.write("\t%d" % x[day+dayoffset][i])
                                outputfile.write("\n")
                            outputfile.write("\n\n")

                outputfile.flush()

