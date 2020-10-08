"""This is the main trajognize settings file of PROJECT_MAZE in 2015 summer
at ELTE. It is included here as the trajognize repo got public after the
publication in Current Biology from this experiment (much later, in 2020).

This file is just an example for you to see how to fill the

trajognize.settings.TrajognizeSettingsBase

class with proper values to setup trajognize specifically to your project.
Detailed help and description about each setting can be found in the base class
definition in trajognize/settings.py

Good luck!
"""

import datetime, os

from trajognize.init import Point
from trajognize.settings import AASettings, FindBestTrajectoriesSettings, \
    TrajognizeSettingsBase

experiments = dict()

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

experiments['learn_male']={ \
    'number': 4,
    'description': """Learning phase with single and group measurements""",
    'start': datetime.datetime(2015,9,14,0,0),
    'stop': datetime.datetime(2015,9,17,23,59),
    'groups': { \
        'M12': "ORB OGB OBG GRB GRP GPB BRP BGP".split(),
        'M34': "ORP OBP OPG OPB GOB GOP GBP BOP".split()},
}

class SettingsForRatMaze(TrajognizeSettingsBase):
    project_name = "PROJECT_MAZE"
    FPS = 25
    image_size = Point(1920, 1080)
    MCHIPS = 3
    color_names = ('red', 'orange', 'green', 'blue', 'pink')

    MAX_INRAT_DIST = 41
    AVG_INRAT_DIST = 28
    MAX_PERFRAME_DIST = 35
    MAX_PERFRAME_DIST_MD = 60
    MAX_PERFRAME_ANGLE = 30

    traj_score_method = 1

    stat_aa_settings = AASettings(
        distance_threshold=200, # [px] = 40 cm
        approacher_velocity_threshold=5, # [px/frame] = 125 px/s = 25 cm/s
        avoider_velocity_threshold=5, # [px/frame] = 125 px/s = 25 cm/s
        min_event_count=5, # 1 <= min_event_count <= min_event_length
        cos_approacher_threshold=0.8,
        cos_avoider_threshold=0.5,
        min_event_length=10
    )

    find_best_trajectories_settings = FindBestTrajectoriesSettings(
        0, 0, 10, 10, 50
    )

    def get_datetime_from_filename(self, filename):
        head, tail = os.path.split(filename)
        return datetime.datetime.strptime(tail.split('_')[1], "%Y%m%d")

    def get_unique_output_filename(outputpath, inputfile):
        return os.path.join(outputpath,
            os.path.splitext(os.path.split(inputfile)[1])[0] + ".txt"
        )

    max_day = 35

    experiments = experiments