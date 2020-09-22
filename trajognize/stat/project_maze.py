"""
This file contains all environmental conditions related to the RATLAB ratmaze
experiments from 2015 summer, at ELTE Department of Biological Physics.
"""

import datetime, math

from trajognize.init import Point, Circle, Ellipse, Rectangle
from trajognize.project import *

#: possible interesting objects
object_types = []

#: areas of objects. Center (and arc) is defined in the experiment, these objects
#: should be placed on those centers concentrically.
object_areas = {}


#: queuing range defined as a default width of extension
object_queuing_range = 80 # +80 px ~= +4/5 patek

#: queuing areas of objects. Center is defined in the experiment, object areas
#: are defined above. These objects should be placed on these concentrically,
#: except when center (offset) is defined here.
#: If so, it is - if above midline, + if below
#: if queuing is not used, all params are zero
object_queuing_areas = {}


#: maximum number of days in an experiment
max_day = 35

#: The main experiment dictionary between 2011.05.25 and 2012.02.27.
#: Point object coordinates are defined in a top-left = 0,0 coordinate system
#: angles are defined in the --> CW [deg] coordinate system, i.e. >0, v90, <180, ^270
experiments = dict()

experiments['pure_single']={ \
    'number': 1,
    'description': """The first part of the ratmaze experiments
    with only single male and female measurements
    """,
    'start': datetime.datetime(2015,8,17,00,00),
    'stop': datetime.datetime(2015,8,30,23,59),
    'groups': {},
}

experiments['group_and_single_male']={ \
    'number': 2,
    'description': """Second phase with group measurements (along with some
    more single measurements""",
    'start': datetime.datetime(2015,9,1,0,0),
    'stop': datetime.datetime(2015,9,13,23,59),
    'groups': { \
        'M12': "ORB OGB OBG GRB GRP GPB BRP BGP".split(),
        'M34': "ORP OBP OPG OPB GOB GOP GBP BOP".split()},
}

experiments['group_and_single_female']={ \
    'number': 3,
    'description': """Second phase with group measurements (along with some
    more single measurements""",
    'start': datetime.datetime(2015,9,1,0,0),
    'stop': datetime.datetime(2015,9,13,23,59),
    'groups': { \
        'F12': "ROG ROB RGO RGB RGP ORB OGP GRB".split(),
        'F34': "ROP RBO RBG RBP RPO RPG RPB ORG".split()},
}

experiments['learn_male']={ \
    'number': 4,
    'description': """Learning phase with single and group measurements""",
    'start': datetime.datetime(2015,9,14,0,0),
    'stop': datetime.datetime(2015,9,17,23,59),
    'groups': { \
        'M12': "ORB OGB OBG GRB GRP GPB BRP BGP".split(),
        'M34': "ORP OBP OPG OPB GOB GOP GBP BOP".split()},
}

experiments['learn_female']={ \
    'number': 5,
    'description': """Learning phase with single and group measurements""",
    'start': datetime.datetime(2015,9,14,0,0),
    'stop': datetime.datetime(2015,9,17,23,59),
    'groups': { \
        'F12': "ROG ROB RGO RGB RGP ORB OGP GRB".split(),
        'F34': "ROP RBO RBG RBP RPO RPG RPB ORG".split()},
}


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
