#!/usr/bin/python
# vim: ts=4 sw=4 sts=4 et
"""
This is a small script that converts a barcode file into an srt file.

Usage:  __file__ something.barcodes projectsettingsfile.py

Output is saved as 'something.barcodes.srt'

"""

import os, sys, time
from glob import glob
from math import sqrt

try:
    import trajognize
    import trajognize.stat
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(
        os.path.dirname(sys.modules[__name__].__file__), "..")))
    import trajognize
    import trajognize.stat

def get_label_color(mfix):
    """Deine color the same way as in ratognize.cpp more or less"""
    color = "#ff0000"
    if mfix & trajognize.init.MFix.CHOSEN:
        if mfix & trajognize.init.MFix.VIRTUAL:
            color = "#ffff00"
        else:
            color = "#ffffff"
    if mfix & trajognize.init.MFix.DEBUG:
        color = "#800080"

    return color

def main(argv=[]):
    """Main entry point."""
    if len(argv) != 2 or "-h" in argv or "--help" in argv:
        print(__doc__)
        return
    inputfile = argv[0]
    projectfile = argv[1]

    print("\nParsing project settings file...")
    project_settings = trajognize.settings.import_trajognize_settings_from_file(projectfile)
    if project_settings is None:
        return
    colorids = project_settings.colorids
    print("Project: %s" % project_settings.project_name)
    print("Image size: %gx%g" % project_settings.image_size)
    print("FPS: %g" % project_settings.FPS)

    print("\nParsing input file '%s'..." % inputfile)
    barcodes = trajognize.parse.parse_barcode_file(inputfile, colorids, lastframe=1000)
    if barcodes is None:
        return
    print("  %d barcode lines parsed" % len(barcodes))

    print("\nWriting subtitles...")
    outputfile = open(inputfile + ".srt", 'w')
    subtitleindex = 0
    for currentframe in range(len(barcodes)):
        for i in range(len(barcodes[currentframe])):
            for barcode in barcodes[currentframe][i]:
                msg = trajognize.stat.util.get_subtitle_string(subtitleindex,
                        currentframe/float(project_settings.FPS),
                        colorids[i],
                        get_label_color(barcode.mfix),
                        barcode.centerx, barcode.centery,
                        project_settings.image_size.x,
                        project_settings.image_size.y)
                subtitleindex += 1
                outputfile.write(msg)

if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:])) # pass only real params to main
    except Exception as ex:
        print(ex, file=sys.stderr)
        import traceback
        traceback.print_exc(ex)
        sys.exit(1)