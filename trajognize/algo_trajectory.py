"""
All kinds of algorithms used by trajognize.main() that are related to creating trajectories.

TODOs:

 - nem hasznalt blobok motion blob folott --> define barcodes (motion blob type connections) <-- maybe it is solved in partlyfound_tdist
 - offset change is not the best in choose_and_connect_trajs()...
 - get_distance() check not from center but from center + blob index +-
 - recalculate added empty virtuals position between partlyfounds
 - better smoothing differentiated for partlyfound 1, 2, fullfound, etc., from previous blob centers and avg dx, dy...
 - ovatosabban vegyuk be a nem hasznaltakat, mondjuk sebesseg alapon, zajszurve, hogy ne ugraljon G-k kozott... (restrict acc to 50 in virtual addition)
 - dinamikus torles-nem torles coloridindex szerint, ha megis kell, reanimate...
 - connectnel frame limit feleig tartsa csak meg a legjobbat, inkabb tobb iteracioban, de az elagazas vege maradjon nyitott, nem egy adott x
 - find_best utan enhance virtual-ban virtualok poziciojat upgradelni non virtual chosen-ek kozott
 - recalculate position of MFIX_VIRTUALs between better ones once a virtual is turned into a better one (possibly in enhance_virtuals)

The three main algos that should be called from outside are the following:

initialize_trajectories()

find_best_trajectories()
    ...global sort and choose very best, iterate...
    connect_chosen_trajs
        fill_connection_with_nub
        mark_traj_chosen
    change_colorid
    mark_barcodes_from_trajs
    ...sort colors and choose remaining good, iterate...
        ...sort trajs...
        connect_chosen_trajs
            fill_connection_with_nub
            mark_traj_chosen
        change_colorid
        mark_barcodes_from_trajs
        extend_chosen_trajs
            connect_chosen_trajs
                fill_connection_with_nub
                mark_traj_chosen
    list_meta_trajs
    enhance_virtual_barcodes

finalize_trajectories()
    extend_chosen_trajs
        connect_chosen_trajs
            fill_connection_with_nub
            mark_traj_chosen
    list_meta_trajs
    add_virtual_barcodes_to_gaps
    list_meta_trajs
    enhance_virtual_barcodes
    (smooth_final_trajectories)
"""

import sys
from operator import attrgetter
from trajognize.project import *
from trajognize.init import *
from trajognize.algo import *
from trajognize.util import *
import trajognize.algo_barcode as algo_barcode
import trajognize.algo_blob as algo_blob


def trajlastframe(traj):
    """Return the last frame number of a trajectory.

    Keyword arguments:
    traj -- a trajectory

    """
    return traj.firstframe + len(traj.barcodeindices) - 1


def append_barcode_to_traj(traj, trajsonframe, trajindex, barcode, barcodeindex,
        strid, blobs):
    """Appends a barcode to the end of a trajectory.
    
    Function also modifies all scores of the trajectory.

    Keyword arguments:
    traj         -- a trajectory to append to
    trajsonframe -- list of trajectory indices of current frame and colorid
    trajindex    -- index of the current trajectory
    barcode      -- a barcode to add to the trajectory
    barcodeindex -- the index of the barcode that is added to traj's barcodeindices
    strid        -- string id of the barcode/traj
    blobs        -- list of all color blobs on the current frame

    """
    traj.barcodeindices.append(barcodeindex)
    trajsonframe.add(trajindex)
    # adjust fullfound_count
    if barcode.mfix & MFIX_FULLFOUND:
        traj.fullfound_count += 1
        # adjust fullnocluster_count
        if barcode.mfix & MFIX_FULLNOCLUSTER:
            traj.fullnocluster_count += 1
    # adjust sharesblob count
    if barcode.mfix & MFIX_SHARESBLOB:
        traj.sharesblob_count += 1
    # adjust colorblob_count
    for i in xrange(MCHIPS):
        color = color2int[strid[i]]
        for blobi in barcode.blobindices:
            if blobs[blobi].color == color:
                traj.colorblob_count[i] += 1
                continue
    # TODO: add more parameters that define the score of the trajectory


def start_new_traj(trajectories, trajsonframe, currentframe, k, barcode,
        barcodeindex, strid, blobs):
    """Starts a new trajectory with a given barcode.

    Keyword arguments:
    trajectories -- global list of all trajectories
    trajsonframe -- global list of trajectory indices per frame per coloridindex
    currentframe -- the current frame
    k            -- the current coloridindex
    barcode      -- a barcode to start the trajectory with
    barcodeindex -- the index of the barcode that initializes the traj
    strid        -- string id of the barcode/traj
    blobs        -- list of all color blobs on the current frame

    """
    trajectories[k].append(trajectory_t(currentframe, k))
    ti = len(trajectories[k])-1
    append_barcode_to_traj(
            trajectories[k][ti], trajsonframe[currentframe][k], ti,
            barcode, barcodeindex, strid, blobs)


def number_and_length_of_trajectories(trajectories):
    """Return total number and average length of (not deleted) trajectories.

    Keyword arguments:
    trajectories -- global list of all trajectories

    """
    count = 0
    avg_length = 0
    for trajs in trajectories:
        count += len(trajs)
        for traj in trajs:
            if traj.state == STATE_DELETED or traj.state == STATE_CHANGEDID:
                count -= 1
            else:
                avg_length += len(traj.barcodeindices)
    if count:
        return (count, avg_length/count)
    else:
        return (0, 0)


def barcode_fits_to_trajlast(lastbarcode, barcode, lastmd_blobs, md_blobs,
        lastmdindices, mdindices):
    """Return true if barcode could be the next element of trajectory,
    based on the last barcode element of the trajectory.

    Function is similar to create_temporal_distlists() in algo_blob.py in that
    it also uses two thresholds, one for static cases, one for dynamic ones
    when motion blobs are also present.
    
    Nevertheless, there are still some cases when we are in the range between
    the two thresholds without motion blobs so trajectory sections need to be
    further concatted with looser criteria.

    Keyword arguments:
    lastbarcode -- last barcode of a given trajectory
    barcode         -- new candidate barcode
    lastmd_blobs    -- list of all motion blobs (motion_blob_t) from the last frame
    md_blobs        -- list of all motion blobs (motion_blob_t) from the current frame
    lastmdindices   -- motion blob index for blobs of the last frame
    mdindices       -- motion blob index for blobs of the current frame

    """
    d = get_distance(lastbarcode, barcode)
    # very close, trivial to add
    if d <= MAX_PERFRAME_DIST:
        return True
    # bit farer, check md blobs and correct with their position change
    if d <= MAX_PERFRAME_DIST_MD:
        mdblob = None
        for i in barcode.blobindices:
            if mdindices[i] > -1:
                mdblob = md_blobs[mdindices[i]]
                break
        lastmdblob = None
        for i in lastbarcode.blobindices:
            if lastmdindices[i] > -1:
                lastmdblob = lastmd_blobs[lastmdindices[i]]
                break
        # both frames contain motion blob, higher threshold is satisfactory,
        # there are rarely any motion blobs closer than MAX_PERFRAME_DIST_MD
        if mdblob and lastmdblob:
            return True
#            dx = mdblob.centerx - lastmdblob.centerx
#            dy = mdblob.centery - lastmdblob.centery
#            corrected_lastbarcode = barcode_t(lastbarcode.centerx+dx, lastbarcode.centery+dy, 0, 0, [])
#            if get_distance(corrected_lastbarcode, barcode) <= MAX_PERFRAME_DIST:
#                return True
        # only last frame contains motion blob, check if current is inside it
        if lastmdblob and is_point_inside_ellipse(barcode, lastmdblob):
            return True
        # only current frame contains motion blob, check if last is inside it
        if mdblob and is_point_inside_ellipse(lastbarcode, mdblob):
            return True

    return False


def initialize_trajectories(trajectories, trajsonframe, barcodes, blobs,
        currentframe, colorids, md_blobs, mdindices):
    """Initialize trajectories by adding barcodes of current frame
    to existing trajectories ending on last frame.
    
    Function should be called for each frame one by one to work properly.
    If there are multiple ongoing paths for a trajectory, it is stopped
    and new ones are created to avoid combinatorical explosion.
    in other words, one barcode will be the member of only one trajectory. If
    it is a branch, its trajectory will be 1 frame long and the two branches
    will start on the next frame. Also, if two braches merge, they stop their
    trajectories one frame before merging and the common path is a new traj.
    
    Keyword arguments:
    trajectories -- global list of all trajectories
    trajsonframe -- global list of trajectory indices per frame per coloridindex
    barcodes     -- global list of all barcodes
    blobs        -- global list of all color blobs
    currentframe -- current frame
    colorids     -- global colorid database created by parse_colorid_file()
    md_blobs    -- global list of all motion blobs
    mdindices   -- global list of motion blob index for all blobs

    Function does not return a value but writes to keyword parameters
    trajectories and trajsonframe (and does not write barcodes yet).

    """
    # if this is the first frame, initialize one trajectory with each barcode
    if currentframe == 0:
        for k in xrange(len(colorids)):
            strid = colorids[k].strid
            for i in xrange(len(barcodes[currentframe][k])):
                barcode = barcodes[currentframe][k][i]
                if not barcode.mfix or (barcode.mfix & MFIX_DELETED):
                    continue
                start_new_traj(
                        trajectories, trajsonframe, currentframe, k, barcode, i,
                        strid, blobs[currentframe])
        return

    # if not first frame, try to append barcodes to existing trajectories
    for k in xrange(len(colorids)):
        strid = colorids[k].strid
        #if strid == 'ORB' and currentframe > 820:
        #    print currentframe, strid, 'trajsonlastframe', trajsonframe[currentframe-1][k]
        for i in xrange(len(barcodes[currentframe][k])):
            #if strid == 'ORB' and currentframe > 820:
            #    print('  barcode', i)
            barcode = barcodes[currentframe][k][i]
            if not barcode.mfix or (barcode.mfix & MFIX_DELETED):
                continue
            found = 0
            # irerate trajectories of the last frame
            for trajindex in trajsonframe[currentframe-1][k]:
                # if found a good one, add to existing trajectory
                traj = trajectories[k][trajindex]
                #if strid == 'ORB' and currentframe > 820:
                #    print('    try trajindex', trajindex, 'with last b.ind.', traj.barcodeindices[-1], 'No. of last barc.', len(barcodes[currentframe-1][k]))
                if trajindex in trajsonframe[currentframe][k]:
                    lastbarcode = barcodes[currentframe-1][k][traj.barcodeindices[-2]]
                else:
                    lastbarcode = barcodes[currentframe-1][k][traj.barcodeindices[-1]]
                if traj.state == STATE_INITIALIZED and barcode_fits_to_trajlast(
                        lastbarcode, barcode,
                        md_blobs[currentframe-1], md_blobs[currentframe],
                        mdindices[currentframe-1], mdindices[currentframe]):
                    found += 1
                    #if strid == 'ORB' and currentframe > 820:
                    #    print('    found', found, 'trajindex', trajindex)
                    if trajindex not in trajsonframe[currentframe][k]:
                    # if not added yet (no split), add barcode to existing trajectory
                        # if this barcode has already caused trouble, stop all trajs that could end with this
                        if found > 1:
                            #if strid == 'ORB' and currentframe > 820:
                            #    print('    stopped trajindex', trajindex)
                            traj.state = STATE_FORCED_END
                        else:
                            #if strid == 'ORB' and currentframe > 820:
                            #    print('    append to trajindex', trajindex)
                            append_barcode_to_traj(
                                    traj, trajsonframe[currentframe][k], trajindex,
                                    barcode, i, strid, blobs[currentframe])
                    # if traj is already being appended by a barcode,
                    # we treat it as a split in the trajectory, end it and start two new ones
                    else:
                        # force to stop old trajectory
                        trajsonframe[currentframe][k].remove(trajindex)
                        old = traj.barcodeindices.pop()
                        traj.state = STATE_FORCED_END
                        # start new trajectory from old index
                        start_new_traj(
                                trajectories, trajsonframe, currentframe, k,
                                barcodes[currentframe][k][old], old,
                                strid, blobs[currentframe])
                        # if this barcode has already caused trouble, stop all trajs that could end with this
                        if found == 1:
                            # start new trajectory from new index
                            start_new_traj(
                                    trajectories, trajsonframe, currentframe, k,
                                    barcode, i, strid, blobs[currentframe])
                            #if strid == 'ORB' and currentframe > 820:
                            #    print('    delete trajindex', trajindex, 'and start two new trajindex', len(trajectories[k])-2, len(trajectories[k])-1)

            # if no trajectories found where this barcode can fit, start a new one
            if not found:
                start_new_traj(trajectories, trajsonframe, currentframe, k,
                        barcode, i, strid, blobs[currentframe])
                #if strid == 'ORB' and currentframe > 820:
                #    print('    not found, starting new one trajindex', len(trajectories[k])-1)


def traj_score(traj, k=None, kk=None, calculate_deleted=True):
    """Return final score of a trajectory.

    fullfound_count is the first approximation to a good score, taking into
    account how many barcodes were found fully in the trajectory.
    fullnocluster takes into account only those fullfound which are not
    part of a larger cluster, therefore it is a stronger metric.
    We choose a score that is the average of these two.
    sharesblob shows the number of barcodes that share blob with other
    not deleted barcodes, it is subtracted from the above score

    Also, when connecting trajs, we might choose candidates from another
    colorid, so a score for these cases must be calculated as well.

    Keyword arguments:
    traj -- a trajectory
    k    -- dst coloridindex of scoring (same as kk in default)
    kk   -- src coloridindex of the traj

    """
    if not calculate_deleted and traj.state == STATE_DELETED:
        return 0

    # if the score is calculated for the trajs color (default case):
    if k == kk:
        if PROJECT in [PROJECT_MAZE, PROJECT_ANTS, PROJECT_ANTS_2019]:
            return len(traj.barcodeindices) + sum(traj.colorblob_count[i] for i in xrange(MCHIPS)) + \
                    (traj.fullfound_count - traj.sharesblob_count + 2*traj.fullnocluster_count)/3 + traj.offset_count
        else:
            return max(0,(traj.fullfound_count - traj.sharesblob_count + traj.fullnocluster_count)/2 + traj.offset_count)
    # if it is calculated for another color:
    else:
        # score is zero if no least color is found
        least = index_of_least_color(traj)
        if least == -1:
            return 0
        # score is proportional to the average diff between least and others,
        # but should not be too high
        others = list(set(range(MCHIPS)).difference(set([least])))
        score = 0
        for i in others:
            score += traj.colorblob_count[i] - traj.colorblob_count[least]
        score /= len(others)
        if PROJECT in [PROJECT_MAZE, PROJECT_ANTS, PROJECT_ANTS_2019]:
            return len(traj.barcodeindices) + (score - traj.sharesblob_count)/3 + traj.offset_count
        else:
            return max(0, (score - traj.sharesblob_count)/3 + traj.offset_count)

def is_traj_good(traj, threshold=50):
    """Return True if trajectory is assumed to be a good one
    and False if it assumed to be a false positive detection.

    Keyword arguments:
    traj      -- a trajectory
    threshold -- above which the trajectory is assumed to be good
    
    Threshold default value of 50 is 2sec recognition, filters out most of the
    false positives. Bads are usually <20,30,40, but sometimes larger than 100,
    goods can be very small but above 100 are generally good 50 looks like a
    good compromise, but be prepared for false positives!

    """

    if traj_score(traj) >= threshold:
        return True
    else:
        return False


def get_chosen_neighbor_traj_perframe(traj, trajectories, trajsonframe, k,
        forward=True, framelimit=1500):
    """Get next chosen trajectory index, -1 if not found.

    TODO: could be optimized more with trajsonframe indexing...

    TODO: it might happen that first neighbor is from another colorid marked
          to switch color. Check for that as well!!!

    Keyword arguments:
    traj         -- a trajectory from which the search starts
    trajectories -- global list of all trajectories
    trajsonframe -- global list of trajectory indices per frame per coloridindex
    k            -- coloridindex of current traj
    forward      -- forward or backward search
    framelimit   -- max number of frames to search (default=1min)

    If framelimit is None, there is no frame limit between neighbors.
    If traj is None, we search for the first/last chosen traj.

    """
    # forward in time
    if forward:
        if traj is None:
            firstframe = 0
        else:
            firstframe = trajlastframe(traj)+1
        if framelimit is None:
            lastframe = len(trajsonframe)-1
        else:
            lastframe = min(firstframe + framelimit - 1, len(trajsonframe)-1)
        for frame in xrange(firstframe, lastframe+1):
            for i in trajsonframe[frame][k]:
                trajx = trajectories[k][i]
                if trajx.state == STATE_CHOSEN and trajx.firstframe == frame:
                    return i
        return -1

    # backward in time
    else:
        if traj is None:
            lastframe = len(trajsonframe) - 1
        else:
            lastframe = traj.firstframe -1
        if framelimit is None:
            firstframe = 0
        else:
            firstframe = max(lastframe - framelimit + 1, 0)
        for frame in xrange(lastframe, firstframe-1, -1):
            for i in trajsonframe[frame][k]:
                trajx = trajectories[k][i]
                if trajx.state == STATE_CHOSEN and trajlastframe(trajx) == frame:
                    return i
        return -1


def get_chosen_neighbor_traj(traj, trajs, forward=True, framelimit=1500):
    """Get next chosen trajectory index, -1 if not found.

    TODO: could be optimized more with trajsonframe indexing...

    TODO: it might happen that first neighbor is from another colorid marked
          to switch color. Check for that as well!!!

    Keyword arguments:
    traj       -- a trajectory from which the search starts
    trajs      -- list of all trajectories with same coloridindex
    forward    -- forward or backward search
    framelimit -- max number of frames to search (default=1min)

    If framelimit is None, there is no frame limit between neighbors.
    If traj is None, we search for the first chosen traj.

    """
    # forward in time
    if forward:
        if traj is None:
            lastframe = 0
        else:
            lastframe = trajlastframe(traj)
        bestindex = -1
        if framelimit is None:
            beststart = 1e10
        else:
            beststart = lastframe + framelimit

        for i in xrange(len(trajs)):
            trajx = trajs[i]
            if trajx.state != STATE_CHOSEN:
                continue
            j = trajx.firstframe
            if  j > lastframe and j < beststart:
                bestindex = i
                beststart = j
        return bestindex

    # backward in time
    else:
        if traj is None:
            raise ValueError("traj=None not compatible with backward mode.""")
        firstframe = traj.firstframe
        bestindex = -1
        if framelimit is None:
            bestend = -1
        else:
            bestend = firstframe - framelimit
        for i in xrange(len(trajs)):
            trajx = trajs[i]
            if trajx.state != STATE_CHOSEN:
                continue
            j = trajlastframe(trajx)
            if j < firstframe and j > bestend:
                bestindex = i
                bestend = j
        return bestindex


def index_of_least_color(traj):
    """Return the index of the color with the least match in the trajectory,
    or -1 if there is no least color.

    Keyword arguments:
    traj -- a trajectory

    """
    si = range(MCHIPS)
    si.sort(lambda x,y: traj.colorblob_count[x] - traj.colorblob_count[y])
    if traj.colorblob_count[si[0]] == traj.colorblob_count[si[1]]:
        return -1
    else:
        return si[0]


def could_be_another_colorid(traj, fromk, tok, colorids):
    """Return true if the given trajectory could be a false positive detection
    and thus would be suitable for another colorid.

    Criteria:
    - traj state is DELETED
    - traj is not marked yet as CHANGEDID (traj.k != k)
    - all but one colors match in the two strids
    - the color not matching has the least occurrence in traj
    
    Keyword arguments:
    traj      -- the trajectory to check
    fromk     -- the original colorid index
    tok       -- the new colorid index
    colorids  -- global colorid database created by parse_colorid_file()

    """
    # check deleted state
    if traj.state != STATE_DELETED:
        return False
    # check whether already marked to switch to a colorid
    if traj.k != fromk:
        return False
    # check at least two colors matching in string ids
    fromstrid = colorids[fromk].strid
    tostrid = colorids[tok].strid
    common = ""
    old = ""
    new = ""
    for c in fromstrid:
        if c in tostrid:
            common += c
        else:
            old += c
    if len(common) != MCHIPS-1:
        return False
    # check number of occurrences in old traj
    if index_of_least_color(traj) != fromstrid.index(old):
        return False
    # no more checks, it could be of the other color
    return True


def max_allowed_dist_between_trajs(framea=0, frameb=0, samecolor=True):
    """Return a threshold distance based on frame difference.

    Keyword arguments:
    framea    -- frame number of first barcode
    frameb    -- frame number of second barcode
    samecolor -- are thw two barcodes from the same coloridindex?

    0:50, 1:55, 2:60, 3:65, 4:70, ... 10:100

    """
    if not samecolor: return 50
    return min(100, 50 + abs(frameb-framea) * 5)


def connect_chosen_trajs(traja, trajb, k, trajectories, trajsonframe, barcodes,
        colorids, framelimit=1500, connections=None, index=-1, level=0):
    """Connect two neighboring chosen trajectories with not yet chosen ones,
    or simply extend a chosen traj with best not chosen chain of trajs
    forward or backward.

    Call with default args for params framelimit, connections, index and level
    since they serve for the recursive inner calls of the same function.

    Keyword arguments:
    traja        -- the first trajectory
    trajb        -- the second trajectory (after the first one), or a string
                    "forward" or "backward" if only extention is needed.
    k            -- coloridindex of the destination chain
                    (which is the same for b, but not necessarily for a)
    trajectories -- global list of all trajectories
    trajsonframe -- global list of trajectory indices per frame per coloridindex
    barcodes     -- global list of all barcodes
    colorids     -- global colorid database created by parse_colorid_file()
    framelimit   -- maximum number of frames to look for (in case of extention mode)
                    this is needed due to the possible high number of recursions
                    and thus slow running time
    connections  -- connections_t() object containing the list of connections
                    used in the recursive calls
    index        -- the index of the last chain to continue
    level        -- level of recursion (inner variable, do not use it)

    Algorithm description:
    1. Recursively create all possible connections between a and b (or simply
       forward or backward unintentionally) using these:
       - not yet chosen same colorid barcodes (trajs)
       - deleted barcodes (trajs) of another color that match certain criteria
    2. Choose best with highest overall score

    Returns list of traj index tuples(coloridindex, index) that create a chain
    to be chosen or None if no such chain was found.

    """
    # initialize
    mode = 'c' # connect
    inc = 1 # increment (1 forward, -1 backward)
    neigh = -1
    if isinstance(trajb, str):
        if trajb == "forward":
            mode = 'f' # forward
        elif trajb == "backward":
            mode = 'b' # backward
            inc = -1
        else:
            raise ValueError("trajb should be of trajectory_t or 'forward' or 'backward' if string")
    # TODO: should be or should not be a switch to connection mode from forward/backward
    # if a chosen neighbor is found in the vicinity? So far there is no switch.
    if mode == 'b':
        fromframe = traja.firstframe - 1
        neigh = get_chosen_neighbor_traj(traja, trajectories[k], False, framelimit)
        if neigh == -1:
            toframe = max(0, fromframe - framelimit + 1)
        else:
            toframe = trajlastframe(trajectories[k][neigh]) + 1
        if fromframe < toframe: return None # add no more to this
    elif mode == 'f':
        fromframe = trajlastframe(traja) + 1
        neigh = get_chosen_neighbor_traj(traja, trajectories[k], True, framelimit)
        if neigh == -1:
            toframe = min(len(barcodes)-1, fromframe + framelimit - 1)
        else:
            toframe = trajectories[k][neigh].firstframe - 1
        if fromframe > toframe: return None # add no more to this
    else: # mode == 'c':
        fromframe = trajlastframe(traja) + 1
        toframe = trajb.firstframe - 1
        if fromframe > toframe: return None # add no more to this
    barcodefrom = barcodes[fromframe-inc][traja.k][traja.barcodeindices[-(inc+1)/2]] # TODO: traja.k is used which should be the k for a (and not yet changed) but might be buggy if a later connection is different from a previous one

    # initialize connections object
    # this is needed because of this: http://effbot.org/zone/default-values.htm
    lastconn = []
    if level == 0:
        connections = connections_t(toframe)
        index = -1

#    print(mode, colorids[k].strid, "level", level, "f%d-%d" % (fromframe, toframe), "flimit", framelimit, "fflimit", connections.fromframelimit, "Nconns", len(connections.data))

    # avoid getting into too deep recursions and also define stricter first frame
    # limit if there are too many recursions. This level should be the last.
    if level > min(200, 2 * sys.getrecursionlimit() / 10):
        connections.recursionlimitreached = True
        if mode == 'b':
            connections.fromframelimit = max(connections.fromframelimit, trajlastframe(traja))
        else:
            connections.fromframelimit = min(connections.fromframelimit, traja.firstframe)
#        print("  recursion limit reached, setting new fflimit", connections.fromframelimit)
        return None


    ############################################################################
    # iterate all frames between traja and trajb to find all candidate
    # connections recursively
    for frame in xrange(fromframe, toframe + inc, inc):
        # iterate all colorids
        for kk in xrange(len(colorids)):
#            # skip other colorids when only elongating
#            if mode != 'c' and k != kk: continue
            # iterate trajectories on current frame
            for i in trajsonframe[frame][kk]:
                # simplify notation
                trajx = trajectories[kk][i]
                # skip ones not starting/ending here and starting/ending after
                if mode == 'b':
                    fromxframe = trajlastframe(trajx)
                    toxframe = trajx.firstframe
                    if fromxframe < connections.fromframelimit: continue
                    if fromxframe != frame: continue
                    if toxframe < toframe: continue
                else:
                    fromxframe = trajx.firstframe
                    toxframe = trajlastframe(trajx)
                    if fromxframe > connections.fromframelimit: continue
                    if fromxframe != frame: continue
                    if toxframe > toframe: continue
                # if different color, check suitability
                if k != kk:
                    if not could_be_another_colorid(trajx, kk, k, colorids): continue
                # if same color, check state. Connection is allowed between non-deleted,
                # extention can be with deleted as well. TODO: is that the best way?
                else:
                    if mode == 'c':
                        if trajx.state == STATE_DELETED: continue
                    if trajx.state == STATE_CHANGEDID or trajx.k != kk: continue
                    if trajx.state == STATE_CHOSEN:
                        print("Warning, something is buggy. state is already CHOSEN")
                # skip ones far away
                if get_distance(
                        barcodefrom, barcodes[frame][kk][trajx.barcodeindices[(inc-1)/2]]) > \
                        max_allowed_dist_between_trajs(fromframe-inc, frame, k==kk):
                    continue

                # create temporary connection
                if index == -1:
                    tempconn = lastconn
                else:
                    tempconn = connections.data[index]
                # if we start a new branch, do not start it with something
                # already used in other better connections
                # TODO: this part should be optimized since it gets really slow
                # when number of possible connections is getting large (>100)
                cont = False
                for ii in xrange(len(connections.data)):
                    conn = connections.data[ii]
                    # if new ending was already used
                    if (kk,i) in conn:
                        m = conn.index((kk,i))
                        # calculate old score
                        scoreold = 0
                        for (kkk,jj) in conn[0:m]:
                            scoreold += traj_score(trajectories[kkk][jj], k, kkk)
                        # calculate new score
                        scorenew = 0
                        for (kkk,jj) in tempconn:
                            scorenew += traj_score(trajectories[kkk][jj], k, kkk)
                        # skip new
                        if scoreold >= scorenew: # TODO more checking on egalitarian state
                            cont = True
                            break
                        # delete old
                        else:
                            del connections.data[ii]
                            if index > ii:
                                index -= 1
                            break
                if cont: continue

                ########## no more checking, candidate is OK ###########
                # initialize chain if it has not been done before
                if index == -1:
                    connections.data.append(lastconn)
                    index = len(connections.data)-1
                # store last connection for next possible chain
                lastconn = list(connections.data[index])
                # store good one as candidate for connection (check close end later)
                connections.data[index].append((kk,i))

                # find connection between new one and last
#                print("  found", colorids[k].strid, "level", level, "f%d-%d" % (trajx.firstframe, trajlastframe(trajx)), "newflimit", framelimit - inc*(toxframe - (fromframe - inc)), "fflimit", connections.fromframelimit, "Nconns", len(connections.data))
                connect_chosen_trajs(trajx, trajb, k, trajectories, trajsonframe,
                        barcodes, colorids, framelimit - inc*(toxframe - (fromframe - inc)),
                        connections, index, level+1)
                # after returning from chain, reset index for next chain
                index = -1

    ############################################################################
    ############################################################################
    # this part executes only after all candidate connections have been found
    if level: return None
    if not connections.data:
#        if neigh != -1: # mode 'f' or 'b'
#            # check if there are any trajs between them at all
#            # this could happen in some not handled cases when both trajs
#            # from both sides are elongated but they are not connected yet
#            # with virtuals
#            for frame in xrange(fromframe, toframe + inc, inc):
#                if len(trajsonframe[frame][kk]): break
#            else:
#                # TODO: no distance is checked here, it could be large...
#                return [(k, neigh)]
        return None

    ############################################################################
    # if max recursion limit has reached, we select best connection so far and
    # continue the search for the rest of the frames
    if connections.recursionlimitreached:
        # calculate total score for all connections until first frame limit
        scores = [0 for i in xrange(len(connections.data))]
        for i in xrange(len(connections.data)):
            conn = connections.data[i]
            if not conn:
                scores[i] = -1
                continue
            for (kk,j) in conn:
                trajx = trajectories[kk][j]
                if mode == 'b':
                    if trajlastframe(trajx) < connections.fromframelimit: break
                else:
                    if trajx.firstframe > connections.fromframelimit: break
                scores[i] += traj_score(trajx, k, kk)
        # choose best (reverse sort according to total score) and continue search
        # using this as beginning
        si = range(len(connections.data))
        si.sort(lambda x,y: scores[y] - scores[x])
        if mode == 'b':
            # reverse list (backward backward == forward)
            tempconn = connections.data[si[0]][::-1]
            trajx = trajectories[tempconn[0][0]][tempconn[0][1]]
            nextfromxframe = trajx.firstframe - 1
        else:
            tempconn = connections.data[si[0]]
            trajx = trajectories[tempconn[-1][0]][tempconn[-1][1]]
            nextfromxframe = trajlastframe(trajx) + 1
        # find connection between new one and last starting new recursion
        # TODO: this is not optimal, but running time gets too long if
        # the whole search is in one recursion...
        # it might happen that many small trajs set fromframelimit too low
        # and therefore win over good long traj, but what can I do...
        print("Warning: recursion limit reached during search, selecting best conn-part so far and starting new part...")
        print(" ", mode, colorids[k].strid, "level", level, "from-to", "%d-%d" % (fromframe, toframe), "flimit", framelimit, "fflimit", connections.fromframelimit, "Nconns", len(connections.data))
        conn = connect_chosen_trajs(trajx, trajb, k, trajectories, trajsonframe,
                barcodes, colorids, framelimit - inc*(nextfromxframe - fromframe))
        if conn:
#           print("conn+", [(colorids[kk].strid, ii, trajectories[kk][ii].firstframe, trajlastframe(trajectories[kk][ii])) for (kk, ii) in tempconn + conn])
           return tempconn + conn

    ############################################################################
    # skip connections that do not end at the right place
    if mode == 'c':
        good = 0
        barcodeto = barcodes[toframe+1][k][trajb.barcodeindices[0]]
        for i in xrange(len(connections.data)):
            conn = connections.data[i]
            (kk, j) = conn[-1]
            trajx = trajectories[kk][j]
            toxframe = trajlastframe(trajx)
            if get_distance(
                    barcodeto, barcodes[toxframe][kk][trajx.barcodeindices[-1]]) > \
                    max_allowed_dist_between_trajs(toxframe, toframe+inc, k==kk):
                connections.data[i] = []
            else:
                good += 1
        if not good: return None

    # calculate total score for all connections
    scores = [0 for i in xrange(len(connections.data))]
    for i in xrange(len(connections.data)):
        conn = connections.data[i]
        if not conn:
            scores[i] = -1
            continue
        for (kk,j) in conn:
            scores[i] += traj_score(trajectories[kk][j], k, kk)

    # choose best (reverse sort according to total score) and return
    si = range(len(connections.data))
    si.sort(lambda x,y: scores[y] - scores[x])

    # In case of pure extention, if there is a chosen neighbor,
    # we check if selected connection ends there. If so, we include neighbor
    # to the connection to be filled with virtuals in between.
    # TODO: it might be better to check for closeness before selecting best
    #       but I am lazy to do it now...
    # TODO: also check for very large temporal distance if needed...
    if neigh != -1:
        trajbb = trajectories[k][neigh] # neighbor
        (kk,j) = connections.data[si[0]][-1] # last element of best conn
        trajx = trajectories[kk][j]
        if mode == 'b':
            fromxframe = trajx.firstframe
            tobframe = trajlastframe(trajbb)
        else: # mode 'f'
            fromxframe = trajlastframe(trajx)
            tobframe = trajbb.firstframe
        if get_distance(
                barcodes[tobframe][k][trajbb.barcodeindices[(inc-1)/2]],
                barcodes[fromxframe][kk][trajx.barcodeindices[-(inc+1)/2]]) <= \
                max_allowed_dist_between_trajs(fromxframe, toframe+inc, k==kk):
            connections.data[si[0]].append((k,neigh))

#    if colorids[k].strid in ["GOP"]:
#        print("helo", colorids[k].strid, "mode", mode, "conn", connections.data[si[0]], "%d-%d" % (fromframe, toframe))

    if mode == 'b':
        # return reverse list (backward backward == forward)
#        print("connb", [(colorids[kk].strid, ii, trajectories[kk][ii].firstframe, trajlastframe(trajectories[kk][ii])) for (kk, ii) in connections.data[si[0]][::-1]])
        return connections.data[si[0]][::-1]
    else:
#        print("connfc", [(colorids[kk].strid, ii, trajectories[kk][ii].firstframe, trajlastframe(trajectories[kk][ii])) for (kk, ii) in connections.data[si[0]]])
        return connections.data[si[0]]


def mark_traj_chosen(trajectories, k, i, trajsonframe, colorids, barcodes, blobs, kk=None):
    """Mark a trajectory chosen and mark all overlapping same colorid as deleted.
    Or if an overlapping, already chosen one found, delete this one and
    do nothing else.

    Do not mark deleted traj's barcodes as deleted (comes at a later stage in
    mark_barcodes_from_trajs()) but modify deleted traj's offset scores if
    they contain shared blobs with chosen traj.

    Note: Assure that already chosen trajs do not call this function.

    Keyword arguments:
    trajectories -- global list of all trajectories
    k            -- coloridindex of traj to be chosen
    i            -- second index of traj to be chosen
    trajsonframe -- global list of trajectory indices per frame per coloridindex
    colorids     -- global colorid database created by parse_colorid_file()
    barcodes     -- global list of all barcodes
    blobs        -- global list of all color blobs
    kk           -- destination coloridindex (not used in default)

    Returns number of deleted, or -1 if self is deleted.

    """
    traj = trajectories[k][i]
    deleted = 0
    if kk is None: kk = k
    if traj.k != k:
        print("Warning, something bad happened (%s i%d f%d-%d) traj.k (%s) != k (%s). kk is %s!!!" % \
                (colorids[k].strid, i, traj.firstframe, trajlastframe(traj), colorids[traj.k].strid, colorids[k].strid, colorids[kk].strid))
        raise ValueError
        return -1

    chosenoverlap = set() # set of trajs overlapping as chosen
    deleteoverlap = set() # set of trajs overlapping to be deleted
    # gather overlapping traj info
    for currentframe in xrange(traj.firstframe, trajlastframe(traj) + 1):
        for j in trajsonframe[currentframe][kk]:
            if j == i: continue
            trajx = trajectories[kk][j]
            if trajx.state == STATE_CHOSEN:
                # this happens if a previously established connection did not include
                # this traj but this traj's score is good enough to be chosen.
                chosenoverlap.add((kk,j))
            elif trajx.state != STATE_DELETED and trajx.state != STATE_CHANGEDID:
                deleteoverlap.add((kk,j))

    # check for overlapping already chosen
    if chosenoverlap:
        for (kkk,j) in chosenoverlap:
            trajx = trajectories[kkk][j]
            print("  Warning: overlapping chosen trajs found (dst %s)." % colorids[kk].strid, end=" ")
            print("old:", colorids[trajx.k].strid, "%d-%d," % (trajx.firstframe, trajlastframe(trajx)), end=" ")
            print("new:", colorids[traj.k].strid, "%d-%d, Deleting new." % (traj.firstframe, trajlastframe(traj)))
        traj.state = STATE_DELETED
        return -1

    # check for overlapping others that are to be deleted
    if deleteoverlap:
        for (kkk,j) in deleteoverlap:
            trajx = trajectories[kkk][j]
            trajx.state = STATE_DELETED
            deleted += 1

            # decrease traj score offset if overlapping is also sharedblob (we chose this so other is bad "for sure")
            # get common frame range
            for frame in xrange(
                    max(traj.firstframe, trajx.firstframe),
                    min(trajlastframe(traj)+1, trajlastframe(trajx)+1)):
                # define good barcode
                barcode = barcodes[frame][k][traj.barcodeindices[frame-traj.firstframe]]
                # get overlapping bad barcode index
                bxi = trajx.barcodeindices[frame-trajx.firstframe]
                # check if they share a blob and if so, decrease bad trajs offset
                for blobi in barcode.blobindices:
                    if bxi in blobs[frame][blobi].barcodeindices:
                        trajx.offset_count -= 1
                        break

    # mark self as CHOSEN (if dst colorid is the same as src)
    if kk == k:
        traj.state = STATE_CHOSEN
    # or mark for changedid (which will come at a later stage)
    # if dst color is different from src
    else:
        traj.k = kk

    return deleted


def change_colorid(trajectories, k, i, trajsonframe, barcodes, colorids, blobs):
    """Create new trajectory with different colorid.

    1. Set original barcode states to deleted
    2. Create new barcodes without false color blob
    3. Add the new barcodeindex to remaining blobs
    3. Create new trajectory of new barcodes

    Keyword arguments:
    trajectories -- global list of all trajectories
    k            -- coloridindex of traj to be changed
    i            -- index of traj to be changed
    trajsonframe -- global list of trajectory indices per frame per coloridindex
    barcodes     -- global list of all barcodes
    colorids     -- global colorid database created by parse_colorid_file()
    blobs        -- global list of all color blobs


    """
    # initialize (assuming that traj.k has been set to mark color change)
    traj = trajectories[k][i]
    traj.state = STATE_CHANGEDID
    kk = traj.k
    strid = colorids[k].strid
    newstrid = colorids[kk].strid
    # create new barcodes and add them to new trajectory
    i = 0
    for frame in xrange(traj.firstframe, trajlastframe(traj)+1):
        # initialize
        barcode = barcodes[frame][k][traj.barcodeindices[i]]
        barcodes[frame][kk].append(barcode_t(
                barcode.centerx, barcode.centery, barcode.orientation,
                barcode.mfix, list(barcode.blobindices)))
        ii = len(barcodes[frame][kk])-1
        newbarcode = barcodes[frame][kk][ii]
        # change old barcode params (permanent deletion)
        barcode.mfix = 0 #|= (MFIX_DELETED | MFIX_CHANGEDID)
        # set new barcode params
        newbarcode.mfix = MFIX_PARTLYFOUND_FROM_TDIST
        # get colors that changed
        cc = list(set(strid).difference(set(newstrid)))
        for bi in list(newbarcode.blobindices):
            blob = blobs[frame][bi]
            for c in cc:
                if blob.color == color2int[c]:
                    del newbarcode.blobindices[newbarcode.blobindices.index(bi)]
                    break
            else:
                blob.barcodeindices.append(barcode_index_t(kk,ii))
        algo_barcode.order_blobindices(newbarcode, newstrid, blobs[frame], True)
        algo_barcode.calculate_params(newbarcode, newstrid, blobs[frame])
        # append barcode to new traj
        if i == 0:
            start_new_traj(trajectories, trajsonframe, frame, kk,
                    newbarcode, ii, newstrid, blobs[frame])
            newtraj = trajectories[kk][-1]
            newtrajindex = len(trajectories[kk]) - 1
        else:
            append_barcode_to_traj(
                    newtraj, trajsonframe[frame][kk], newtrajindex,
                    newbarcode, ii, newstrid, blobs[frame])
        # iterate
        i += 1


def fill_connection_with_nub(conn, k, trajectories, trajsonframe, barcodes, colorids, blobs):
    """Once a connection was estabilished, try to connect missing frames with
    not used barcodes, blobs, deleted barcodes, etc. In case of no success,
    create virtual barcodes to connect the gap.

    Keyword arguments:
    conn         -- the connection with (k,j) tuples of trajectory indices
    k            -- the colorid of the connection (not used yet, but might be)
    trajectories -- global list of all trajectories
    trajsonframe -- global list of trajectory indices per frame per coloridindex
    barcodes     -- global list of all barcodes
    colorids     -- global colorid database created by parse_colorid_file()
    blobs        -- global list of all color blobs

    """
    count_found = 0
    count_virtual = 0
    (oldkk, oldj) = (conn[0][0], conn[0][1])
    oldtraj = trajectories[oldkk][oldj]
    for (kk,j) in conn[1:]:
        traj = trajectories[kk][j]
        endframe = trajlastframe(oldtraj)
        startframe = traj.firstframe
        # if there is a gap, fill it with not used barcodes or with virtual ones
        if startframe - endframe > 1:
            oldbarcode = barcodes[endframe][oldtraj.k][oldtraj.barcodeindices[-1]]
            startbarcode = barcodes[startframe][traj.k][traj.barcodeindices[0]]
            # iterate all frames
            for frame in xrange(endframe+1, startframe):
                found = False
                # search for (deleted) same color barcodes, possibly not part of traj
                mindist = max_allowed_dist_between_trajs()
                for bi in xrange(len(barcodes[frame][oldkk])):
                    if not algo_barcode.barcode_is_free(
                            barcodes[frame], oldkk, bi, blobs[frame]):
                        continue
                    barcode = barcodes[frame][oldkk][bi]
                    dist = get_distance(oldbarcode, barcode)
                    if dist < mindist and get_distance(barcode, startbarcode) < max_allowed_dist_between_trajs(0,0,oldkk==kk):
                        candidate = barcode
                        cbi = bi
                        mindist = dist
                if mindist < max_allowed_dist_between_trajs():
                    candidate.mfix &= ~MFIX_DELETED
                    append_barcode_to_traj(oldtraj, trajsonframe[frame][oldkk],
                            oldj, candidate, cbi, colorids[oldkk].strid, blobs[frame])
                    found = True
                    count_found += 1

                # TODO: implement search with other methods, like:
                #       - Not used blobs
                #       - barcode of original color, if applicable
                #       - backward search from second traj
                #
                #       or include all these to virtual barcodes at a later stage,
                #       during traj smoothing - this is better...

                # not found, create virtual barcode with same params as last one
                if not found:
                    candidate = barcode_t(
                            oldbarcode.centerx, oldbarcode.centery,
                            oldbarcode.orientation, MFIX_VIRTUAL | MFIX_CHOSEN, [])
                    barcodes[frame][oldkk].append(candidate)
                    append_barcode_to_traj(oldtraj, trajsonframe[frame][oldkk],
                                oldj, candidate, len(barcodes[frame][oldkk])-1,
                                colorids[oldkk].strid, blobs[frame])
                    count_virtual +=1
                # store last barcode
                oldbarcode = candidate
            # frame iteration ends
        # save last params
        oldtraj = traj
        (oldkk, oldj) = (kk, j)

#    print("found", count_found)
#    print("virtual", count_virtual)
#    for (kk,j) in conn:
#        traj = trajectories[kk][j]
#        print(kk, j, colorids[traj.k].strid, "%d-%d" % (traj.firstframe, trajlastframe(traj)))

    return (count_found, count_virtual)


def enhance_virtual_barcodes(trajectories, trajsonframe, colorids, barcodes, blobs):
    """Try to add not used barcodes to virtual barcodes and not used blobs to
    all chosen barcodes (that already have blobs) to enhance their parameters.

    This functions should be called after fill_..._nub() which created the
    virtual barcodes first. Could be called on a later stage as well.

    Adds MFIX_DEBUG on possible conflicts (overlapping virtuals, shared, etc.).

    Keyword arguments:
    trajectories -- global list of all trajectories
    trajsonframe -- global list of trajectory indices per frame per coloridindex
    colorids     -- global colorid database created by parse_colorid_file()
    barcodes     -- blobal list of all barcodes
    blobs        -- global list of all color blobs

    """
    changes = 0
    print("   ", end=" ")
    for k in xrange(len(colorids)):
        print(colorids[k].strid, end=" ")
        # get first chosen traj
        i = get_chosen_neighbor_traj_perframe(None, trajectories, trajsonframe, k, True, None)
        while i != -1:
            traj = trajectories[k][i]
            frame = traj.firstframe
            for j in traj.barcodeindices:
                oldbarcode = barcodes[frame][k][j]
                kj = barcode_index_t(k,j)

                # search around for (deleted) same color barcodes
                # for all new virtual barcodes (nothing assigned to them yet)
                if (oldbarcode.mfix & MFIX_VIRTUAL) and not oldbarcode.blobindices:
                    mindist = max_allowed_dist_between_trajs()
                    for bi in xrange(len(barcodes[frame][k])):
                        if bi == j: continue
                        if not algo_barcode.barcode_is_free(
                                barcodes[frame], k, bi, blobs[frame]): # TODO: first round: only deleted count or all? Not only deleted is not filtered out
                            continue
                        barcode = barcodes[frame][k][bi]
                        dist = get_distance(oldbarcode, barcode)
                        if dist < mindist:
                            candidate = barcode
                            mindist = dist
                    # set new params if candidate found
                    if mindist < max_allowed_dist_between_trajs():
                        # form new one based on deleted old
                        oldbarcode.centerx = candidate.centerx
                        oldbarcode.centery = candidate.centery
                        oldbarcode.orientation = candidate.orientation
                        oldbarcode.blobindices = list(candidate.blobindices)
                        for ii in oldbarcode.blobindices:
                            blob = blobs[frame][ii]
                            if kj not in blob.barcodeindices:
                                blob.barcodeindices.append(kj)
                        oldbarcode.mfix = candidate.mfix
                        oldbarcode.mfix &= ~MFIX_DELETED
                        # permanently delete old candidate
                        candidate.mfix = 0 # |= MFIX_DELETED
#                        oldbarcode.mfix &= ~MFIX_VIRTUAL # TODO: might not be needed if further check on virtuals will be done
                        oldbarcode.mfix |= MFIX_CHOSEN
                        algo_barcode.order_blobindices(oldbarcode, colorids[k].strid, blobs[frame], True)
                        algo_barcode.calculate_params(oldbarcode, colorids[k].strid, blobs[frame])
                        if oldbarcode.mfix & MFIX_FULLFOUND:
                            traj.fullfound_count += 1
                            if oldbarcode.mfix & MFIX_FULLNOCLUSTER:
                                traj.fullnocluster_count += 1
                        # TODO: colorblob count + sharesblob count
                        changes += 1

                # search around for not used blobs (and choose best=closest for each color)
                # for all chosen barcodes (virtual and not virtual) that already have blobs
                # (i.e. they were based on a barcode at the beginning - this way
                # we avoid adding noise blobs to empty virtual barcodes)
                if oldbarcode.mfix & MFIX_CHOSEN and oldbarcode.blobindices:
                    allcolors = set([color2int[x] for x in colorids[k].strid])
                    usedcolors = set([blobs[frame][x].color for x in oldbarcode.blobindices])
                    notusedcolors = allcolors.difference(usedcolors)
                    # short double check on blob consistency
#                    if len(allcolors) != len(usedcolors) + len(notusedcolors):
#                        raise ValueError("Warning: blobindices mismatch, used %d, not used %d, all %d" % (len(usedcolors), len(notusedcolors), len(allcolors)))
                    newblobs = [[] for x in xrange(len(color2int))]
                    found = False
                    for ii in xrange(len(blobs[frame])):
                        blob = blobs[frame][ii]
                        if algo_blob.barcodeindices_not_deleted(blob.barcodeindices, barcodes[frame]): continue
                        # if new color, save as canidate for new color
                        if blob.color in notusedcolors and \
                                get_distance(oldbarcode, blob) < max_allowed_dist_between_trajs():
                            newblobs[blob.color].append(ii)
                            found = True
                    # add bests if found not used blobs
                    if found:
                        # get best blob for each new color
                        for cblobs in newblobs:
                            if not cblobs: continue
                            best = cblobs[0]
                            if len(cblobs) > 1:
                                mindist = 1e6
                                for jj in cblobs:
                                    dist = get_distance(oldbarcode,blobs[frame][jj])
                                    if dist < mindist:
                                        mindist = dist
                                        best = jj
                            blob = blobs[frame][best]
                            oldbarcode.blobindices.append(best)
                            blob.barcodeindices.append(kj)
                            traj.colorblob_count[colorids[k].strid.index(int2color[blob.color])] += 1
                        # set new params
                        changes += 1
#                        if len(oldbarcode.blobindices) > MCHIPS:
#                            raise ValueError("debug should have happened before, error is here somewhere...")
                        if len(oldbarcode.blobindices) == MCHIPS:
                            oldbarcode.mfix &= ~MFIX_PARTLYFOUND_FROM_TDIST
                            oldbarcode.mfix |= MFIX_FULLFOUND
                            traj.fullfound_count += 1
                            # TODO: fullnocluster_count is not increased here yet, nor colorblob count, nor sharesblob count...
                        else:
                            oldbarcode.mfix |= MFIX_PARTLYFOUND_FROM_TDIST
#                        oldbarcode.mfix &= ~MFIX_VIRTUAL # TODO: might not be needed if further check on virtuals will be done
                        algo_barcode.order_blobindices(oldbarcode, colorids[k].strid, blobs[frame], True)
                        algo_barcode.calculate_params(oldbarcode, colorids[k].strid, blobs[frame])
                # iterate to next frame
                frame += 1
            # get next chosen traj
            i = get_chosen_neighbor_traj_perframe(traj, trajectories, trajsonframe, k, True, None)
    print()
    return changes


def choose_and_connect_trajs(si, score_threshold, trajectories, trajsonframe,
        colorids, barcodes, blobs, kkkk=None, framelimit=1500):
    """Helper algo for find_best_trajectories(). Name speaks for itself.

    Keyword arguments:
    si              -- (k, i) index of all trajectories in a sorted list (good scores first)
    score_threshold -- minimum score for good trajectories
    trajectories    -- global list of all trajectories
    trajsonframe    -- global list of trajectory indices per frame per coloridindex
    colorids        -- global colorid database created by parse_colorid_file()
    barcodes        -- global list of all barcodes
    blobs           -- global list of all color blobs
    kkkk            -- optional param to restrict algo for only one coloridindex
    framelimit      -- optional param to define frame limit of traj extentions

    """
    # initialize
    chosen = 0
    deleted = 0
    connected = 0
    virtual = 0
    rebirth = 0
    deletedgood = []
    connections = [[] for x in xrange(len(colorids))]
    changedcolor = []
    # iterate all trajectories
    print("\n  Scores of chosen:", end=" ")
    for i in xrange(len(si)):
        k = si[i][0]
        ii = si[i][1]
        traj = trajectories[k][ii]
        # end iteration if traj is not good any more
        if not is_traj_good(traj, score_threshold + traj.offset_count):
            break
        print(traj_score(traj), colorids[k].strid, "i%d s%d (%d-%d)," % (ii, traj.state, traj.firstframe, trajlastframe(traj)), end=" ")
        # skip ones that look good, but are already deleted (by better ones or due to changed score)
        if traj.state == STATE_DELETED:
            deletedgood.append((colorids[k].strid, traj_score(traj)))
            continue
        # and also skip ones that were chosen for another colorid
        if traj.state == STATE_CHANGEDID or traj.k != k: # actually second should not occur here yet
            print("\n  Warning: changed %s traj colorid to %s with score %d, colorblob_count: %s," % (colorids[k].strid,
                    colorids[traj.k].strid, traj_score(traj), traj.colorblob_count), end=" ")
            continue
        # skip already chosen ones
        if traj.state == STATE_CHOSEN:
            continue

        # mark best trajectories with CHOSEN flag and delete all that are
        # overlapping, thus are assumed to be false positive detections
        a = mark_traj_chosen(trajectories, k, ii, trajsonframe, colorids, barcodes, blobs)
        # if an overlapping already chosen one was found, we do not choose this one
        if a == -1: continue
        # this one was chosen successfully, increase counters
        deleted += a
        chosen += 1

        # try to connect neighboring (max 1 min) chosen ones forward
        next = get_chosen_neighbor_traj(traj, trajectories[k], forward=True, framelimit=framelimit)
        if next != -1:
            conn = connect_chosen_trajs(traj, trajectories[k][next], k, trajectories, trajsonframe, barcodes, colorids, framelimit=framelimit)
            if conn:
                # fill connection with not used barcodes or new virtual ones
                (a, b) = fill_connection_with_nub(
                        [(k, ii)] + conn + [(k, next)], k, trajectories,
                        trajsonframe, barcodes, colorids, blobs)
                rebirth += a
                virtual += b
                # set CHOSEN property if good connection was found
                for (kk, j) in conn:
                    a = mark_traj_chosen(trajectories, kk, j, trajsonframe, colorids, barcodes, blobs, k)
                    if k != kk:
                        changedcolor.append((kk,j))
                    if a == -1:
                        deleted += 1
                    else:
                        chosen += 1
                        connected += 1
                        deleted += a

        # try to connect neighboring (max 1 min) chosen ones backward
        prev = get_chosen_neighbor_traj(traj, trajectories[k], forward=False, framelimit=framelimit)
        if prev != -1:
            conn = connect_chosen_trajs(trajectories[k][prev], traj, k, trajectories, trajsonframe, barcodes, colorids, framelimit=framelimit)
            if conn:
                # fill connection with not used barcodes or new virtual ones
                (a, b) = fill_connection_with_nub(
                        [(k, prev)] + conn + [(k, ii)], k, trajectories,
                        trajsonframe, barcodes, colorids, blobs)
                rebirth += a
                virtual += b
                # set CHOSEN property if good connection was found
                for (kk,j) in conn:
                    a = mark_traj_chosen(trajectories, kk, j, trajsonframe, colorids, barcodes, blobs, k)
                    if k != kk:
                        changedcolor.append((kk,j))
                    if a == -1:
                        deleted += 1
                    else:
                        chosen += 1
                        connected += 1
                        deleted += a

    print()
    print("    chosen:", chosen, "deleted:", deleted, "connected:", connected)
    print("    deleted trajs with score over the threshold (possibly deleted false positive detections):", deletedgood)
    print("    barcodes reanimated to fill gap between chosen trajs:", rebirth)
    print("    virtual barcodes added to trajs to fill gap between static chosen trajs:", virtual)

    # change colorids on marked ones
    print("  Changing colorid of some (possibly false detected) trajs...")
    for (k,i) in changedcolor:
        change_colorid(trajectories, k, i, trajsonframe, barcodes, colorids, blobs)
    print("    changed:", len(changedcolor))

    # set barcodes chosen/deleted property (first round)
    print("  Set barcode properties (first round)...")
    (chosen, deleted) = mark_barcodes_from_trajs(trajectories, barcodes, colorids, kkkk)
    print("    chosen barcodes:", chosen, " deleted barcodes:", deleted)
    sys.stdout.flush()


def recalculate_score(traj, k, barcodes, blobs, colorids):
    """Recalculate sharesblob on traj to change its overall score.
    
    Keyword arguments:
    traj      -- a trajectory
    k         -- coloridindex of the trajectory
    barcodes  -- global list of all barcodes
    blobs     -- global list of all color blobs
    colorids  -- global colorid database created by parse_colorid_file()

    """
    frame = traj.firstframe
    traj.sharesblob_count = 0
    for i in traj.barcodeindices:
        a = barcodes[frame][k][i]
        for kk in xrange(len(colorids)):
            for b in barcodes[frame][kk]:
                if a == b or not b.mfix or b.mfix & MFIX_DELETED: continue
                if algo_barcode.could_be_sharesblob(a, b, k, kk, blobs[frame], colorids):
                    traj.sharesblob_count += 1
                    break
        frame += 1


def find_best_trajectories(trajectories, trajsonframe, colorids, barcodes, blobs,
        settings):
    """Sort all trajectories according to their score, keep the best, delete the rest.
    Do this iteratively until all trajs are done.

    Actually trajectories are not deleted, only assigned with
    STATE_DELETED/STATE_CHANGEDID flags.

    Algorithm details:
    1. sort colorids according to total score of trajs for all colors and
       mark not good enough as deleted. TODO: how to get dynamic global threshold?
    2. sort trajectories according to score, regardless of coloridindex, and mark
       very best with high threshold as chosen (see point 4.)
    3. iterate colorids according to total good score, iterate trajs inside
       according to score and mark them as chosen again (see point 4.)
    4. a) iterate from best traj, mark as chosen (and overlapping as deleted) and
       try to connect with first neighbor (not too far, but in both directions)
       which is chosen already. Mark best connection as chosen, overlapping as
       deleted. See connect_chosen_trajs() for more details.
       Note: traj score (offset) can change dinamically, so second check after sorting is
       also implemented to avoid trajs with initially good but later decreased score.
       b) If connections contained deleted trajs from another color, create new
       barcodes and a new trajectory for same barcodes with different colorid
       c) Enhance virtual barcodes (include not used blobs and barcodes closeby)
    5. find all deleted trajs over not used blobs, and reanimate best ones
       accidentally deleted by point 1. Perform the same on new color as with
       the others before

    Keyword arguments:
    trajectories -- global list of all trajectories
    trajsonframe -- global list of trajectory indices per frame per coloridindex
    colorids     -- global colorid database created by parse_colorid_file()
    barcodes     -- global list of all barcodes
    blobs        -- global list of all color blobs
    settings     -- find_best_trajectories_settings_t class for settings

    """

    ##########################################################################
    # sort colorids according to total score of trajs and delete peculiar ones

    best_scores = [0 for k in xrange(len(colorids))]
    worst_scores = [0 for k in xrange(len(colorids))]
    sum_scores = [0 for k in xrange(len(colorids))]
    sum_good_scores = [0 for k in xrange(len(colorids))]
    for k in xrange(len(colorids)):
        if trajectories[k]:
            best_scores[k] = max(traj_score(x) for x in trajectories[k])
            worst_scores[k] = min(traj_score(x) for x in trajectories[k])
            sum_scores[k] = sum(traj_score(x) for x in trajectories[k])
            sum_good_scores[k] = sum(traj_score(x) if is_traj_good(x,
                    settings.good_score_threshold) else 0 for x in trajectories[k])
    sortedk = range(len(colorids))
    sortedk.sort(lambda x,y: sum_scores[y] - sum_scores[x])
    for k in sortedk:
        strid = colorids[k].strid
        deleteit = False
        if best_scores[k] < settings.might_be_bad_score_threshold and \
                sum_good_scores[k] < settings.might_be_bad_sum_good_score_threshold:
            deleteit = True
            for traj in trajectories[k]:
                traj.state = STATE_DELETED
        print("  %s trajs: %5d sum: %5d sum_good: %5d best: %5d worst: %5d %s" % (strid,
                len(trajectories[k]), sum_scores[k], sum_good_scores[k], best_scores[k],
                worst_scores[k], "<-- all deleted" if deleteit else ""))
    sys.stdout.flush()

    ############################################################################
    # first phase: assign chosen state to very good trajs, regardless of color
    # sort all trajectories according to reverse global score
    si = [] # si stands for 'sorted index'
    for k in xrange(len(colorids)):
        si += [(k, i) for i in xrange(len(trajectories[k]))]
    si.sort(lambda x,y: traj_score(trajectories[y[0]][y[1]]) - traj_score(trajectories[x[0]][x[1]]))
    # choose and connect them
    choose_and_connect_trajs(si, settings.good_for_sure_score_threshold, trajectories,
            trajsonframe, colorids, barcodes, blobs, kkkk=None, framelimit=settings.framelimit)

    ############################################################################
    # second phase: interate all remaining trajs according to best colorid
    # and extend them as well after all good have been chosen
    for k in sortedk:
        # recalculate score (sharesblob might have been modified)
        for traj in trajectories[k]:
            recalculate_score(traj, k, barcodes, blobs, colorids)
        # sort all trajectories in given color according to reverse score
        si = [(k, i) for i in xrange(len(trajectories[k]))] # si stands for 'sorted index'
        si.sort(lambda x,y: traj_score(trajectories[y[0]][y[1]]) - traj_score(trajectories[x[0]][x[1]]))
        # choose and connect them
        choose_and_connect_trajs(si, settings.good_score_threshold, trajectories,
                trajsonframe, colorids, barcodes, blobs, kkkk=k, framelimit=settings.framelimit)
        # extend all chosen barcodes
        print("  Extending chosen trajs with not yet chosen in both temporal directions...")
        (virtual, rebirth) = extend_chosen_trajs(trajectories, trajsonframe, colorids, barcodes, blobs, k)
        print("    new virtual barcodes:", virtual, " barcodes reanimated:", rebirth)

    ############################################################################
    # third phase: cleanup, list, enhance virtual

    # list meta trajs
    print("\n  List meta trajs and gaps between...")
    list_meta_trajs(trajectories, trajsonframe, barcodes, colorids, blobs)

    # try to include not used blobs and not used barcodes to virtual barcodes
    print("  Enhance virtual barcodes with not used barcodes/blobs...")
    # TODO: too slow
    changes = enhance_virtual_barcodes(trajectories, trajsonframe, colorids, barcodes, blobs)
    print("    number of changes:", changes)


def extend_chosen_trajs(trajectories, trajsonframe, colorids, barcodes, blobs,
        kkkk=None, framelimit=1500):
    """Extend all chosen trajs in both temporal directions with remaining
    not chosen trajs.

    This function should be called after best trajectories have already been
    chosen and connected, if possible.
    
    Function calls connect_chosen_trajs(), like find_best_trajectories(),
    but now without specific ending and frame limit. On the other hand,
    there should be less parts to extend. Anyway, algo might take long,
    especially because of unknown number of iterations.

    Actually trajectories are not deleted, only assigned with STATE_DELETED flag.

    Keyword arguments:
    trajectories -- global list of all trajectories
    trajsonframe -- global list of trajectory indices per frame per coloridindex
    colorids     -- global colorid database created by parse_colorid_file()
    barcodes     -- blobal list of all barcodes
    blobs        -- global list of all color blobs
    kkkk         -- optional argument to extend only a given colorid
    framelimit   -- optional param to define frame limit of traj extentions

    """

    deleted = 0
    chosen = 0
    virtual = 0
    rebirth = 0

    oldchosen = -1
    olddeleted = -1
    it = 0
    if kkkk is None:
        klist = range(len(colorids))
    else:
        klist = [kkkk]

    # iteration is needed, because traj states change in between. (TODO: why exactly?)
    while oldchosen != chosen or olddeleted != deleted:
        changedcolor = []
        oldchosen = chosen
        olddeleted = deleted
        print("   ", end=" ")
        for k in klist:
            print(colorids[k].strid, end=" ")
            for i in xrange(len(trajectories[k])):
                traj = trajectories[k][i]
                if traj.state != STATE_CHOSEN: continue

                # elongate forward
                conn = connect_chosen_trajs(traj, "forward", k, trajectories, trajsonframe, barcodes, colorids, framelimit=framelimit)
                if conn:
                    # fill connection with not used barcodes or new virtual ones
                    (a, b) = fill_connection_with_nub(
                            [(k, i)] + conn, k, trajectories,
                            trajsonframe, barcodes, colorids, blobs)
                    rebirth += a
                    virtual += b
                    # set CHOSEN property if good connection was found
                    for (kk, j) in conn:
#                        print("forward", colorids[kk].strid, trajectories[kk][j].firstframe, trajlastframe(trajectories[kk][j]))
                        a = mark_traj_chosen(trajectories, kk, j, trajsonframe, colorids, barcodes, blobs, k)
                        if k != kk:
                            changedcolor.append((kk,j))
                        if a == -1:
                            deleted += 1
                        else:
                            chosen += 1
                            deleted += a

                # elongate backward
                conn = connect_chosen_trajs(traj, "backward", k, trajectories, trajsonframe, barcodes, colorids, framelimit=framelimit)
                if conn:
                    # fill connection with not used barcodes or new virtual ones
                    (a, b) = fill_connection_with_nub(
                            conn + [(k, i)], k, trajectories,
                            trajsonframe, barcodes, colorids, blobs)
                    rebirth += a
                    virtual += b
                    # set CHOSEN property if good connection was found
                    for (kk,j) in conn:
 #                       print("backward", colorids[kk].strid, trajectories[kk][j].firstframe, trajlastframe(trajectories[kk][j]))
                        a = mark_traj_chosen(trajectories, kk, j, trajsonframe, colorids, barcodes, blobs, k)
                        if k != kk:
                            changedcolor.append((kk,j))
                        if a == -1:
                            deleted += 1
                        else:
                            chosen += 1
                            deleted += a

        # change colorids on marked ones
        for (k,i) in changedcolor:
            change_colorid(trajectories, k, i, trajsonframe, barcodes, colorids, blobs)

        # change barcode properties as well
        mark_barcodes_from_trajs(trajectories, barcodes, colorids)

        # iterate next
        it += 1
        print("\n    iteration #%d -" % it, "chosen:", chosen-oldchosen, "deleted:", deleted-olddeleted, "changed color:", len(changedcolor))
        sys.stdout.flush()
    return (virtual, rebirth)


def add_virtual_barcodes_to_gaps(trajectories, trajsonframe, colorids, barcodes):
    """Fill all remaining gaps between chosen trajectories with virtual barcodes.

    Adds MFIX_DEBUG on possible conflicts (too large gap between chosens).

    Keyword arguments:
    trajectories -- global list of all trajectories
    trajsonframe -- global list of trajectory indices per frame per coloridindex
    colorids     -- global colorid database created by parse_colorid_file()
    barcodes     -- blobal list of all barcodes

    Return number of virtual barcodes added.

    TODO: insert time limit to connection

    """
    simulate = False
    if simulate: print("    Warning: add_virtual_barcodes_to_gaps() is in simulation mode.")
    virtual = 0

    for k in xrange(len(colorids)):
        strid = colorids[k].strid

        ########################################
        # get first traj, add virtuals before it
        i = get_chosen_neighbor_traj_perframe(
                None, trajectories, trajsonframe, k, True, None)
        if i == -1: continue
        # add virtual barcodes to the beginning
        traj = trajectories[k][i]
        barcode = barcodes[traj.firstframe][k][traj.barcodeindices[0]]
        if not simulate:
            for frame in xrange(traj.firstframe):
                barcodes[frame][k].append(barcode_t(
                    barcode.centerx, barcode.centery,
                    barcode.orientation, MFIX_VIRTUAL | MFIX_CHOSEN, []))
                trajsonframe[frame][k].add(i)
                virtual += 1
            traj.barcodeindices = [len(barcodes[x][k])-1 for x in xrange(traj.firstframe)] + traj.barcodeindices
            traj.firstframe = 0

        ######################################################
        # connect all chosen trajs in the middle with virtuals
        next = get_chosen_neighbor_traj_perframe(
                traj, trajectories, trajsonframe, k, True, None)
        while next != -1:
            trajx = trajectories[k][next]
            a = trajlastframe(traj)
            b = trajx.firstframe
            if b > a+1:
                barcodea = barcodes[a][k][traj.barcodeindices[-1]]
                barcodeb = barcodes[b][k][trajx.barcodeindices[0]]
                dist = get_distance(barcodea, barcodeb)
                debug = False
                if dist > max_allowed_dist_between_trajs(a,b):
                    print("    Warning: distance between neighboring chosen %s trajs is large (%d)." % (colorids[k].strid, dist), end=" ")
                    print("a i%d" % i, "f%d-%d" % (traj.firstframe, trajlastframe(traj)), end=" ")
                    print("b i%d" % next, "f%d-%d" % (trajx.firstframe, trajlastframe(trajx)))
                    if trajx.firstframe - trajlastframe(traj) > 25:
                        debug = True
                    elif dist > 250:
                        debug = True
                if not simulate:
                    dx = (barcodeb.centerx - barcodea.centerx) / (b - a)
                    dy = (barcodeb.centery - barcodea.centery) / (b - a)
                    do = barcodeb.orientation - barcodea.orientation
                    while do > pi: do -= 2*pi
                    while do < -pi: do += 2*pi
                    do /= (b - a)
                    j = 1
                    for frame in xrange(a+1, b):
                        barcodes[frame][k].append(barcode_t(
                                barcodea.centerx + j*dx,
                                barcodea.centery + j*dy,
                                barcodea.orientation + j*do,
                                MFIX_VIRTUAL | MFIX_CHOSEN | (MFIX_DEBUG if debug else 0), []))
                        trajsonframe[frame][k].add(i)
                        traj.barcodeindices.append(len(barcodes[frame][k])-1)
                        virtual += 1
                        j += 1
            # save params for next iteration
            i = next
            traj = trajectories[k][i]
            next = get_chosen_neighbor_traj_perframe(
                    trajx, trajectories, trajsonframe, k, True, None)

        # last - add virtual barcodes to the end
        barcode = barcodes[trajlastframe(traj)][k][traj.barcodeindices[-1]]
        if not simulate:
            for frame in xrange(trajlastframe(traj)+1, len(trajsonframe)):
                barcodes[frame][k].append(barcode_t(
                    barcode.centerx, barcode.centery,
                    barcode.orientation, MFIX_VIRTUAL | MFIX_CHOSEN, []))
                trajsonframe[frame][k].add(i)
                traj.barcodeindices.append(len(barcodes[frame][k])-1)
                virtual += 1

    return virtual


def get_next_fullfound_from_traj(traj, frame, barcodes, k):
    """Get next frame index that contains a fullfound barcode.

    Keyword arguments:
    traj     -- a trajectory (supposedly a chosen one)
    frame    -- first absolute frame to start the iteration with
    barcodes -- global list of barcodes
    k        -- coloridindex

    Function returns -1 if not found.

    """
    lastframe = trajlastframe(traj)
    while frame <= lastframe:
        if (barcodes[frame][k][traj.barcodeindices[frame - traj.firstframe]].mfix & MFIX_FULLFOUND):
            return frame
        frame += 1
    # error, not found
    return -1


def smooth_partlyfound_params(traj, barcodes, k, strid):
    """Smooth the orientation and center of partlyfound barcodes in a trajectory
    with the fullfound orientations and centers.
    
    Keyword arguments:
    traj     -- a trajectory (supposedly a chosen one)
    barcodes -- global list of barcodes
    k        -- coloridindex
    strid    -- string id corresponding to coloridindex k

    Function does not return a value but changes barcode parameters in the trajectory.
    """

    # start smoothing at the first fullfound element
    currentframe = get_next_fullfound_from_traj(traj, traj.firstframe, barcodes, k)
    if currentframe == -1:
        return
    current = barcodes[currentframe][k][traj.barcodeindices[currentframe - traj.firstframe]]
    lastframe = trajlastframe(traj)
    # get first fullfound
    while currentframe <= lastframe:
        # get next fullfound
        nextfullframe = get_next_fullfound_from_traj(traj, currentframe+1, barcodes, k)
        if nextfullframe == -1:
            return
        next = barcodes[nextfullframe][k][traj.barcodeindices[nextfullframe - traj.firstframe]]
        # check if there is at least one partlyfound between them:
        # check properties of current and next fullfound, only change if there is no motion
        if nextfullframe - currentframe == 1 or get_distance(current, next) > MAX_PERFRAME_DIST_MD:
            currentframe = nextfullframe
            current = next
            continue
        dx = (next.centerx - current.centerx) / (nextfullframe - currentframe)
        dy = (next.centery - current.centery) / (nextfullframe - currentframe)
        do = next.orientation - current.orientation
        while do > pi: do -= 2*pi
        while do < -pi: do += 2*pi
        do /= (nextfullframe - currentframe)
        for i in xrange(1, nextfullframe-currentframe):
            barcode = barcodes[currentframe + i][k][traj.barcodeindices[currentframe + i - traj.firstframe]]
            barcode.centerx = current.centerx + i*dx
            barcode.centery = current.centery + i*dy
            barcode.orientation = current.orientation + i*do
        # proceed to next fullfound
        currentframe = nextfullframe
        current = next


def get_next_barcode_with_mfix(frame, barcodes, k, mfix, lastframe=None):
    """Get next (frame, index) tuple that contains a barcode with given mfix flag.

    Keyword arguments:
    frame     -- first absolute frame to start the iteration with
    barcodes  -- global list of barcodes
    k         -- coloridindex
    mfix      -- an mfix value
    lastframe -- optional argument to restrict search until an explicit frame

    Function returns -1 if not found.

    """
    if lastframe == None:
        lastframe = len(barcodes)-1
    while frame <= lastframe:
        for i in xrange(len(barcodes[frame][k])):
            if barcodes[frame][k][i].mfix & mfix == mfix:
                return (frame, i)
        frame += 1
    # error, not found
    return (-1, -1)


def list_meta_trajs(trajectories, trajsonframe, barcodes, colorids, blobs):
    """List meta trajs and peculiar gaps between them.

    Keyword arguments:
    trajectories -- global list of all trajectories
    trajsonframe -- global list of trajectory indices per frame per coloridindex
    barcodes     -- global list of all barcodes
    colorids     -- global colorid database created by parse_colorid_file()
    blobs        -- global list of all blobs

    """
    changes = 0
    for k in xrange(len(colorids)):
        print("   ", colorids[k].strid, end=" ")
        # get first chosen traj
        i = get_chosen_neighbor_traj_perframe(None, trajectories, trajsonframe, k, True, None)
        while i != -1:
            # get next continuous chain of traj indices into chosens
            chosens = [i]
            oldtraj = trajectories[k][i]
            firstframe = oldtraj.firstframe
            while 1:
                i = get_chosen_neighbor_traj_perframe(oldtraj, trajectories, trajsonframe, k, True, None)
                if i == -1:
                    break
                traj = trajectories[k][i]
                if trajlastframe(oldtraj) + 1 != traj.firstframe:
                    break
                chosens.append(i)
                oldtraj = traj
            lastframe = trajlastframe(trajectories[k][chosens[-1]])
            print("%d-%d" % (firstframe, lastframe), end=" ")
            if i != -1:
                print("(d%d)" % get_distance(
                        barcodes[lastframe][k][trajectories[k][chosens[-1]].barcodeindices[-1]],
                        barcodes[trajectories[k][i].firstframe][k][trajectories[k][i].barcodeindices[0]]), end=" ")
            # iterate to next chain of trajs
        print()
        # iterate to next colorid


def smooth_final_trajectories(trajectories, trajsonframe, barcodes, colorids, blobs):
    """Smooth all chosen barcode chains.

    TODO: algo so far is only informative on meta-trajs but no action is taken.

    Keyword arguments:
    trajectories -- global list of all trajectories
    trajsonframe -- global list of trajectory indices per frame per coloridindex
    barcodes     -- global list of all barcodes
    colorids     -- global colorid database created by parse_colorid_file()
    blobs        -- global list of all blobs

    """
    changes = 0
    for k in xrange(len(colorids)):
        print("   ", colorids[k].strid, end=" ")
        # get first chosen traj
        i = get_chosen_neighbor_traj_perframe(None, trajectories, trajsonframe, k, True, None)
        while i != -1:
            # get next continuous chain of traj indices into chosens
            chosens = [i]
            oldtraj = trajectories[k][i]
            firstframe = oldtraj.firstframe
            while 1:
                i = get_chosen_neighbor_traj_perframe(oldtraj, trajectories, trajsonframe, k, True, None)
                if i == -1:
                    break
                traj = trajectories[k][i]
                if trajlastframe(oldtraj) + 1 != traj.firstframe:
                    break
                chosens.append(i)
                oldtraj = traj
            lastframe = trajlastframe(trajectories[k][chosens[-1]])
            # get first fullfound
            (oldfullframe, ii) = get_next_barcode_with_mfix(firstframe, barcodes, k, MFIX_CHOSEN | MFIX_FULLFOUND)
            print("%d-%d" % (firstframe, lastframe), end=" ")
            if i != -1:
                print("(d%d)" % get_distance(
                        barcodes[lastframe][k][trajectories[k][chosens[-1]].barcodeindices[-1]],
                        barcodes[trajectories[k][i].firstframe][k][trajectories[k][i].barcodeindices[0]]), end=" ")
# TODOdebug
#            if colorids[k].strid == "GOP" and lastframe == 326:
#                for xx in xrange(320, 360):
#                    print("frame", xx)
#                    for xxx in trajsonframe[xx][k]:
#                        xxxx = trajectories[k][xxx]
#                        print("  i%d f%d-%d" % (xxx, xxxx.firstframe, trajlastframe(xxxx)), STATE_STR[xxxx.state])
# TODOdebug

            # no more fullfound until the end of current frame
            # TODO? what to do with end?
            # go to next chain
            if oldfullframe > lastframe or oldfullframe == -1:
                continue
            # chain starts with not fullfound.
            # TODO? What to do with beginning?
            if oldfullframe > firstframe:
                pass
            oldfullbarcode = barcodes[oldfullframe][k][ii]
            # iterate frames between fullfounds
            while 1:
                # get next fullfound
                (fullframe, ii) = get_next_barcode_with_mfix(oldfullframe + 1, barcodes, k, MFIX_CHOSEN | MFIX_FULLFOUND)
                if fullframe > lastframe or fullframe == -1:
                    # no more fullfound until the end of current frame
                    # TODO? what to do with the end?
                    # go to next chain
                    break
                fullbarcode = barcodes[fullframe][k][ii]
                if fullframe > oldfullframe + 1:
                    # initialize params from two fullfound barcodes on the side
                    dx = float(fullbarcode.centerx - oldfullbarcode.centerx) / (fullframe - oldfullframe)
                    dy = float(fullbarcode.centery - oldfullbarcode.centery) / (fullframe - oldfullframe)
                    do = float(fullbarcode.orientation - oldfullbarcode.orientation)
                    while do > pi: do -= 2*pi
                    while do < -pi: do += 2*pi
                    do /= (fullframe - oldfullframe)
#                    if colorids[k].strid == 'GPB':
#                        print("oldfull", colorids[k].strid, oldfullframe, oldfullbarcode.centerx, oldfullbarcode.centery, oldfullbarcode.orientation, mfix2str(oldfullbarcode.mfix))
                    oldframe = oldfullframe
                    # set partlyfound params between
                    while 1:
                        (frame, ii) = get_next_barcode_with_mfix(oldframe + 1, barcodes, k, MFIX_CHOSEN)
                        # no more partlyfound
                        if frame >= fullframe:
                            break
                        # set params

# TODO debug commented out
#                        barcode = barcodes[frame][k][ii]
#                        barcode.centerx = oldfullbarcode.centerx + (frame-oldfullframe)*dx
#                        barcode.centery = oldfullbarcode.centery + (frame-oldfullframe)*dy
#                        barcode.orientation = oldfullbarcode.orientation + (frame-oldfullframe)*do
#                        barcode.mfix |= MFIX_DEBUG
#                        while barcode.orientation > pi: barcode.orientation -= 2*pi
#                        while barcode.orientation < -pi: barcode.orientation += 2*pi
# TODO debug comment ends

#                        if colorids[k].strid == 'GPB':
#                            print("barcode", colorids[k].strid, frame, barcode.centerx, barcode.centery, barcode.orientation, mfix2str(barcode.mfix))
                        changes += 1
                        # save old params
                        oldframe = frame
                    # save old params
#                    if colorids[k].strid == 'GPB':
#                        print("full", colorids[k].strid, fullframe, fullbarcode.centerx, fullbarcode.centery, fullbarcode.orientation, mfix2str(fullbarcode.mfix))
                oldfullframe = fullframe
                oldfullbarcode = fullbarcode
            # iterate to next chain of trajs
        # iterate to next colorid
        print()
    return changes


def mark_barcodes_from_trajs(trajectories, barcodes, colorids, kkkk=None):
    """Set barcode states according to traj states.
    
    Keyword arguments:
    trajectories -- global list of all trajectories
    barcodes     -- global list of all barcodes
    colorids     -- global colorid database created by parse_colorid_file()
    kkkk         -- optional param to restrict algo for only one coloridindex

    """
    chosen = 0
    deleted = 0
    if kkkk is None:
        klist = range(len(colorids))
    else:
        klist = [kkkk]
    for k in klist:
        # deleted
        for traj in trajectories[k]:
            if traj.state != STATE_CHOSEN:
                # mark all barcodes contained by not chosen trajectories with deleted flag
                currentframe = traj.firstframe
                for bi in traj.barcodeindices:
                    barcode = barcodes[currentframe][k][bi]
                    if barcode.mfix and not (barcode.mfix & MFIX_DELETED):
                        barcode.mfix |= MFIX_DELETED
                        deleted += 1
                    currentframe += 1
        # chosen
        for traj in trajectories[k]:
            if traj.state == STATE_CHOSEN:
                # mark all barcodes contained by chosen trajectories with chosen flag
                currentframe = traj.firstframe
                for bi in traj.barcodeindices:
                    barcode = barcodes[currentframe][k][bi]
                    barcode.mfix &= ~MFIX_DELETED
                    barcode.mfix |= MFIX_CHOSEN
                    chosen += 1
                    currentframe += 1

    return (chosen, deleted)


def finalize_trajectories(trajectories, trajsonframe, barcodes, blobs, colorids):
    """Finalize trajectories, make them continuous throughout the whole video.

    Cleanup algos:
OK  1. Extend/elongate all chosen in both temporal directions
       TODO: get info from another video
       TODO: change algo to recursive chain type...
OK  2. Fill all remaining gaps with virtual barcodes
    3. Go through all chosen (and virtual) and add blobs if they belong to barcode
        if blobs are shared:
            i) if only this is chosen, delete other barcode
            ii) if both are chosen, try to find another blob around that is not used
OK  4. Mark barcodes as chosen/deleted and perform basic position and orientation
        smoothing on partlyfound blobs between full blobs.
        TODO: what to do with initialized, forced to end, etc. trajs and barcodes?

    Keyword arguments:
    trajectories -- global list of all trajectories
    trajsonframe -- global list of trajectory indices per frame per coloridindex
    barcodes     -- global list of all barcodes
    blobs        -- global list of all blobs
    colorids     -- global colorid database created by parse_colorid_file()

    Function returns number of (chosen, deleted) barcodes
    and writes to keyword parameters barcodes and trajectories.

    """

    # TODO: go through all frames, include nub to barcodes,
    # include n.u. barcodes to missing ones, etc.
    # assign possibility to location of all barcodes on all frames

    print("  Extending chosen trajs with not yet chosen in both temporal directions...")
    (virtual, rebirth) = extend_chosen_trajs(trajectories, trajsonframe, colorids, barcodes, blobs)
    print("    new virtual barcodes:", virtual, " barcodes reanimated:", rebirth)

    # list meta trajs
    print("  List meta trajs and gaps between...")
    list_meta_trajs(trajectories, trajsonframe, barcodes, colorids, blobs)

    print("  Filling gaps between chosen trajectories with virtual barcodes...")
    virtual = add_virtual_barcodes_to_gaps(trajectories, trajsonframe, colorids, barcodes)
    print("    virtual barcodes:", virtual)

    # list meta trajs
    print("  List meta trajs and gaps between...")
    list_meta_trajs(trajectories, trajsonframe, barcodes, colorids, blobs)

    # try to include not used blobs and not used barcodes to virtual barcodes
    print("  Enhance virtual barcodes with not used barcodes/blobs...")
    # TODO: too slow
    changes = enhance_virtual_barcodes(trajectories, trajsonframe, colorids, barcodes, blobs)
    print("    number of changes:", changes)

#    print("  Smooth final trajectories (TODO: good algo not implemented yet)...")
#    changes = smooth_final_trajectories(trajectories, trajsonframe, barcodes, colorids, blobs)
#    print("    number of changes:", changes)

