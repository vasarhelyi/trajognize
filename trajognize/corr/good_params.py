"""This file contains good params for all param/pairparam files that are
generated by trajognize.plot scripts into the corr directory.

Use python regular expression (re) matching wildcards.

"""

chosen_dominance_index = "BBS"  # normDS and LDI are also candidates

good_params = {
    "pairparams_plot_aa.txt": [
        "aa_nightlight_group_(.*)_D"
    ],  # this is only one but group is different everywhere TODO: D or F ?
    "pairparams_plot_dailyfqobj.txt": [],  # none is used for dailyfqobj for main analysis
    "pairparams_plot_fqobj.txt": ["(.*)_D"],  # food, water, wheel TODO: D or F ?
    "pairparams_plot_fqfood.txt": ["(.*)_D"],  # food, water, wheel TODO: D or F ?
    "pairparams_plot_nearestneighbor.txt": [
        "nearestneighbor_nightlight_any_group_(.*)_D"
    ],  # only one, TODO: D or F? TODO: real/virt or any?
    "pairparams_plot_butthead.txt": [
        "butthead_nightlight_group_(.*)_D"
    ],  # only one, TODO: D or F?
    "pairparams_plot_neighbor.txt": ["neighbor_network_nightlight_group_(.*)"],
    "params_calc_heatmap_corroutput.txt": [
        "heatmap_NIGHTLIGHT_ANY_count_nonzero_framenormed",
        "heatmap_NIGHTLIGHT_ANY_count_territory_framenormed",
        "heatmap_NIGHTLIGHT_ANY_percent_nonzero$",
        "heatmap_NIGHTLIGHT_ANY_percent_territory$",
    ],
    "params_calc_motionmap_corroutput.txt": [
        "motionmap_NIGHTLIGHT_ANY_count_nonzero_framenormed",
        "motionmap_NIGHTLIGHT_ANY_count_territory_framenormed",
        "motionmap_NIGHTLIGHT_ANY_percent_nonzero$",
        "motionmap_NIGHTLIGHT_ANY_percent_territory$",
    ],
    "params_calc_dist24hobj_avgfood.txt": ["avgfooddist24hobj_alldays_(.*)"],
    "params_plot_aa.txt": [
        "aa_nightlight_group_(.*)_F_%s" % chosen_dominance_index,
        "aa_nightlight_group_(.*)_F_(rowsum|winaboveavg|loseaboveavg)",
    ],
    "params_plot_dailyfqobj.txt": [],  # none is used for dailyfqobj for main analysis
    "params_plot_dailyobj.txt": [
        "dailyobj_nightlight_(food|wheel)_(.*)",
        "dailyobj_daylight_entrance_(.*)",
    ],
    "params_plot_distfromwall.txt": [
        "distfromwall_avg_nightlight_onlymoving_ANY_group_(.*)"
    ],  # allspeed excluded, onlymoving better
    "params_plot_fqobj.txt": [
        "fqobj_nightlight_wheel_group_(.*)_F_%s" % chosen_dominance_index
    ],  # water excluded, food also, next line is better
    "params_plot_fqfood.txt": [
        "fqfood_(.*)light_group_(.*)_F_%s" % chosen_dominance_index
    ],
    "params_plot_fqwhilef.txt": [
        "fqwhilef_(.*)light_(food|wheel)_group_(.*)_(0|avg|num)"
    ],  # food is restricted to feeding times!
    "params_plot_nearestneighbor.txt": [
        "nearestneighbor_nightlight_any_group_(.*)_F_%s" % chosen_dominance_index
    ],
    "params_plot_butthead.txt": [
        "butthead_nightlight_group_(.*)_F_%s" % chosen_dominance_index
    ],
    "params_plot_neighbor.txt": ["neighbor_number_nightlight_group_(.*)"],
    "params_plot_wounds.txt": ["wounds_group_(.*)"],
    "params_plot_bodymass.txt": ["bodymass_group_(.*)"]
    #    'params_individual_tests.txt': ['.*']
}

all_params = {
    "pairparams_plot_aa.txt": [".*"],
    "pairparams_plot_dailyfqobj.txt": [],  # none is used for dailyfqobj for main analysis
    "pairparams_plot_fqobj.txt": [".*"],
    "pairparams_plot_fqfood.txt": [".*"],
    "pairparams_plot_nearestneighbor.txt": [".*"],
    "pairparams_plot_butthead.txt": [".*"],
    "pairparams_plot_neighbor.txt": [".*"],
    "params_calc_heatmap_corroutput.txt": [".*"],
    "params_calc_motionmap_corroutput.txt": [".*"],
    "params_calc_dist24hobj_avgfood.txt": [".*"],
    "params_plot_aa.txt": [".*"],
    "params_plot_dailyfqobj.txt": [],  # none is used for dailyfqobj for main analysis
    "params_plot_dailyobj.txt": [".*"],
    "params_plot_distfromwall.txt": [".*"],
    "params_plot_fqobj.txt": [".*"],
    "params_plot_fqfood.txt": [".*"],
    "params_plot_fqwhilef.txt": [".*"],
    "params_plot_nearestneighbor.txt": [".*"],
    "params_plot_butthead.txt": [".*"],
    "params_plot_neighbor.txt": [".*"],
    "params_plot_wounds.txt": [".*"],
    "params_plot_bodymass.txt": [".*"]
    #    'params_individual_tests.txt': ['.*']
}
