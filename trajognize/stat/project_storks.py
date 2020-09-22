"""
This file contains all environmental conditions related to the storks project
by Iris and Mate, 2019/2020.
"""

import datetime, math, os

from trajognize.init import Point, Circle, Ellipse, Rectangle
from trajognize.project import *

#: possible interesting objects
object_types = []

#: areas of objects. Center (and arc) is defined in the experiment, these objects
#: should be placed on those centers concentrically.
object_areas = {}


#: queuing range defined as a default width of extension
object_queuing_range = 200 # [px] not really relevant in this experiment

#: queuing areas of objects. Center is defined in the experiment, object areas
#: are defined above. These objects should be placed on these concentrically,
#: except when center (offset) is defined here.
#: If so, it is - if above midline, + if below
#: if queuing is not used, all params are zero
object_queuing_areas = {}

#: maximum number of days in an experiment
max_day = 1000

#: The main experiment dictionary
#: Point object coordinates are defined in a top-left = 0,0 coordinate system
#: angles are defined in the --> CW [deg] coordinate system, i.e. >0, v90, <180, ^270
experiments = dict()

experiments['storks'] = {
    'number': 1,
    'description': """The one and only storks experiment.
    """,
    'start': datetime.datetime(2019, 1, 1, 0, 0),
    'stop': datetime.datetime(2019, 12, 31, 23, 59),
    'groups': {
        "storks":
            "WRY WRC WRB WRP "
            "WYR WYC WYB WYP "
            "WCR WCY WCB WCP "
            "WBR WBY WBC WBP "
            "WPR WPY WPC WPB".split()
    }
}


weekly_feeding_times = {}


def get_wall_polygons(experiment, group):
    """Create two wall polygons for a given experiment.

    'wall'/'area' will be the flat territory without wheel/home for distance from wall stat
    'wallall'/'areaall' will be the full territory

    :param experiment: an experiment
    :param group: the group within the experiment.

    """
    polys = [[]]
    polysall = [[]]
    i = 0

    # TODO: define better, this is only full frame

    polys[i].append(Point(0,0))
    polysall[i].append(Point(0,0))

    polys[i].append(Point(image_size.x,0))
    polysall[i].append(Point(image_size.x,0))

    polys[i].append(Point(image_size.x,image_size.y))
    polysall[i].append(Point(image_size.x,image_size.y))

    polys[i].append(Point(0,image_size.y))
    polysall[i].append(Point(0,image_size.y))

    return (polys, polysall)


def get_unique_output_filename(outputpath, inputfile):
    """Get unique output filename for statsum. If '-u' is specified, results
    will be written to a unique output file with this path and filename.
    """
    return os.path.join(outputpath,
        os.path.splitext(os.path.split(inputfile)[1])[0] + ".txt"
    )
