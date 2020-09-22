try:
    import trajognize
    import trajognize.stat
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(
        os.path.dirname(sys.modules[__name__].__file__), "..")))
    import trajognize
    import trajognize.stat


exps = trajognize.stat.experiments.get_initialized_experiments()
barcode = trajognize.init.Barcode()
objectcenter = exps['fifth_G1_G4_large_G2_G3_small'][obj]['G1L'][0]
obj = 'water'
obj = 'wheel'
obj = 'home'
obj = 'watertop'
obj = 'food'

for x in range(0,2000,50):
    for y in range(0,1080,50):
        b.centerx = x
        b.centery = y
        if trajognize.stat.experiments.is_barcode_under_object(barcode, objectcenter,
#                trajognize.stat.experiments.object_areas[obj]):
                trajognize.stat.project.object_queuing_areas[obj]):
            print("ez van alatta: %d, %d " % (x, y))