#!/usr/bin/python
# vim: ts=4 sw=4 sts=4 et
"""
This is a minimal script that checks ratmaze trajognize results.

Usage: __file__ inputdir

where 'inputdir' is a location where subdirectories of
atlasz trajognize results can be found.

"""

import os, sys
from glob import glob

def main(argv=[]):
    """Main entry point."""
    if len(argv) != 1 or "-h" in argv or "--help" in argv:
        print(__doc__)
        return
    print("\t".join(["#inputdir", "number_of_rats", "blob_frames", "full_barcodes",
            "full_barcodes/blob_frames/number_of_rats"]))
    for inputdir in glob(os.path.join(argv[0], "ratmaze_full_run__trajognize*")):
        if not os.path.isdir(inputdir):
            continue
        blob_frames = "nan"
        full_barcodes = "nan"
        number_of_rats = 8 if "M12" in inputdir or "M34" in inputdir or \
                "F12" in inputdir or "F34" in inputdir else 1
        try:
            inputfile = glob(os.path.join(inputdir, "*.trajognize.stdout"))[0]
        except:
            pass
        else:
            for line in open(inputfile, 'r'):
                if "BLOB frames read" in line:
                    blob_frames = line.replace("BLOB frames read", "").strip()
                if "full barcodes found" in line:
                    full_barcodes = line.replace("full barcodes found", "").strip()
                if blob_frames != "nan" and full_barcodes != "nan":
                    break
        print("\t".join([os.path.split(inputdir)[1], str(number_of_rats),
                blob_frames, full_barcodes,
                str(float(full_barcodes) / float(blob_frames) / number_of_rats)]))


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:])) # pass only real params to main
    except Exception as ex:
        print(ex, file=sys.stderr)
        import traceback
        traceback.print_exc(ex)
        sys.exit(1)
