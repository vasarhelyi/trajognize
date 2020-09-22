"""
All variables that are experiment/project-specific are defined here
"""

from collections import namedtuple
import datetime
import os

################################################################################
# project definitions
PROJECT_2011 = 1 # the big rat experiment back in 2011 by ELTE CollMot
PROJECT_MAZE = 2 # the rat maze experiment in 2015 summer at ELTE
PROJECT_FISH = 3 # fish experiments 2015 by Ian Cousin Lab
PROJECT_ANTS = 4 # ant experiments 2016 by Stephen Pratt
PROJECT_ANTS_2019 = 5 # ant experiments 2019 by Stephen Pratt
PROJECT_STORKS = 6 # storks experiment 2019/2020 by Iris and Mate

project_str = {
    PROJECT_2011: 'PROJECT_2011',
    PROJECT_MAZE: 'PROJECT_MAZE',
    PROJECT_FISH: 'PROJECT_FISH',
    PROJECT_ANTS: 'PROJECT_ANTS',
    PROJECT_ANTS_2019: 'PROJECT_ANTS_2019',
    PROJECT_STORKS: 'PROJECT_STORKS',
}

# define current project
PROJECT = PROJECT_ANTS_2019 # PROJECT_STORKS

################################################################################
# image/video parameters

#: video temporal resolution (deinterlaced)

if PROJECT == PROJECT_FISH:
    FPS = 30
elif PROJECT in [PROJECT_ANTS, PROJECT_ANTS_2019]:
    FPS = 60
else:
    FPS = 25

# TODO: this is redundant with init.py but otherwise we have circular imports
Point = namedtuple('Point','x y')

#: width/height of the video image
image_size = Point(1920, 1080)

#: average center x coordinate of the cage, determined from 84 sample video averages
cage_center = Point(925, 537)

################################################################################
# color blob definitions

#: number of chips/bins/colors/decimal places in a colorid
MCHIPS = 4

#: define colors. Take care to have different initials for all colors
if PROJECT == PROJECT_ANTS:
    colornames = ('orange', 'blue', 'yellow', 'green', 'magenta', 'purple')
elif PROJECT == PROJECT_ANTS_2019:
    colornames = ('orange', 'yellow', 'green', 'blue', 'magenta')
elif PROJECT == PROJECT_STORKS:
    colornames = ('red', 'yellow', 'cyan', 'blue', 'purple', 'white')
else:
    colornames = ('red', 'orange', 'green', 'blue', 'pink')

#: number of colors (base of the colorids)
MBASE = len(colornames)

#: color lookup table - this should be constant in all projects
#: use string keys so that we don't have to turn into int just for this lookup
int2color = "".join([colornames[i].upper()[0] for i in range(MBASE)])
#: define int keys as well, they might be needed
color2int = dict([(colornames[i].upper()[0], i) for i in range(MBASE)])


################################################################################
# blob/barcode detection parameters

#: [pixels] - max distance between two neighboring blobs on the same rat (from measurement results)
if PROJECT == PROJECT_MAZE:
    MAX_INRAT_DIST = 41
elif PROJECT == PROJECT_FISH:
    MAX_INRAT_DIST = 41
elif PROJECT == PROJECT_ANTS:
    MAX_INRAT_DIST = 40 # 001.MTS
#    MAX_INRAT_DIST = 23 # full dueling
#    MAX_INRAT_DIST = 28 # closeup1
#    MAX_INRAT_DIST = 40 # closeup2
elif PROJECT == PROJECT_ANTS_2019:
#    MAX_INRAT_DIST = 40 # S1 and S2
    MAX_INRAT_DIST = 27 # 49B1(15) and F102(30) and SAFC20A(60)

elif PROJECT == PROJECT_STORKS:
    MAX_INRAT_DIST = 65 # TODO: define it from blob radii as we have it dynamically by now
else:
    MAX_INRAT_DIST = 35

#: [pixels] - average distance between two neighboring blobs on the same rat (from measurement results)
if PROJECT == PROJECT_MAZE:
    AVG_INRAT_DIST = 28
elif PROJECT == PROJECT_FISH:
    AVG_INRAT_DIST = 28
elif PROJECT == PROJECT_ANTS:
    AVG_INRAT_DIST = 27 # 001.MTS
#    AVG_INRAT_DIST = 15 # full dueling
#    AVG_INRAT_DIST = 21 # closeup1
#    AVG_INRAT_DIST = 23 # closeup1
elif PROJECT == PROJECT_ANTS_2019:
#    AVG_INRAT_DIST = 27 # S1 and S2
#    AVG_INRAT_DIST = 17 # 49B1(15) and F102(30)
    AVG_INRAT_DIST = 15 # SAFC20A(60)
elif PROJECT == PROJECT_STORKS:
    AVG_INRAT_DIST = 40 # TODO: this is different for white-other (~60) and other-other (21) blobs
else:
    AVG_INRAT_DIST = 23

#: [pixels] - max distance a blob travels between two consecutive frames (from measurement results)
if PROJECT == PROJECT_MAZE:
    MAX_PERFRAME_DIST = 35
elif PROJECT == PROJECT_FISH:
    MAX_PERFRAME_DIST = 35
elif PROJECT == PROJECT_ANTS:
    MAX_PERFRAME_DIST = 15 # 001.MTS
#    MAX_PERFRAME_DIST = 15 # full dueling
#    MAX_PERFRAME_DIST = 35 # closeup1
#    MAX_PERFRAME_DIST = 35 # closeup1
elif PROJECT == PROJECT_ANTS_2019:
    MAX_PERFRAME_DIST = 15
elif PROJECT == PROJECT_STORKS:
    MAX_PERFRAME_DIST = 15
else:
    MAX_PERFRAME_DIST = 15

#: [pixels] - max distance a blob travels between two consecutive frames when there is an md blob under it (from measurement results)
if PROJECT == PROJECT_MAZE:
    MAX_PERFRAME_DIST_MD = 60
elif PROJECT == PROJECT_FISH:
    MAX_PERFRAME_DIST_MD = 60
elif PROJECT == PROJECT_ANTS:
    MAX_PERFRAME_DIST_MD = 15 # closeup1, 2, dueling, 001.MTS, does not count
elif PROJECT == PROJECT_ANTS_2019:
    MAX_PERFRAME_DIST_MD = 15
elif PROJECT == PROJECT_STORKS:
    MAX_PERFRAME_DIST_MD = 10
else:
    MAX_PERFRAME_DIST_MD = 40 # 35 #30 - lets try 40, it occurs sometimes, some false positives but they can be filtered out later...

#: [deg] - max angle a barcode rotates on a frame in degrees
if PROJECT == PROJECT_ANTS_2019:
    MAX_PERFRAME_ANGLE = 20
else:
    MAX_PERFRAME_ANGLE = 30

################################################################################
# stat parameters

#: possible light conditions that are differentiated in the outputs
if PROJECT == PROJECT_2011:
    good_light = ['DAYLIGHT', 'NIGHTLIGHT']
    all_light = ['DAYLIGHT', 'NIGHTLIGHT', 'STRANGELIGHT', 'EXTRALIGHT']
else:
    good_light = ['NIGHTLIGHT']
    all_light = ['NIGHTLIGHT']

#: should we use dynamic cage correction data for cage center estimation?
correctcage=True

#: should we filter results for valid group cage?
#: Note: if not indicated in results file, no filter was used
filter_for_valid_cage = True


################################################################################
# settings for find_best_trajectories() in algo_trajectory.py

class FindBestTrajectoriesSettings():
    def __init__(self,
            might_be_bad_score_threshold=100,
            might_be_bad_sum_good_score_threshold=200,
            good_for_sure_score_threshold=500,
            good_score_threshold=100,
            framelimit=1500):
        self.might_be_bad_score_threshold = might_be_bad_score_threshold
        self.might_be_bad_sum_good_score_threshold = might_be_bad_sum_good_score_threshold
        self.good_for_sure_score_threshold = good_for_sure_score_threshold
        self.good_score_threshold = good_score_threshold
        self.framelimit = framelimit

if PROJECT == PROJECT_MAZE:
    find_best_trajectories_settings = FindBestTrajectoriesSettings(
            0, 0, 10, 10, 50)
elif PROJECT == PROJECT_ANTS:
    find_best_trajectories_settings = FindBestTrajectoriesSettings(
            100, 200, 500, 100, 100)
elif PROJECT == PROJECT_ANTS_2019:
    find_best_trajectories_settings = FindBestTrajectoriesSettings(
            100, 200, 500, 100, 100)
elif PROJECT == PROJECT_STORKS:
    find_best_trajectories_settings = FindBestTrajectoriesSettings(
            100, 200, 500, 100, 100)
else:
    find_best_trajectories_settings = FindBestTrajectoriesSettings(
            100, 200, 500, 100, 1500)


################################################################################
# functions that are project-specific

def get_datetime_from_filename(filename):
    """Return datetime object parsed from ratlab video file names.

    :param filename: input file name that contains date and time, e.g. using
                     format YYYY-MM-DD_HH-MM-SS.SSSSSS

    """
    # get filename
    head, tail = os.path.split(filename)
    if PROJECT == PROJECT_2011:
        # get datetime part and return it
        return datetime.datetime.strptime(tail[:tail.find('.ts.blob')], "%Y-%m-%d_%H-%M-%S.%f")
    elif PROJECT == PROJECT_MAZE:
        return datetime.datetime.strptime(tail.split('_')[1], "%Y%m%d")
    elif PROJECT == PROJECT_ANTS:
        # TODO: this is a hack, we do not really need time in this experiment...
        return datetime.datetime(2016, 11, 1, 0, 0)
    elif PROJECT == PROJECT_ANTS_2019:
        # TODO: this is a hack, we do not really need time in this experiment...
        return datetime.datetime(2018, 9, 25, 0, 0)
    elif PROJECT == PROJECT_STORKS:
        # TODO: make sure all storks files start with this date format
        return datetime.datetime.strptime(tail[:19], "%Y-%m-%d_%H-%M-%S")
    else:
        return None

# Note: all further project-specific parameters are stored in stat/project.py
