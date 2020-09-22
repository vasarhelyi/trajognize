"""
Deprecated: All variables that are experiment/project-specific were defined here
"""

from collections import namedtuple


# TODO: this is redundant with init.py but otherwise we have circular imports
Point = namedtuple('Point','x y')


################################################################################
# project definitions

PROJECT_2011 = 1 # the big rat experiment back in 2011 by ELTE CollMot
PROJECT_MAZE = 2 # the rat maze experiment in 2015 summer at ELTE
PROJECT_FISH = 3 # fish experiments 2015 by Ian Couzin Lab
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