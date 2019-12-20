"""
This file contains all project-specific data that is need for trajognize stat.

To add more projects, create separate project files while keeping naming
conventions and include them here in a project-dependent manner.
See project_2011.py as the default example.
"""

from trajognize.project import *

if PROJECT == PROJECT_2011:
    import project_2011
    weekly_feeding_times = project_2011.weekly_feeding_times
    object_types = project_2011.object_types
    object_areas = project_2011.object_areas
    object_queuing_areas = project_2011.object_queuing_areas
    max_day = project_2011.max_day

    experiments = project_2011.experiments
    get_wall_polygons = project_2011.get_wall_polygons

elif PROJECT == PROJECT_MAZE:
    import project_maze
    weekly_feeding_times = {}
    object_types = project_maze.object_types
    object_areas = project_maze.object_areas
    object_queuing_areas = project_maze.object_queuing_areas
    max_day = project_maze.max_day

    experiments = project_maze.experiments
    get_wall_polygons = project_maze.get_wall_polygons

elif PROJECT == PROJECT_ANTS:
    import project_ants
    weekly_feeding_times = {}
    object_types = project_ants.object_types
    object_areas = project_ants.object_areas
    object_queuing_areas = project_ants.object_queuing_areas
    max_day = project_ants.max_day

    experiments = project_ants.experiments
    get_wall_polygons = project_ants.get_wall_polygons

elif PROJECT == PROJECT_ANTS_2019:
    import project_ants_2019
    weekly_feeding_times = {}
    object_types = project_ants_2019.object_types
    object_areas = project_ants_2019.object_areas
    object_queuing_areas = project_ants_2019.object_queuing_areas
    max_day = project_ants_2019.max_day

    experiments = project_ants_2019.experiments
    get_wall_polygons = project_ants_2019.get_wall_polygons

else:
    weekly_feeding_times = {}
    object_types = []
    object_areas = {}
    object_queuing_areas = {}
    max_day = 0

    experiments = {}
    get_wall_polygons = None

################################################################################
# stat settings

class aa_settings_t():
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
    stat_aa_settings = aa_settings_t(
            distance_threshold=400, #200 # [px]
            approacher_velocity_threshold=3, # [px/frame]
            avoider_velocity_threshold=3, # [px/frame]
            min_event_count=3, # 1 <= min_event_count <= min_event_length
            cos_approacher_threshold=0.8,
            cos_avoider_threshold=0.5,
            min_event_length=10)
elif PROJECT == PROJECT_ANTS_2019:
    stat_aa_settings = aa_settings_t(
            distance_threshold=200, # [px]
            approacher_velocity_threshold=2, # [px/frame]
            avoider_velocity_threshold=1, # [px/frame]
            min_event_count=3, # 1 <= min_event_count <= min_event_length
            cos_approacher_threshold=0.8,
            cos_avoider_threshold=0.5,
            min_event_length=10)
else:
    stat_aa_settings = aa_settings_t(
            distance_threshold=200, # [px] = 40 cm
            approacher_velocity_threshold=5, # [px/frame] = 125 px/s = 25 cm/s
            avoider_velocity_threshold=5, # [px/frame] = 125 px/s = 25 cm/s
            min_event_count=5, # 1 <= min_event_count <= min_event_length
            cos_approacher_threshold=0.8,
            cos_avoider_threshold=0.5,
            min_event_length=10)
