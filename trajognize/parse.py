"""
Input file parsers for trajognize.
"""

from collections import deque
import datetime
import xml.dom.minidom
from math import radians, sqrt

from .init import ColorBlob, ColorBlobE, MDBlob, RatBlob, Barcode
from .util import exit, strid2coloridindex


def parse_paintdates(inputfile):
    """Parse paint date file and return list of paint dates."""
    paintdates = []
    for linenum, line in enumerate(open(inputfile).readlines()):
        line = line.strip()
        # check for empty and comment lines
        if not line or line.startswith("#"):
            continue
        linesplit = line.split(" ", 3)
        # some error checking
        if linesplit[0] != "PAINT" or len(linesplit) < 2:
            print("WARNING - line #%d is probably bad:\n%s" % (linenum, line))
            continue
        # convert line to datetime (and let datetime do the error handling)
        try:
            t = datetime.datetime.strptime(linesplit[1], "%Y-%m-%d_%H-%M-%S")
        except ValueError:
            print("WARNING - format error in line %d:\n%s" % (linenum, line))
            raise
        paintdates.append(t)
    return paintdates


def parse_entry_times(inputfile):
    """Parse text file containing entry times to be skipped during analysis.

    Keyword arguments:
    inputfile -- any text file lines like this:
                 YYYY.MM.DD  HH:MM   HH:MM   comments

    Return value:
    dictionary containing list of entry time dicts for each day as main dict key.

    Note: use util.is_entry_time() to check whether a time instance
    is an entry time or not.

    """
    entrytimes = dict()
    for linenum, line in enumerate(open(inputfile).readlines()):
        line = line.strip()
        # check for empty and comment lines
        if not line or line.startswith("#"):
            continue
        # add all elements to global list
        linesplit = line.split("\t", 3)
        # some error checking
        if len(linesplit) < 3:
            print("WARNING - too few blocks in line %d:\n%s" % (linenum, line))
            continue
        # convert line to date and time (and let datetime do the error handling)
        try:
            date = datetime.datetime.strptime(linesplit[0], "%Y.%m.%d").date()
            timefrom = datetime.datetime.strptime(linesplit[1], "%H:%M").time()
            timeto = datetime.datetime.strptime(linesplit[2], "%H:%M").time()
        except ValueError:
            print("WARNING - format error in line %d:\n%s" % (linenum, line))
            raise
        if len(linesplit) > 3:
            comment = linesplit[3]
        else:
            comment = ""
        # add to entrytimes dict
        key = date.isoformat()
        value = {
            "from": datetime.datetime.combine(date, timefrom),
            "to": datetime.datetime.combine(date, timeto),
            "comment": comment,
        }
        if key not in entrytimes.keys():
            entrytimes[key] = [value]
        else:
            entrytimes[key].append(value)
    return entrytimes


def parse_blob_file(inputfile, lastframe=None):
    """Parse a full .blobs file created by ratognize.

    Keyword arguments:
    inputfile -- any *.blobs file created by ratognize
    lastframe -- debug option not to parse the whole file, only the beginning

    Return value:
    full data tuple (blob, md, rat), where:
        blob[framenum][index] is a ColorBlob object
        md[framenum][index]   is a MDBlob object
        rat[framenum][index]  is a RatBlob object

        Examples:
            blob[6][10].centerx means 6th frame, 10th blob center x coordinate
            md[0][0].orientation means the 0th frame 0th md blob orientation in radians

    """
    linetypes = {"MD": 5, "RAT": 5, "BLOB": 4, "BLOBE": 6}

    # get number of frames quickly
    try:
        i = int(deque(open(inputfile), 1)[0].split(None, 1)[0])
    except IndexError:
        print("ERROR: could not read frame number from blob file.")
        return (None, None, None)
    if lastframe is None or lastframe < 0 or lastframe > i:
        lastframe = i

    color_blobs = [[] for x in range(lastframe + 1)]
    md_blobs = [[] for x in range(lastframe + 1)]
    rat_blobs = [[] for x in range(lastframe + 1)]

    for linenum, line in enumerate(open(inputfile).readlines()):
        line = line.strip()
        # check for empty and comment lines
        if not line or line.startswith("#"):
            continue
        # add all elements to global list
        linesplit = line.split()
        # skip empty lines (there is one at the end of each list/file)
        i = len(linesplit)
        if i < 3:
            print("WARNING - too few blocks in line #%d:\n%s" % (linenum, line))
            continue
        framenum = int(linesplit[0])
        if framenum > lastframe:
            break
        linetype = linesplit[1]
        blobcount = int(linesplit[2])
        # quick check on element count
        if i != blobcount * linetypes[linetype] + 3:
            print(
                "WARNING - blobcount mismatch in line #%d; %d elements instead of %d*%d=%d"
                % (
                    linenum,
                    i - 3,
                    blobcount,
                    linetypes[linetype],
                    blobcount * linetypes[linetype],
                )
            )
        j = 3
        try:
            if linetype == "BLOB":
                # if framenum != len(color_blobs):
                #    print("WARNING - framenum mismatch, framenum=%d, len(color_blobs)=%d" % (framenum, len(color_blobs)))
                # color_blobs.append([ [] for x in project_settings.color2int_lookup ])
                for i in range(blobcount):
                    color = int(linesplit[j][1:])
                    centerx = float(linesplit[j + 1])
                    centery = float(linesplit[j + 2])
                    radius = float(linesplit[j + 3][:-1])
                    color_blobs[framenum].append(
                        ColorBlob(color, centerx, centery, radius, [])
                    )
                    j += linetypes[linetype]
            elif linetype == "BLOBE":
                # if framenum != len(color_blobs):
                #    print("WARNING - framenum mismatch, framenum=%d, len(color_blobs)=%d" % (framenum, len(color_blobs)))
                # color_blobs.append([ [] for x in color2int ])
                for i in range(blobcount):
                    color = int(linesplit[j][1:])
                    centerx = float(linesplit[j + 1])
                    centery = float(linesplit[j + 2])
                    axisA = float(linesplit[j + 3])
                    axisB = float(linesplit[j + 4])
                    radius = sqrt(axisA * axisB)
                    orientation = radians(float(linesplit[j + 5][:-1]))  # [deg]->[rad]
                    color_blobs[framenum].append(
                        ColorBlobE(
                            color,
                            centerx,
                            centery,
                            radius,
                            axisA,
                            axisB,
                            orientation,
                            [],
                        )
                    )
                    j += linetypes[linetype]
            elif linetype == "MD":
                # if framenum != len(md_blobs):
                #    print("WARNING - framenum mismatch, framenum=%d, len(md_blobs)=%d" % (framenum, len(md_blobs)))
                # md_blobs.append([])
                for i in range(blobcount):
                    centerx = float(linesplit[j][1:])
                    centery = float(linesplit[j + 1])
                    axisA = float(linesplit[j + 2])
                    axisB = float(linesplit[j + 3])
                    orientation = radians(float(linesplit[j + 4][:-1]))  # [deg]->[rad]
                    md_blobs[framenum].append(
                        MDBlob(centerx, centery, axisA, axisB, orientation)
                    )
                    j += linetypes[linetype]
            elif linetype == "RAT":
                # if framenum != len(rat_blobs):
                #    print("WARNING - framenum mismatch, framenum=%d, len(rat_blobs)=%d" % (framenum, len(rat_blobs)))
                # rat_blobs.append([])
                for i in range(blobcount):
                    centerx = float(linesplit[j][1:])
                    centery = float(linesplit[j + 1])
                    axisA = float(linesplit[j + 2])
                    axisB = float(linesplit[j + 3])
                    orientation = radians(float(linesplit[j + 4][:-1]))  # [deg]->[rad]
                    rat_blobs[framenum].append(
                        RatBlob(centerx, centery, axisA, axisB, orientation)
                    )
                    j += linetypes[linetype]
        except:
            print("ERROR - in line #%d" % linenum)
            raise

    return (color_blobs, md_blobs, rat_blobs)


def parse_log_file(inputfile, lastframe=None):
    """Parse a full .log file and extract light condition and cage center list (so far).

    Keyword arguments:
    inputfile -- any *.log file created by ratognize
    lastframe -- debug option not to parse the whole file, only the beginning

    Return value:
    (light_log, cage_log) tuple, where members are dictionaries of light/cage
    condition changes with key as frame number, value as new light/cage condition.

    each light_log value is a light string (e.g. DAYLIGHT),
    each cage_log value is a list of [center_x center_y horizontal_angle vertical_angle]

    TODO: add the rest of log as separate dicttionaries, if needed

    """

    # get number of frames quickly
    try:
        i = int(deque(open(inputfile), 1)[0].split(None, 1)[0])
    except IndexError:
        print("ERROR: could not read frame number from log file.")
        return (None, None)
    if lastframe is None or lastframe < 0 or lastframe > i:
        lastframe = i

    light_log = {}
    cage_log = {}

    for line in open(inputfile).readlines():
        line = line.strip()
        # check for empty and comment lines
        if not line or line.startswith("#"):
            continue
        linesplit = line.split()
        if len(linesplit) < 2:
            continue
        framenum = int(linesplit[0])
        if framenum > lastframe:
            break
        # parse LED lines
        if len(linesplit) == 3 and linesplit[1] == "LED":
            light_log[framenum] = linesplit[2]
        # parse CAGE lines
        elif len(linesplit) == 6 and linesplit[1] == "CAGE":
            cage_log[framenum] = [float(i) for i in linesplit[2:6]]

    return (light_log, cage_log)


def parse_barcode_file(inputfile, colorids, firstframe=0, lastframe=None):
    """Parse a full .blobs.barcodes file created by trajognize itself.

    Keyword arguments:
    inputfile -- any *.blobs.barcodes file created by trajognize
    colorids  -- global colorid database
    firstframe -- debug option not to parse wht whole file, only the end
    lastframe -- debug option not to parse the whole file, only the beginning

    Return value:
    list of barcodes organized like this:
        barcodes[framenum][coloridindex][index] is a Barcode object

    """
    MCHIPS = len(colorids[0])
    # get number of frames quickly
    try:
        i = int(deque(open(inputfile), 1)[0].split(None, 1)[0])
    except IndexError:
        print("ERROR: could not read frame number from barcode file.")
        return None
    if firstframe < 0:
        firstframe = 0
    if firstframe:
        print(
            "WARNING: debug option firstframe specified, frame number will not be equal to list index in output!"
        )
        if firstframe > i:
            firstframe = i
    if lastframe is None or lastframe < firstframe or lastframe > i:
        lastframe = i

    barcodes = [
        [[] for k in range(len(colorids))] for x in range(firstframe, lastframe + 1)
    ]

    for line in open(inputfile).readlines():
        line = line.strip()
        # check for empty and comment lines
        if not line or line.startswith("#"):
            continue
        # add all elements to global list
        linesplit = line.split()
        # skip empty lines (there is one at the end of each list/file)
        i = len(linesplit)
        if i < 2:
            print("WARNING - too few blocks in line:\n%s" % line)
            continue
        framenum = int(linesplit[0])
        if framenum < firstframe:
            continue
        if framenum > lastframe:
            break
        barcodecount = int(linesplit[1])
        j = 2
        for i in range(barcodecount):
            barcode = Barcode(
                float(linesplit[j + 1]),  # centerx
                float(linesplit[j + 2]),  # centery
                radians(float(linesplit[j + 5])),  # orientation [deg]->[rad]
                int(linesplit[j + 6]),  # mfix
                MCHIPS,
            )

            k = strid2coloridindex(linesplit[j], colorids)
            barcodes[framenum - firstframe][k].append(barcode)
            j += 7

    return barcodes


def parse_stat_output_file(inputfile, index=None):
    """Parse a full _stat_*.txt file created by trajognize stat(sum).

    Note that trajognize stat sum outputs are also saved in compressed
    python object format, in most of the cases it is simpler to load
    those with util.load_object()

    Keyword arguments:
    inputfile  -- any _stat_*.txt file that contains data in paragraphs
    index      -- if only a given paragraph is to be parsed

    Return value:
    parsed data in the following format:
    data[p][x][y] = data entry of paragraph p, row x, column y, including headers

    if index is defined, data is only data[x][y]

    Paragraphs are separated by at least 2 empty lines

    """
    data = []
    emptylines = 2
    p = -1
    linenum = 0
    for line in open(inputfile).readlines():
        line = line.strip()
        linenum += 1
        # check for empty and comment lines
        if line.startswith("#"):
            continue
        if not line:
            emptylines += 1
            continue
        linesplit = line.split("\t")
        # jump to next paragraph
        if emptylines > 1:
            p += 1
            data.append([])
        # or check error
        elif emptylines == 1:
            print(
                "Error in data, only one line separates paragraphs in line #%d"
                % linenum
            )
            return None
        # or check this paragraph
        else:
            # check for error
            lenprev = len(data[p][-1])
            lenthis = len(linesplit)
            # if size is decreasing, we throw an error
            if lenprev > lenthis:
                print(
                    "Error in data, length mismatch in line #%d (%d > %d)"
                    % (linenum, lenprev, lenthis)
                )
                return None
            # if greater, we insert empty values to previous entries and throw only warning
            # (e.g. heatmap dailyoutput uses this format that header line is only 1 entry long)
            elif lenprev < lenthis:
                for i in range(len(data[p])):
                    data[p][i] += [""] * (lenthis - lenprev)
        #                print("Warning in data, length mismatch in line #%d (%d < %d)" % (linenum, lenprev, lenthis))
        #        if index is None or index == p:
        data[p].append(list(linesplit))
        emptylines = 0

    if index is None:
        return data
    else:
        return data[index]
