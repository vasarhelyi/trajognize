"""
This file contains all environmental conditions related to the RATLAB experiments
back in 2011-2012, at ELTE Department of Biological Physics.
"""

import sys
import datetime
import math

from trajognize.init import Point, Circle, Ellipse, Rectangle

#: index for weekdays starting from saturday
ordered_weekdays = ['saturday', 'sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday']

def get_experiment(experiments, sometime, allonday=False):
    """Return the name of the experiments that were running at a given moment,
    or empty list if no proper experiement was found.

    If there are overlapping experiments found, list is sorted according
    to growing experiment number. Note that algo assumes that there are no true
    overlapping experiments defined, only cut up ones!

    :param experiments: the global experiments dictionary
    :param sometime:    a datetime value representing a given time instance
    :param allonday:    return full experiment list for the given day
                        ordered by exp number

    """
    if allonday:
        t1 = datetime.datetime.combine(sometime.date(), datetime.time(0,0,0))
        explist1 = get_experiment(experiments, t1)
        t2 = datetime.datetime.combine(sometime.date(), datetime.time(23,59,59))
        explist2 = get_experiment(experiments, t2)
        explist = sorted(list(set(explist1) | set(explist2)),
                lambda a,b: experiments[a]['number'] - experiments[b]['number'])
        return explist

    explist = []
    for name in experiments:
        experiment = experiments[name]
        if sometime >= experiment['start'] and sometime <= experiment['stop']:
            explist.append(name)
            # allow max 2 overlapping experiments (e.g. first + first_part_*)
            if len(explist) > 1:
                # order according to experiment number
                explist.sort(lambda a,b: experiments[a]['number'] - experiments[b]['number'])
                break
    return explist


def are_in_same_group(stridi, stridj, experiment):
    """Return true if rats i and j are in the same group in a given experiment.

    :param stridi: string id of one rat
    :param stridj: string id of another rat
    :param experiment: an experiment in which the check should be performed

    """
    if experiment['groupid'][stridi] == experiment['groupid'][stridj]:
        return True
    else:
        return False


def is_wall_between(a, b, cage, use_cage):
    """Return true if there is a cage wall between the two barcodes on the
    given frame.

    :param a: first barcode (or any object with centerx/centery member)
    :param b: second barcode (or any object with centerx/centery member)
    :param cage: cage params at given frame: [x, y, alpha, beta]
    :param use_cage: should we use cage at all?

    Algo description:
    The equation of a line is y = ix+b
    We are first looking for the junction of two lines, one through a and b,
    and one which is the cage wall (and there are actually two cage walls).
    The steepness of the line through a and b is defined from their centers (i),
    the steepness of the cage line is defined from its angle (j).
    Then distances are calculated between a, b and the junction x, all on the
    same line. If the junction x is between a and b, we return true.

    WARNING: If two pateks are in the same group, the wall around the cage center
    is opened. Now there is no check on group consistency, but we return False in
    all cases when the junction point is very close the the cage center. This also
    implicates that this function should be used together with are_in_same_group()
    TODO: find a reasonable max diameter for this correction, now 50 pixel is used.

    """
    if use_cage is False:
        return False

    # check cage params, return "there is no wall" if cage coords is nan
    for i in range(4):
        if cage[i] != cage[i]:
            return False
    # get steepness of the two cage lines
    for j in [math.tan(cage[2]), math.tan(cage[3])]:
        # calculate coordinates of junction
        # special case: a and b are on a vertical line
        if a.centerx == b.centerx:
            x = a.centerx
            y = cage[1] + (x - cage[0])*j
        # normal case
        else:
            i = float(b.centery - a.centery) / (b.centerx - a.centerx)
            # special case: lines are parallel -> return true if lines overlap
            if i == j: # note that it could be < epsilon but it is not really important...
                if a.centery == cage[1] - cage[0]*j + a.centerx*j:
                    return True
                else:
                    continue
            x = ((cage[1] - cage[0]*j) - (a.centery - a.centerx*i)) / (i-j)
            y = i * x + (a.centery - a.centerx*i)
        # check wheter junction point is close to cage center and skip wall if so
        cx = math.hypot(cage[0] - x, cage[1] - y)
        if cx < 50:
            continue
        # calculate distances between junction and points
        ab = math.hypot(a.centerx - b.centerx, a.centery - b.centery)
        ax = math.hypot(a.centerx - x, a.centery - y)
        bx = math.hypot(b.centerx - x, b.centery - y)
        # check distances whether line is axb(True), abx(False) or bax(False)
        if (ax >= bx and ax <= ab) or (bx >= ax and bx <= ab):
            return True

    # no, there is no wall between a and b
    return False


def queuing_center_offset(objectcenter, objectarea, image_size):
    """if center of objectarea is nonzero, it is used as center offset,
    depending on quarter of image (- if < mid, + if > mid

    """
    # define center offset x defined as objectarea center x
    if not objectarea.x:
        ofsx = 0
    else:
        ofsx = objectarea.x
        if objectcenter.x < image_size.x / 2:
            ofsx = -ofsx
    # define center offset y defined as objectarea center y
    if not objectarea.y:
        ofsy = 0
    else:
        ofsy = objectarea.y
        if objectcenter.y < image_size.y / 2:
            ofsy = -ofsy

    return (ofsx, ofsy)


def is_barcode_under_object(barcode, objectcenter, objectarea, image_size):
    """Return true if barcode lays on/under object, defined by objectcenter as center
    (and arc if circle) and and objectarea as area (radius, height, width) with
    optional center offset.

    :param barcode: a barcode
    :param objectcenter: a Point/Circle object defining the CENTER (and arc) of the object
    :param objectarea: an object defining the AREA (width, height, radius) of the object
                       and possible center offset (see queuing_center_offset())
    :param image_size: size of the image in pixels

    Warning: function assumes that all angles are in the range of [0, 360]

    """
    (ofsx, ofsy) = queuing_center_offset(objectcenter, objectarea, image_size)
    # check for rectangles
    if isinstance(objectarea, Rectangle):
        if barcode.centerx < (objectcenter.x + ofsx) - objectarea.w/2.0: return False
        if barcode.centerx > (objectcenter.x + ofsx) + objectarea.w/2.0: return False
        if barcode.centery < (objectcenter.y + ofsy) - objectarea.h/2.0: return False
        if barcode.centery > (objectcenter.y + ofsy) + objectarea.h/2.0: return False
        return True
    # check for circles
    elif isinstance(objectarea, Circle):
        # check radius
        dx = barcode.centerx - (objectcenter.x + ofsx)
        dy = barcode.centery - (objectcenter.y + ofsy)
        r = math.hypot(dx, dy)
        if r > objectarea.r:
            return False
        # check angle if given
        if isinstance(objectcenter, Point):
            return True
        elif isinstance(objectcenter, Circle):
            a1 = objectcenter.a1
            a2 = objectcenter.a2
        else:
            raise NotImplementedError("unhandled type of 'objectcenter'")
        angle = math.degrees(math.atan2(dy, dx))
        if angle < 0: angle += 360
        if a2 >= a1:
            if angle >= a1 and angle <= a2:
                return True
            else:
                return False
        else:
            if angle >= a1 or angle <= a2:
                return True
            else:
                return False
    else:
        raise NotImplementedError("unhandled type of 'objectarea'")


def get_formatted_description(experiment, commentchar=None):
    """Return formatted experiment description.

    :param experiment: the experiment to print info about
    :param commentchar: optional comment char to the beginning of each line

    """
    output = "Experiment '%s'\n\n" \
             "start: %s\n"      \
             "stop: %s\n\n" % (experiment['name'],
            experiment['start'], experiment['stop'])

    for group in experiment['groups']:
        output += "group %s: %s\n" % (group, experiment['groups'][group])
    output += "\n"

    lines = experiment['description'].split('\n')
    for line in lines:
        line = line.strip()
        output += line + "\n"
    output = output[:-1]

    if commentchar is not None:
        output = commentchar + " " + output
        output = output.replace("\n", "\n%s " % commentchar)
    return output + "\n"


def get_days_since_start(experiment, sometime):
    """Return number of days since the start of an experiment."""
    return (sometime.date() - experiment['start'].date()).days


def get_day_offset(experiment):
    """Get day offset of a given experiment. This is a hack in project_2011
    to accomodate first experiment cut up parts... Works until you do not define
    an experiment name containing the string 'first_part'. Sorry..."""

    if "first_part" in experiment['name']:
        return (experiment['start'].date() -
            experiments['first_A1_A2_B1_B2']['start'].date()
        ).days
    else:
        return 0


def get_dayrange_of_experiment(experiment):
    """Return a list of strings containing all days through an experiment."""
    firstday = experiment['start'].date()
    lastday = experiment['stop'].date()
    dayrange = [str(firstday + datetime.timedelta(n))
        for n in range(int((lastday - firstday).days) + 1)
    ]

    return dayrange


def get_dayrange_of_all_experiments(experiments):
    """Return a list of strings containing all days through all experiments."""
    firstday = None
    lastday = None
    for exp in experiments.values():
        if firstday is None or firstday > exp['start']: firstday = exp['start']
        if lastday is None or lastday < exp['stop']: lastday = exp['stop']
    firstday = firstday.date()
    lastday = lastday.date()
    dayrange = [str(firstday + datetime.timedelta(n))
        for n in range(int((lastday - firstday).days) + 1)
    ]

    return dayrange


def is_weekly_feeding_time(date, weekly_feeding_times, exclude_fridays=False):
    """Check whether a given datetime is part of the weekly feeding time
    schedule."""

    if not weekly_feeding_times:
        return False

    weekday = date.strftime('%A').lower()
    hour = date.hour
    # skip fridays because feeding is infinitely available on that day
    if weekday == 'friday' and exclude_fridays:
        return False
    # skip non feeding hours
    for start, duration in weekly_feeding_times[weekday]:
        if hour >= start and hour < start + duration:
            return True

    return False


def is_object_queueable(object_queuing_area):
    """Return true if there is queuing area defined for the given object.

    Parameters:
        object_queuing_area - should be project_settings.object_queuing_areas[object]
    """
    # check for rectangles
    if isinstance(object_queuing_area, Rectangle):
        if object_queuing_area.w or object_queuing_area.h:
            return True
    # check for circles
    elif isinstance(object_queuing_area, Circle):
        if object_queuing_area.r:
            return True
    # not queueable
    return False
