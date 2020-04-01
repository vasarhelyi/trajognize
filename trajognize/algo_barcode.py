"""
All kinds of algorithms used by trajognize.main() that are related to barcodes.
"""

import itertools

from trajognize.project import *
from trajognize.init import *
from trajognize.algo import *
from trajognize.algo_blob import *
from trajognize.util import mfix2str


def get_chosen_barcode_indices(barcodes):
    """Return list of chosen barcode indices from list of barcodes on current frame.

    :param barcodes: list of barcodes of the current frame

    """
    id_count = len(barcodes)
    chosen = [None for k in range(id_count)]
    for k in range(id_count):
        for i in range(len(barcodes[k])):
            if barcodes[k][i].mfix & MFIX_CHOSEN:
                chosen[k] = i
                break
    return chosen


def barcode_is_free(barcodes, k, j, blobs):
    """Check whether a barcode is free to use, because it is deleted
    (but not permanently deleted) and all its blobs are free, too.

    Keyword arguments:
    barcodes   -- list of all barcodes in current frame
    k,j        -- barcode index of barcode to check
    blobs      -- list of all color blobs (color_blob_t) for current frame

    """
    barcode = barcodes[k][j]
    if not barcode.mfix or not (barcode.mfix & MFIX_DELETED):
        return False
    for i in barcode.blobindices:
        blob = blobs[i]
        if barcodeindices_not_deleted(blob.barcodeindices, barcodes):
            return False
    return True


def check_barcode_blob_consistency(barcodes, blobs, colorids):
    """Debug function to check all blob indices of barcodes and all
    barcode indices of blobs whether they are consistent or not."""
    print("Checking barcode-blob consistency...", end=" ")
    for frame in range(len(barcodes)):
        # check from barcodes
        for k in range(len(colorids)):
            for i in range(len(barcodes[frame][k])):
                barcode = barcodes[frame][k][i]
                ki = barcode_index_t(k,i)
                for j in barcode.blobindices:
                    if ki not in blobs[frame][j].barcodeindices:
                        raise ValueError("mismatch on frame %d, blob %d does not contain %s barcode #%d %s" % (frame, j, colorids[k].strid, i, mfix2str(barcode.mfix)))
        # check from blobs
        for j in range(len(blobs[frame])):
            blob = blobs[frame][j]
            for ki in blob.barcodeindices:
                if j not in barcodes[frame][ki.k][ki.i].blobindices:
                    raise ValueError("mismatch on frame %d, %s barcode #%d %s does not contain blob %d " % (frame, colorids[ki.k].strid, ki.i, mfix2str(barcode.mfix), j))
    print("OK\n")


def print_max_barcode_count(barcodes, colorids):
    """Debug function to print the maximum number of barcodes present simultaneously."""
    count = [[0,0,[]] for k in range(len(colorids))]
    for frame in range(len(barcodes)):
        for k in range(len(colorids)):
            x = len(barcodes[frame][k])
            if x > count[k][0]:
                count[k] = [x, frame, barcodes[frame][k]]
    print("Max barcodes simultaneously:")
    sum = 0
    for k in range(len(colorids)):
        sum += count[k][0]
        print(" ", colorids[k].strid, count[k][0], "frame", count[k][1], end=" ")
        for barcode in count[k][2]:
            print("xy", int(barcode.centerx), int(barcode.centery), mfix2str(barcode.mfix), end=" ")
        print
    print("  sum max:", sum)
    print


def find_missing_unused_blob(barcode, strid, blobs, sdistlists, currentframe):
    """Try to find missing and unused blobs
    to include them into partly found barcodes.

    Keyword arguments:
    barcode      -- a barcode of barcode_t type
    strid        -- string ID of the barcode (colorids[coloridindex])
    blobs        -- list of all color blobs (color_blob_t) for current frame
    sdistlists   -- possible chain connections on current frame, created in advance by
                    create_spatial_distlists()
    """
    # assert: len(strid) == MCHIPS
    n = len(barcode.blobindices)
    if n > MCHIPS:
        raise ValueError("too many %s blob indices on frame %d (%d>%d), " % (strid, currentframe, n, MCHIPS), mfix2str(barcode.mfix))
    # do not change anything if all blobs were found
    if n == MCHIPS:
        return 0

    # get list of contained colors in barcode
    containedcolors = set(blobs[i].color for i in barcode.blobindices)
    containedindex = [0 for x in range(len(strid))]

    # find candidates for all positions
    candidates = [set() for x in range(len(strid))]
    newones = 0
    for i in range(len(strid)):
        color = color2int[strid[i]]
        # if barcode contains blob at position, store as candidate
        if color in containedcolors:
            containedindex[i] = 1
            for j in barcode.blobindices:
                if blobs[j].color == color:
                    candidates[i].add(j)
        # if color is missing, find all candidates that are close to contained blobs,
        # are not assigned to anything and color matches missing color at given position
        # TODO: how to treat deleted? (they are not ignored since blobindices is not empty)
        else:
            for blobi in barcode.blobindices:
                ii = strid.index(int2color[blobs[blobi].color])
                # check all candidates with smaller distance threshold
                for j in sdistlists[blobi][0]:
                    if not blobs[j].barcodeindices and blobs[j].color == color:
                        candidates[i].add(j)
                        newones += 1
                # check second neighbor with greater distance threshold
                if abs(i-ii) > 1:
                    for j in sdistlists[blobi][1]:
                        if not blobs[j].barcodeindices and blobs[j].color == color:
                            candidates[i].add(j)
                            newones += 1
    if not newones: return 0

    # create virual blob chains to decide whether they could be barcodes or not
    fullfound = 1
    for candidate in candidates:
        if not candidate:
            fullfound = 0
            break
    if fullfound:
        blobchains = list(itertools.product(*candidates))
        #print('  find_missing_unused_blob() found full:', currentframe, strid, [blobchains[x] for x in range(len(blobchains))])
        candidate_blobchains = []
        for i in range(len(blobchains)):
            if is_blob_chain_appropriate_as_barcode([blobs[j] for j in blobchains[i]]):
                candidate_blobchains.append(i)
        if not candidate_blobchains: return 0

        # if there are more candidates, print warning
        if len(candidate_blobchains) > 1:
            print("\n  WARNING#1 in find_missing_unused_blob(): frame", currentframe, 'color', int2color[color], 'in', strid, 'candidates', [blobchains[x] for x in candidate_blobchains], 'missingcolors', MCHIPS-len(containedcolors), 'storing first candidate')
        # store first good candidate
        barcode.blobindices = list(blobchains[candidate_blobchains[0]])

    else:
        #print('  partial', currentframe, strid, [candidates[x] for x in range(len(candidates))])
        for i in range(len(strid)):
            candidate = candidates[i]
            if not candidate or containedindex[i]: continue
            # if there are more candidates, print warning
            good = 0
            for blobi in candidate:
                # Warning: we assume here that barcode is from tempbarcode that is initialized
                # with the same position and orientation as on the last frame, namely,
                # that barcode parameters are well initialized at assumed position on current frame.
                if is_point_inside_ellipse(blobs[blobi],
                        rat_blob_t(barcode.centerx, barcode.centery,
                            MAX_INRAT_DIST * MCHIPS / 2,
                            MAX_INRAT_DIST / 2,
                            barcode.orientation)):
                    good += 1
                    if good == 1:
                        barcode.blobindices.append(blobi)
                    else:
                        print("\n  WARNING#2 in find_missing_unused_blob(): frame", currentframe, 'color', int2color[color], 'in', strid, 'candidates', candidate, 'missingcolors', MCHIPS-len(containedcolors), 'storing first candidate')
    return 1


def order_blobindices(barcode, strid, blobs, forcefull=False):
    """Order partlyfound blobs in the order they should appear according to color id.

    Keyword arguments:
    barcode   -- a barcode of barcode_t type
    strid     -- string ID of the barcode (colorids[coloridindex])
    blobs     -- list of all color blobs (color_blob_t) for current frame
    forcefull -- if true, change order of full barcodes as well (might be needed)

    """
    # do not change if all/none/1 blobs were found (unless forcefull is on)
    n = len(barcode.blobindices)
    if n > MCHIPS:
        raise ValueError("too many blob indices are assigned to %s barcode (%d>%d) %s" % (strid, n, MCHIPS, mfix2str(barcode.mfix)))
    if  n < 2:
        return
    if n == MCHIPS and not forcefull:
        return

    # store colors from old order
    oldindices = list(barcode.blobindices)
    oldcolors = [blobs[i].color for i in barcode.blobindices]
    # TODO debug double check, later comment out if everything works well...
    if set(oldcolors).difference(set([color2int[x] for x in strid])):
        raise ValueError("unwanted color in blobindices")
    # create new order from colorid string
    i = 0
    for c in strid:
        ii = color2int[c]
        for j in range(len(oldcolors)):
            if ii == oldcolors[j]:
                barcode.blobindices[i] = oldindices[j]
                i += 1
                break


def calculate_params(barcode, strid, blobs):
    """Calculate barcode parameters based on blob data provided as arguments.

    Function assumes that blob indices are in the order appearing on the rat.

    Keyword arguments:
    barcode -- a barcode of barcode_t type
    strid   -- string id of the barcode
    blobs   -- list of all color blobs (color_blob_t) for current frame

    """
    # define some parameters
    n = len(barcode.blobindices)
    if n > MCHIPS:
        raise ValueError("too many %s blob indices (%d>%d), " % (strid, n, MCHIPS), mfix2str(barcode.mfix))
    colors = set([blobs[i].color for i in barcode.blobindices])
    # do not change params if there are no blobs
    if not n: return

    # calculate center
    barcode.centerx = 0
    barcode.centery = 0
    for i in barcode.blobindices:
        barcode.centerx += blobs[i].centerx
        barcode.centery += blobs[i].centery
    barcode.centerx /= n
    barcode.centery /= n

    # calculate orientation
    if n >= 3:
        # calculate orientation with least squares around center
        # source: http://mathworld.wolfram.com/LeastSquaresFitting.html
        xx=0; xy=0; yy=0
        for i in barcode.blobindices:
            #print(i, blobs[barcode.blobindices[i]].centerx, blobs[barcode.blobindices[i]].centery, barcode.centerx, barcode.centery)
            xx += (blobs[i].centerx - barcode.centerx) * (blobs[i].centerx - barcode.centerx)
            xy += (blobs[i].centerx - barcode.centerx) * (blobs[i].centery - barcode.centery)
            yy += (blobs[i].centery - barcode.centery) * (blobs[i].centery - barcode.centery)

        # orientation transformation from [0,180] to [-180,180]
        # orientation always points towards the front of the rat,
        # where the 0th bin position stands
        #
        #    _/-------\
        #   <_  01..k  =======---
        #     \-------/
        #
        #  coordinate system with angle starting CW from x (as on screen):
        #
        #  +-------- x 0
        #  |
        #  |
        #  |y 90
        #
        ##################

        # OK
        if xx>yy: # -45 --> 45
            barcode.orientation = atan2(xy,xx)
            if blobs[barcode.blobindices[-1]].centerx > blobs[barcode.blobindices[0]].centerx: # 135 --> 225
                barcode.orientation += pi
        else: # 45 --> 135
            barcode.orientation = pi / 2 - atan2(xy, yy)
            if blobs[barcode.blobindices[-1]].centery > blobs[barcode.blobindices[0]].centery: # 225 --> 315
                barcode.orientation += pi
        d = barcode.orientation
        barcode.orientation = atan2(sin(d),cos(d)) # [-pi,pi] range
    elif n == 2:
        barcode.orientation = atan2(
                blobs[barcode.blobindices[0]].centery - blobs[barcode.blobindices[1]].centery,
                blobs[barcode.blobindices[0]].centerx - blobs[barcode.blobindices[1]].centerx)
    elif n == 1:
        # do not change orientation, it is possibly set from previous barcode orientation

    # correct center if needed now as we have an estimate for the orientation
    if n < len(strid):
        j = 0
        jsum = 0
        for i in range(len(strid)):
            if color2int[strid[i]] in colors:
                j +=  i - (len(strid) - 1) / 2
                jsum += 1
        j /= jsum
        barcode.centerx += j * AVG_INRAT_DIST * cos(barcode.orientation)
        barcode.centery += j * AVG_INRAT_DIST * sin(barcode.orientation)


def remove_overlapping_fullfound(barcodes, blobs, cluster):
    """Remove (possibly) false positive full barcodes that are overlapping.

    Keyword arguments:
    barcodes  -- list of all barcodes (barcode_t) for current frame
    blobs     -- list of all color blobs (color_blob_t) for current frame
    cluster   -- current blob cluster

    Returns number of barcodes deleted and also changes barcode mfix properties.

    And now something completely different: a larch.

    """
    # These iterators are used everywhere below:
    # i - blobindex (int)
    # j - barcodeindex (barcode_index_t)
    # find barcodes that belong to the current blob cluster
    barcodecluster = set()
    for i in cluster:
        for j in barcodeindices_not_deleted(
                blobs[i].barcodeindices, barcodes, MFIX_FULLFOUND):
            barcodecluster.add(j)
    # iterate all barcodes and find ones that are fully overlapping others,
    # (all blobs have more than one barcode index)
    overlappedbarcodes = set()
    for ki in barcodecluster:
        overlapped = True
        for i in barcodes[ki.k][ki.i].blobindices:
            if len(barcodeindices_not_deleted(blobs[i].barcodeindices, barcodes)) < 2:
                overlapped = False
                break
        if (overlapped):
            overlappedbarcodes.add(ki)
    # delete all overlapped barcodes now
    # TODO: maybe more sophisticated algo needed
    # TODO: should we have permanent delete (mfix=0) insted?
    for ki in overlappedbarcodes:
        barcodes[ki.k][ki.i].mfix |= MFIX_DELETED
    return len(overlappedbarcodes)


def set_nocluster_property(barcodes, blobs, cluster):
    """Set nocluster property for 'remote' barcodes (i.e. not surrounded by
    other blobs not belonging to the same barcode.

    Keyword arguments:
    barcodes  -- list of all barcodes (barcode_t) for current frame
    blobs     -- list of all color blobs (color_blob_t) for current frame
    cluster   -- current blob cluster

    Warning: function might return 16 tons.

    """
    # return everywhere in the function when a missed criterium is found
    # return if cannot be fullfound
    if len(cluster) != MCHIPS:
        return
    barcodeindex = -1
    for i in cluster:
        barcodeindices = barcodeindices_not_deleted(
                blobs[i].barcodeindices, barcodes, MFIX_FULLFOUND)
        # return if more barcodes are present around
        if len(barcodeindices) != 1:
            return
        if barcodeindex == -1:
            barcodeindex = barcodeindices[0]
        # return if another barcode is present around
        elif barcodeindex != barcodeindices[0]:
            return

    # no error, set nocluster property
    barcodes[barcodeindex.k][barcodeindex.i].mfix |= MFIX_FULLNOCLUSTER
    return "16 tons"


def find_partlyfound_from_tdist(
        direction, currentframe, tdistlists, color_blobs, barcodes, colorids, sdistlists, md_blobs, mdindices):
    """Find partlyfound barcodes based on temporal blob-based closeness.

    Keyword arguments:
    direction   -- 'backward' or 'forward' to define temporal direction of algo
    curretframe -- current frame number during the analysis
    tdistlists  -- temporal closeness matrix created by
                   create_temporal_distlists()
    color_blobs -- global list of all color blobs (color_blob_t)
                   structured like this: [framenum][index]
    barcodes    -- global list of all barcodes (barcode_t)
                   structured like this: [framenum][coloridindex][index]
    colorids    -- global colorid database created by parse_colorid_file()
    sdistlists  -- possible chain connections on current frame, created in advance by
                   create_spatial_distlists()
    md_blobs    -- global list of all motion blobs (motion_blob_t)
                   structured like this: [framenum][index]
    mdindices   -- global list of motion blob index for all blobs
                   structured like this: [framenum][blobindex] = value (-1 if none)

    Description of algorithm:
    1. Create temporal distance matrix between consecutive frames
    2. Define new barcodes on current frame if the following conditions are met:
        a) There was a barcode on the previous frame containing blobs that
           are close to blobs on the current frame.
        b) Blobs on current frame are not yet assigned to a barcode.
    3. Group blobs that possibly belong to the same new barcode. If more blobs
       of the same color are close enough to be part of the new barcode,
       choose the one closest to the barcode center on the previous frame.
    4. Store new barcodes with mfix value of MFIX_PARTLYFOUND_FROM_TDIST
    5. Check all remaining not used blobs, cluster them and try to assign
       a barcode to them which is not present on the current frame yet
       but was present closeby sometime in the last/next few seconds.

    Function returns number of barcodes (found, adjusted, new) and
    and modifies list-type keyword parameters 'tdistlists' and 'barcodes'.

    """
    if direction == 'forward':
        inc = 1
    elif direction == 'backward':
        inc = -1
    else:
        0/0
    maxskip = 50 # max number of frames around not used blob pairs
    tempbarcodes = [[] for x in range(len(colorids))] # temporarily found new barcodes
    # calculate temporal distances between blobs
    tdistlists[currentframe] = create_temporal_distlists(
            color_blobs[currentframe-inc], color_blobs[currentframe],
            md_blobs[currentframe-inc], md_blobs[currentframe],
            mdindices[currentframe-inc], mdindices[currentframe])
    # temporary storage of notusedblobs
    notusedblobs = set()
    # temporarily store all barcodes that could be found based on tdist from previous barcodes (full or partial)
    # iterate for all blobs on current frame
    for blobi in range(len(color_blobs[currentframe])):
        # skip blobs that ARE already assigned to something not deleted:
        if barcodeindices_not_deleted(
                color_blobs[currentframe][blobi].barcodeindices, barcodes[currentframe]):
            continue
        # skip blobs not close to anything on the previous frame
        if not tdistlists[currentframe][blobi]:
            # store not used one
            notusedblobs.add(blobi)
            continue
        # iterate all close previous
        for prevblobi in tdistlists[currentframe][blobi]:
            # if prev is NOT assigned to a non-deleted barcode, skip
            goodprevbarcodes = barcodeindices_not_deleted(
                    color_blobs[currentframe-inc][prevblobi].barcodeindices,
                    barcodes[currentframe-inc])
            if not goodprevbarcodes:
                # store not used one
                notusedblobs.add(blobi)
                continue
            # iterate all assigned barcodes from prev frame
            for prevbarcodei in goodprevbarcodes:
                # color index is k as always, index is ii now
                k = prevbarcodei.k
                ii = prevbarcodei.i
                oldbarcode = barcodes[currentframe-inc][k][ii]
                # copy prev barcode, change parameters and store in temporary list
                barcode = barcode_t(
                        oldbarcode.centerx, oldbarcode.centery, oldbarcode.orientation,
                        MFIX_PARTLYFOUND_FROM_TDIST, [blobi])
                # store barcode temporarily if it is the first with given color
                if not tempbarcodes[k]:
                    tempbarcodes[k].append(barcode)
                # group temporary barcodes if they come from the same previous barcode
                # or one very close
                else:
                    for i in range(len(tempbarcodes[k])):
                        # new barcode comes from the same as one in already tempbarcodes (or close)
                        if get_distance(barcode, tempbarcodes[k][i]) < 10:
#                            abs(barcode.orientation - tempbarcodes[k][i].orientation) < pi/180):
                            # What if more than one blobs are there with the same color?
                            # Now we use the closest one to prev barcode center.
                            for j in range(len(tempbarcodes[k][i].blobindices)):
                                blobj = tempbarcodes[k][i].blobindices[j]
                                # if different color, skip
                                if color_blobs[currentframe][blobj].color != color_blobs[currentframe][blobi].color: continue
                                # there is and old blob with same color, which one to choose?
                                # if newer one (blobi) is closer than old one (blobj), replace it
                                if (get_distance(oldbarcode, color_blobs[currentframe][blobi]) <
                                        get_distance(oldbarcode, color_blobs[currentframe][blobj])):
                                    tempbarcodes[k][i].blobindices[j] = blobi
                                # otherwise keep old (nop)
                                else:
                                    pass
                                # and end iteration in both cases
                                break
                            # if there was no blob with this color, add new blob
                            else:
                                tempbarcodes[k][i].blobindices.append(blobi)
                            # end iteration
                            break
                    # if this barcode comes from an old barcode not close to any already appended, add new barcode
                    else:
                        tempbarcodes[k].append(barcode)

    # store temporary barcodes in global barcode database
    count = 0
    count_adjusted = 0
    count_notused = 0
    for k in range(len(colorids)):
        for barcode in tempbarcodes[k]:
            # skip ones that are already present in barcodes and undelete them
            # TODO: maybe include new blobs if needed...
            for oldbarcode in barcodes[currentframe][k]:
                if get_distance(oldbarcode, barcode) < 10:
                    oldbarcode.mfix &= ~MFIX_DELETED
                    break
            else:
                count_adjusted += find_missing_unused_blob(barcode, colorids[k].strid, color_blobs[currentframe], sdistlists, currentframe)
                order_blobindices(barcode, colorids[k].strid, color_blobs[currentframe])
                calculate_params(barcode, colorids[k].strid, color_blobs[currentframe])
                barcodes[currentframe][k].append(barcode)
                count += 1
                # store barcode indices in [colorid, index] format in color_blob .barcodeindices list
                for blobi in barcode.blobindices:
                    color_blobs[currentframe][blobi].barcodeindices.append(
                            barcode_index_t(k, len(barcodes[currentframe][k])-1))

    # try to assign new barcodes to still not used and not-close-to-anything blobs
    # remove not used blobs that were added to barcodes lately
    for blobi in list(notusedblobs):
        if color_blobs[currentframe][blobi].barcodeindices:
            notusedblobs.remove(blobi)
    # convert to list
    notusedblobs = list(notusedblobs)
    # create cluster list of not used blobs with temporarily defined blob and sdist lists
    notusedblobsx = [color_blobs[currentframe][blobi] for blobi in notusedblobs]
    sdistlistsx = create_spatial_distlists(notusedblobsx)
    (clusterlists, clusterindices) = find_clusters_in_sdistlists(notusedblobsx, sdistlistsx, 1)
    # check all clusters
    for cluster in clusterlists:
        # skip large clusters
        if len(cluster) > MCHIPS: continue
        # create new barcode from cluster
        newbarcode = barcode_t(0, 0, 0, MFIX_PARTLYFOUND_FROM_TDIST, [notusedblobs[i] for i in cluster])
        colorsincluster = set()
        skip = False
        for i in cluster:
            blob = color_blobs[currentframe][notusedblobs[i]]
            if blob.color in colorsincluster:
                skip = True
                break
            else:
                colorsincluster.add(blob.color)
            newbarcode.centerx += blob.centerx
            newbarcode.centery += blob.centery
        if skip: continue
        newbarcode.centerx /= len(cluster)
        newbarcode.centery /= len(cluster)
        # get colorid candidates
        goodcolors = []
        for k in range(len(colorids)):
            strid = colorids[k].strid
            # skip colorids that do not contain all colors in cluster
            if set([int2color[x] for x in colorsincluster]) - set(strid): continue
            # skip colors that already have a barcode close on current frame
            skip = False
            for barcode in barcodes[currentframe][k]:
                if get_distance(barcode, newbarcode) < 200: # TODO: bring distance limit to global
                    skip = True
                    break
            if skip: continue
            # store good color
            goodcolors.append(k)
        # add barcode that was close enough to this pair in the past 2 seconds (maxskip)
        mindist = MAX_PERFRAME_DIST_MD
        bestk = None
        if inc == 1:
            lastframe = max(0, currentframe - maxskip)
        else:
            lastframe = min(len(barcodes)-1, currentframe + maxskip)
        for frame in range(currentframe, lastframe, -inc):
            for k in goodcolors:
                # find candidates
                for barcode in barcodes[frame][k]:
                    # skip ones with not more than one blob
                    if len(barcode.blobindices) < 2:
                        # ok, changed my mind, keep it if under md (good for sure)
                        if not (barcode.blobindices and mdindices[frame][barcode.blobindices[0]] != -1):
                            continue
                    dist = get_distance(barcode, newbarcode)
                    if dist < mindist:
                        mindist = dist
                        bestk = k
            # store first occurrence
            if mindist < MAX_PERFRAME_DIST_MD:
                order_blobindices(newbarcode, colorids[bestk].strid, color_blobs[currentframe])
                calculate_params(newbarcode, colorids[bestk].strid, color_blobs[currentframe])
                barcodes[currentframe][bestk].append(newbarcode)
                count += 1
                count_notused += 1
                # store barcode indices in [colorid, index] format in color_blob .barcodeindices list
                for bi in newbarcode.blobindices:
                    color_blobs[currentframe][bi].barcodeindices.append(
                            barcode_index_t(bestk, len(barcodes[currentframe][bestk])-1))
                break

    return (count, count_adjusted, count_notused)


def could_be_sharesblob(a, b, ka, kb, blobs, colorids):
    """Are two barcodes good candidates for sharesblob?

    Keyword arguments:
    a        -- first barcode
    b        -- second barcode
    ka       -- coloridindex of first barcode
    kb       -- coloridindex of second barcode
    blobs    -- list of all blobs for current frame
    colorids -- global colorid database created by parse_colorid_file()

    Returns list of blobs that could be shared (or empty list if none found)

    """
    sharedblobs = []
    if get_distance(a, b) < MAX_INRAT_DIST * 2:
        allblobs = set(a.blobindices + b.blobindices)
        cia = [blobs[x].color for x in a.blobindices]
        cib = [blobs[x].color for x in b.blobindices]
        for blobi in allblobs:
            blob = blobs[blobi]
            c = int2color[blob.color]
            # skip blobs if its color is not common in a and b
            if c not in colorids[ka].strid : continue
            if c not in colorids[kb].strid : continue
            # skip blobs if there is another blob with same color in one barcode
            if blob.color in cia and blob.color in cib and \
                    a.blobindices[cia.index(blob.color)] != \
                    b.blobindices[cib.index(blob.color)]:
                continue
            # skip blobs if not under both barcodes
            if not is_point_inside_ellipse(blob, rat_blob_t(a.centerx,
                    a.centery, MAX_INRAT_DIST * MCHIPS / 2, MAX_INRAT_DIST / 2,
                    a.orientation)):
                continue
            if not is_point_inside_ellipse(blob, rat_blob_t(b.centerx,
                    b.centery, MAX_INRAT_DIST * MCHIPS / 2, MAX_INRAT_DIST / 2,
                    b.orientation)):
                continue
            # no more check, sharesblob applies
            sharedblobs.append(blobi)
    return sharedblobs


def set_shared_mfix_flags(barcodes, blobs, colorids):
    """Set mfix SHARESBLOB and SHARESID flags based on barcode/blob states.

    Do not change deleted.

    Keyword arguments:
    blobs    -- list of all color blobs (color_blob_t) from the current frame
    barcodes -- list of all barcodes (barcode_t) from the current frame,
                structured like this: [coloridindex][index]
    colorids -- global colorid database created by parse_colorid_file()

    Function does not return a value but modifies mfix properties in
    list-type keyword parameter 'barcodes'.

    """
    # set SHARESID property
    for k in range(len(barcodes)):
        #check 'deleted' flags
        num = 0
        for barcode in barcodes[k]:
            barcode.mfix &= ~MFIX_SHARESBLOB
            if not barcode.mfix or (barcode.mfix & MFIX_DELETED): continue
            num += 1
            # and remove sharesblob property now (add later again)
        # skip ones with no sharesid (some deleted, only one left)
        if num < 2:
            for barcode in barcodes[k]:
                barcode.mfix &= ~MFIX_SHARESID
        else:
            # set sharesid flag
            for barcode in barcodes[k]:
                barcode.mfix |= MFIX_SHARESID

    # set SHARESBLOB property (on non deleted ones)
    for blob in blobs:
        notdeleted = barcodeindices_not_deleted(blob.barcodeindices, barcodes)
        if len(notdeleted) > 1:
            for x in notdeleted:
                barcodes[x.k][x.i].mfix |= MFIX_SHARESBLOB

    # set SHARESBLOB property also on overlapping barcodes
    # get all barcode indices
    allindices = []
    for k in range(len(barcodes)):
        for i in range(len(barcodes[k])):
            allindices += barcodeindices_not_deleted(
                    [barcode_index_t(k, i)], barcodes)
    # iterate over all pairs
    for i in range(1, len(allindices)):
        for j in range(i):
            a = barcodes[allindices[i].k][allindices[i].i]
            b = barcodes[allindices[j].k][allindices[j].i]
            if could_be_sharesblob(a, b, allindices[i].k, allindices[j].k,
                    blobs, colorids):
                a.mfix |= MFIX_SHARESBLOB
                b.mfix |= MFIX_SHARESBLOB


def remove_close_sharesid(barcodes, blobs, colorids, mfix = None):
    """Find barcodes that share the same colorid and are very close
    and delete/concat superfluous ones depending on their mfix value.

    Algo: if both are PARTLYFOUND, first we make an attempt to join them
    into one barcode. This is needed after forward/backward partlyfound
    detection when the 1st and 3rd blobs are far away and create two sharesid barcodes
    After that all sharesid that are close fight and bigger one wins, other gets deleted.

    TODO: find a better algo to concat barcodes instead of deleting them,
    but I did not implement anything yet because blob indices need to be
    treated correspondingly, and it is not straightforward.

    Keyword arguments:
    barcodes -- list of all barcodes (barcode_t) from the current frame,
                structured like this: [coloridindex][index]
    blobs    -- list of all blobs (color_blob_t) from the current frame
    mfix     -- special part of algo is executed if MFIX_PARTLYFOUND_FROM_TDIST

    Returns number of barcodes removed and also changes barcode properties

    """
    count = 0
    for k in range(len(barcodes)):
        # skip ones with no sharesid
        if len(barcodes[k]) < 2: continue
        strid = colorids[k].strid
        # iterate barcodes
        for i in range(len(barcodes[k])):
            barcode = barcodes[k][i]
            # skip ones that has been deleted already
            if not barcode.mfix or (barcode.mfix & MFIX_DELETED): continue
            for j in range(i):
                candidate = barcodes[k][j]
                # skip ones that has been deleted already
                if not candidate.mfix or (candidate.mfix & MFIX_DELETED): continue

                # this part is only executed on partlyfounds to concat them if they match
                if (mfix == MFIX_PARTLYFOUND_FROM_TDIST) and (barcode.mfix & mfix) and (candidate.mfix & mfix):
                    # skip ones that are far away
                    if get_distance(barcode, candidate) > 2 * MAX_INRAT_DIST: continue
                    # keep pairs only with appropriate blobs together
                    color = [0 for x in range(MCHIPS)]
                    commonindices = set(barcode.blobindices + candidate.blobindices)
                    for blobi in commonindices:
                        color[strid.index(int2color[blobs[blobi].color])] += 1
                    if max(x for x in color) < 2: # TODO: do something if there are multiple colors as well...
                        # delete one (permanently)
                        candidate.mfix = 0 # |= MFIX_DELETED
                        # add all blobs from deleted to other one
                        barcode.blobindices = list(commonindices)
                        # and add barcode index to blobs as well to be consistent
                        x = barcode_index_t(k,i)
                        for blobi in commonindices:
                            blob = blobs[blobi]
                            if x not in blob.barcodeindices:
                                blob.barcodeindices.append(x)
                        # also change mfix if all blobs have been found accidentally
                        if len(commonindices) == MCHIPS:
                            barcode.mfix &= ~MFIX_PARTLYFOUND_FROM_TDIST
                            barcode.mfix |= MFIX_FULLFOUND
                        # recalculate its params with new blob indices
                        order_blobindices(barcode, strid, blobs)
                        calculate_params(barcode, strid, blobs)
                        count += 1
                        continue

                # this part is executed at all times to remove close ones - bigger wins
                # skip ones that are far away
                if get_distance(barcode, candidate) > MAX_INRAT_DIST: continue
                # skip ones that have too different orientation
                if cos(barcode.orientation - candidate.orientation) < 0: continue # max 90 deg difference
                # keep the one containing bigger blobs
                count += 1
                # TODO: better algorithm, average and treat blobs correspondingly
                sumri = sum(blobs[blobi].radius for blobi in barcode.blobindices)
                sumrj = sum(blobs[blobj].radius for blobj in candidate.blobindices)
                # set permanent 'deleted' flag on the not chosen one
                if (sumrj>sumri):
                    barcode.mfix = 0 # |= MFIX_DELETED
                    break
                else:
                    candidate.mfix = 0 #|= MFIX_DELETED

    return count

