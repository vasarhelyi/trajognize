"""
This file contains all project-specific data that is need for trajognize stat.

To add more projects, create separate project files while keeping naming
conventions and include them here in a project-dependent manner.
See project_2011.py as the default example.
"""

from trajognize.project import *

perform_project_import = True
if PROJECT == PROJECT_2011:
    from . import project_2011 as actual_project
elif PROJECT == PROJECT_MAZE:
    from . import project_maze as actual_project
elif PROJECT == PROJECT_ANTS:
    from . import project_ants as actual_project
elif PROJECT == PROJECT_ANTS_2019:
    from . import project_ants_2019 as actual_project
elif PROJECT == PROJECT_STORKS:
    from . import project_storks as actual_project
else:
    perform_project_import = False

    weekly_feeding_times = {}
    object_types = []
    object_areas = {}
    object_queuing_areas = {}
    max_day = 0
    experiments = {}
    get_wall_polygons = None
    get_unique_output_filename = None

if perform_project_import:
    weekly_feeding_times = actual_project.weekly_feeding_times
    object_types = actual_project.object_types
    object_areas = actual_project.object_areas
    object_queuing_areas = actual_project.object_queuing_areas
    max_day = actual_project.max_day

    experiments = actual_project.experiments
    get_wall_polygons = actual_project.get_wall_polygons
    get_unique_output_filename = actual_project.get_unique_output_filename

if PROJECT == PROJECT_MAZE:
    get_exp_from_colorid_filename = True
else:
    get_exp_from_colorid_filename = False

################################################################################
# stat settings

class AASettings():
    def __init__(self,
            distance_threshold=400, #200 # [px]
            approacher_velocity_threshold=3, # [px/frame]
            avoider_velocity_threshold=3, # [px/frame]
            min_event_count=3, # 1 <= min_event_count <= min_event_length
            cos_approacher_threshold=0.8,
            cos_avoider_threshold=0.5,
            min_event_length=10):
        self.distance_threshold = distance_threshold
        self.approacher_velocity_threshold = approacher_velocity_threshold
        self.avoider_velocity_threshold = avoider_velocity_threshold
        self.min_event_count = min_event_count
        self.cos_approacher_threshold = cos_approacher_threshold
        self.cos_avoider_threshold = cos_avoider_threshold
        self.min_event_length = min_event_length

if PROJECT == PROJECT_ANTS:
    stat_aa_settings = AASettings(
            distance_threshold=400, #200 # [px]
            approacher_velocity_threshold=3, # [px/frame]
            avoider_velocity_threshold=3, # [px/frame]
            min_event_count=3, # 1 <= min_event_count <= min_event_length
            cos_approacher_threshold=0.8,
            cos_avoider_threshold=0.5,
            min_event_length=10)
elif PROJECT == PROJECT_ANTS_2019:
    stat_aa_settings = AASettings(
            distance_threshold=200, # [px]
            approacher_velocity_threshold=2, # [px/frame]
            avoider_velocity_threshold=1, # [px/frame]
            min_event_count=3, # 1 <= min_event_count <= min_event_length
            cos_approacher_threshold=0.8,
            cos_avoider_threshold=0.5,
            min_event_length=10)
else:
    stat_aa_settings = AASettings(
            distance_threshold=200, # [px] = 40 cm
            approacher_velocity_threshold=5, # [px/frame] = 125 px/s = 25 cm/s
            avoider_velocity_threshold=5, # [px/frame] = 125 px/s = 25 cm/s
            min_event_count=5, # 1 <= min_event_count <= min_event_length
            cos_approacher_threshold=0.8,
            cos_avoider_threshold=0.5,
            min_event_length=10)
