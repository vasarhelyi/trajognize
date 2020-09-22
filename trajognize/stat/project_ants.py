"""
This file contains all environmental conditions related to the ant project with
Stephen Pratt <Stephen.Pratt@asu.edu> from Arizona State University during
late 2016 about Harpegnathos saltator worker ants
as they form a reproductive hierarchy.
"""

import datetime, math, os

from trajognize.init import Point, Circle, Ellipse, Rectangle
from trajognize.project import *

# define the colony we are analysing
COLONY = "F30" # October 21 to November 4, 2016
#COLONY = "F89" # October 21 to November 4, 2016

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
max_day = 15

#: The main experiment dictionary
#: Point object coordinates are defined in a top-left = 0,0 coordinate system
#: angles are defined in the --> CW [deg] coordinate system, i.e. >0, v90, <180, ^270
experiments = dict()

experiments['late2016']={ \
    'number': 1,
    'description': """Late 2016 ant experiment.
    """,
    'start': datetime.datetime(2016,10,21,00,00),
    'stop': datetime.datetime(2016,11,04,23,59),
    'groups': { \
        COLONY: "OGB PYB OBM OGP BPO GOB MOY GMY YGB YOB".split()}
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
        os.path.split(os.path.split(os.path.split(inputfile)[0])[0])[1] + "__" +
        os.path.splitext(os.path.split(inputfile)[1])[0] + ".txt"
    )
