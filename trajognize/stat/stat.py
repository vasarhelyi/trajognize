"""
Miscellaneous statistical functions for the analysis of trajognize results.

These functions should be called on each barcode dataset of a given video to
extract different statistics on the barcodes.

Each calculating function should have a corresponding class in
trajognize.stat.init with the following naming convention:

    stat.init.Xxx() is the object type to fill with the statistic
    stat.stat.calculate_xxx() is the function call to calculate the statistic
    stat.stat.subclasses_xxx() if there are virtual subclasses of that stat

This convention allows for automatic script generation and easy file read/write
operations of the data and later statistic summary.

barcodes[currentframe][k] should be a list of Barcode type barcodes of
colorids[k], on frame currentframe.

Another convention is that if dailyoutput is specified in a stat, it should
return a list of objects, not an object, where the 0th item corresponds to the
first day, 1st to the second day of the video.

"""

# external imports
import os, numpy
from math import hypot, atan2, cos, sin, radians

# imports from base class
import trajognize.init
import trajognize.util
import trajognize.algo

# imports from self subclass
from . import init
from . import util
from . import experiments


def subclasses_heatmap(project_settings):
    """Return dict of heatmap virtual subclass names.

    We have one virtual subclass for each barcode and one for 'all' summary.
    It is needed because image outputs are too big to be in one stat,
    calculation and summary takes too long.

    """
    colorids = project_settings.colorids
    return [colorids[k] for k in range(len(colorids))] + ["all"]


def calculate_heatmap(
    barcodes,
    light_log,
    cage_log,
    entrytimes,
    starttime,
    project_settings,
    experiment,
    subclassindex,
    dailyoutput,
):
    """Get barcode position distributions as heatmaps for all light conditions
    and real/virt states.

    :param barcodes: global list of barcodes (Barcode)
            structured like this: [framenum][coloridindex][index]
    :param light_log: dictionary of light changes created by
            trajognize.util.parse_log_file()
    :param cage_log: dictionary of cage center changes created by
            trajognize.util.parse_log_file()
    :param entrytimes: dictionary of entry times created by
            trajognize.parse.parse_entry_times()
    :param starttime: datetime of the first frame of the current video
    :param project_settings: global project settings imported by
            trajognize.settings.import_trajognize_settings_from_file()
    :param experiment: the current experiment that defines rat groups, walls and
            interesting object centers. If experiment is None,
            we do not calculate anything.
    :param subclassindex: index of virtual subclass (coloridindex)
    :param dailyoutput: if True, return a list of objects instead of a
            single object, corresponding to the days that the stat covers

    """
    colorids = project_settings.colorids
    light_at_frame = trajognize.util.param_at_frame(light_log)
    cage_at_frame = trajognize.util.param_at_frame(cage_log)
    day = 0
    if dailyoutput:
        heatmaps = [
            init.HeatMap(project_settings.good_light, project_settings.image_size),
            init.HeatMap(project_settings.good_light, project_settings.image_size),
        ]
        # do not calculate anything if we are not part of an experiment
        if experiment is None:
            return heatmaps
    else:
        heatmaps = [
            init.HeatMap(project_settings.good_light, project_settings.image_size)
        ]
        # do not calculate anything if we are not part of an experiment
        if experiment is None:
            return heatmaps[0]
    id_count = len(barcodes[0])
    for currentframe in range(len(barcodes)):
        # get current date
        datetimeatframe = trajognize.util.get_datetime_at_frame(
            starttime, currentframe, project_settings.FPS
        )
        # check day lapse
        if dailyoutput and not day and datetimeatframe.date() > starttime.date():
            day = 1
        # check entry times and skip current frame if not valid
        if trajognize.util.is_entry_time(entrytimes, datetimeatframe):
            continue
        # get light and skip bad lighting conditions
        light = light_at_frame(currentframe)
        if light not in project_settings.good_light:
            continue
        # get cage
        cagecenter = cage_at_frame(currentframe)
        # get virtual subclass
        if subclassindex == id_count:
            klist = range(id_count)
        else:
            klist = [subclassindex]
        # store barcodes on heatmap
        for k in klist:
            for barcode in barcodes[currentframe][k]:
                # get mfix_type
                mfi = util.get_mfi(barcode)
                if mfi == -1:
                    continue  # this excludes not chosen ones, too
                # get center and skip bad ones: nan or outside image area
                centerx = barcode.centerx
                centery = barcode.centery
                if project_settings.correct_cage:
                    centerx += project_settings.cage_center.x - cagecenter[0]
                    centery += project_settings.cage_center.y - cagecenter[1]
                if (
                    centerx != centerx
                    or centerx >= project_settings.image_size.x
                    or centerx < 0
                ):
                    continue
                if (
                    centery != centery
                    or centery >= project_settings.image_size.y
                    or centery < 0
                ):
                    continue
                # filter results based on whether pateks are inside their own cage/territory
                if project_settings.filter_for_valid_cage:
                    pos = trajognize.init.Point(centerx, centery)
                    group = experiment["groupid"][colorids[k]]
                    for poly in experiment["wallall"][group]:
                        if util.is_inside_polygon(pos, poly):
                            break
                    else:
                        continue
                # store good ones on heatmap
                heatmaps[day].data[light][mfi][int(centerx)][int(centery)] += 1
                heatmaps[day].points[light][mfi] += 1
        heatmaps[day].frames[light] += 1
    for d in range(day + 1):
        heatmaps[d].files = 1
    if dailyoutput:
        return heatmaps
    else:
        return heatmaps[0]


def subclasses_motionmap(project_settings):
    """Return dict of motion heatmap virtual subclass names.

    We have one virtual subclass for each barcode and one for 'all' summary.
    It is needed because image outputs are too big to be in one stat,
    calculation and summary takes too long.

    """
    colorids = project_settings.colorids
    return [colorids[k] for k in range(len(colorids))] + ["all"]


def calculate_motionmap(
    barcodes,
    light_log,
    cage_log,
    entrytimes,
    starttime,
    project_settings,
    experiment,
    subclassindex,
):
    """Get moving barcode position distributions as motion heatmaps
    for all light conditions and real/virt states.

    :param barcodes: global list of barcodes (Barcode)
            structured like this: [framenum][coloridindex][index]
    :param light_log: dictionary of light changes created by
            trajognize.util.parse_log_file()
    :param cage_log: dictionary of cage center changes created by
            trajognize.util.parse_log_file()
    :param entrytimes: dictionary of entry times created by
            trajognize.parse.parse_entry_times()
    :param starttime: datetime of the first frame of the current video
    :param project_settings: global project settings imported by
            trajognize.settings.import_trajognize_settings_from_file()
    :param experiment: the current experiment that defines rat groups, walls and
            interesting object centers. If experiment is None,
            we do not calculate anything.
    :param subclassindex: index of virtual subclass (coloridindex)

    """
    colorids = project_settings.colorids
    light_at_frame = trajognize.util.param_at_frame(light_log)
    cage_at_frame = trajognize.util.param_at_frame(cage_log)
    motionmaps = init.MotionMap(
        project_settings.good_light, project_settings.image_size
    )
    # do not calculate anything if we are not part of an experiment
    if experiment is None:
        return motionmaps
    id_count = len(barcodes[0])
    prevframe = 0
    prevchosens = util.get_chosen_barcodes(barcodes[0])
    prevcagecenter = cage_at_frame(0)
    for currentframe in range(1, len(barcodes)):
        # check entry times and skip current frame if not valid
        if trajognize.util.is_entry_time(
            entrytimes,
            trajognize.util.get_datetime_at_frame(
                starttime, currentframe, project_settings.FPS
            ),
        ):
            continue
        # get light and skip bad lighting conditions
        light = light_at_frame(currentframe)
        if light not in project_settings.good_light:
            continue
        # get cage
        cagecenter = cage_at_frame(currentframe)
        # get chosen barcodes for current frame
        chosens = util.get_chosen_barcodes(barcodes[currentframe])
        if currentframe == prevframe + 1:
            # get virtual subclass
            if subclassindex == id_count:
                klist = range(id_count)
            else:
                klist = [subclassindex]
            # store barcodes on motionmap
            for k in klist:
                if not chosens[k] or not prevchosens[k]:
                    continue
                barcode = chosens[k]
                prevbarcode = prevchosens[k]
                # get center and skip bad ones: nan or outside image area
                cx = barcode.centerx
                cy = barcode.centery
                if project_settings.correct_cage:
                    cx += project_settings.cage_center.x - cagecenter[0]
                    cy += project_settings.cage_center.y - cagecenter[1]
                if cx != cx or cx >= project_settings.image_size.x or cx < 0:
                    continue
                if cy != cy or cy >= project_settings.image_size.y or cy < 0:
                    continue
                # filter results based on whether pateks are inside their own cage/territory
                if project_settings.filter_for_valid_cage:
                    pos = trajognize.init.Point(cx, cy)
                    group = experiment["groupid"][colorids[k]]
                    for poly in experiment["wallall"][group]:
                        if util.is_inside_polygon(pos, poly):
                            break
                    else:
                        continue
                # do the same for prev barcode
                prevcx = prevbarcode.centerx
                prevcy = prevbarcode.centery
                if project_settings.correct_cage:
                    prevcx += project_settings.cage_center.x - prevcagecenter[0]
                    prevcy += project_settings.cage_center.y - prevcagecenter[1]
                if (
                    prevcx != prevcx
                    or prevcx >= project_settings.image_size.x
                    or prevcx < 0
                ):
                    continue
                if (
                    prevcy != prevcy
                    or prevcy >= project_settings.image_size.y
                    or prevcy < 0
                ):
                    continue
                # filter results based on whether pateks are inside their own cage/territory
                if project_settings.filter_for_valid_cage:
                    pos = trajognize.init.Point(prevcx, prevcy)
                    for poly in experiment["wallall"][group]:
                        if util.is_inside_polygon(pos, poly):
                            break
                    else:
                        continue
                # get velocity
                vx = cx - prevcx
                vy = cy - prevcy
                v = hypot(vx, vy)
                if v < motionmaps.velocity_threshold:
                    continue
                v = int(v)
                dvx = vx / v  # deliberately not (v-1)
                dvy = vy / v  # deliberately not (v-1)
                # store velocity-number-of-points interpolated between
                # the two positions (on prev frame and current frame)
                # skipping exact position on current frame (will be added
                # to next frame if velocity is still large...)
                for i in range(v):
                    x = int(prevcx + i * dvx)
                    y = int(prevcy + i * dvy)
                    # store good ones on motionmap
                    motionmaps.data[light][x][y] += 1
                motionmaps.points[light] += 1
            motionmaps.frames[light] += 1
        prevframe = currentframe
        prevchosens = chosens
        prevcagecenter = cagecenter
    motionmaps.files = 1
    return motionmaps


def subclasses_dist24h():
    """Return dict of dist24h virtual subclass names.

    We have one virtual subclass for each day of week and one for 'all' summary.
    It could be included into the statistics itself but why not make things
    more parallel.

    """
    return [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
        "alldays",
    ]


def calculate_dist24h(
    barcodes,
    light_log,
    cage_log,
    entrytimes,
    starttime,
    project_settings,
    experiment,
    subclassindex,
):
    """Calculate 24h time distribution of barcodes.

    :param barcodes: global list of barcodes (Barcode)
            structured like this: [framenum][coloridindex][index]
    :param light_log: dictionary of light changes created by
            trajognize.util.parse_log_file()
    :param cage_log: dictionary of cage center changes created by
            trajognize.util.parse_log_file()
    :param entrytimes: dictionary of entry times created by
            trajognize.parse.parse_entry_times()
    :param starttime: datetime of the first frame of the current video
    :param project_settings: global project settings imported by
            trajognize.settings.import_trajognize_settings_from_file()
    :param experiment: the current experiment that defines rat groups, walls and
            interesting object centers. If experiment is None,
            we do not calculate anything.
    :param subclassindex: index of virtual subclass (weekday index)

    """
    colorids = project_settings.colorids
    light_at_frame = trajognize.util.param_at_frame(light_log)
    cage_at_frame = trajognize.util.param_at_frame(cage_log)
    id_count = len(barcodes[0])
    dist24h = init.Dist24h(project_settings, id_count)
    # get starting time
    secofday = starttime.hour * 3600 + starttime.minute * 60 + starttime.second
    # iterate for all frames
    for currentframe in range(len(barcodes)):
        # get current time
        datetime_at_frame = trajognize.util.get_datetime_at_frame(
            starttime, currentframe, project_settings.FPS
        )
        # check for weekday (indexed by subclassindex)
        if subclassindex < 7 and subclassindex != datetime_at_frame.weekday():
            continue
        # check entry times and skip current frame if not valid
        if trajognize.util.is_entry_time(entrytimes, datetime_at_frame):
            continue
        # get cage
        cagecenter = cage_at_frame(currentframe)
        # get light and skip bad lighting conditions
        light = light_at_frame(currentframe)
        if light not in project_settings.good_light:
            continue
        # get current frame in min (TODO: use datetime_at_frame instead)
        bin = int(((secofday + currentframe / project_settings.FPS) % 86400) / 60)
        # get chosen barcodes
        chosens = util.get_chosen_barcodes(barcodes[currentframe])
        # store number of barcodes in the proper time bin
        for k in range(id_count):
            if chosens[k] is None:
                continue
            # get center and skip bad ones: nan or outside image area
            barcode = chosens[k]
            centerx = barcode.centerx
            centery = barcode.centery
            if project_settings.correct_cage:
                centerx += project_settings.cage_center.x - cagecenter[0]
                centery += project_settings.cage_center.y - cagecenter[1]
            if (
                centerx != centerx
                or centerx >= project_settings.image_size.x
                or centerx < 0
            ):
                continue
            if (
                centery != centery
                or centery >= project_settings.image_size.y
                or centery < 0
            ):
                continue
            # filter results based on whether pateks are inside their own cage/territory
            if project_settings.filter_for_valid_cage:
                pos = trajognize.init.Point(centerx, centery)
                group = experiment["groupid"][colorids[k]]
                for poly in experiment["wallall"][group]:
                    if util.is_inside_polygon(pos, poly):
                        break
                else:
                    continue
            # no errors, store data
            num = [0] * len(init.mfix_types)
            mfi = util.get_mfi(chosens[k])
            num[mfi] = 1
            # calculate new avg, std, num based on this method:
            # http://en.wikipedia.org/wiki/Standard_deviation#Rapid_calculation_methods
            for i in range(len(init.mfix_types)):
                prev_avg = dist24h.avg[k, i, bin]
                dist24h.num[k, i, bin] += 1
                dist24h.avg[k, i, bin] += (num[i] - prev_avg) / dist24h.num[k, i, bin]
                dist24h.stv[k, i, bin] += (num[i] - prev_avg) * (
                    num[i] - dist24h.avg[k, i, bin]
                )
                dist24h.points[i] += 1
        dist24h.frames += 1
    dist24h.files = 1
    return dist24h


def subclasses_dist24hobj():
    """Return dict of dist24hobj virtual subclass names.

    We have one virtual subclass for each day of week and one for 'all' summary.
    It could be included into the statistics itself but why not make things
    more parallel.

    """
    return [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
        "alldays",
    ]


def calculate_dist24hobj(
    barcodes,
    light_log,
    cage_log,
    entrytimes,
    starttime,
    project_settings,
    experiment,
    subclassindex,
):
    """Calculate 24h time distribution of barcodes around interesting objects.

    Note that in joined groups when more food/home/water/entrance objects
    are available, results will be summarized for all common object types.
    It can be changed if needed of course...

    :param barcodes: global list of barcodes (Barcode)
            structured like this: [framenum][coloridindex][index]
    :param light_log: dictionary of light changes created by
            trajognize.util.parse_log_file()
    :param cage_log: dictionary of cage center changes created by
            trajognize.util.parse_log_file()
    :param entrytimes: dictionary of entry times created by
            trajognize.parse.parse_entry_times()
    :param starttime: datetime of the first frame of the current video
    :param project_settings: global project settings imported by
            trajognize.settings.import_trajognize_settings_from_file()
    :param experiment: the current experiment that defines rat groups, walls and
            interesting object centers. If experiment is None,
            we do not calculate anything.
    :param subclassindex: index of virtual subclass (weekday index)

    """
    colorids = project_settings.colorids
    # initialize object
    id_count = len(barcodes[0])
    dist24hobj = init.Dist24hObj(project_settings.object_types, id_count)
    # do not calculate anything if we are not part of an experiment
    if experiment is None:
        return dist24hobj
    # initialize light
    light_at_frame = trajognize.util.param_at_frame(light_log)
    cage_at_frame = trajognize.util.param_at_frame(cage_log)
    tempbarcode = trajognize.init.Barcode(MCHIPS=project_settings.MCHIPS)
    # get starting time
    secofday = starttime.hour * 3600 + starttime.minute * 60 + starttime.second
    # iterate for all frames
    for currentframe in range(len(barcodes)):
        # get current time
        datetime_at_frame = trajognize.util.get_datetime_at_frame(
            starttime, currentframe, project_settings.FPS
        )
        # check for weekday (indexed by subclassindex)
        if subclassindex < 7 and subclassindex != datetime_at_frame.weekday():
            continue
        # check entry times and skip current frame if not valid
        if trajognize.util.is_entry_time(entrytimes, datetime_at_frame):
            continue
        # get light and skip bad lighting conditions
        light = light_at_frame(currentframe)
        if light not in project_settings.good_light:
            continue
        # get cage
        cagecenter = cage_at_frame(currentframe)
        # get current frame in min (TODO: use datetime_at_frame instead)
        bin = ((secofday + currentframe / project_settings.FPS) % 86400) / 60
        # get chosen barcodes
        chosens = util.get_chosen_barcodes(barcodes[currentframe])
        # store number of barcodes in the proper time bin
        for k in range(id_count):
            strid = colorids[k]
            if chosens[k] is None:
                continue
            # get center and skip bad ones: nan or outside image area
            tempbarcode.centerx = chosens[k].centerx
            tempbarcode.centery = chosens[k].centery
            if project_settings.correct_cage:
                tempbarcode.centerx += project_settings.cage_center.x - cagecenter[0]
                tempbarcode.centery += project_settings.cage_center.y - cagecenter[1]
            if (
                tempbarcode.centerx != tempbarcode.centerx
                or tempbarcode.centerx >= project_settings.image_size.x
                or tempbarcode.centerx < 0
            ):
                continue
            if (
                tempbarcode.centery != tempbarcode.centery
                or tempbarcode.centery >= project_settings.image_size.y
                or tempbarcode.centery < 0
            ):
                continue
            # check if barcode is under any object of the group
            num = [0] * len(project_settings.object_types)
            group = experiment["groupid"][strid]
            for i in range(len(project_settings.object_types)):
                object = project_settings.object_types[i]
                if object not in experiment.keys():
                    continue
                for objectcenter in experiment[object][group]:
                    if experiments.is_barcode_under_object(
                        tempbarcode,
                        objectcenter,
                        project_settings.object_areas[object],
                        project_settings.image_size,
                    ):
                        num[i] = 1
                        break
                else:
                    continue
                break
            # calculate new avg, std, num based on this method:
            # http://en.wikipedia.org/wiki/Standard_deviation#Rapid_calculation_methods
            for i in range(len(project_settings.object_types)):
                prev_avg = dist24hobj.avg[k, i, bin]
                dist24hobj.num[k, i, bin] += 1
                dist24hobj.avg[k, i, bin] += (num[i] - prev_avg) / dist24hobj.num[
                    k, i, bin
                ]
                dist24hobj.stv[k, i, bin] += (num[i] - prev_avg) * (
                    num[i] - dist24hobj.avg[k, i, bin]
                )
            dist24hobj.points += 1
        dist24hobj.frames += 1
    dist24hobj.files = 1
    return dist24hobj


def calculate_dailyobj(
    barcodes, light_log, cage_log, entrytimes, starttime, project_settings, experiment
):
    """Calculate daily occurrence of barcodes around interesting objects.

    Day number is calculated from the beginning of the current experiment.

    Note that in joined groups when more food/home/water/entrance objects
    are available, results will be summarized for all common object types.
    It can be changed if needed of course...

    :param barcodes: global list of barcodes (Barcode)
            structured like this: [framenum][coloridindex][index]
    :param light_log: dictionary of light changes created by
            trajognize.util.parse_log_file()
    :param cage_log: dictionary of cage center changes created by
            trajognize.util.parse_log_file()
    :param entrytimes: dictionary of entry times created by
            trajognize.parse.parse_entry_times()
    :param starttime: datetime of the first frame of the current video
    :param project_settings: global project settings imported by
            trajognize.settings.import_trajognize_settings_from_file()
    :param experiment: the current experiment that defines rat groups, walls and
            interesting object centers. If experiment is None,
            we do not calculate anything.

    """
    colorids = project_settings.colorids
    # initialize object
    id_count = len(barcodes[0])
    dailyobj = init.DailyObj(
        project_settings.good_light,
        project_settings.object_types,
        project_settings.max_day,
        id_count,
    )
    # do not calculate anything if we are not part of an experiment
    if experiment is None:
        return dailyobj
    # initialize light
    light_at_frame = trajognize.util.param_at_frame(light_log)
    cage_at_frame = trajognize.util.param_at_frame(cage_log)
    tempbarcode = trajognize.init.Barcode(MCHIPS=project_settings.MCHIPS)
    # iterate for all frames
    for currentframe in range(len(barcodes)):
        # get current time
        datetime_at_frame = trajognize.util.get_datetime_at_frame(
            starttime, currentframe, project_settings.FPS
        )
        # get day
        day = trajognize.stat.experiments.get_days_since_start(
            experiment, datetime_at_frame
        )
        # check entry times and skip current frame if not valid
        if trajognize.util.is_entry_time(entrytimes, datetime_at_frame):
            continue
        # get light and skip bad lighting conditions
        light = light_at_frame(currentframe)
        if light not in project_settings.good_light:
            continue
        # get cage
        cagecenter = cage_at_frame(currentframe)
        # get chosen barcodes
        chosens = util.get_chosen_barcodes(barcodes[currentframe])
        # store number of barcodes in the proper time bin
        for k in range(id_count):
            strid = colorids[k]
            if chosens[k] is None:
                continue
            # get center and skip bad ones: nan or outside image area
            tempbarcode.centerx = chosens[k].centerx
            tempbarcode.centery = chosens[k].centery
            if project_settings.correct_cage:
                tempbarcode.centerx += project_settings.cage_center.x - cagecenter[0]
                tempbarcode.centery += project_settings.cage_center.y - cagecenter[1]
            if (
                tempbarcode.centerx != tempbarcode.centerx
                or tempbarcode.centerx >= project_settings.image_size.x
                or tempbarcode.centerx < 0
            ):
                continue
            if (
                tempbarcode.centery != tempbarcode.centery
                or tempbarcode.centery >= project_settings.image_size.y
                or tempbarcode.centery < 0
            ):
                continue
            # check if barcode is under any object of the group
            num = [0] * len(project_settings.object_types)
            group = experiment["groupid"][strid]
            for i in range(len(project_settings.object_types)):
                object = project_settings.object_types[i]
                if object not in experiment.keys():
                    continue
                for objectcenter in experiment[object][group]:
                    if experiments.is_barcode_under_object(
                        tempbarcode,
                        objectcenter,
                        project_settings.object_areas[object],
                        project_settings.image_size,
                    ):
                        num[i] = 1
                        break
                else:
                    continue
                break
            # calculate new avg, std, num based on this method:
            # http://en.wikipedia.org/wiki/Standard_deviation#Rapid_calculation_methods
            for i in range(len(project_settings.object_types)):
                prev_avg = dailyobj.avg[light][k, i, day]
                dailyobj.num[light][k, i, day] += 1
                dailyobj.avg[light][k, i, day] += (num[i] - prev_avg) / dailyobj.num[
                    light
                ][k, i, day]
                dailyobj.stv[light][k, i, day] += (num[i] - prev_avg) * (
                    num[i] - dailyobj.avg[light][k, i, day]
                )
            dailyobj.points[light] += 1
        dailyobj.frames[light] += 1
    dailyobj.files = 1
    return dailyobj


def calculate_sameiddist(barcodes, light_log, entrytimes, starttime, project_settings):
    """Calculate distributions of number of barcodes of the same ID.

    This stat is a debug stat. Final output contains 1 chosen only...

    :param barcodes: global list of barcodes (Barcode)
            structured like this: [framenum][coloridindex][index]
    :param light_log: dictionary of light changes created by
            trajognize.util.parse_log_file()
    :param entrytimes: dictionary of entry times created by
            trajognize.parse.parse_entry_times()
    :param starttime: datetime of the first frame of the current video
    :param project_settings: global project settings imported by
            trajognize.settings.import_trajognize_settings_from_file()

    """
    light_at_frame = trajognize.util.param_at_frame(light_log)
    id_count = len(barcodes[0])
    sameiddists = init.SameIDDist(project_settings.good_light, id_count)
    for currentframe in range(len(barcodes)):
        # check entry times and skip current frame if not valid
        if trajognize.util.is_entry_time(
            entrytimes,
            trajognize.util.get_datetime_at_frame(
                starttime, currentframe, project_settings.FPS
            ),
        ):
            continue
        # get light and skip bad lighting conditions
        light = light_at_frame(currentframe)
        if light not in project_settings.good_light:
            continue
        for k in range(id_count):
            # get number of barcodes
            num = len(barcodes[currentframe][k])
            sameiddists.points[light][0] += num
            # store all (including deleted)
            if num <= sameiddists.max_same_id:
                sameiddists.data[light][k, 0, num] += 1
                sameiddists.data[light][id_count, 0, num] += 1
            # store good ones (excluding deleted)
            for barcode in barcodes[currentframe][k]:
                if not barcode.mfix or barcode.mfix & trajognize.init.MFix.DELETED:
                    num -= 1
            sameiddists.points[light][1] += num
            if num <= sameiddists.max_same_id:
                sameiddists.data[light][k, 1, num] += 1
                sameiddists.data[light][id_count, 1, num] += 1
        sameiddists.frames[light] += 1
    sameiddists.files = 1
    return sameiddists


def calculate_nearestneighbor(
    barcodes, light_log, cage_log, entrytimes, starttime, project_settings, experiment
):
    """Calculate nearest neighbor occurence matrix.

    :param barcodes: global list of barcodes (Barcode)
            structured like this: [framenum][coloridindex][index]
    :param light_log: dictionary of light changes created by
            trajognize.util.parse_log_file()
    :param cage_log: dictionary of cage center changes created by
            trajognize.util.parse_log_file()
    :param entrytimes: dictionary of entry times created by
            trajognize.parse.parse_entry_times()
    :param starttime: datetime of the first frame of the current video
    :param project_settings: global project settings imported by
            trajognize.settings.import_trajognize_settings_from_file()
    :param experiment: the current experiment that defines rat groups
            to avoid nearest neighbors through walls. If experiment is None,
            we do not calculate anything.

    Pairs are skipped if:
        - they are not in the same experiment
        - there is a cage wall between them
        - they are not chosen barcodes
        - they are not in their own valid cage

    WARNING: no real world coordinate transformation is implemented yet.

    """
    colorids = project_settings.colorids
    light_at_frame = trajognize.util.param_at_frame(light_log)
    cage_at_frame = trajognize.util.param_at_frame(cage_log)
    id_count = len(barcodes[0])
    nearestneighbors = init.NearestNeighbor(project_settings.good_light, id_count)
    # do not calculate anything if we are not part of an experiment
    if experiment is None:
        return nearestneighbors
    for currentframe in range(len(barcodes)):
        # check entry times and skip current frame if not valid
        if trajognize.util.is_entry_time(
            entrytimes,
            trajognize.util.get_datetime_at_frame(
                starttime, currentframe, project_settings.FPS
            ),
        ):
            continue
        # get light and skip bad lighting conditions
        light = light_at_frame(currentframe)
        if light not in project_settings.good_light:
            continue
        # get cage
        cagecenter = cage_at_frame(currentframe)
        # get chosen barcodes for current frame
        chosens = util.get_chosen_barcodes(barcodes[currentframe])
        # get nearest neighbors
        for i in range(id_count):
            if not chosens[i]:
                continue
            # get center and skip bad ones: nan or outside image area
            barcode = chosens[i]
            cx = barcode.centerx
            cy = barcode.centery
            if project_settings.correct_cage:
                cx += project_settings.cage_center.x - cagecenter[0]
                cy += project_settings.cage_center.y - cagecenter[1]
            if cx != cx or cx >= project_settings.image_size.x or cx < 0:
                continue
            if cy != cy or cy >= project_settings.image_size.y or cy < 0:
                continue
            # filter results based on whether pateks are inside their own cage/territory
            if project_settings.filter_for_valid_cage:
                pos = trajognize.init.Point(cx, cy)
                group = experiment["groupid"][colorids[i]]
                for poly in experiment["wallall"][group]:
                    if util.is_inside_polygon(pos, poly):
                        break
                else:
                    continue
            # initialize min distance to something surely too big
            mindist = project_settings.image_size.x + project_settings.image_size.y
            k = None
            for j in range(id_count):
                if i == j or not chosens[j]:
                    continue
                # check for group consistency
                if not experiments.are_in_same_group(
                    colorids[i], colorids[j], experiment
                ):
                    continue
                # check for cage wall between them
                if experiments.is_wall_between(
                    chosens[i], chosens[j], cagecenter, project_settings.use_cage
                ):
                    continue
                # get center and skip bad ones: nan or outside image area
                barcode = chosens[j]
                cx = barcode.centerx
                cy = barcode.centery
                if project_settings.correct_cage:
                    cx += project_settings.cage_center.x - cagecenter[0]
                    cy += project_settings.cage_center.y - cagecenter[1]
                if cx != cx or cx >= project_settings.image_size.x or cx < 0:
                    continue
                if cy != cy or cy >= project_settings.image_size.y or cy < 0:
                    continue
                # filter results based on whether pateks are inside their own cage/territory
                if project_settings.filter_for_valid_cage:
                    pos = trajognize.init.Point(cx, cy)
                    for poly in experiment["wallall"][group]:
                        if util.is_inside_polygon(pos, poly):
                            break
                    else:
                        continue
                # get distance between barcodes
                dist = trajognize.algo.get_distance(chosens[i], chosens[j])
                if dist < mindist:
                    k = j
                    mindist = dist
            # store k as nearest neighbor to i
            if k is not None:
                nearestneighbors.data[light][2][i, k] += 1
                # get mfix_type
                mfi = util.get_mfi(chosens[i])
                mfk = util.get_mfi(chosens[k])
                # store both real
                if mfi == 0 and mfk == 0:
                    nearestneighbors.data[light][0][i, k] += 1
                # store both virtual
                elif mfi == 1 and mfk == 1:
                    nearestneighbors.data[light][1][i, k] += 1
                nearestneighbors.points[light] += 1
        nearestneighbors.frames[light] += 1
    nearestneighbors.files = 1
    return nearestneighbors


def calculate_neighbor(
    barcodes, light_log, cage_log, entrytimes, starttime, project_settings, experiment
):
    """Calculate neighbor matrices and neighbor number distributions.

    :param barcodes: global list of barcodes (Barcode)
            structured like this: [framenum][coloridindex][index]
    :param light_log: dictionary of light changes created by
            trajognize.util.parse_log_file()
    :param cage_log: dictionary of cage center changes created by
            trajognize.util.parse_log_file()
    :param entrytimes: dictionary of entry times created by
            trajognize.parse.parse_entry_times()
    :param starttime: datetime of the first frame of the current video
    :param project_settings: global project settings imported by
            trajognize.settings.import_trajognize_settings_from_file()
    :param experiment: the current experiment that defines rat groups
            to avoid nearest neighbors through walls. If experiment is None,
            we do not calculate anything.

    Pairs are skipped if:
        - they are not in the same experiment
        - there is a cage wall between them
        - they are not chosen barcodes

    WARNING: no real world coordinate transformation is implemented yet.

    """
    colorids = project_settings.colorids
    light_at_frame = trajognize.util.param_at_frame(light_log)
    cage_at_frame = trajognize.util.param_at_frame(cage_log)
    id_count = len(barcodes[0])
    neighbors = init.Neighbor(
        project_settings.good_light, project_settings.max_day, id_count
    )
    # do not calculate anything if we are not part of an experiment
    if experiment is None:
        return neighbors
    for currentframe in range(len(barcodes)):
        # get current day
        datetime_at_frame = trajognize.util.get_datetime_at_frame(
            starttime, currentframe, project_settings.FPS
        )
        day = trajognize.stat.experiments.get_days_since_start(
            experiment, datetime_at_frame
        )
        # check entry times and skip current frame if not valid
        if trajognize.util.is_entry_time(entrytimes, datetime_at_frame):
            continue
        # get light and skip bad lighting conditions
        light = light_at_frame(currentframe)
        if light not in project_settings.good_light:
            continue
        # get cage
        cagecenter = cage_at_frame(currentframe)
        # get chosen barcodes for current frame
        chosens = util.get_chosen_barcodes(barcodes[currentframe])
        # get neighbors
        for i in range(id_count):
            if not chosens[i]:
                continue
            barcode = chosens[i]
            # get center and skip bad ones: nan or outside image area
            cx = barcode.centerx
            cy = barcode.centery
            if project_settings.correct_cage:
                cx += project_settings.cage_center.x - cagecenter[0]
                cy += project_settings.cage_center.y - cagecenter[1]
            if cx != cx or cx >= project_settings.image_size.x or cx < 0:
                continue
            if cy != cy or cy >= project_settings.image_size.y or cy < 0:
                continue
            # filter results based on whether pateks are inside their own cage/territory
            if project_settings.filter_for_valid_cage:
                pos = trajognize.init.Point(cx, cy)
                group = experiment["groupid"][colorids[i]]
                for poly in experiment["wallall"][group]:
                    if util.is_inside_polygon(pos, poly):
                        break
                else:
                    continue
            num = 0
            # initialize min distance to something surely too big
            for j in range(id_count):
                if i == j or not chosens[j]:
                    continue
                # check for group consistency
                if not experiments.are_in_same_group(
                    colorids[i], colorids[j], experiment
                ):
                    continue
                # check for cage wall between them
                if experiments.is_wall_between(
                    chosens[i], chosens[j], cagecenter, project_settings.use_cage
                ):
                    continue
                barcode = chosens[j]
                # get center and skip bad ones: nan or outside image area
                cx = barcode.centerx
                cy = barcode.centery
                if project_settings.correct_cage:
                    cx += project_settings.cage_center.x - cagecenter[0]
                    cy += project_settings.cage_center.y - cagecenter[1]
                if cx != cx or cx >= project_settings.image_size.x or cx < 0:
                    continue
                if cy != cy or cy >= project_settings.image_size.y or cy < 0:
                    continue
                # filter results based on whether pateks are inside their own cage/territory
                if project_settings.filter_for_valid_cage:
                    pos = trajognize.init.Point(cx, cy)
                    for poly in experiment["wallall"][group]:
                        if util.is_inside_polygon(pos, poly):
                            break
                    else:
                        continue
                # check distance between barcodes
                if (
                    trajognize.algo.get_distance(chosens[i], chosens[j])
                    < neighbors.distance_threshold
                ):
                    num += 1
                    neighbors.data[light][0][day][i, j] += 1
                    neighbors.points[light] += 1
            neighbors.data[light][1][day][i, num] += 1
        neighbors.frames[light] += 1
    neighbors.files = 1
    return neighbors


def calculate_dailyfqobj(
    barcodes, light_log, cage_log, entrytimes, starttime, project_settings, experiment
):
    """Calculate daily generalized FQ matrix, i.e. pairwise OR norm over/queuing
    object relations.

    :param barcodes: global list of barcodes (Barcode)
            structured like this: [framenum][coloridindex][index]
    :param light_log: dictionary of light changes created by
            trajognize.util.parse_log_file()
    :param cage_log: dictionary of cage center changes created by
            trajognize.util.parse_log_file()
    :param entrytimes: dictionary of entry times created by
            trajognize.parse.parse_entry_times()
    :param starttime: datetime of the first frame of the current video
    :param project_settings: global project settings imported by
            trajognize.settings.import_trajognize_settings_from_file()
    :param experiment: the current experiment that defines rat groups, walls and
            interesting object centers. If experiment is None,
            we do not calculate anything.

    This stat is special in the way that it calls calculate_fqobj() with an
    extra parameter to calculate data on a daily basis. For more details see
    fqobj stat.

    """
    colorids = project_settings.colorids
    dailyfqobj = init.DailyFQObj(
        project_settings.good_light,
        project_settings.object_types,
        project_settings.max_day,
        len(colorids),
    )
    calculate_fqobj(
        barcodes,
        light_log,
        cage_log,
        entrytimes,
        starttime,
        project_settings,
        experiment,
        dailyfqobj,
    )
    return dailyfqobj


def calculate_fqfood(
    barcodes, light_log, cage_log, entrytimes, starttime, project_settings, experiment
):
    """Calculate real feeding-queuing matrix, i.e. pairwise OR norm
    feeding/queuing relations for real feeding times (and no friday).

    :param barcodes: global list of barcodes (Barcode)
            structured like this: [framenum][coloridindex][index]
    :param light_log: dictionary of light changes created by
            trajognize.util.parse_log_file()
    :param cage_log: dictionary of cage center changes created by
            trajognize.util.parse_log_file()
    :param entrytimes: dictionary of entry times created by
            trajognize.parse.parse_entry_times()
    :param starttime: datetime of the first frame of the current video
    :param project_settings: global project settings imported by
            trajognize.settings.import_trajognize_settings_from_file()
    :param experiment: the current experiment that defines rat groups, walls and
            interesting object centers. If experiment is None,
            we do not calculate anything.

    This stat is special in the way that it calls calculate_fqobj() with an
    extra parameter. For more details see fqobj stat.

    """
    colorids = project_settings.colorids
    fqfood = init.FQFood(project_settings.good_light, len(colorids))
    calculate_fqobj(
        barcodes,
        light_log,
        cage_log,
        entrytimes,
        starttime,
        project_settings,
        experiment,
        None,
        fqfood,
    )
    return fqfood


def calculate_fqwhilef(
    barcodes, light_log, cage_log, entrytimes, starttime, project_settings, experiment
):
    """Calculate how many others are feeding or queuing while one is feeding
    during real feeding times (and no friday).

    :param barcodes: global list of barcodes (Barcode)
            structured like this: [framenum][coloridindex][index]
    :param light_log: dictionary of light changes created by
            trajognize.util.parse_log_file()
    :param cage_log: dictionary of cage center changes created by
            trajognize.util.parse_log_file()
    :param entrytimes: dictionary of entry times created by
            trajognize.parse.parse_entry_times()
    :param starttime: datetime of the first frame of the current video
    :param project_settings: global project settings imported by
            trajognize.settings.import_trajognize_settings_from_file()
    :param experiment: the current experiment that defines rat groups, walls and
            interesting object centers. If experiment is None,
            we do not calculate anything.

    This stat is special in the way that it calls calculate_fqobj() with an
    extra parameter. For more details see fqobj stat.

    """
    colorids = project_settings.colorids
    fqwhilef = init.FQWhileF(
        project_settings.good_light, project_settings.object_types, len(colorids)
    )
    calculate_fqobj(
        barcodes,
        light_log,
        cage_log,
        entrytimes,
        starttime,
        project_settings,
        experiment,
        None,
        None,
        fqwhilef,
    )
    return fqwhilef


def calculate_fqobj(
    barcodes,
    light_log,
    cage_log,
    entrytimes,
    starttime,
    project_settings,
    experiment,
    dailyfqobj=None,
    fqfood=None,
    fqwhilef=None,
):
    """Calculate generalized FQ matrix, i.e. pairwise OR norm over/queuing
    object relations.

    :param barcodes: global list of barcodes (Barcode)
            structured like this: [framenum][coloridindex][index]
    :param light_log: dictionary of light changes created by
            trajognize.util.parse_log_file()
    :param cage_log: dictionary of cage center changes created by
            trajognize.util.parse_log_file()
    :param entrytimes: dictionary of entry times created by
            trajognize.parse.parse_entry_times()
    :param starttime: datetime of the first frame of the current video
    :param project_settings: global project settings imported by
            trajognize.settings.import_trajognize_settings_from_file()
    :param experiment: the current experiment that defines rat groups, walls and
            interesting object centers. If experiment is None,
            we do not calculate anything.
    :param dailyfqobj: optional param to save results on daily basis. It is used
            for the DailyFQObj stat.
    :param fqfood: optional param to save results for food restricted to real
            feeding times (and exculding friday). It is used for the FQFood stat.

    Pairs are skipped if:
        - they are not in the same group
        - there is a cage wall between them
        - they are not chosen barcodes

    WARNING: no real world coordinate transformation is implemented yet.

    TODO: how to take into account REAL/VIRTUAL?
    TODO: implement closestFQ

    """
    colorids = project_settings.colorids
    assert not (
        (dailyfqobj and fqfood) or (dailyfqobj and fqwhilef) or (fqfood and fqwhilef)
    )
    light_at_frame = trajognize.util.param_at_frame(light_log)
    cage_at_frame = trajognize.util.param_at_frame(cage_log)
    id_count = len(barcodes[0])
    fqobj = init.FQObj(
        project_settings.good_light, project_settings.object_types, id_count
    )
    # do not calculate anything if we are not part of an experiment
    if experiment is None:
        return fqobj
    for currentframe in range(len(barcodes)):
        # get current time
        datetime_at_frame = trajognize.util.get_datetime_at_frame(
            starttime, currentframe, project_settings.FPS
        )
        # get day if needed
        if dailyfqobj is not None:
            day = trajognize.stat.experiments.get_days_since_start(
                experiment, datetime_at_frame
            )
        # check entry times and skip current frame if not valid
        if trajognize.util.is_entry_time(entrytimes, datetime_at_frame):
            continue
        # restrict stat to feeding time (-friday) for fqfood
        if fqfood is not None:
            # we exclude fridays (True) and non-feeding times in general
            if not experiments.is_weekly_feeding_time(
                datetime_at_frame, project_settings.weekly_feeding_times, True
            ):
                continue
        # get light and skip bad lighting conditions
        light = light_at_frame(currentframe)
        if light not in project_settings.good_light:
            continue
        # get cage
        cagecenter = cage_at_frame(currentframe)
        # get chosen barcodes for current frame
        chosens = util.get_chosen_barcodes(barcodes[currentframe])
        if fqwhilef is not None:
            who_is_f = [
                [0] * id_count for i in range(len(project_settings.object_types))
            ]  # who is feeding
            who_is_fq = [
                [0] * id_count for i in range(len(project_settings.object_types))
            ]  # who is feeding or queuing?
        # iterate colorids i
        for i in range(id_count):
            if not chosens[i]:
                continue
            a = trajognize.init.Barcode(
                chosens[i].centerx,
                chosens[i].centery,
                chosens[i].orientation,
                MCHIPS=project_settings.MCHIPS,
            )
            if project_settings.correct_cage:
                a.centerx += project_settings.cage_center.x - cagecenter[0]
                a.centery += project_settings.cage_center.y - cagecenter[1]
            if (
                a.centerx != a.centerx
                or a.centerx >= project_settings.image_size.x
                or a.centerx < 0
            ):
                continue
            if (
                a.centery != a.centery
                or a.centery >= project_settings.image_size.y
                or a.centery < 0
            ):
                continue
            # iterate colorids j
            for j in range(id_count):
                if i == j or not chosens[j]:
                    continue
                b = trajognize.init.Barcode(
                    chosens[j].centerx,
                    chosens[j].centery,
                    chosens[j].orientation,
                    MCHIPS=project_settings.MCHIPS,
                )
                if project_settings.correct_cage:
                    b.centerx += project_settings.cage_center.x - cagecenter[0]
                    b.centery += project_settings.cage_center.y - cagecenter[1]
                if (
                    b.centerx != b.centerx
                    or b.centerx >= project_settings.image_size.x
                    or b.centerx < 0
                ):
                    continue
                if (
                    b.centery != b.centery
                    or b.centery >= project_settings.image_size.y
                    or b.centery < 0
                ):
                    continue
                # check for group consistency
                if not experiments.are_in_same_group(
                    colorids[i], colorids[j], experiment
                ):
                    continue
                group = experiment["groupid"][colorids[i]]
                # check for cage wall between them (we check on original coords, not corrected)
                if experiments.is_wall_between(
                    chosens[i], chosens[j], cagecenter, project_settings.use_cage
                ):
                    continue

                # TODO: check if they are nearest neighbours or not!

                # iterate all objects
                for obi in range(len(project_settings.object_types)):
                    obj = project_settings.object_types[obi]
                    if obj not in experiment.keys():
                        continue
                    if not experiments.is_object_queueable(
                        project_settings.object_queuing_areas[obj]
                    ):
                        continue
                    # fqfood is only calculated for 'food' object
                    if fqfood is not None:
                        if obj != "food":
                            continue
                    # fqwhilef is calculated for all objects, but for food only for feeding times
                    elif fqwhilef is not None:
                        # we exclude fridays (True) and non-feeding times in general
                        if obj == "food" and not experiments.is_weekly_feeding_time(
                            datetime_at_frame,
                            project_settings.weekly_feeding_times,
                            True,
                        ):
                            continue
                    for objectcenter in experiment[obj][group]:
                        # check angle, skip if not pointing towards object center +- 90deg
                        bangle = atan2(
                            objectcenter.y - b.centery, objectcenter.x - b.centerx
                        )
                        if cos(bangle - b.orientation) < 0:
                            continue
                        # check F and Q states
                        if experiments.is_barcode_under_object(
                            a,
                            objectcenter,
                            project_settings.object_areas[obj],
                            project_settings.image_size,
                        ):
                            fa = True
                        else:
                            fa = False
                        if experiments.is_barcode_under_object(
                            b,
                            objectcenter,
                            project_settings.object_areas[obj],
                            project_settings.image_size,
                        ):
                            fb = True
                        else:
                            fb = False
                        if experiments.is_barcode_under_object(
                            a,
                            objectcenter,
                            project_settings.object_queuing_areas[obj],
                            project_settings.image_size,
                        ):
                            qa = True
                        else:
                            qa = False
                        if experiments.is_barcode_under_object(
                            b,
                            objectcenter,
                            project_settings.object_queuing_areas[obj],
                            project_settings.image_size,
                        ):
                            qb = True
                        else:
                            qb = False
                        # set results
                        if qa or qb:
                            if dailyfqobj is not None:
                                dailyfqobj.qorq[light][obi, i, j, day] += 1
                            elif fqfood is not None:
                                fqfood.qorq[light][i, j] += 1
                            elif fqwhilef is not None:
                                if fa and qb:
                                    who_is_f[obi][i] = 1
                                    who_is_fq[obi][j] = 1
                            else:
                                fqobj.qorq[light][obi, i, j] += 1
                            if fa and qb and not fb:
                                if dailyfqobj is not None:
                                    dailyfqobj.fandq[light][obi, i, j, day] += 1
                                    dailyfqobj.points[light] += 1
                                elif fqfood is not None:
                                    fqfood.fandq[light][i, j] += 1
                                    fqfood.points[light] += 1
                                elif fqwhilef is not None:
                                    pass
                                else:
                                    fqobj.fandq[light][obi, i, j] += 1
                                    fqobj.points[light] += 1
        if fqwhilef is not None:
            for obi in range(len(project_settings.object_types)):
                for i in range(id_count):
                    if who_is_f[obi][i]:
                        # count number of ForQ-ing others
                        fqwhilef.data[light][obi, i, sum(who_is_fq[obi]) - 1] += 1
                        fqwhilef.points[light] += 1
        fqobj.frames[light] += 1
    if dailyfqobj is not None:
        # no return needed, we write to dailyfqobj param pointer
        for light in project_settings.good_light:
            dailyfqobj.frames[light] = fqobj.frames[light]
        dailyfqobj.files = 1
    elif fqfood is not None:
        # no return needed, we write to fqfood param pointer
        for light in project_settings.good_light:
            fqfood.frames[light] = fqobj.frames[light]
        fqfood.files = 1
    elif fqwhilef is not None:
        # no return needed, we write to fqwhilef param pointer
        for light in project_settings.good_light:
            fqwhilef.frames[light] = fqobj.frames[light]
        fqwhilef.files = 1
    else:
        fqobj.files = 1
        return fqobj


def calculate_aamap(
    barcodes,
    light_log,
    cage_log,
    entrytimes,
    starttime,
    project_settings,
    experiment,
    subtitlefile,
):
    """Calculate AA (approach-avoidance) heatmap.

    :param barcodes: global list of barcodes (Barcode)
            structured like this: [framenum][coloridindex][index]
    :param light_log: dictionary of light changes created by
            trajognize.util.parse_log_file()
    :param cage_log: dictionary of cage center changes created by
            trajognize.util.parse_log_file()
    :param entrytimes: dictionary of entry times created by
            trajognize.parse.parse_entry_times()
    :param starttime: datetime of the first frame of the current video
    :param project_settings: global project settings imported by
            trajognize.settings.import_trajognize_settings_from_file()
    :param experiment: the current experiment that defines rat groups, walls and
            interesting object centers. If experiment is None,
            we do not calculate anything.
    :param subtitlefile: write subtitles to this file (None if not applicable)

    This stat is special in the way that it calls calculate_aa() with an extra
    parameter to plot data to heatmap. For more details see aa stat.

    WARNING: no cage correction is defined on aamap yet

    """
    aamap = init.AAMap(project_settings.good_light, project_settings.image_size)
    calculate_aa(
        barcodes,
        light_log,
        cage_log,
        entrytimes,
        starttime,
        project_settings,
        experiment,
        subtitlefile,
        aamap,
    )
    return aamap


def calculate_aa(
    barcodes,
    light_log,
    cage_log,
    entrytimes,
    starttime,
    project_settings,
    experiment,
    subtitlefile,
    aamap=None,
):
    """Calculate AA (approach-avoidance) matrix.

    :param barcodes: global list of barcodes (Barcode)
            structured like this: [framenum][coloridindex][index]
    :param light_log: dictionary of light changes created by
            trajognize.util.parse_log_file()
    :param cage_log: dictionary of cage center changes created by
            trajognize.util.parse_log_file()
    :param entrytimes: dictionary of entry times created by
            trajognize.parse.parse_entry_times()
    :param starttime: datetime of the first frame of the current video
    :param project_settings: global project settings imported by
            trajognize.settings.import_trajognize_settings_from_file()
    :param experiment: the current experiment that defines rat groups, walls and
            interesting object centers. If experiment is None,
            we do not calculate anything.
    :param subtitlefile: write subtitles to this file (None if not applicable)
    :param aamap: optional 'hack' parameter to output results to a map
            instead of the standard AA statistics. It is used by stat aamap.

    Pairs are skipped if:
        - they are not in the same group
        - there is a cage wall between them
        - they are not chosen barcodes
        - they are not in their own valid cage

    WARNING: no real world coordinate transformation is implemented yet.
    WARNING: no cage correction is defined on aamap yet

    """
    colorids = project_settings.colorids
    light_at_frame = trajognize.util.param_at_frame(light_log)
    cage_at_frame = trajognize.util.param_at_frame(cage_log)
    id_count = len(barcodes[0])
    aa = init.AA(
        project_settings.good_light, id_count, project_settings.stat_aa_settings
    )
    history = [
        [[-aa.min_event_length] * aa.min_event_length for i in range(id_count)]
        for j in range(id_count)
    ]
    # do not calculate anything if we are not part of an experiment
    if experiment is None:
        return aa
    prevchosens = util.get_chosen_barcodes(barcodes[0])
    prevframe = 0
    if subtitlefile is not None:
        subtitlefile.write("#frame\tID1\tx1\ty1\tID2\tx2\ty2\n")
        subtitleindex = 0
    for currentframe in range(1, len(barcodes)):
        # check entry times and skip current frame if not valid
        if trajognize.util.is_entry_time(
            entrytimes,
            trajognize.util.get_datetime_at_frame(
                starttime, currentframe, project_settings.FPS
            ),
        ):
            continue
        # get light and skip bad lighting conditions
        light = light_at_frame(currentframe)
        if light not in project_settings.good_light:
            continue
        # get cage
        cagecenter = cage_at_frame(currentframe)
        # get chosen barcodes for current frame
        chosens = util.get_chosen_barcodes(barcodes[currentframe])
        if currentframe == prevframe + 1:
            # iterate colorids i
            for i in range(id_count):
                if not chosens[i] or not prevchosens[i]:
                    continue
                # get center and skip bad ones: nan or outside image area
                barcode = chosens[i]
                cx = barcode.centerx
                cy = barcode.centery
                if project_settings.correct_cage:
                    cx += project_settings.cage_center.x - cagecenter[0]
                    cy += project_settings.cage_center.y - cagecenter[1]
                if cx != cx or cx >= project_settings.image_size.x or cx < 0:
                    continue
                if cy != cy or cy >= project_settings.image_size.y or cy < 0:
                    continue
                # filter results based on whether pateks are inside their own cage/territory
                if project_settings.filter_for_valid_cage:
                    pos = trajognize.init.Point(cx, cy)
                    group = experiment["groupid"][colorids[i]]
                    for poly in experiment["wallall"][group]:
                        if util.is_inside_polygon(pos, poly):
                            break
                    else:
                        continue
                # iterate colorids j
                for j in range(id_count):
                    if i == j or not chosens[j] or not prevchosens[j]:
                        continue
                    # check for group consistency
                    if not experiments.are_in_same_group(
                        colorids[i], colorids[j], experiment
                    ):
                        continue
                    group = experiment["groupid"][colorids[i]]
                    # check for cage wall between them
                    if experiments.is_wall_between(
                        chosens[i], chosens[j], cagecenter, project_settings.use_cage
                    ):
                        continue
                    # get center and skip bad ones: nan or outside image area
                    barcode = chosens[j]
                    cx = barcode.centerx
                    cy = barcode.centery
                    if project_settings.correct_cage:
                        cx += project_settings.cage_center.x - cagecenter[0]
                        cy += project_settings.cage_center.y - cagecenter[1]
                    if cx != cx or cx >= project_settings.image_size.x or cx < 0:
                        continue
                    if cy != cy or cy >= project_settings.image_size.y or cy < 0:
                        continue
                    # filter results based on whether pateks are inside their own cage/territory
                    if project_settings.filter_for_valid_cage:
                        pos = trajognize.init.Point(cx, cy)
                        for poly in experiment["wallall"][group]:
                            if util.is_inside_polygon(pos, poly):
                                break
                        else:
                            continue

                    # get velocity of approacher (a)
                    vax = chosens[i].centerx - prevchosens[i].centerx
                    vay = chosens[i].centery - prevchosens[i].centery
                    va = hypot(vax, vay)
                    # skip slow approacher
                    if va < aa.approacher_velocity_threshold:
                        continue

                    # #Mate20190524
                    # get orientation of the approacher and check whether he is
                    # moving forward as compared to it orientation
                    oax = cos(chosens[i].orientation)
                    oay = sin(chosens[i].orientation)
                    # skip if the angle between the orienation and the velocity
                    # is not small enough
                    cos_ori_vel_approacher = (vax * oax + vay * oay) / va
                    if cos_ori_vel_approacher < cos(radians(30)):
                        continue

                    # get velocity of avoider (b)
                    vbx = chosens[j].centerx - prevchosens[j].centerx
                    vby = chosens[j].centery - prevchosens[j].centery
                    vb = hypot(vbx, vby)
                    # skip slow avoider
                    if vb < aa.avoider_velocity_threshold:
                        continue

                    # get distance between the two
                    dx = chosens[j].centerx - chosens[i].centerx
                    dy = chosens[j].centery - chosens[i].centery
                    d = hypot(dx, dy)
                    # skips ones on each other and far away
                    if not d or d > aa.distance_threshold:
                        continue

                    # get approacher angle and skip bad ones
                    # # v_i * d_ij / ||v_i|| ||d||
                    cos_approacher = (vax * dx + vay * dy) / (d * va)
                    if cos_approacher < aa.cos_approacher_threshold:
                        continue
                    # get avoider angle and skip bad ones
                    # v_j * d_ij / ||v_j|| ||d||
                    cos_avoider = (vbx * dx + vby * dy) / (d * vb)
                    if cos_avoider < aa.cos_avoider_threshold:
                        continue

                    # save it in history and perform multi-frame continouity check
                    # note that it won't work on actions between two videos
                    history[i][j].pop(0)
                    history[i][j].append(currentframe)
                    if (
                        history[i][j][aa.min_event_length - aa.min_event_count]
                        < currentframe - aa.min_event_length + 1
                    ):
                        continue

                    if aamap is None:
                        aa.data[light][i, j] += 1
                        aa.points[light] += 1
                        # write event to subtitlefile, if needed
                        if subtitlefile is not None:
                            subtitleindex += 1
                            #                             msg = util.get_subtitle_string(
                            #                                     subtitleindex,
                            #                                     currentframe/float(project_settings.FPS),
                            #                                     "%s -> %s" % (colorids[i], colorids[j]),
                            #                                     "#ffffff",
                            #                                     (chosens[i].centerx + chosens[j].centerx)/2.0,
                            #                                     (chosens[i].centery + chosens[j].centery)/2.0,
                            #                                     project_settings.image_size.x,
                            #                                     project_settings.image_size.y)
                            msg = "%d\t%s\t%g\t%g\t%s\t%g\t%g\n" % (
                                currentframe,
                                colorids[i],
                                chosens[i].centerx,
                                chosens[i].centery,
                                colorids[j],
                                chosens[j].centerx,
                                chosens[j].centery,
                            )
                            subtitlefile.write(msg)
                    # store AA as point on a heatmap for AAMap stat
                    else:
                        va = int(va)
                        dvx = vax / va  # deliberately not (v-1)
                        dvy = vay / va  # deliberately not (v-1)
                        # store velocity-number-of-points interpolated between
                        # the two positions (on prev frame and current frame)
                        # skipping exact position on current frame (will be added
                        # to next frame if velocity is still large...)
                        for ii in range(va):
                            x = int(prevchosens[i].centerx + ii * dvx)
                            if x < 0 or x >= project_settings.image_size.x:
                                continue
                            y = int(prevchosens[i].centery + ii * dvy)
                            if y < 0 or y >= project_settings.image_size.y:
                                continue
                            # store good ones on aamap
                            aamap.data[light][x][y] += 1
                        aamap.points[light] += 1
            if aamap is None:
                aa.frames[light] += 1
            else:
                aamap.frames[light] += 1
        prevchosens = chosens
        prevframe = currentframe
    if aamap is None:
        aa.files = 1
        return aa
    else:
        aamap.files = 1
        # no return needed, we write to aamap param pointer


def calculate_butthead(
    barcodes,
    light_log,
    cage_log,
    entrytimes,
    starttime,
    project_settings,
    experiment,
    subtitlefile,
):
    """Calculate butthead matrix.

    :param barcodes: global list of barcodes (Barcode)
            structured like this: [framenum][coloridindex][index]
    :param light_log: dictionary of light changes created by
            trajognize.util.parse_log_file()
    :param cage_log: dictionary of cage center changes created by
            trajognize.util.parse_log_file()
    :param entrytimes: dictionary of entry times created by
            trajognize.parse.parse_entry_times()
    :param starttime: datetime of the first frame of the current video
    :param project_settings: global project settings imported by
            trajognize.settings.import_trajognize_settings_from_file()
    :param experiment: the current experiment that defines rat groups, walls and
            interesting object centers. If experiment is None,
            we do not calculate anything.
    :param subtitlefile: write subtitles to this file (None if not applicable)

    Pairs are skipped if:
        - they are not in the same group
        - there is a cage wall between them
        - they are not chosen barcodes

    WARNING: no real world coordinate transformation is implemented yet.

    """
    colorids = project_settings.colorids
    light_at_frame = trajognize.util.param_at_frame(light_log)
    cage_at_frame = trajognize.util.param_at_frame(cage_log)
    id_count = len(barcodes[0])
    butthead = init.ButtHead(project_settings.good_light, id_count)
    # do not calculate anything if we are not part of an experiment
    if experiment is None:
        return butthead
    if subtitlefile is not None:
        subtitleindex = 0
    for currentframe in range(1, len(barcodes)):
        # check entry times and skip current frame if not valid
        if trajognize.util.is_entry_time(
            entrytimes,
            trajognize.util.get_datetime_at_frame(
                starttime, currentframe, project_settings.FPS
            ),
        ):
            continue
        # get light and skip bad lighting conditions
        light = light_at_frame(currentframe)
        if light not in project_settings.good_light:
            continue
        # get cage
        cagecenter = cage_at_frame(currentframe)
        # get chosen barcodes for current frame
        chosens = util.get_chosen_barcodes(barcodes[currentframe])
        # iterate colorids i
        for i in range(id_count):
            if not chosens[i]:
                continue
            # get center and skip bad ones: nan or outside image area
            barcode = chosens[i]
            cx = barcode.centerx
            cy = barcode.centery
            if project_settings.correct_cage:
                cx += project_settings.cage_center.x - cagecenter[0]
                cy += project_settings.cage_center.y - cagecenter[1]
            if cx != cx or cx >= project_settings.image_size.x or cx < 0:
                continue
            if cy != cy or cy >= project_settings.image_size.y or cy < 0:
                continue
            # filter results based on whether pateks are inside their own cage/territory
            if project_settings.filter_for_valid_cage:
                pos = trajognize.init.Point(cx, cy)
                group = experiment["groupid"][colorids[i]]
                for poly in experiment["wallall"][group]:
                    if util.is_inside_polygon(pos, poly):
                        break
                else:
                    continue
            # iterate colorids j
            for j in range(id_count):
                if i == j or not chosens[j]:
                    continue
                # check for group consistency
                if not experiments.are_in_same_group(
                    colorids[i], colorids[j], experiment
                ):
                    continue
                group = experiment["groupid"][colorids[i]]
                # check for cage wall between them
                if experiments.is_wall_between(
                    chosens[i], chosens[j], cagecenter, project_settings.use_cage
                ):
                    continue
                # get center and skip bad ones: nan or outside image area
                barcode = chosens[j]
                cx = barcode.centerx
                cy = barcode.centery
                if project_settings.correct_cage:
                    cx += project_settings.cage_center.x - cagecenter[0]
                    cy += project_settings.cage_center.y - cagecenter[1]
                if cx != cx or cx >= project_settings.image_size.x or cx < 0:
                    continue
                if cy != cy or cy >= project_settings.image_size.y or cy < 0:
                    continue
                # filter results based on whether pateks are inside their own cage/territory
                if project_settings.filter_for_valid_cage:
                    pos = trajognize.init.Point(cx, cy)
                    for poly in experiment["wallall"][group]:
                        if util.is_inside_polygon(pos, poly):
                            break
                    else:
                        continue

                # get behind-head point of approacher (halfway between center and head)
                ox = cos(chosens[i].orientation)
                oy = sin(chosens[i].orientation)
                hx = chosens[i].centerx + butthead.patek_length / 4 * ox
                hy = chosens[i].centery + butthead.patek_length / 4 * oy
                # get butt point of avoider
                bx = chosens[j].centerx - butthead.patek_length / 2 * cos(
                    chosens[j].orientation
                )
                by = chosens[j].centery - butthead.patek_length / 2 * sin(
                    chosens[j].orientation
                )
                # get distance between the two points
                dx = bx - hx
                dy = by - hy
                d = hypot(dx, dy)
                # skips ones on each other (p-->0) and
                # far away (distance limit is half-patek-length)
                if not d or d > butthead.patek_length / 2:
                    continue
                # get approacher angle and skip bad ones
                # # o_i * d_ij / ||o_i|| ||d||
                cos_approacher = (ox * dx + oy * dy) / d
                if cos_approacher < butthead.cos_approacher_threshold:
                    continue
                # store good data points
                butthead.data[light][i, j] += 1
                butthead.points[light] += 1
                # write event to subtitlefile, if needed
                if subtitlefile is not None:
                    subtitleindex += 1
                    msg = util.get_subtitle_string(
                        subtitleindex,
                        currentframe / float(project_settings.FPS),
                        "%s -> %s" % (colorids[i], colorids[j]),
                        "#0000ff",
                        (chosens[i].centerx + chosens[j].centerx) / 2.0,
                        (chosens[i].centery + chosens[j].centery) / 2.0,
                        project_settings.image_size.x,
                        project_settings.image_size.y,
                    )
                    #                            msg = "%d\t%s\t%g\t%g\t%s\t%g\t%g\n" % (
                    #                                    currentframe,
                    #                                    colorids[i], chosens[i].centerx, chosens[i].centery,
                    #                                    colorids[j], chosens[j].centerx, chosens[j].centery)
                    subtitlefile.write(msg)
        butthead.frames[light] += 1
    butthead.files = 1
    return butthead


def calculate_sdist(
    barcodes, light_log, cage_log, entrytimes, starttime, project_settings, experiment
):
    """Calculate spatial distance distribution of barcodes of
    different color on the same frame.

    :param barcodes: global list of barcodes (Barcode)
            structured like this: [framenum][coloridindex][index]
    :param light_log: dictionary of light changes created by
            trajognize.util.parse_log_file()
    :param cage_log: dictionary of cage center changes created by
            trajognize.util.parse_log_file()
    :param entrytimes: dictionary of entry times created by
            trajognize.parse.parse_entry_times()
    :param starttime: datetime of the first frame of the current video
    :param project_settings: global project settings imported by
            trajognize.settings.import_trajognize_settings_from_file()
    :param experiment: the current experiment that defines rat groups, walls and
            interesting object centers. If experiment is None,
            we do not calculate anything.

    Pairs are skipped if:
        - they are not in the same experiment
        - there is a cage wall between them
        - they are not chosen barcodes

    WARNING: no real world coordinate transformation is implemented yet.

    """
    colorids = project_settings.colorids
    light_at_frame = trajognize.util.param_at_frame(light_log)
    cage_at_frame = trajognize.util.param_at_frame(cage_log)
    id_count = len(barcodes[0])
    sdist = init.SDist(project_settings.good_light)
    # do not calculate anything if we are not part of an experiment
    if experiment is None:
        return sdist
    for currentframe in range(len(barcodes)):
        # check entry times and skip current frame if not valid
        if trajognize.util.is_entry_time(
            entrytimes,
            trajognize.util.get_datetime_at_frame(
                starttime, currentframe, project_settings.FPS
            ),
        ):
            continue
        # get light and skip bad lighting conditions
        light = light_at_frame(currentframe)
        if light not in project_settings.good_light:
            continue
        # get cage
        cagecenter = cage_at_frame(currentframe)
        # get chosen barcodes for current frame
        chosens = util.get_chosen_barcodes(barcodes[currentframe])
        # get spatial distance between them
        for i in range(id_count - 1):
            if not chosens[i]:
                continue
            # get center and skip bad ones: nan or outside image area
            barcode = chosens[i]
            cx = barcode.centerx
            cy = barcode.centery
            if project_settings.correct_cage:
                cx += project_settings.cage_center.x - cagecenter[0]
                cy += project_settings.cage_center.y - cagecenter[1]
            if cx != cx or cx >= project_settings.image_size.x or cx < 0:
                continue
            if cy != cy or cy >= project_settings.image_size.y or cy < 0:
                continue
            # filter results based on whether pateks are inside their own cage/territory
            if project_settings.filter_for_valid_cage:
                pos = trajognize.init.Point(cx, cy)
                group = experiment["groupid"][colorids[i]]
                for poly in experiment["wallall"][group]:
                    if util.is_inside_polygon(pos, poly):
                        break
                else:
                    continue
            for j in range(i + 1, id_count):
                if not chosens[j]:
                    continue
                # check for group consistency
                if not experiments.are_in_same_group(
                    colorids[i], colorids[j], experiment
                ):
                    continue
                # check for cage wall between them
                if experiments.is_wall_between(
                    chosens[i], chosens[j], cagecenter, project_settings.use_cage
                ):
                    continue
                # get center and skip bad ones: nan or outside image area
                barcode = chosens[i]
                cx = barcode.centerx
                cy = barcode.centery
                if project_settings.correct_cage:
                    cx += project_settings.cage_center.x - cagecenter[0]
                    cy += project_settings.cage_center.y - cagecenter[1]
                if cx != cx or cx >= project_settings.image_size.x or cx < 0:
                    continue
                if cy != cy or cy >= project_settings.image_size.y or cy < 0:
                    continue
                # filter results based on whether pateks are inside their own cage/territory
                if project_settings.filter_for_valid_cage:
                    pos = trajognize.init.Point(cx, cy)
                    for poly in experiment["wallall"][group]:
                        if util.is_inside_polygon(pos, poly):
                            break
                    else:
                        continue

                # get distance between barcodes
                dist = trajognize.algo.get_distance(chosens[i], chosens[j])
                if dist < sdist.maxdist:
                    sdist.data[light][int(dist)] += 1
                    sdist.points[light] += 1
        sdist.frames[light] += 1
    sdist.files = 1
    return sdist


def calculate_veldist(
    barcodes, light_log, cage_log, entrytimes, starttime, project_settings, experiment
):
    """Calculate velocity distribution of barcodes of same color from positions
    on consecutive frames.

    :param barcodes: global list of barcodes (Barcode)
            structured like this: [framenum][coloridindex][index]
    :param light_log: dictionary of light changes created by
            trajognize.util.parse_log_file()
    :param cage_log: dictionary of cage center changes created by
            trajognize.util.parse_log_file()
    :param entrytimes: dictionary of entry times created by
            trajognize.parse.parse_entry_times()
    :param starttime: datetime of the first frame of the current video
    :param project_settings: global project settings imported by
            trajognize.settings.import_trajognize_settings_from_file()
    :param experiment: the current experiment that defines rat groups, walls and
            interesting object centers. If experiment is None,
            we do not calculate anything.

    Barcodes are skipped if:
        - they are not chosen ones
        - they are not in their own valid cage


    WARNING: no real world coordinate transformation is implemented yet.

    """
    colorids = project_settings.colorids
    light_at_frame = trajognize.util.param_at_frame(light_log)
    cage_at_frame = trajognize.util.param_at_frame(cage_log)
    id_count = len(barcodes[0])
    veldist = init.VelDist(project_settings.good_light, id_count)
    prevchosens = util.get_chosen_barcodes(barcodes[0])
    prevframe = 0
    for currentframe in range(1, len(barcodes)):
        # get cage
        cagecenter = cage_at_frame(currentframe)
        # check entry times and skip current frame if not valid
        if trajognize.util.is_entry_time(
            entrytimes,
            trajognize.util.get_datetime_at_frame(
                starttime, currentframe, project_settings.FPS
            ),
        ):
            continue
        # get light and skip bad lighting conditions
        light = light_at_frame(currentframe)
        if light not in project_settings.good_light:
            continue
        chosens = util.get_chosen_barcodes(barcodes[currentframe])
        if currentframe == prevframe + 1:
            for k in range(id_count):
                if not chosens[k] or not prevchosens[k]:
                    continue
                # get center and skip bad ones: nan or outside image area
                barcode = chosens[k]
                cx = barcode.centerx
                cy = barcode.centery
                if project_settings.correct_cage:
                    cx += project_settings.cage_center.x - cagecenter[0]
                    cy += project_settings.cage_center.y - cagecenter[1]
                if cx != cx or cx >= project_settings.image_size.x or cx < 0:
                    continue
                if cy != cy or cy >= project_settings.image_size.y or cy < 0:
                    continue
                # filter results based on whether pateks are inside their own cage/territory
                if project_settings.filter_for_valid_cage:
                    pos = trajognize.init.Point(cx, cy)
                    group = experiment["groupid"][colorids[k]]
                    for poly in experiment["wallall"][group]:
                        if util.is_inside_polygon(pos, poly):
                            break
                    else:
                        continue

                vel = trajognize.algo.get_distance(prevchosens[k], chosens[k])
                if vel < veldist.maxvel:
                    veldist.data[light][k, int(vel)] += 1
                    veldist.data[light][id_count, int(vel)] += 1
                    veldist.points[light] += 1
            veldist.frames[light] += 1
        prevframe = currentframe
        prevchosens = chosens
    veldist.files = 1
    return veldist


def calculate_accdist(
    barcodes, light_log, cage_log, entrytimes, starttime, project_settings, experiment
):
    """Calculate acceleration distribution of barcodes of same color from positions
    on 3 consecutive frames.

    :param barcodes: global list of barcodes (Barcode)
            structured like this: [framenum][coloridindex][index]
    :param light_log: dictionary of light changes created by
            trajognize.util.parse_log_file()
    :param cage_log: dictionary of cage center changes created by
            trajognize.util.parse_log_file()
    :param entrytimes: dictionary of entry times created by
            trajognize.parse.parse_entry_times()
    :param starttime: datetime of the first frame of the current video
    :param project_settings: global project settings imported by
            trajognize.settings.import_trajognize_settings_from_file()
    :param experiment: the current experiment that defines rat groups, walls and
            interesting object centers. If experiment is None,
            we do not calculate anything.

    Barcodes are skipped if:
        - they are not chosen ones
        - they are not in their own valid cage

    WARNING: no real world coordinate transformation is implemented yet.

    """
    colorids = project_settings.colorids
    light_at_frame = trajognize.util.param_at_frame(light_log)
    cage_at_frame = trajognize.util.param_at_frame(cage_log)
    id_count = len(barcodes[0])
    accdist = init.AccDist(project_settings.good_light, id_count)
    prevprevchosens = util.get_chosen_barcodes(
        barcodes[0]
    )  # , trajognize.init.MFix.VIRTUAL)
    prevchosens = util.get_chosen_barcodes(
        barcodes[1]
    )  # , trajognize.init.MFix.VIRTUAL)
    prevprevframe = 0
    prevframe = 1
    for currentframe in range(2, len(barcodes)):
        # get cage
        cagecenter = cage_at_frame(currentframe)
        # check entry times and skip current frame if not valid
        if trajognize.util.is_entry_time(
            entrytimes,
            trajognize.util.get_datetime_at_frame(
                starttime, currentframe, project_settings.FPS
            ),
        ):
            continue
        # get light and skip bad lighting conditions
        light = light_at_frame(currentframe)
        if light not in project_settings.good_light:
            continue
        chosens = util.get_chosen_barcodes(
            barcodes[currentframe]
        )  # , trajognize.init.MFix.VIRTUAL)
        if currentframe == prevframe + 1 and prevframe == prevprevframe + 1:
            for k in range(id_count):
                if not chosens[k] or not prevchosens[k] or not prevprevchosens[k]:
                    continue
                # get center and skip bad ones: nan or outside image area
                barcode = chosens[k]
                cx = barcode.centerx
                cy = barcode.centery
                if project_settings.correct_cage:
                    cx += project_settings.cage_center.x - cagecenter[0]
                    cy += project_settings.cage_center.y - cagecenter[1]
                if cx != cx or cx >= project_settings.image_size.x or cx < 0:
                    continue
                if cy != cy or cy >= project_settings.image_size.y or cy < 0:
                    continue
                # filter results based on whether pateks are inside their own cage/territory
                if project_settings.filter_for_valid_cage:
                    pos = trajognize.init.Point(cx, cy)
                    group = experiment["groupid"][colorids[k]]
                    for poly in experiment["wallall"][group]:
                        if util.is_inside_polygon(pos, poly):
                            break
                    else:
                        continue

                accx = (
                    chosens[k].centerx
                    - 2 * prevchosens[k].centerx
                    + prevprevchosens[k].centerx
                )
                accy = (
                    chosens[k].centery
                    - 2 * prevchosens[k].centery
                    + prevprevchosens[k].centery
                )
                acc = hypot(accx, accy)
                if acc < accdist.maxacc:
                    accdist.data[light][k, int(acc)] += 1
                    accdist.data[light][id_count, int(acc)] += 1
                    accdist.points[light] += 1
            accdist.frames[light] += 1
        prevprevframe = prevframe
        prevframe = currentframe
        prevprevchosens = prevchosens
        prevchosens = chosens
    accdist.files = 1
    return accdist


def calculate_basic(
    barcodes, light_log, cage_log, entrytimes, starttime, project_settings, experiment
):
    """Get basic statitics on frame numbers, errors, etc.

    :param barcodes: global list of barcodes (Barcode)
            structured like this: [framenum][coloridindex][index]
    :param light_log: dictionary of light changes created by
            trajognize.util.parse_log_file()
    :param cage_log: dictionary of cage center changes created by
            trajognize.util.parse_log_file()
    :param entrytimes: dictionary of entry times created by
            trajognize.parse.parse_entry_times()
    :param starttime: datetime of the first frame of the current video
    :param project_settings: global project settings imported by
            trajognize.settings.import_trajognize_settings_from_file()
    :param experiment: the current experiment that defines rat groups, walls and
            interesting object centers. If experiment is None,
            we do not calculate anything.

    Note that mfix flags can be overlapping so the sum of the mfix flag counts
    can be (and probably is) much larger than the total number of barcodes.

    """
    colorids = project_settings.colorids
    light_at_frame = trajognize.util.param_at_frame(light_log)
    cage_at_frame = trajognize.util.param_at_frame(cage_log)
    basic = init.Basic(project_settings.all_light, project_settings.MBASE)
    id_count = len(barcodes[0])
    for currentframe in range(len(barcodes)):
        # get light condition
        light = light_at_frame(currentframe)
        basic.frames[light] += 1

        # check entry times
        if trajognize.util.is_entry_time(
            entrytimes,
            trajognize.util.get_datetime_at_frame(
                starttime, currentframe, project_settings.FPS
            ),
        ):
            basic.entrytime[light] += 1
            continue

        # get cage errors (nan)
        cagecenter = cage_at_frame(currentframe)
        for param in cagecenter:
            if param != param:
                basic.cageerror[light] += 1
                break

        # get chosen barcodes and count all mfix flags
        chosens = util.get_chosen_barcodes(barcodes[currentframe])
        for k in range(id_count):
            if chosens[k] is None:
                basic.mfixcount[light][-1] += 1
                continue
            for i in range(len(trajognize.init.MFix)):
                if chosens[k].mfix & (1 << i):
                    basic.mfixcount[light][i] += 1
            for c in colorids[k]:
                basic.colors_chosen[light][project_settings.color2int(c)] += 1

            # get all barcodes to calculate non-valid cage stat
            # get center and skip bad ones: nan or outside image area
            barcode = chosens[k]
            cx = barcode.centerx
            cy = barcode.centery
            if project_settings.correct_cage:
                cx += project_settings.cage_center.x - cagecenter[0]
                cy += project_settings.cage_center.y - cagecenter[1]
            if cx != cx or cx >= project_settings.image_size.x or cx < 0:
                continue
            if cy != cy or cy >= project_settings.image_size.y or cy < 0:
                continue
            # filter results based on whether pateks are inside their own cage/territory
            pos = trajognize.init.Point(cx, cy)
            group = experiment["groupid"][colorids[k]]
            for poly in experiment["wallall"][group]:
                if util.is_inside_polygon(pos, poly):
                    break
            else:
                basic.nonvalidcage[light] += 1
                continue

        # get all barcodes to calculate color stats
        for k in range(id_count):
            for barcode in barcodes[currentframe][k]:
                # TODO: this is not accurate, blobs should be checked instead...
                if barcode.mfix & trajognize.init.MFix.VIRTUAL:
                    continue
                for c in colorids[k]:
                    basic.colors_all[light][project_settings.color2int(c)] += 1

    basic.files = 1
    return basic


def calculate_distfromwall(
    barcodes, light_log, cage_log, entrytimes, starttime, project_settings, experiment
):
    """Calculate daily distance-from-wall distribution of barcodes.

    Day number is calculated from the beginning of the current experiment.

    :param barcodes: global list of barcodes (Barcode)
            structured like this: [framenum][coloridindex][index]
    :param light_log: dictionary of light changes created by
            trajognize.util.parse_log_file()
    :param cage_log: dictionary of cage center changes created by
            trajognize.util.parse_log_file()
    :param entrytimes: dictionary of entry times created by
            trajognize.parse.parse_entry_times()
    :param starttime: datetime of the first frame of the current video
    :param project_settings: global project settings imported by
            trajognize.settings.import_trajognize_settings_from_file()
    :param experiment: the current experiment that defines rat groups, walls and
            interesting object centers. If experiment is None,
            we do not calculate anything.

    """
    colorids = project_settings.colorids
    # initialize object
    id_count = len(barcodes[0])
    distfromwall = init.DistFromWall(
        project_settings.good_light,
        project_settings.image_size,
        project_settings.max_day,
        id_count,
    )
    # do not calculate anything if we are not part of an experiment
    if experiment is None:
        return distfromwall
    # initialize light
    light_at_frame = trajognize.util.param_at_frame(light_log)
    cage_at_frame = trajognize.util.param_at_frame(cage_log)
    # iterate for all frames
    px = [-1] * id_count
    py = [-1] * id_count
    prevframe = 0
    for currentframe in range(len(barcodes)):
        # get current time
        datetime_at_frame = trajognize.util.get_datetime_at_frame(
            starttime, currentframe, project_settings.FPS
        )
        # get day
        day = trajognize.stat.experiments.get_days_since_start(
            experiment, datetime_at_frame
        )
        # check entry times and skip current frame if not valid
        if trajognize.util.is_entry_time(entrytimes, datetime_at_frame):
            continue
        # get light and skip bad lighting conditions
        light = light_at_frame(currentframe)
        if light not in project_settings.good_light:
            continue
        # get cage
        cagecenter = cage_at_frame(currentframe)
        # get chosen barcodes
        chosens = util.get_chosen_barcodes(barcodes[currentframe])
        # store number of barcodes in the proper time bin
        for k in range(id_count):
            if chosens[k] is None:
                px[k] = -1
                py[k] = -1
                continue
            strid = colorids[k]
            group = experiment["groupid"][strid]
            mfi = util.get_mfi(chosens[k])
            # get center and skip bad ones: nan or outside image area
            x = chosens[k].centerx
            y = chosens[k].centery
            if project_settings.correct_cage:
                x += project_settings.cage_center.x - cagecenter[0]
                y += project_settings.cage_center.y - cagecenter[1]
            if x != x or x >= project_settings.image_size.x or x < 0:
                px[k] = -1
                py[k] = -1
                continue
            if y != y or y >= project_settings.image_size.y or y < 0:
                px[k] = -1
                py[k] = -1
                continue
            pos = trajognize.init.Point(x, y)
            # get distance from wall on open area
            maxdist = len(distfromwall.data[light][k][0][mfi][day])
            mindist = maxdist
            for poly in experiment["wall"][group]:
                if not util.is_inside_polygon(pos, poly):
                    continue
                dist = int(util.distance_from_polygon(pos, poly))
                if dist < mindist:
                    mindist = dist
            if mindist < maxdist:
                distfromwall.data[light][k][0][mfi][day][mindist] += 1  # 0=allspeed
                # store moving one, too, if applicable
                if currentframe == prevframe + 1 and px[k] != -1 and py[k] != -1:
                    vx = x - px[k]
                    vy = y - py[k]
                    v = hypot(vx, vy)
                    if v > distfromwall.velocity_threshold:
                        distfromwall.data[light][k][1][mfi][day][
                            mindist
                        ] += 1  # 1=onlymoving
                distfromwall.points[light] += 1
            px[k] = x
            py[k] = y
        prevframe = currentframe
        distfromwall.frames[light] += 1
    distfromwall.files = 1
    return distfromwall
