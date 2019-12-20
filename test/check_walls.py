import visual
import visual.graph
from trajognize.stat.experiments import *

exps = get_initialized_experiments()
for exp in exps:
    visual.graph.gdisplay(title=exp + "wall")
    for group in exps[exp]['groups']:
        for poly in exps[exp]['wall'][group]:
            gcurve = visual.graph.gcurve()
            gcurve.plot(pos=poly)
            gcurve.plot(pos=poly[0])
    visual.graph.gdisplay(title=exp + "wallall")
    for group in exps[exp]['groups']:
        for poly in exps[exp]['wallall'][group]:
            gcurve = visual.graph.gcurve()
            gcurve.plot(pos=poly)
            gcurve.plot(pos=poly[0])
