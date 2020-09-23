import sys
import vpython
import vpython.graph

import trajognize.settings

projectfile = input("Please enter a project file to check its experiments: ")
project_settings = trajognize.settings.import_trajognize_settings_from_file(projectfile)
if project_settings is None:
    print("Could not load project file.")
    sys.exit(1)

exps = projectfile.experiments

for exp in exps:
    vpython.graph.gdisplay(title=exp + "wall")
    for group in exps[exp]['groups']:
        for poly in exps[exp]['wall'][group]:
            gcurve = vpython.graph.gcurve()
            gcurve.plot(pos=poly)
            gcurve.plot(pos=poly[0])
    vpython.graph.gdisplay(title=exp + "wallall")
    for group in exps[exp]['groups']:
        for poly in exps[exp]['wallall'][group]:
            gcurve = vpython.graph.gcurve()
            gcurve.plot(pos=poly)
            gcurve.plot(pos=poly[0])
