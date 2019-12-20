"""
This file contains all environmental conditions related to the RATLAB experiments
back in 2011-2012, at ELTE Department of Biological Physics.
"""

import datetime, math
from trajognize.init import point_t, circle_t, ellipse_t, rectangle_t
from trajognize.project import *

#: possible interesting objects
object_types = ['home', 'entrance', 'food', 'water', 'watertop', 'wheel', 'femaleshigh', 'femaleslow']

#: areas of objects. Center (and arc) is defined in the experiment, these objects
#: should be placed on those centers concentrically.
object_areas = { \
    'home':        rectangle_t(0,0,90,120),
    'entrance':    rectangle_t(0,0,70,60),
    'food':        circle_t(0,0,90,0,0),
    'water':       circle_t(0,0,90,0,0),
    'watertop':    circle_t(0,0,90,0,0),
    'wheel':       rectangle_t(0,0,90,60),
    'femaleshigh': rectangle_t(0,0,100,150),
    'femaleslow':  rectangle_t(0,0,125,150),
}


#: queuing range defined as a default width of extension
object_queuing_range = 80 # +80 px ~= +4/5 patek

#: queuing areas of objects. Center is defined in the experiment, object areas
#: are defined above. These objects should be placed on these concentrically,
#: except when center (offset) is defined here.
#: If so, it is - if above midline, + if below
#: if queuing is not used, all params are zero
object_queuing_areas = { \
    # not used
    'home':        rectangle_t(0,0,0,0),
    # not used
    'entrance':    rectangle_t(0,0,0,0),
    # extend concentrically
    'food':        circle_t(0,0, object_areas['food'].r + object_queuing_range, 0,0),
    # extend concentrically
    'water':       circle_t(0,0, object_areas['water'].r + object_queuing_range, 0,0),
    # not used
    'watertop':    circle_t(0,0,0,0,0),
    # extend width on both sides, extend height on only one side (wall is on other side)
    'wheel':       rectangle_t(0, object_queuing_range/2, object_areas['wheel'].w + 2*object_queuing_range, object_areas['wheel'].h + object_queuing_range),
    # no extention on width (between wall and femaleslow), extend height on one side (wall is on other side)
    'femaleshigh': rectangle_t(0, object_queuing_range/2, object_areas['femaleshigh'].w, object_areas['femaleshigh'].h + object_queuing_range),
    # extend width on one side (femaleshigh on other side), extend height on one side (wall is on other side)
    'femaleslow':  rectangle_t(object_queuing_range/2, object_queuing_range/2, object_areas['femaleslow'].w + object_queuing_range, object_areas['femaleslow'].h + object_queuing_range),
}

#: maximum number of days in an experiment (exp_first is 146, 150 will do)
max_day = 150

#: The main experiment dictionary between 2011.05.25 and 2012.02.27.
#: point_t object coordinates are defined in a top-left = 0,0 coordinate system
#: angles are defined in the --> CW [deg] coordinate system, i.e. >0, v90, <180, ^270
experiments = dict()

experiments['first_A1_A2_B1_B2']={ \
    'number': 1,
    'description': """The very first experiment and also the first time when
    the rats got to know each other. Four groups of 7 tiny rats, feeding,
    developing, making friends and enemies. Note that throughout the very first
    weeks of the experiments (between 05.24. and 06.06.) the rats are
    small, the ID colors are not final, the light is not final yet either.
    Unique color definitions should be created to process this part properly!

    |------|------|
    |  A2  |  B2  |
    |------|------|  entrance
    |  A1  |  B1  |
    |------|------|

    """,
    'start': datetime.datetime(2011,05,24,19,32),
    'stop': datetime.datetime(2011,10,17,16,29),
    'groups': { \
        'A1': "OPG ROG RPG ORG OBG GOB RBG".split(),
        'A2': "OBP RBP OPB ORP ROP RPO GOP".split(),
        'B1': "RGB GPB OGB ROB RPB GRB ORB".split(),
        'B2': "GRP OGP BGP BOP GBP RBO RGP".split()},
    'home': { \
        'A1': [point_t(841,973)],
        'A2': [point_t(830,104)],
        'B1': [point_t(1006,965)],
        'B2': [point_t(1002,100)]},
    'entrance': { \
        'A1': [point_t(848,867)],
        'A2': [point_t(823,205)],
        'B1': [point_t(1013,870)],
        'B2': [point_t(992,198)]},
    'food': { \
        'A1': [circle_t(314,553,0,0,90)], # [point_t(351,591)],
        'A2': [circle_t(317,511,0,270,360)], # [point_t(344,485)],
        'B1': [circle_t(1520,549,0,90,180)], # [point_t(1487,592)],
        'B2': [circle_t(1526,519,0,180,270)]}, # [point_t(1492,499)]},
    'water': { \
        'A1': [circle_t(317,1015,0,270,360)], #[point_t(349,979)],
        'A2': [circle_t(321,43,0,0,90)], #[point_t(356,85)],
        'B1': [circle_t(1513,1006,0,180,270)], # [point_t(1480,986)],
        'B2': [circle_t(1522,54,0,90,180)]}, # [point_t(1489,95)]},
    'watertop': { \
        'A1': [circle_t(317,1015,0,10,260)], #[point_t(349,979)],
        'A2': [circle_t(321,43,0,100,350)], #[point_t(356,85)],
        'B1': [circle_t(1513,1006,0,280,170)], # [point_t(1480,986)],
        'B2': [circle_t(1522,54,0,190,80)]}, # [point_t(1489,95)]},
    'wheel': { \
        'A1': [point_t(693,591)],
        'A2': [point_t(690,483)],
        'B1': [point_t(1116,592)],
        'B2': [point_t(1111,483)]},
}


experiments['first_part_1']={ \
    'number': 101,
    'description': """First three weeks of the first experiment.""",
    'start': datetime.datetime(2011,05,24,19,32),
    'stop': datetime.datetime(2011,06,13,16,29),
    'groups': experiments['first_A1_A2_B1_B2']['groups'],
    'home': experiments['first_A1_A2_B1_B2']['home'],
    'entrance': experiments['first_A1_A2_B1_B2']['entrance'],
    'food': experiments['first_A1_A2_B1_B2']['food'],
    'water': experiments['first_A1_A2_B1_B2']['water'],
    'watertop': experiments['first_A1_A2_B1_B2']['watertop'],
    'wheel': experiments['first_A1_A2_B1_B2']['wheel'],
}


experiments['first_part_2']={ \
    'number': 102,
    'description': """Second three weeks of the first experiment.""",
    'start': datetime.datetime(2011,06,13,16,30),
    'stop': datetime.datetime(2011,07,04,16,29),
    'groups': experiments['first_A1_A2_B1_B2']['groups'],
    'home': experiments['first_A1_A2_B1_B2']['home'],
    'entrance': experiments['first_A1_A2_B1_B2']['entrance'],
    'food': experiments['first_A1_A2_B1_B2']['food'],
    'water': experiments['first_A1_A2_B1_B2']['water'],
    'watertop': experiments['first_A1_A2_B1_B2']['watertop'],
    'wheel': experiments['first_A1_A2_B1_B2']['wheel'],
}


experiments['first_part_3']={ \
    'number': 103,
    'description': """Third three weeks of the first experiment.""",
    'start': datetime.datetime(2011,07,04,16,30),
    'stop': datetime.datetime(2011,07,25,16,29),
    'groups': experiments['first_A1_A2_B1_B2']['groups'],
    'home': experiments['first_A1_A2_B1_B2']['home'],
    'entrance': experiments['first_A1_A2_B1_B2']['entrance'],
    'food': experiments['first_A1_A2_B1_B2']['food'],
    'water': experiments['first_A1_A2_B1_B2']['water'],
    'watertop': experiments['first_A1_A2_B1_B2']['watertop'],
    'wheel': experiments['first_A1_A2_B1_B2']['wheel'],
}


experiments['first_part_4']={ \
    'number': 104,
    'description': """Fourth three weeks of the first experiment.""",
    'start': datetime.datetime(2011,07,25,16,30),
    'stop': datetime.datetime(2011,8,15,16,29),
    'groups': experiments['first_A1_A2_B1_B2']['groups'],
    'home': experiments['first_A1_A2_B1_B2']['home'],
    'entrance': experiments['first_A1_A2_B1_B2']['entrance'],
    'food': experiments['first_A1_A2_B1_B2']['food'],
    'water': experiments['first_A1_A2_B1_B2']['water'],
    'watertop': experiments['first_A1_A2_B1_B2']['watertop'],
    'wheel': experiments['first_A1_A2_B1_B2']['wheel'],
}


experiments['first_part_5']={ \
    'number': 105,
    'description': """Fifth three weeks of the first experiment.""",
    'start': datetime.datetime(2011,8,15,16,30),
    'stop': datetime.datetime(2011,9,05,16,29),
    'groups': experiments['first_A1_A2_B1_B2']['groups'],
    'home': experiments['first_A1_A2_B1_B2']['home'],
    'entrance': experiments['first_A1_A2_B1_B2']['entrance'],
    'food': experiments['first_A1_A2_B1_B2']['food'],
    'water': experiments['first_A1_A2_B1_B2']['water'],
    'watertop': experiments['first_A1_A2_B1_B2']['watertop'],
    'wheel': experiments['first_A1_A2_B1_B2']['wheel'],
}


experiments['first_part_6']={ \
    'number': 106,
    'description': """Sixth three weeks of the first experiment.""",
    'start': datetime.datetime(2011,9,05,16,30),
    'stop': datetime.datetime(2011,9,26,16,29),
    'groups': experiments['first_A1_A2_B1_B2']['groups'],
    'home': experiments['first_A1_A2_B1_B2']['home'],
    'entrance': experiments['first_A1_A2_B1_B2']['entrance'],
    'food': experiments['first_A1_A2_B1_B2']['food'],
    'water': experiments['first_A1_A2_B1_B2']['water'],
    'watertop': experiments['first_A1_A2_B1_B2']['watertop'],
    'wheel': experiments['first_A1_A2_B1_B2']['wheel'],
}


experiments['first_part_7']={ \
    'number': 107,
    'description': """Seventh three weeks of the first experiment.""",
    'start': datetime.datetime(2011,9,26,16,30),
    'stop': datetime.datetime(2011,10,17,16,29),
    'groups': experiments['first_A1_A2_B1_B2']['groups'],
    'home': experiments['first_A1_A2_B1_B2']['home'],
    'entrance': experiments['first_A1_A2_B1_B2']['entrance'],
    'food': experiments['first_A1_A2_B1_B2']['food'],
    'water': experiments['first_A1_A2_B1_B2']['water'],
    'watertop': experiments['first_A1_A2_B1_B2']['watertop'],
    'wheel': experiments['first_A1_A2_B1_B2']['wheel'],
}


# weekly experiments
for i in xrange(1, 22):
    name = 'first_week_%d' % i
    experiments[name] = experiments[first_A1_A2_B1_B2].copy()
    experiments[name]['number'] = 1000 + i
    if i > 1:
        experiments[name]['start'] = datetime.datetime(2011,05,24,16,30) + datetime.timedelta(weeks=i-1)
    experiments[name]['stop'] =  datetime.datetime(2011,05,31,16,29) + datetime.timedelta(weeks=i-1)


experiments['second_merge_A1A2_B1B2']={ \
    'number': 2,
    'description': """The second experiment where the original four groups got
    merged into two bigger ones: A1-A2 and B1-B2. The walls remained unchanged,
    but holes were made for the rats to be able to visit the original
    territory of the other experiment.

    |------|------|
    |  A2  |  B2  |
    |----- | -----|  entrance
    |  A1  |  B1  |
    |------|------|

    """,
    'start': datetime.datetime(2011,10,17,17,13),
    'stop': datetime.datetime(2011,11,07,17,07),
    'groups': { \
        'A1A2': "OPG ROG RPG ORG OBG GOB RBG OBP RBP OPB ORP ROP RPO GOP".split(),
        'B1B2': "RGB GPB OGB ROB RPB GRB ORB GRP OGP BGP BOP GBP RBO RGP".split()},
    'home': { \
        'A1A2': [point_t(841,973), point_t(830,104)],
        'B1B2': [point_t(1006,965), point_t(1002,100)]},
    'entrance': { \
        'A1A2': [point_t(848,861), point_t(823,205)],
        'B1B2': [point_t(1023,861), point_t(995,204)]},
    'food': { \
        'A1A2': [circle_t(314,553,0,0,90), circle_t(317,511,0,270,360)], # [point_t(351,591), point_t(344,485)],
        'B1B2': [circle_t(1520,549,0,90,180), circle_t(1526,519,0,180,270)]}, #[point_t(1487,592), point_t(1492,499)]},
    'water': { \
        'A1A2': [circle_t(317,1015,0,270,360), circle_t(321,43,0,0,90)], # [point_t(349,979), point_t(356,85)],
        'B1B2': [circle_t(1513,1006,0,180,270), circle_t(1522,54,0,90,180)]}, # [point_t(1480,986), point_t(1489,95)]},
    'watertop': { \
        'A1A2': [circle_t(317,1015,0,10,260), circle_t(321,43,0,100,350)], # [point_t(349,979), point_t(356,85)],
        'B1B2': [circle_t(1513,1006,0,280,170), circle_t(1522,54,0,190,80)]}, # [point_t(1480,986), point_t(1489,95)]},
    'wheel': { \
        'A1A2': [point_t(693,591), point_t(690,483)],
        'B1B2': [point_t(1116,592), point_t(1111,483)]},
}


experiments['third_merge_A1A2B1B2']={ \
    'number': 3,
    'description': """The third experiment where all groups (previously already
    A1A2 and B1B2) got merged into one colony, with walls remaining and
    yet new holes between all previous territories.

    |------|------|
    |  A2  |  B2  |
    |-----   -----|  entrance
    |  A1  |  B1  |
    |------|------|

    """,
    'start': datetime.datetime(2011,11,07,18,29),
    'stop': datetime.datetime(2011,11,28,17,29),
    'groups': { \
        'A1A2B1B2': "OPG ROG RPG ORG OBG GOB RBG OBP RBP OPB ORP ROP RPO GOP RGB GPB OGB ROB RPB GRB ORB GRP OGP BGP BOP GBP RBO RGP".split()},
    'home': { \
        'A1A2B1B2': [point_t(841,973), point_t(830,104), point_t(1006,965), point_t(1002,100)]},
    'entrance': { \
        'A1A2B1B2': [point_t(848,861), point_t(823,205), point_t(1032,854), point_t(997,213)]},
    'food': { \
        'A1A2B1B2': [circle_t(314,553,0,0,90), circle_t(317,511,0,270,360), circle_t(1520,549,0,90,180), circle_t(1526,519,0,180,270)]}, # [point_t(351,591), point_t(344,485), point_t(1487,592), point_t(1492,499)]},
    'water': { \
        'A1A2B1B2': [circle_t(317,1015,0,270,360), circle_t(321,43,0,0,90), circle_t(1513,1006,0,180,270), circle_t(1522,54,0,90,180)]}, # [point_t(349,979), point_t(356,85), point_t(1480,986), point_t(1489,95)]},
    'watertop': { \
        'A1A2B1B2': [circle_t(317,1015,0,10,260), circle_t(321,43,0,100,350), circle_t(1513,1006,0,280,170), circle_t(1522,54,0,190,80)]}, # [point_t(349,979), point_t(356,85), point_t(1480,986), point_t(1489,95)]},
    'wheel': { \
        'A1A2B1B2': [point_t(693,591), point_t(690,483), point_t(1116,592), point_t(1111,483)]},
}


experiments['fourth_split_into_G1_G2_G3_G4']={ \
    'number': 4,
    'description': """The fourth experiment in which the whole colony previously
    living together got split into new subgroups G1, G2, G3 and G4. The whole
    lab was cleaned, houses, treadwheel, etc.

    |------|------|
    |  G1  |  G2  |
    |------|------|  entrance
    |  G3  |  G4  |
    |------|------|

    Notes:
    2011.12.05. - microphones were installed, camera got moved
    2011.12.09. - long painting, huge part of data missing (10th day)

    """,
    'start': datetime.datetime(2011,11,28,20,07),
    'stop': datetime.datetime(2011,12,19,15,22),
    'groups': { \
        'G1': "OPG ROG OBP RBP RGB GRP OGP".split(),
        'G2': "RPG ORG OPB GPB OGB BGP BOP".split(),
        'G3': "OBG GOB ORP ROP ROB RPB GBP".split(),
        'G4': "RBG RPO GOP GRB ORB RBO RGP".split()},
    'home': { \
        'G1': [point_t(828,113)],
        'G2': [point_t(1000,111)],
        'G3': [point_t(842, 968)],
        'G4': [point_t(1022,960)]},
    'entrance': { \
        'G1': [point_t(823,208)],
        'G2': [point_t(997,212)],
        'G3': [point_t(844,856)],
        'G4': [point_t(1023,860)]},
    'food': { \
        'G1': [circle_t(321,526,0,270,360)], # [point_t(345,489)],
        'G2': [circle_t(1513,523,0,180,270)], # [point_t(1494,485)],
        'G3': [circle_t(323,558,0,0,90)], # [point_t(338,601)],
        'G4': [circle_t(1515,560,0,90,180)]}, # [point_t(1490,596)]},
    'water': { \
        'G1': [circle_t(324,40,0,0,90)], # [point_t(356,94)],
        'G2': [circle_t(1526,59,0,90,180)], # [point_t(1492,102)],
        'G3': [circle_t(310,1029,0,270,360)], # [point_t(352,989)],
        'G4': [circle_t(1513,1016,0,180,270)]}, # [point_t(1476,989)]},
    'watertop': { \
        'G1': [circle_t(324,40,0,100,350)], # [point_t(356,94)],
        'G2': [circle_t(1526,59,0,190,80)], # [point_t(1492,102)],
        'G3': [circle_t(310,1029,0,10,260)], # [point_t(352,989)],
        'G4': [circle_t(1513,1016,0,280,170)]}, # [point_t(1476,989)]},
    'wheel': { \
        'G1': [point_t(679,477)],
        'G2': [point_t(1120,485)],
        'G3': [point_t(704,596)],
        'G4': [point_t(1129,605)]},
}


experiments['fifth_G1_G4_large_G2_G3_small']={ \
    'number': 5,
    'description': """The fifth experiment in which G1-4 groups remained unchanged,
    but territory size got changed so that G1 and G4 got larger place, while
    G2 and G3 got smaller place.
    
    |--------/----|
    | G1L   / G2S |
    |------/------|  entrance
    | G3S /   G4L |
    |----/--------|

    Notes:
    2011.12.19. - RBP was totally removed from the experiment due to wounds and weight loss.
    2012.01.05. - OBP was taken out because of too many big wounds until 2012.01.27
    2012.01.06. - ORG has an injured eye.

    2012-01-06_DIGITALIZALO_DOBOZ_LEFAGYASA_MIATT_FELVETEL_LEALLT:
        last good before: 2012-01-05_05-53-05.243852.ts
        first good after: 2012-01-07_17-31-12.772791.ts
                    
    """,
    'start': datetime.datetime(2011,12,19,18,57),
    'stop': datetime.datetime(2012,01,07,15,58),
    'groups': { \
        'G1L': "OPG ROG OBP RBP RGB GRP OGP".split(), # RBP not present
        'G2S': "RPG ORG OPB GPB OGB BGP BOP".split(),
        'G3S': "OBG GOB ORP ROP ROB RPB GBP".split(),
        'G4L': "RBG RPO GOP GRB ORB RBO RGP".split()},
    'home': { \
        'G1L': [point_t(1072,113)],
        'G2S': [point_t(1335,117)],
        'G3S': [point_t(502,957)],
        'G4L': [point_t(791,958)]},
    'entrance': { \
        'G1L': [point_t(1045,204)],
        'G2S': [point_t(1317,218)],
        'G3S': [point_t(518,848)],
        'G4L': [point_t(809,851)]},
    'food': { \
        'G1L': [circle_t(333,511,0,270,360)], # [point_t(341,492)],
        'G2S': [circle_t(1515,516,0,180,270)], # [point_t(1506,484)],
        'G3S': [circle_t(330,553,0,0,90)], # [point_t(338,584)],
        'G4L': [circle_t(1517,558,0,90,180)]}, # [point_t(1499,584)]},
    'water': { \
        'G1L': [circle_t(333,50,0,0,90)], # [point_t(359,76)],
        'G2S': [circle_t(1533,52,0,90,180)], # [point_t(1505,90)],
        'G3S': [circle_t(330,1011,0,270,360)], # [point_t(354,987)],
        'G4L': [circle_t(1510,1006,0,180,270)]}, # [point_t(1486,989)]},
    'watertop': { \
        'G1L': [circle_t(333,50,0,100,350)], # [point_t(359,76)],
        'G2S': [circle_t(1533,52,0,190,80)], # [point_t(1505,90)],
        'G3S': [circle_t(330,1011,0,10,260)], # [point_t(354,987)],
        'G4L': [circle_t(1510,1006,0,280,170)]}, # [point_t(1486,989)]},
    'wheel': { \
        'G1L': [point_t(695,474)],
        'G2S': [point_t(1125,485)],
        'G3S': [point_t(706,592)],
        'G4L': [point_t(1126,600)]},
}


experiments['sixth_G1_G4_small_G2_G3_large']={ \
    'number': 6,
    'description': """The sixth experiment in which G1-4 groups remained unchanged,
    but territory size got changed again so that G1 and G4 got smaller place, while
    G2 and G3 got larger place.

    |----\--------|
    | G1S \   G2L |
    |------\------|  entrance
    | G3L   \ G4S |
    |--------\----|

    Notes:
    2011.12.19. - RBP was totally removed from the experiment due to wounds and weight loss.
    2012.01.23. - OGP and RGB was fed separately during weight measurement.
    2012.01.05. - OBP was taken out because of too many big wounds until 2012.01.27

    """,
    'start': datetime.datetime(2012,01,07,17,47),
    'stop': datetime.datetime(2012,01,26,14,33), 
    'groups': { \
        'G1S': "OPG ROG OBP RBP RGB GRP OGP".split(), # RBP not present
        'G2L': "RPG ORG OPB GPB OGB BGP BOP".split(),
        'G3L': "OBG GOB ORP ROP ROB RPB GBP".split(),
        'G4S': "RBG RPO GOP GRB ORB RBO RGP".split()},
    'home': { \
        'G1S': [point_t(493,103)],
        'G2L': [point_t(784,111)],
        'G3L': [point_t(1069,958)],
        'G4S': [point_t(1334,966)]},
    'entrance': { \
        'G1S': [point_t(502,202)],
        'G2L': [point_t(784,207)],
        'G3L': [point_t(1062,863)],
        'G4S': [point_t(1331,855)]},
    'food': { \
        'G1S': [circle_t(323,511,0,270,360)], # [point_t(344,487)],
        'G2L': [circle_t(1513,526,0,180,270)], # [point_t(1492,490)],
        'G3L': [circle_t(323,544,0,0,90)], # [point_t(342,564)],
        'G4S': [circle_t(1515,565,0,90,180)]}, # [point_t(1492,599)]},
    'water': { \
        'G1S': [circle_t(330,40,0,0,90)], # [point_t(356,81)],
        'G2L': [circle_t(1529,57,0,90,180)], # [point_t(1496,94)],
        'G3L': [circle_t(319,1013,0,270,360)], # [point_t(347,972)],
        'G4S': [circle_t(1517,1020,0,180,270)]}, # [point_t(1485,993)]},
    'watertop': { \
        'G1S': [circle_t(330,40,0,100,350)], # [point_t(356,81)],
        'G2L': [circle_t(1529,57,0,190,80)], # [point_t(1496,94)],
        'G3L': [circle_t(319,1013,0,10,260)], # [point_t(347,972)],
        'G4S': [circle_t(1517,1020,0,280,170)]}, # [point_t(1485,993)]},
    'wheel': { \
        'G1S': [point_t(690,477)],
        'G2L': [point_t(1118,485)],
        'G3L': [point_t(695,594)],
        'G4S': [point_t(1118,605)]},
}


experiments['seventh_G1_G2_G3_G4_females']={ \
    'number': 7,
    'description': """The last experiment in which G1-4 groups remained unchanged,
    but females were put into their territory.

    |------|------|
    |  G1 *|* G2  |
    |------|------|  entrance
    |  G3 *|* G4  |
    |------|------|

    Notes:
    2011.12.19. - RBP was totally removed from the experiment due to wounds and weight loss.
    3 females coded as A,B,C, and an empty cage.
    The femeales were rotated as:
    Group:		G1	G2	G3	G4
    Female,	1.week	A	B	C	none
		2.week	none	A	B	C
		3.week	C	none	A	B
		4.week	B	C	none	A
    2012.02.05	8:52	9:20	nosteny csere
    2012.02.12	8:52	9:21	nosteny csere

    2012.01.31 - 2012.02.03: THERE IS NO DATA (DATA CORRUPT):
        last good before: 2012-01-31_01-05-09.018859.ts
        first good after: 2012-02-03_16-16-27.597430.ts

    """,
    'start': datetime.datetime(2012,01,27,17,40),
    'stop': datetime.datetime(2012,02,26,9,16), 
    'groups': { \
        'G1': "OPG ROG OBP RBP RGB GRP OGP".split(), # RBP not present
        'G2': "RPG ORG OPB GPB OGB BGP BOP".split(),
        'G3': "OBG GOB ORP ROP ROB RPB GBP".split(),
        'G4': "RBG RPO GOP GRB ORB RBO RGP".split()},
    'home': { \
        'G1': [point_t(823,112)],
        'G2': [point_t(1015,115)],
        'G3': [point_t(830,968)],
        'G4': [point_t(1008,975)]},
    'entrance': { \
        'G1': [point_t(818,209)],
        'G2': [point_t(1002,211)],
        'G3': [point_t(839,862)],
        'G4': [point_t(1025,868)]},
    'food': { \
        'G1': [circle_t(326,516,0,270,360)], # [point_t(340,501)],
        'G2': [circle_t(1515,537,0,180,270)], # [point_t(1494,503)],
        'G3': [circle_t(325,556,0,0,90)], # [point_t(338,591)],
        'G4': [circle_t(1510,576,0,90,180)]}, # [point_t(1497,608)]},
    'water': { \
        'G1': [circle_t(328,52,0,0,90)], # [point_t(361,92)],
        'G2': [circle_t(1529,64,0,90,180)], # [point_t(1503,95)],
        'G3': [circle_t(321,1015,0,270,360)], # [point_t(351,987)],
        'G4': [circle_t(1504,1025,0,180,270)]}, # [point_t(1475,1005)]},
    'watertop': { \
        'G1': [circle_t(328,52,0,100,350)], # [point_t(361,92)],
        'G2': [circle_t(1529,64,0,190,80)], # [point_t(1503,95)],
        'G3': [circle_t(321,1025,0,10,260)], # [point_t(351,987)],
        'G4': [circle_t(1504,1032,0,280,170)]}, # [point_t(1475,1005)]},
    'wheel': { \
        'G1': [point_t(514,490)],
        'G2': [point_t(1317,492)],
        'G3': [point_t(523,591)],
        'G4': [point_t(1327,613)]},
    'femaleshigh': { \
        'G1': [point_t(856,449)],
        'G2': [point_t(992,454)],
        'G3': [point_t(855,620)],
        'G4': [point_t(985,630)]},
    'femaleslow': { \
        'G1': [point_t(743,449)],
        'G2': [point_t(1105,454)],
        'G3': [point_t(742,620)],
        'G4': [point_t(1098,630)]},
}

#: weekly feeding times. each daily list contains list of tuples of (start, duration)
#: expressed in hours. day is same as datetime.weekday(), 0 is Monday, 6 is Sunday
#: list imported (but reformatted) from SVN: rat-project/hdpvr_recorder/feeder_daemon.py
weekly_feeding_times = {
    'monday':    [(6,1), (12,1), (18,1)], # 5h breaks
    'tuesday':   [(6,1), (18,1)], # 11h break between the two
    'wednesday': [(6,1), (18,1)], # 11h break between the two
    'thursday':  [(6,1), (18,1)], # 11h break between the two
    'friday':    [(6,13)], # continuous feeding all day, ends at 19:00
    'saturday':  [(6,1), (12,1), (18,1)], # 5h breaks
    'sunday':    [(6,1), (12,1), (18,1)], # 5h breaks
}


def get_wall_polygons(experiment, group):
    """Create two wall polygons for a given experiment.

    'wall'/'area' will be the flat territory without wheel/home for distance from wall stat
    'wallall'/'areaall' will be the full territory

    :param experiment: an experiment
    :param group: the group within the experiment.

    TODO: fifth, sixth experiments miss correct position of angled wall end
    TODO: seventh experiment miss exclusion of females in the center
    TODO: nothing is accurate due to wall width around center that is missed

    """
    polys = []
    polysall = []
    for i in xrange(len(experiment['home'][group])):
        polys.append([])
        polysall.append([])
        # 1: food center
        polys[i].append(point_t(
                experiment['food'][group][i].x,
                experiment['food'][group][i].y))
        polysall[i].append(point_t(
                experiment['food'][group][i].x,
                experiment['food'][group][i].y))
        # 2: water center
        polys[i].append(point_t(
                experiment['water'][group][i].x,
                experiment['water'][group][i].y))
        polysall[i].append(point_t(
                experiment['water'][group][i].x,
                experiment['water'][group][i].y))
        # 3: home corner 1 - closest corner to water
        ix = [1,1,-1,-1] # 30  |-> x
        iy = [1,-1,1,-1] # 21  v   y
        homecorners = [point_t(
                experiment['home'][group][i].x + ix[j] * object_areas['home'].w/2,
                experiment['home'][group][i].y + iy[j] * object_areas['home'].h/2) \
                for j in xrange(4)]
        dists = [math.hypot(homecorners[j].x - polys[-1][-1].x, homecorners[j].y - polys[-1][-1].y) \
                for j in xrange(4)]
        index1 = min(xrange(len(dists)),key=dists.__getitem__)
        polys[i].append(homecorners[index1])
        # 4: home corner 2 - x same, y different: 0->1 1->0 2->3 3->2
        index2 = index1 + iy[index1]
        polys[i].append(homecorners[index2])
        # 5: home corner 3 - y same, x different: 0->2 2->0 1->3 3->1
        index3 = index2 + 2*ix[index2]
        polys[i].append(homecorners[index3])
        # home corner 4 - x same, y different: 0->1 1->0 2->3 3->2
        index4 = index3 + iy[index3]
        polysall[i].append(homecorners[index4])
        # for fifth and sixth experiment we need the 4th corner as well + angled wall end
        if experiment['name'].startswith('fifth') or experiment['name'].startswith('sixth'):
            # add fourth corner to these walls, too
            polys[i].append(homecorners[index4])
            # 7: angled wall end --> TODO: do it manually
            polys[i].append(point_t(
                    2*homecorners[index4].x - homecorners[index2].x,
                    homecorners[index4].y))
            polysall[i].append(point_t(
                    2*homecorners[index4].x - homecorners[index2].x,
                    homecorners[index4].y))

        # TODO: for the seventh experiment we need the females...
        # 6/8: center
        d = 15
        polys[i].append(point_t(
                cage_center.x + math.copysign(d, polys[i][1].x - cage_center.x),
                cage_center.y + math.copysign(d, polys[i][1].y - cage_center.y)))
        polysall[i].append(point_t(
                cage_center.x + math.copysign(d, polys[i][1].x - cage_center.x),
                cage_center.y + math.copysign(d, polys[i][1].y - cage_center.y)))
        # correct for previous one if not 5th or 6th exp:
        if len(polys[i]) == 6:
            polys[i][-2] = point_t(polys[i][-1].x, polys[i][-2].y)
            polysall[i][-2] = point_t(polysall[i][-1].x, polysall[i][-2].y)
        # 7/9: wheel corner 1 - closest corner to center
        wheelcorners = [point_t(
                experiment['wheel'][group][i].x + ix[j] * object_areas['wheel'].w/2,
                experiment['wheel'][group][i].y + iy[j] * object_areas['wheel'].h/2) \
                for j in xrange(4)]
        dists = [math.hypot(wheelcorners[j].x - polys[-1][-1].x, wheelcorners[j].y - polys[-1][-1].y) \
                for j in xrange(4)]
        index1 = min(xrange(len(dists)),key=dists.__getitem__)
        polys[i].append(wheelcorners[index1])
        # 8/10: wheel corner 2 - x same, y different: 0->1 1->0 2->3 3->2
        index2 = index1 + iy[index1]
        polys[i].append(wheelcorners[index2])
        # 9/11: wheel corner 3 - y same, x different: 0->2 2->0 1->3 3->1
        index3 = index2 + 2*ix[index2]
        polys[i].append(wheelcorners[index3])
        # 10/12: wheel corner 4 - x same, y different: 0->1 1->0 2->3 3->2
        index4 = index3 + iy[index3]
        polys[i].append(wheelcorners[index4])
    return (polys, polysall)
