"""
All kinds of algorithms used by trajognize.main() that are related to barcodes.
"""

import itertools

from .project import *
from .init import *
from .algo import get_angle_deg, get_distance, get_distance_at_position
from .util import mfix2str

from . import algo_blob


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
        if i is None: continue
        blob = blobs[i]
        if algo_blob.barcodeindices_not_deleted(blob.barcodeindices, barcodes):
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
                ki = barcode_index_t(k, i)
                for j in barcode.blobindices:
                    if j is None: continue
                    if ki not in blobs[frame][j].barcodeindices:
                        raise ValueError("mismatch on frame %d, blob %d does not contain %s barcode #%d %s" % (
                            frame, j, colorids[k].strid, i, mfix2str(barcode.mfix)))
        # check from blobs
        for j in range(len(blobs[frame])):
            blob = blobs[frame][j]
            for ki in blob.barcodeindices:
                if j not in barcodes[frame][ki.k][ki.i].blobindices:
                    raise ValueError("mismatch on frame %d, %s barcode #%d %s does not contain blob %d in %s" % (
                        frame, colorids[ki.k].strid, ki.i, mfix2str(barcode.mfix), j, barcodes[frame][ki.k][ki.i].blobindices))
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


def add_missing_unused_blob(barcode, strid, blobs, sdistlists, currentframe):
    """Try to find missing and unused blobs to include them into
    partly found barcodes.

    Warning: function adds to barcode.blobindices, so call
    update_blob_barcodeindices() afterwards!


    Keyword arguments:
    barcode      -- a barcode of barcode_t type
    strid        -- string ID of the barcode (colorids[coloridindex])
    blobs        -- list of all color blobs (color_blob_t) for current frame
    sdistlists   -- possible chain connections on current frame, created
                    in advance by create_spatial_distlists()
    """
    # do not change anything if all blobs are found
    if None not in barcode.blobindices:
        return 0

    # find candidates for all empty positions
    candidates = [set() for x in range(len(strid))]
    newones = 0
    for i in range(len(strid)):
        color = color2int[strid[i]]
        blobi = barcode.blobindices[i]
        # if barcode contains blob at position, we do not care about this position
        # but keep current blob (for convenience store as candidate)
        if blobi is not None:
            candidates[i].add(blobi)
            continue
        # find all candidates that are close to contained blobs, are not
        # assigned to anything and color matches missing color at given position
        # TODO: how to treat deleted? (they are not ignored since blobindices is not empty)
        for ii, blobii in enumerate(barcode.blobindices):
            if blobii is None: continue
            # check all candidates with smaller distance threshold
            for j in sdistlists[blobii][0]:
                if not blobs[j].barcodeindices and blobs[j].color == color:
                    candidates[i].add(j)
                    newones += 1
            # check second neighbor with greater distance threshold
            if abs(i - ii) == 2:
                for j in sdistlists[blobii][1]:
                    if not blobs[j].barcodeindices and blobs[j].color == color:
                        candidates[i].add(j)
                        newones += 1
    if not newones:
        return 0

    # for fullfounds, create virual blob chains to decide whether
    # they could be barcodes or not
    fullfound = 1
    for candidateset in candidates:
        if not candidateset:
            fullfound = 0
            break
    if fullfound:
        blobchains = list(itertools.product(*candidates))
        candidate_blobchain_indices = []
        for i, blobchain in enumerate(blobchains):
            if algo_blob.is_blob_chain_appropriate_as_barcode([blobs[j] for j in blobchain]):
                candidate_blobchain_indices.append(i)
        # if there are no candidates, we return without changing anything
        if not candidate_blobchain_indices:
            return 0
        # if there are more candidates, we choose one with best positioning
        best = candidate_blobchain_indices[0]
        if len(candidate_blobchain_indices) > 1:
            mindist = 1e6
            for i in candidate_blobchain_indices:
                blobchain = blobchains[i]
                dist = 0
                # Warning: we assume here that barcode is from tempbarcode that is initialized
                # with the same position and orientation as on the last frame, namely,
                # that barcode parameters are well initialized at assumed position on current frame.
                for j, blobi in enumerate(blobchain):
                    dist += get_distance_at_position(barcode, j, blobs[blobi])
                if dist < mindist:
                    best = i
                    mindist = dist
        # check orientation of best candidate
        temp = barcode_t(0, 0, 0, 0, list(blobchains[best]))
        calculate_params(temp, strid, blobs)
        if get_angle_deg(barcode, temp) > MAX_PERFRAME_ANGLE:
            return 0
        # store best candidate as all tests have passed
        barcode.blobindices = list(blobchains[best])
        return 1

    # for partlyfounds we simply get good enough candidate for all missing positions
    temp = barcode_t(0, 0, 0, 0, list(barcode.blobindices))
    for i in range(len(strid)):
        candidatelist = list(candidates[i])
        if not candidatelist or barcode.blobindices[i] is not None:
            continue
        # if there are more candidates, we get one that has better positioning
        # Warning: we assume here that barcode is from tempbarcode that is initialized
        # with the same position and orientation as on the last frame, namely,
        # that barcode parameters are well initialized at assumed position on current frame.
        best = candidatelist[0]
        mindist = 1e6
        for blobi in candidatelist:
            dist = get_distance_at_position(barcode, i, blobs[blobi])
            if dist < mindist:
                best = blobi
                mindist = dist
        temp.blobindices[i] = best
        calculate_params(temp, strid, blobs)
        if get_distance(temp, barcode) > MAX_PERFRAME_DIST_MD or \
                get_angle_deg(temp, barcode) > MAX_PERFRAME_ANGLE:
            temp.blobindices[i] = None
    # everything is still good, we store new blobs
    barcode.blobindices = list(temp.blobindices)
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
    n = len(barcode.blobindices) - barcode.blobindices.count(None)
    if n > MCHIPS:
        raise ValueError("too many %s blob indices (%d>%d), " % (strid, n, MCHIPS), mfix2str(barcode.mfix))
    # do not change params if there are no blobs
    if n == 0:
        return

    # calculate center
    barcode.centerx = 0
    barcode.centery = 0
    for i in barcode.blobindices:
        if i is None: continue
        barcode.centerx += blobs[i].centerx
        barcode.centery += blobs[i].centery
    barcode.centerx /= n
    barcode.centery /= n

    # get first and last valid blob index (there should be at least one as n > 0)
    for first in barcode.blobindices:
        if first is not None:
            break
    for last in barcode.blobindices[::-1]:
        if last is not None:
            break
    # calculate orientation
    if n >= 3:
        # calculate orientation with least squares around center
        # source: http://mathworld.wolfram.com/LeastSquaresFitting.html
        xx=0; xy=0; yy=0
        for i in barcode.blobindices:
            if i is None: continue
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
        if xx > yy: # -45 --> 45
            barcode.orientation = atan2(xy, xx)
            if blobs[last].centerx > blobs[first].centerx: # 135 --> 225
                barcode.orientation += pi
        else: # 45 --> 135
            barcode.orientation = pi / 2 - atan2(xy, yy)
            if blobs[last].centery > blobs[first].centery: # 225 --> 315
                barcode.orientation += pi
        d = barcode.orientation
        barcode.orientation = atan2(sin(d),cos(d)) # [-pi,pi] range
    elif n == 2:
        barcode.orientation = atan2(
                blobs[first].centery - blobs[last].centery,
                blobs[first].centerx - blobs[last].centerx)
    elif n == 1:
        # do not change orientation, it is possibly set from previous barcode orientation
        pass

    # correct center if needed now as we have an estimate for the orientation
    if n < len(strid):
        j = 0
        jsum = 0
        for i in range(len(strid)):
            if barcode.blobindices[i] is not None:
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
        for j in algo_blob.barcodeindices_not_deleted(
                blobs[i].barcodeindices, barcodes, MFIX_FULLFOUND):
            barcodecluster.add(j)
    # iterate all barcodes and find ones that are fully overlapping others,
    # (all blobs have more than one barcode index)
    overlappedbarcodes = set()
    for ki in barcodecluster:
        overlapped = True
        for i in barcodes[ki.k][ki.i].blobindices:
            if i is None: continue
            if len(algo_blob.barcodeindices_not_deleted(blobs[i].barcodeindices, barcodes)) < 2:
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
        barcodeindices = algo_blob.barcodeindices_not_deleted(
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
       choose the one at best position based on last frame.
    4. Store new barcodes with mfix value of MFIX_PARTLYFOUND_FROM_TDIST
    5. Check all remaining not used blobs, cluster them and try to assign
       a barcode to them which is not present on the current frame yet
       but was present closeby sometimes in the last/next few seconds.

    Function returns number of barcodes (found, adjusted, new) and
    and modifies list-type keyword parameters 'tdistlists' and 'barcodes'.

    """
    if direction == 'forward':
        inc = 1
    elif direction == 'backward':
        inc = -1
    else:
        raise ValueError("unknown direction: {}".format(direction))
    tempbarcodes = [[] for x in range(len(colorids))] # temporarily found new barcodes
    # calculate temporal distances between blobs
    tdistlists[currentframe] = algo_blob.create_temporal_distlists(
            color_blobs[currentframe-inc], color_blobs[currentframe],
            md_blobs[currentframe-inc], md_blobs[currentframe],
            mdindices[currentframe-inc], mdindices[currentframe])
    # temporary storage of notusedblobs
    notusedblobs = set()
    # temporarily store all barcodes that could be found based on tdist from previous barcodes (full or partial)
    # iterate for all blobs on current frame
    for blobi in range(len(color_blobs[currentframe])):
        # skip blobs that ARE already assigned to something not deleted:
        if algo_blob.barcodeindices_not_deleted(
                color_blobs[currentframe][blobi].barcodeindices, barcodes[currentframe]):
            continue
        # skip blobs not close to anything on the previous frame
        if not tdistlists[currentframe][blobi]:
            # store as not yet used one
            notusedblobs.add(blobi)
            continue
        # iterate all close previous
        for prevblobi in tdistlists[currentframe][blobi]:
            # if prev is NOT assigned to a non-deleted barcode, skip
            goodprevbarcodes = algo_blob.barcodeindices_not_deleted(
                    color_blobs[currentframe-inc][prevblobi].barcodeindices,
                    barcodes[currentframe-inc])
            if not goodprevbarcodes:
                # store as not yet used one
                notusedblobs.add(blobi)
                continue
            # iterate all assigned barcodes from prev frame
            for prevbarcodei in goodprevbarcodes:
                # color index is k as always, index is ii now
                k = prevbarcodei.k
                ii = prevbarcodei.i
                oldbarcode = barcodes[currentframe-inc][k][ii]
                # copy prev barcode parameters and store in temporary list
                barcode = barcode_t(
                        oldbarcode.centerx, oldbarcode.centery, oldbarcode.orientation,
                        MFIX_PARTLYFOUND_FROM_TDIST)
                jj = oldbarcode.blobindices.index(prevblobi)
                barcode.blobindices[jj] = blobi
                # store barcode temporarily if it is the first with given colorid
                if not tempbarcodes[k]:
                    tempbarcodes[k].append(barcode)
                # group temporary barcodes if they come from the same previous barcode
                # or one very close
                else:
                    for i in range(len(tempbarcodes[k])):
                        # new barcode comes from the same as one in already tempbarcodes
                        if get_distance(barcode, tempbarcodes[k][i]) == 0:
                            # if this is a not yet used color index, we simply merge
                            if tempbarcodes[k][i].blobindices[jj] is None:
                                tempbarcodes[k][i].blobindices[jj] = blobi
                            # if this color index is already used, we choose better one
                            else:
                                blobj = tempbarcodes[k][i].blobindices[jj]
                                if (get_distance_at_position(oldbarcode, jj, color_blobs[currentframe][blobi]) <
                                        get_distance_at_position(oldbarcode, jj, color_blobs[currentframe][blobj])):
                                    tempbarcodes[k][i].blobindices[jj] = blobi
                            # end iteration
                            break
                    # if this barcode comes from an old barcode not close to any
                    # already appended, add new barcode
                    else:
                        tempbarcodes[k].append(barcode)

    # store good temporary barcodes in global barcode database
    count = 0
    count_adjusted = 0
    count_notused = 0
    for k in range(len(colorids)):
        for barcode in tempbarcodes[k]:
            # so far tempbarcodes contains old barcode position and orientation,
            # we calculate new one now based on actual blob data
            temp = barcode_t(0, 0, 0, 0, list(barcode.blobindices))
            calculate_params(temp, colorids[k].strid, color_blobs[currentframe])
            # check if barcode position orientation is consistent, skip if not
            if get_distance(temp, barcode) > MAX_PERFRAME_DIST_MD or \
                    get_angle_deg(temp, barcode) > MAX_PERFRAME_ANGLE:
                continue
            # skip ones that are already present in barcodes and undelete them
            # instead of this one to avoid increasing barcode list size
            for i, oldbarcode in enumerate(barcodes[currentframe][k]):
                if get_distance(oldbarcode, barcode) < 10:
                    oldbarcode.mfix &= ~MFIX_DELETED
                    # remove old blob correspondences
                    for blobj in oldbarcode.blobindices:
                        if blobj is None: continue
                        algo_blob.remove_blob_barcodeindex(color_blobs[currentframe][blobj], k, i)
                    # add new blobindices
                    oldbarcode.blobindices = list(barcode.blobindices)
                    algo_blob.update_blob_barcodeindices(oldbarcode, k, i, color_blobs[currentframe])
                    # we store oldbarcode (and i as well as it stays what it is currently)
                    barcode = oldbarcode
                    break
            # find missing unused blobs to supplement current tempbarcode (or oldbarcode)
            count_adjusted += add_missing_unused_blob(barcode, colorids[k].strid, color_blobs[currentframe], sdistlists, currentframe)
            calculate_params(barcode, colorids[k].strid, color_blobs[currentframe])
            if barcode != oldbarcode:
                barcodes[currentframe][k].append(barcode)
                i = len(barcodes[currentframe][k]) - 1
            algo_blob.update_blob_barcodeindices(barcode, k, i, color_blobs[currentframe])
            count += 1

# TODO: code below here is not functional yet, it does not change anything as
# it is not yet harmonized with new ordered blobindices structure (2020.04.03.)

#     # try to assign new barcodes to still not used and not-close-to-anything blobs
#     # remove not used blobs that were added to barcodes lately
#     maxskip = 50 # max number of frames around not used blob pairs
#     for blobi in list(notusedblobs):
#         if color_blobs[currentframe][blobi].barcodeindices:
#             notusedblobs.remove(blobi)
#     # convert to list
#     notusedblobs = list(notusedblobs)
#     # create cluster list of not used blobs with temporarily defined blob and sdist lists
#     notusedblobsx = [color_blobs[currentframe][blobi] for blobi in notusedblobs]
#     sdistlistsx = algo_blob.create_spatial_distlists(notusedblobsx)
#     clusterlists, _ = algo_blob.find_clusters_in_sdistlists(notusedblobsx, sdistlistsx, 1)
#     # check all clusters
#     for cluster in clusterlists:
#         # skip large clusters
#         if len(cluster) > MCHIPS: continue
#         # create new barcode from cluster
#         # Warning: blobindices are not in proper order yet...
#         newbarcode = barcode_t(0, 0, 0, MFIX_PARTLYFOUND_FROM_TDIST, [notusedblobs[i] for i in cluster])
#         colorsincluster = []
#         for i in cluster:
#             blob = color_blobs[currentframe][notusedblobs[i]]
#             colorsincluster.append(blob.color)
#             newbarcode.centerx += blob.centerx
#             newbarcode.centery += blob.centery
#         newbarcode.centerx /= len(cluster)
#         newbarcode.centery /= len(cluster)
#         # get colorid candidates
#         goodcolors = []
#         for k in range(len(colorids)):
#             strid = colorids[k].strid
#             # skip colorids that cannot contain colors in cluster
#             skip = False
#             for ci in colorsincluster:
#                 c = int2color[ci]
#                 if strid.count(c) < colorsincluster.count(ci):
#                     skip = True
#                     break
#             if skip: continue
#             # skip clusters that already have a barcode close on current frame
#             skip = False
#             for barcode in barcodes[currentframe][k]:
#                 if get_distance(barcode, newbarcode) < AVG_INRAT_DIST * (MCHIPS - 1) * 2:
#                     skip = True
#                     break
#             if skip: continue
#             # store good color
#             goodcolors.append(k)
#         # add barcode that was close enough to this cluster in the past 2 seconds (maxskip)
#         mindist = MAX_PERFRAME_DIST_MD
#         bestk = None
#         if inc == 1:
#             lastframe = max(0, currentframe - maxskip)
#         else:
#             lastframe = min(len(barcodes)-1, currentframe + maxskip)
#         for frame in range(currentframe, lastframe, -inc):
#             for k in goodcolors:
#                 # find candidates
#                 for barcode in barcodes[frame][k]:
#                     # skip ones missing too many blobs
#                     if len(barcode.blobindices) - barcode.blobindices.count(None) < 2:
#                         # ok, changed my mind, keep it if all blobs are under md (good for sure)
#                         skip = False
#                         for i in barcode.blobindices:
#                             if i is None: continue
#                             if mdindices[frame][i] == -1:
#                                 skip = True
#                                 break
#                         if skip: continue
#                     dist = get_distance(barcode, newbarcode)
#                     if dist < mindist:
#                         mindist = dist
#                         bestk = k
#             # store first occurrence
#             if mindist < MAX_PERFRAME_DIST_MD:
# # TODO: order_blobindices not transformed yet to new blobindices structure,
# #       how to assign random order blobs to barcode??? Would be easier if
# #       orientation would be known already...
# #                order_blobindices(newbarcode, colorids[bestk].strid, color_blobs[currentframe])
# #                calculate_params(newbarcode, colorids[bestk].strid, color_blobs[currentframe])
# #                barcodes[currentframe][bestk].append(newbarcode)
# #                algo_blob.update_blob_barcodeindices(newbarcode, bestk, len(barcodes[currentframe][bestk]) - 1, color_blobs[currentframe])
# #                count += 1
# #                count_notused += 1
#                 break

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

    Return:
        - list of blobs that could be shared (or empty list if none found)
        - (potential) positions of these blobs in barcode a

    """
    sharedblobs = []
    positions = []
    if get_distance(a, b) < MAX_INRAT_DIST * 2:
        allblobs = set(a.blobindices + b.blobindices)
        allblobs.discard(None)
        for blobi in allblobs:
            # add trivial cases
            if blobi in a.blobindices and blobi in b.blobindices:
                sharedblobs.append(blobi)
                positions.append(a.blobindices.index(blobi))
                continue
            blob = blobs[blobi]
            c = int2color[blob.color]
            # skip blob if its color is not common in a and b
            if c not in colorids[ka].strid : continue
            if c not in colorids[kb].strid : continue
            # skip blob if there is no room left for not used blobs of that color
            # or if their position is far away from their predicted position
            if blobi in a.blobindices:
                loca = a.blobindices.index(blobi)
                keep = False
                mindist = MAX_INRAT_DIST
                for i, bi in enumerate(b.blobindices):
                    if colorids[kb].strid[i] != c: continue
                    if bi is None:
                        d = get_distance_at_position(b, i, blob)
                        if d < mindist:
                            d = mindist
                            keep = True
                if not keep: continue
            elif blobi in b.blobindices:
                loca = None
                keep = False
                mindist = MAX_INRAT_DIST
                for i, ai in enumerate(a.blobindices):
                    if colorids[kb].strid[i] != c: continue
                    if ai is None:
                        d = get_distance_at_position(a, i, blob)
                        if d < mindist:
                            d = mindist
                            loca = i
                            keep = True
                if not keep: continue
            # no more check, potential sharesblob applies
            sharedblobs.append(blobi)
            positions.append(loca)

    return sharedblobs, positions


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
        notdeleted = algo_blob.barcodeindices_not_deleted(blob.barcodeindices, barcodes)
        if len(notdeleted) > 1:
            for x in notdeleted:
                barcodes[x.k][x.i].mfix |= MFIX_SHARESBLOB

    # set SHARESBLOB property also on overlapping barcodes
    # get all barcode indices
    allindices = []
    for k in range(len(barcodes)):
        for i in range(len(barcodes[k])):
            allindices += algo_blob.barcodeindices_not_deleted(
                    [barcode_index_t(k, i)], barcodes)
    # iterate over all pairs
    for i in range(1, len(allindices)):
        for j in range(i):
            a = barcodes[allindices[i].k][allindices[i].i]
            b = barcodes[allindices[j].k][allindices[j].i]
            if could_be_sharesblob(a, b, allindices[i].k, allindices[j].k,
                    blobs, colorids)[0]:
                a.mfix |= MFIX_SHARESBLOB
                b.mfix |= MFIX_SHARESBLOB


def remove_close_sharesid(barcodes, blobs, colorids, mfix=None):
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
        for i in range(len(barcodes[k]) - 1):
            barcode = barcodes[k][i]
            # skip ones that has been deleted already
            if not barcode.mfix or (barcode.mfix & MFIX_DELETED): continue
            for j in range(i + 1, len(barcodes[k])):
                candidate = barcodes[k][j]
                # skip ones that has been deleted already
                if not candidate.mfix or (candidate.mfix & MFIX_DELETED): continue

                # this part is only executed on partlyfounds to concat them if they match
                if mfix == MFIX_PARTLYFOUND_FROM_TDIST and (barcode.mfix & mfix) and (candidate.mfix & mfix):
                    # skip ones that are far away
                    if get_distance(barcode, candidate) > 2 * MAX_INRAT_DIST: continue
                    # keep pairs only where we can merge and there are no double blob candidates
                    skip = False
                    for ii in range(MCHIPS):
                        if barcode.blobindices[ii] is not None and candidate.blobindices[ii] is not None:
                            skip = True
                            break
                    if skip: continue
                    # delete one (permanently)
                    candidate.mfix = 0 # |= MFIX_DELETED
                    # add all blobs from deleted to other one
                    barcode.blobindices = [a if a is not None else b for a, b in zip(barcode.blobindices, candidate.blobindices)]
                    # and add barcode index to blobs as well to be consistent
                    update_blob_barcodeindices(barcode, k, i, blobs)
                    # also change mfix if all blobs have been found accidentally
                    if None not in barcode.blobindices:
                        barcode.mfix &= ~MFIX_PARTLYFOUND_FROM_TDIST
                        barcode.mfix |= MFIX_FULLFOUND
                    # recalculate its params with new blob indices
                    calculate_params(barcode, strid, blobs)
                    count += 1
                    continue

                # this part is executed at all times to remove close ones - bigger wins
                # skip ones that are far away
                if get_distance(barcode, candidate) > MAX_INRAT_DIST: continue
                # skip ones that have too different orientation
                if get_angle_deg(barcode, candidate) > 90: continue
                # keep the one containing bigger blobs
                count += 1
                # TODO: better algorithm, average and treat blobs correspondingly
                sumri = sum(0 if blobi is None else blobs[blobi].radius for blobi in barcode.blobindices)
                sumrj = sum(0 if blobj is None else blobs[blobj].radius for blobj in candidate.blobindices)
                # set permanent 'deleted' flag on the not chosen one
                if (sumrj > sumri):
                    barcode.mfix = 0 # |= MFIX_DELETED
                    break
                else:
                    candidate.mfix = 0 #|= MFIX_DELETED

    return count

