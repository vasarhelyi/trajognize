"""
Output file generation functions for trajognize.
"""

from trajognize.init import *
from trajognize.util import mfix2str_allascomment
from trajognize.algo_blob import barcodeindices_not_deleted
from math import degrees
import os, datetime

# global output file handlers - we do not want to open them on every frame separately
oft = []       # barcode text file
oftlog = []    # log file


def barcode_textfile_init(filename, barcodes):
    """Open output file and write barcode text file header.

    Keyword arguments:
    filename -- output file name
    barcodes -- global list of all barcodes (barcode_t)
                structured like this: [framenum][coloridindex][index]

    Uses the global variable 'oft' as the file handler.

    """
    global oft
    if os.path.isfile(filename):
        os.remove(filename)
    oft = open(filename, 'w')
    oft.write("# number of IDs: %d\n" % len(barcodes[0]))
    oft.write("# number of frames: %d\n" % len(barcodes))
    oft.write(mfix2str_allascomment())
    oft.write('# fix width format: framenum barcodenum {ID centerx centery xWorld yWorld orientation mFix} {...\n')
    oft.write('\n')


def barcode_textfile_writeframe(barcodes, framenum, colorids, deleted=True):
    """Write all barcodes of current frame to text file.

    Keyword arguments:
    barcodes -- barcodes (barcode_t) of the current frame
                structured like this: [coloridindex][index]
    framenum -- current frame number
    colorids -- global colorid database created by parse_colorid_file()
    deleted  -- should we write deleted barcodes as well?

    Uses the global variable 'oft' as the file handler.
    
    """

    global oft
    # get list of barcodes to be written
    barcodeindices = [[barcode_index_t(k,x) for x in xrange(len(barcodes[k]))] for k in xrange(len(barcodes))]
    if not deleted:
        for k in xrange(len(barcodes)):
            barcodeindices[k] = barcodeindices_not_deleted(barcodeindices[k], barcodes)
    # write framenum and barcodenum
    i = 0
    for sameid in barcodeindices:
        i += len(sameid)
    oft.write("%d\t%d" % (framenum, i))
    # write data
    for k in xrange(len(barcodeindices)):
        strid = colorids[k].strid
        for ki in barcodeindices[k]:
            barcode = barcodes[ki.k][ki.i]
            oft.write("\t%s\t%.1f\t%.1f\t%.1f\t%.1f\t%.1f\t%d" % (strid, barcode.centerx, barcode.centery, 0, 0, degrees(barcode.orientation), barcode.mfix))
    oft.write('\n')


def barcode_textfile_writeall(barcodes, colorids, deleted=True):
    """Write all barcodes from all frames to textfile.

    Keyword arguments:
    barcodes -- global list of all barcodes (barcode_t)
                structured like this: [framenum][coloridindex][index]
    colorids -- global colorid database created by parse_colorid_file()
    deleted  -- should we write deleted barcodes as well?

    """
    for framenum in xrange(len(barcodes)):
        barcode_textfile_writeframe(barcodes[framenum], framenum, colorids, deleted)


def barcode_textfile_close():
    """Close barcode output text file.

    Uses the global variable 'oft' as the file handler.

    """
    global oft
    oft.flush()
    oft.close()


def logfile_init(filename):
    """Open output log file and write log file header.

    Keyword arguments:
    filename -- output file name

    Uses the global variable 'oftlog' as the file handler.

    """
    global oftlog
    if os.path.isfile(filename):
        os.remove(filename)
    oftlog = open(filename, 'w')
    oftlog.write("# trajognize log file created on %s\n\n" % str(datetime.datetime.now()))
    oftlog.write("# Log file format: frame warningtype params\n")
    oftlog.write("# Log file entry types:\n")
    oftlog.write("#   NUB blobcount list_of_blob_indices -- not used blob indices (pointing to .blobs file)\n")
    oftlog.write("\n")


def logfile_writeframe(blobs, barcodes, framenum):
    """Write logfile entry for current frame.

    Keyword arguments:
    blobs    -- list of all blobs (color_blob_t) from a given frame
    barcodes -- barcodes (barcode_t) of the current frame
                structured like this: [coloridindex][index]
    framenum -- current frame number

    Uses the global variable 'oftlog' as the file handler.

    """

    global oftlog
    # get NUB - not used blobs
    nub = []
    for i in xrange(len(blobs)):
        if not barcodeindices_not_deleted(blobs[i].barcodeindices, barcodes):
            nub.append(i)
    # write it
    oftlog.write("%d\tNUB\t%d" % (framenum, len(nub)))
    for x in nub:
        oftlog.write("\t%d" % x)
    oftlog.write("\n")


def logfile_writeall(blobs, barcodes):
    """Write log data from all frames to log file

    Keyword arguments:
    blobs    -- global list of all blobs (color_blob_t)
                structured like this: [framenum][index]
    barcodes -- global list of all barcodes (barcode_t)
                structured like this: [framenum][coloridindex][index]

    """
    for framenum in range(len(blobs)):
        logfile_writeframe(blobs[framenum], barcodes[framenum], framenum)


def logfile_close():
    """Close logfile.

    Uses the global variable 'oftlog' as the file handler.

    """
    global oftlog
    oftlog.flush()
    oftlog.close()


def matrixfile_write(outputfile, W, name = "", idorder=None):
    """Print a data matrix.
    
    Keyword arguments:
    outputfile -- output file to save data to
    data       -- square data matrix (dict/list) to save
    idorder    -- order of rows and columns (list)

    """
    n = len(W)
    if isinstance(W, dict):
        if idorder is None: idorder = list(W) # TODO: this case is not defined well!!!
    elif isinstance(W, list):
        if idorder is None: idorder = range(n)
    else:
        0/0

    s = [name] + [str(i) for i in idorder]
    outputfile.write("\t".join(s) + "\n")
    for i in idorder:
        s = [str(i)] + ["%1.12g" % W[i][j] for j in idorder]
        outputfile.write("\t".join(s) + "\n")
