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
 - recalculate position of MFix.VIRTUALs between better ones once a virtual is turned into a better one (possibly in enhance_virtuals)

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
from math import pi
from typing import List, Optional, Union

from .init import MFix, TrajState, Barcode, Trajectory, Connections
from .algo import get_distance, get_distance_at_position, is_point_inside_ellipse
from .settings import TrajognizeSettingsBase

from . import algo_barcode
from . import algo_blob


def trajlastframe(traj):
    """Return the last frame number of a trajectory.

    Keyword arguments:
    traj -- a trajectory

    """
    return traj.firstframe + len(traj.barcodeindices) - 1


def append_barcode_to_traj(
    traj, trajsonframe, trajindex, barcode, barcodeindex, strid, blobs
):
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
    if barcode.mfix & MFix.FULLFOUND:
        traj.fullfound_count += 1
        # adjust fullnocluster_count
        if barcode.mfix & MFix.FULLNOCLUSTER:
            traj.fullnocluster_count += 1
    # adjust sharesblob count
    if barcode.mfix & MFix.SHARESBLOB:
        traj.sharesblob_count += 1
    # adjust colorblob_count
    for i in range(len(strid)):
        for i, blobi in enumerate(barcode.blobindices):
            if blobi is None:
                continue
            traj.colorblob_count[i] += 1
    # TODO: add more parameters that define the score of the trajectory


def start_new_traj(
    trajectories, trajsonframe, currentframe, k, barcode, barcodeindex, strid, blobs
):
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
    trajectories[k].append(Trajectory(currentframe, k, len(strid)))
    ti = len(trajectories[k]) - 1
    append_barcode_to_traj(
        trajectories[k][ti],
        trajsonframe[currentframe][k],
        ti,
        barcode,
        barcodeindex,
        strid,
        blobs,
    )


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
            if traj.state == TrajState.DELETED or traj.state == TrajState.CHANGEDID:
                count -= 1
            else:
                avg_length += len(traj.barcodeindices)
    if count:
        return (count, int(avg_length / count))
    else:
        return (0, 0)


def barcode_fits_to_trajlast(
    lastbarcode,
    barcode,
    lastmd_blobs,
    md_blobs,
    lastmdindices,
    mdindices,
    project_settings,
):
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
    project_settings -- global project-specific settings

    """
    d = get_distance(lastbarcode, barcode)
    # very close, trivial to add
    if d <= project_settings.MAX_PERFRAME_DIST:
        return True
    # bit further away, check md blobs and correct with their position change
    if d <= project_settings.MAX_PERFRAME_DIST_MD:
        mdblob = None
        for i in barcode.blobindices:
            if i is None:
                continue
            if mdindices[i] > -1:
                mdblob = md_blobs[mdindices[i]]
                break
        lastmdblob = None
        for i in lastbarcode.blobindices:
            if i is None:
                continue
            if lastmdindices[i] > -1:
                lastmdblob = lastmd_blobs[lastmdindices[i]]
                break
        # both frames contain motion blob, higher threshold is satisfactory,
        # there are rarely any motion blobs closer than MAX_PERFRAME_DIST_MD
        if mdblob and lastmdblob:
            return True
        # only last frame contains motion blob, check if current is inside it
        if lastmdblob and is_point_inside_ellipse(barcode, lastmdblob):
            return True
        # only current frame contains motion blob, check if last is inside it
        if mdblob and is_point_inside_ellipse(lastbarcode, mdblob):
            return True

    return False


def initialize_trajectories(
    trajectories,
    trajsonframe,
    barcodes,
    blobs,
    currentframe,
    project_settings,
    md_blobs,
    mdindices,
):
    """Initialize trajectories by adding barcodes of current frame
    to existing trajectories ending on last frame.

    Function should be called for each frame one by one to work properly.
    If there are multiple ongoing paths (barcodes) for a trajectory, they are
    branching, but one barcode can be part of only one trajectory to avoid
    combinatorical explosion.

    Keyword arguments:
    trajectories -- global list of all trajectories
    trajsonframe -- global list of trajectory indices per frame per coloridindex
    barcodes     -- global list of all barcodes
    blobs        -- global list of all color blobs
    currentframe -- current frame
    project_settings -- global project-specific settings
    md_blobs    -- global list of all motion blobs
    mdindices   -- global list of motion blob index for all blobs

    Function does not return a value but writes to keyword parameters
    trajectories and trajsonframe (and does not write barcodes yet).

    """
    colorids = project_settings.colorids
    # if this is the first frame, initialize one trajectory with each barcode
    if currentframe == 0:
        for k, strid in enumerate(colorids):
            for i, barcode in enumerate(barcodes[currentframe][k]):
                if not barcode.mfix or (barcode.mfix & MFix.DELETED):
                    continue
                start_new_traj(
                    trajectories,
                    trajsonframe,
                    currentframe,
                    k,
                    barcode,
                    i,
                    strid,
                    blobs[currentframe],
                )
        return

    # if not first frame, try to append barcodes to existing trajectories
    for k, strid in enumerate(colorids):
        for i, barcode in enumerate(barcodes[currentframe][k]):
            if not barcode.mfix or (barcode.mfix & MFix.DELETED):
                continue
            found = 0
            # irerate trajectories of the last frame
            for trajindex in trajsonframe[currentframe - 1][k]:
                # if found a good one, add to existing trajectory
                traj = trajectories[k][trajindex]
                if trajindex in trajsonframe[currentframe][k]:
                    lastbarcode = barcodes[currentframe - 1][k][traj.barcodeindices[-2]]
                else:
                    lastbarcode = barcodes[currentframe - 1][k][traj.barcodeindices[-1]]
                if traj.state == TrajState.INITIALIZED and barcode_fits_to_trajlast(
                    lastbarcode,
                    barcode,
                    md_blobs[currentframe - 1],
                    md_blobs[currentframe],
                    mdindices[currentframe - 1],
                    mdindices[currentframe],
                    project_settings,
                ):
                    found += 1
                    if trajindex not in trajsonframe[currentframe][k]:
                        # if not added yet (no split), add barcode to existing trajectory
                        if found == 1:
                            append_barcode_to_traj(
                                traj,
                                trajsonframe[currentframe][k],
                                trajindex,
                                barcode,
                                i,
                                strid,
                                blobs[currentframe],
                            )
                        else:
                            # if this barcode has already been added elsewhere,
                            # we simply do not add it any more

                            # TODO: check which traj is better for this barcode
                            # and keep it only there
                            pass
                    # if traj is already being appended by another barcode,
                    # we treat it as a split in the trajectory
                    else:
                        # if this barcode is not added anywhere yet,
                        # we start a new branch on it
                        if found == 1:
                            # start new trajectory from new index
                            start_new_traj(
                                trajectories,
                                trajsonframe,
                                currentframe,
                                k,
                                barcode,
                                i,
                                strid,
                                blobs[currentframe],
                            )
                        # if this barcode has already been used in another traj,
                        # we simply do not add it again
                        else:
                            pass

            # if no trajectories found where this barcode can fit, start a new one
            if not found:
                start_new_traj(
                    trajectories,
                    trajsonframe,
                    currentframe,
                    k,
                    barcode,
                    i,
                    strid,
                    blobs[currentframe],
                )


def traj_score(
    traj: Trajectory,
    MCHIPS: int,
    method: int = 1,
    k: Optional[int] = None,
    kk: Optional[int] = None,
    calculate_deleted: bool = True,
):
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

    Parameters:
        traj: a trajectory
        MCHIPS: number of chips / bins in a barcode
        method: 1 or 2, depending on what arbitrary method you need
        k: dst coloridindex of scoring (same as kk in default)
        kk: src coloridindex of the traj
        calculate_deleted: should we calculate score for deleted traj?

    """
    if not calculate_deleted and traj.state == TrajState.DELETED:
        return 0

    # if the score is calculated for the trajs color (default case):
    if k == kk:
        if method == 1:
            return (
                len(traj.barcodeindices)
                + sum(traj.colorblob_count)
                + (
                    traj.fullfound_count
                    - traj.sharesblob_count
                    + 2 * traj.fullnocluster_count
                )
                / 3
                + traj.offset_count
            )
        elif method == 2:
            return max(
                0,
                (
                    traj.fullfound_count
                    - traj.sharesblob_count
                    + traj.fullnocluster_count
                )
                / 2
                + traj.offset_count,
            )
        else:
            raise NotImplementedError("unhandled traj score method: {}".format(method))

    # if it is calculated for another color:
    else:
        # score is proportional to the average diff between least and others,
        # but should not be too high
        least = index_of_least_color(traj)
        score = (sum(traj.colorblob_count) - MCHIPS * traj.colorblob_count[least]) / (
            MCHIPS - 1
        )
        if method == 1:
            return (
                len(traj.barcodeindices)
                + (score - traj.sharesblob_count) / 3
                + traj.offset_count
            )
        elif method == 2:
            return max(0, (score - traj.sharesblob_count) / 3 + traj.offset_count)
        else:
            raise NotImplementedError("unhandled traj score method: {}".format(method))


def is_traj_good(traj, MCHIPS, traj_score_method, threshold=50):
    """Return True if trajectory is assumed to be a good one
    and False if it assumed to be a false positive detection.

    Keyword arguments:
    traj      -- a trajectory
    MCHIPS    -- number of chips / bins in a barcode
    traj_score_method -- param inherited from project_settings
    threshold -- above which the trajectory is assumed to be good

    Threshold default value of 50 is 2sec recognition, filters out most of the
    false positives. Bads are usually <20,30,40, but sometimes larger than 100,
    goods can be very small but above 100 are generally good 50 looks like a
    good compromise, but be prepared for false positives!

    """

    if traj_score(traj, MCHIPS, traj_score_method) >= threshold:
        return True
    else:
        return False


def get_chosen_neighbor_traj_perframe(
    traj, trajectories, trajsonframe, k, forward=True, framelimit=1500
):
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
            firstframe = trajlastframe(traj) + 1
        if framelimit is None:
            lastframe = len(trajsonframe) - 1
        else:
            lastframe = min(firstframe + framelimit - 1, len(trajsonframe) - 1)
        for frame in range(firstframe, lastframe + 1):
            for i in trajsonframe[frame][k]:
                trajx = trajectories[k][i]
                if trajx.state == TrajState.CHOSEN and trajx.firstframe == frame:
                    return i
        return -1

    # backward in time
    else:
        if traj is None:
            lastframe = len(trajsonframe) - 1
        else:
            lastframe = traj.firstframe - 1
        if framelimit is None:
            firstframe = 0
        else:
            firstframe = max(lastframe - framelimit + 1, 0)
        for frame in range(lastframe, firstframe - 1, -1):
            for i in trajsonframe[frame][k]:
                trajx = trajectories[k][i]
                if trajx.state == TrajState.CHOSEN and trajlastframe(trajx) == frame:
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

        for i, trajx in enumerate(trajs):
            if trajx.state != TrajState.CHOSEN:
                continue
            j = trajx.firstframe
            if j > lastframe and j < beststart:
                bestindex = i
                beststart = j
        return bestindex

    # backward in time
    else:
        if traj is None:
            raise ValueError("traj=None not compatible with backward mode." "")
        firstframe = traj.firstframe
        bestindex = -1
        if framelimit is None:
            bestend = -1
        else:
            bestend = firstframe - framelimit
        for i, trajx in enumerate(trajs):
            if trajx.state != TrajState.CHOSEN:
                continue
            j = trajlastframe(trajx)
            if j < firstframe and j > bestend:
                bestindex = i
                bestend = j
        return bestindex


def index_of_least_color(traj):
    """Return the index of the color with the least match in the trajectory.

    Keyword arguments:
        traj -- a trajectory

    """
    least = min(traj.colorblob_count)
    return traj.colorblob_count.index(least)


def could_be_another_colorid(traj, fromk, tok, colorids):
    """Return true if the given trajectory could be a false positive detection
    and thus would be suitable for another colorid.

    Criteria:
    - traj state is DELETED
    - traj is not marked yet as CHANGEDID (traj.k != k)
    - there is MCHIPS-1 token overlap in the two strids
    - the color not matching has the least occurrence in traj

    Note that we assume that there are no palindromes in strids.

    Keyword arguments:
    traj      -- the trajectory to check
    fromk     -- the original colorid index
    tok       -- the new colorid index
    colorids  -- global colorid database

    """
    MCHIPS = len(colorids[0])
    # check deleted state
    if traj.state != TrajState.DELETED:
        return False
    # check whether already marked to switch to a colorid
    if traj.k != fromk:
        return False
    # get strids
    fromstrid = colorids[fromk]
    tostrid = colorids[tok]
    # check for at least MCHIPS-1 long token overlap in the two strids
    ii = None
    if fromstrid[:-1] in tostrid or fromstrid[:-1] in tostrid[::-1]:
        ii = MCHIPS - 1
    elif fromstrid[1:] in tostrid or fromstrid[1:] in tostrid[::-1]:
        ii = 0
    if ii is None:
        return False
    # check number of occurrences in old traj
    if index_of_least_color(traj) != ii:
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
    if not samecolor:
        return 50
    return min(100, 50 + abs(frameb - framea) * 5)


def connect_chosen_trajs(
    traja: Trajectory,
    trajb: Union[Trajectory, str],
    k: int,
    trajectories: List[List[Trajectory]],
    trajsonframe: List[List[int]],
    barcodes: List[List[List[Barcode]]],
    project_settings: TrajognizeSettingsBase,
    framelimit: int = 1500,
    connections: Optional[Connections] = None,
    index: int = -1,
    level: int = 0,
):
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
    project_settings -- global project-specific settings
    framelimit   -- maximum number of frames to look for (in case of extention mode)
                    this is needed due to the possible high number of recursions
                    and thus slow running time
    connections  -- Connections() object containing the list of connections
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

    # print(
    #     "traja",
    #     traja.firstframe,
    #     len(traja.barcodeindices),
    #     traja.state,
    #     "trajb",
    #     trajb,
    #     "k",
    #     k,
    #     "trajs",
    #     len(trajectories[k]),
    #     "conns",
    #     len(connections.data if connections is not None else []),
    #     "index",
    #     index,
    #     "level",
    #     level,
    #     "framelimit",
    #     framelimit,
    # )

    # initialize
    colorids = project_settings.colorids
    MCHIPS = project_settings.MCHIPS
    mode = "c"  # connect
    inc = 1  # increment (1 forward, -1 backward)
    neigh = -1
    if isinstance(trajb, str):
        if trajb == "forward":
            mode = "f"  # forward
        elif trajb == "backward":
            mode = "b"  # backward
            inc = -1
        else:
            raise ValueError(
                "trajb should be of Trajectory or 'forward' or 'backward' if string"
            )
    # TODO: should be or should not be a switch to connection mode from forward/backward
    # if a chosen neighbor is found in the vicinity? So far there is no switch.
    if mode == "b":
        fromframe = traja.firstframe - 1
        neigh = get_chosen_neighbor_traj(traja, trajectories[k], False, framelimit)
        if neigh == -1:
            toframe = max(0, fromframe - framelimit + 1)
        else:
            toframe = trajlastframe(trajectories[k][neigh]) + 1
        if fromframe < toframe:
            return None  # add no more to this
    elif mode == "f":
        fromframe = trajlastframe(traja) + 1
        neigh = get_chosen_neighbor_traj(traja, trajectories[k], True, framelimit)
        if neigh == -1:
            toframe = min(len(barcodes) - 1, fromframe + framelimit - 1)
        else:
            toframe = trajectories[k][neigh].firstframe - 1
        if fromframe > toframe:
            return None  # add no more to this
    elif mode == "c":
        assert not isinstance(trajb, str)
        fromframe = trajlastframe(traja) + 1
        toframe = trajb.firstframe - 1
        if fromframe > toframe:
            return None  # add no more to this
    else:
        raise NotImplementedError("Unknown mode: {}".format(mode))
    # TODO: traja.k is used which should be the k for a (and not yet changed)
    # but might be buggy if a later connection is different from a previous one
    barcodefrom = barcodes[fromframe - inc][traja.k][
        traja.barcodeindices[-(inc + 1) // 2]
    ]

    # initialize connections object
    # this is needed because of this: http://effbot.org/zone/default-values.htm
    lastconn = []
    if level == 0:
        connections = Connections(toframe)
        index = -1

    #    print(mode, colorids[k], "level", level, "f%d-%d" % (fromframe, toframe), "flimit", framelimit, "fflimit", connections.fromframelimit, "Nconns", len(connections.data))

    # avoid getting into too deep recursions and also define stricter first frame
    # limit if there are too many recursions. This level should be the last.
    if level > min(200, 2 * sys.getrecursionlimit() // 10):
        connections.recursionlimitreached = True
        if mode == "b":
            connections.fromframelimit = max(
                connections.fromframelimit, trajlastframe(traja)
            )
        else:
            connections.fromframelimit = min(
                connections.fromframelimit, traja.firstframe
            )
        #        print("  recursion limit reached, setting new fflimit", connections.fromframelimit)
        return None

    ############################################################################
    # iterate all frames between traja and trajb to find all candidate
    # connections recursively
    for frame in range(fromframe, toframe + inc, inc):
        # iterate all colorids
        for kk in range(len(colorids)):
            #            # skip other colorids when only elongating
            #            if mode != 'c' and k != kk: continue
            # iterate trajectories on current frame
            for i in trajsonframe[frame][kk]:
                # simplify notation
                trajx = trajectories[kk][i]
                # skip ones not starting/ending here and starting/ending after
                if mode == "b":
                    fromxframe = trajlastframe(trajx)
                    toxframe = trajx.firstframe
                    if fromxframe < connections.fromframelimit:
                        continue
                    if fromxframe != frame:
                        continue
                    if toxframe < toframe:
                        continue
                else:
                    fromxframe = trajx.firstframe
                    toxframe = trajlastframe(trajx)
                    if fromxframe > connections.fromframelimit:
                        continue
                    if fromxframe != frame:
                        continue
                    if toxframe > toframe:
                        continue
                # if different color, check suitability
                if k != kk:
                    if not could_be_another_colorid(trajx, kk, k, colorids):
                        continue
                # if same color, check state. Connection is allowed between non-deleted,
                # extention can be with deleted as well. TODO: is that the best way?
                else:
                    if mode == "c":
                        if trajx.state == TrajState.DELETED:
                            continue
                    if trajx.state == TrajState.CHANGEDID or trajx.k != kk:
                        continue
                    if trajx.state == TrajState.CHOSEN:
                        print("Warning, something is buggy. state is already CHOSEN")
                # skip ones far away
                if get_distance(
                    barcodefrom,
                    barcodes[frame][kk][trajx.barcodeindices[(inc - 1) // 2]],
                ) > max_allowed_dist_between_trajs(fromframe - inc, frame, k == kk):
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
                for ii in range(len(connections.data)):
                    conn = connections.data[ii]
                    # if new ending was already used
                    if (kk, i) in conn:
                        m = conn.index((kk, i))
                        # calculate old score
                        scoreold = 0
                        for (kkk, jj) in conn[0:m]:
                            scoreold += traj_score(
                                trajectories[kkk][jj],
                                MCHIPS,
                                project_settings.traj_score_method,
                                k,
                                kkk,
                            )
                        # calculate new score
                        scorenew = 0
                        for (kkk, jj) in tempconn:
                            scorenew += traj_score(
                                trajectories[kkk][jj],
                                MCHIPS,
                                project_settings.traj_score_method,
                                k,
                                kkk,
                            )
                        # skip new
                        if (
                            scoreold >= scorenew
                        ):  # TODO more checking on egalitarian state
                            cont = True
                            break
                        # delete old
                        else:
                            del connections.data[ii]
                            if index > ii:
                                index -= 1
                            break
                if cont:
                    continue

                ########## no more checking, candidate is OK ###########
                # initialize chain if it has not been done before
                if index == -1:
                    connections.data.append(lastconn)
                    index = len(connections.data) - 1
                # store last connection for next possible chain
                lastconn = list(connections.data[index])
                # store good one as candidate for connection (check close end later)
                connections.data[index].append((kk, i))

                # find connection between new one and last
                # print("  found", colorids[k], "level", level, "f%d-%d" % (trajx.firstframe, trajlastframe(trajx)), "newflimit", framelimit - inc*(toxframe - (fromframe - inc)), "fflimit", connections.fromframelimit, "Nconns", len(connections.data))
                connect_chosen_trajs(
                    trajx,
                    trajb,
                    k,
                    trajectories,
                    trajsonframe,
                    barcodes,
                    project_settings,
                    framelimit - inc * (toxframe - (fromframe - inc)),
                    connections,
                    index,
                    level + 1,
                )
                # after returning from chain, reset index for next chain
                index = -1

    ############################################################################
    ############################################################################
    # this part executes only after all candidate connections have been found
    if level:
        return None
    if not connections.data:
        #        if neigh != -1: # mode 'f' or 'b'
        #            # check if there are any trajs between them at all
        #            # this could happen in some not handled cases when both trajs
        #            # from both sides are elongated but they are not connected yet
        #            # with virtuals
        #            for frame in range(fromframe, toframe + inc, inc):
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
        scores = [0 for i in range(len(connections.data))]
        for i in range(len(connections.data)):
            conn = connections.data[i]
            if not conn:
                scores[i] = -1
                continue
            for (kk, j) in conn:
                trajx = trajectories[kk][j]
                if mode == "b":
                    if trajlastframe(trajx) < connections.fromframelimit:
                        break
                else:
                    if trajx.firstframe > connections.fromframelimit:
                        break
                scores[i] += traj_score(
                    trajx, MCHIPS, project_settings.traj_score_method, k, kk
                )
        # choose best (reverse sort according to total score) and continue search
        # using this as beginning
        si = sorted(
            list(range(len(connections.data))), key=lambda x: scores[x], reverse=True
        )
        if mode == "b":
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
        print(
            "Warning: recursion limit reached during search, selecting best conn-part so far and starting new part..."
        )
        print(
            " ",
            mode,
            colorids[k],
            "level",
            level,
            "from-to",
            "%d-%d" % (fromframe, toframe),
            "flimit",
            framelimit,
            "fflimit",
            connections.fromframelimit,
            "Nconns",
            len(connections.data),
        )
        conn = connect_chosen_trajs(
            trajx,
            trajb,
            k,
            trajectories,
            trajsonframe,
            barcodes,
            project_settings,
            framelimit - inc * (nextfromxframe - fromframe),
        )
        if conn:
            #           print("conn+", [(colorids[kk], ii, trajectories[kk][ii].firstframe, trajlastframe(trajectories[kk][ii])) for (kk, ii) in tempconn + conn])
            return tempconn + conn

    ############################################################################
    # skip connections that do not end at the right place
    if mode == "c":
        good = 0
        barcodeto = barcodes[toframe + 1][k][trajb.barcodeindices[0]]
        for i in range(len(connections.data)):
            conn = connections.data[i]
            (kk, j) = conn[-1]
            trajx = trajectories[kk][j]
            toxframe = trajlastframe(trajx)
            if get_distance(
                barcodeto, barcodes[toxframe][kk][trajx.barcodeindices[-1]]
            ) > max_allowed_dist_between_trajs(toxframe, toframe + inc, k == kk):
                connections.data[i] = []
            else:
                good += 1
        if not good:
            return None

    # calculate total score for all connections
    scores = [0 for i in range(len(connections.data))]
    for i in range(len(connections.data)):
        conn = connections.data[i]
        if not conn:
            scores[i] = -1
            continue
        for (kk, j) in conn:
            scores[i] += traj_score(
                trajectories[kk][j], MCHIPS, project_settings.traj_score_method, k, kk
            )

    # choose best (reverse sort according to total score) and return
    si = sorted(
        list(range(len(connections.data))), key=lambda x: scores[x], reverse=True
    )

    # In case of pure extention, if there is a chosen neighbor,
    # we check if selected connection ends there. If so, we include neighbor
    # to the connection to be filled with virtuals in between.
    # TODO: it might be better to check for closeness before selecting best
    #       but I am lazy to do it now...
    # TODO: also check for very large temporal distance if needed...
    if neigh != -1:
        trajbb = trajectories[k][neigh]  # neighbor
        (kk, j) = connections.data[si[0]][-1]  # last element of best conn
        trajx = trajectories[kk][j]
        if mode == "b":
            fromxframe = trajx.firstframe
            tobframe = trajlastframe(trajbb)
        else:  # mode 'f'
            fromxframe = trajlastframe(trajx)
            tobframe = trajbb.firstframe
        if get_distance(
            barcodes[tobframe][k][trajbb.barcodeindices[(inc - 1) // 2]],
            barcodes[fromxframe][kk][trajx.barcodeindices[-(inc + 1) // 2]],
        ) <= max_allowed_dist_between_trajs(fromxframe, toframe + inc, k == kk):
            connections.data[si[0]].append((k, neigh))

    #    if colorids[k] in ["GOP"]:
    #        print("helo", colorids[k], "mode", mode, "conn", connections.data[si[0]], "%d-%d" % (fromframe, toframe))

    if mode == "b":
        # return reverse list (backward backward == forward)
        #        print("connb", [(colorids[kk], ii, trajectories[kk][ii].firstframe, trajlastframe(trajectories[kk][ii])) for (kk, ii) in connections.data[si[0]][::-1]])
        return connections.data[si[0]][::-1]
    else:
        #        print("connfc", [(colorids[kk], ii, trajectories[kk][ii].firstframe, trajlastframe(trajectories[kk][ii])) for (kk, ii) in connections.data[si[0]]])
        return connections.data[si[0]]


def mark_traj_chosen(
    trajectories, k, i, trajsonframe, colorids, barcodes, blobs, kk=None
):
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
    colorids     -- global colorid database
    barcodes     -- global list of all barcodes
    blobs        -- global list of all color blobs
    kk           -- destination coloridindex (not used in default)

    Returns number of deleted, or -1 if self is deleted.

    """
    traj = trajectories[k][i]
    deleted = 0
    if kk is None:
        kk = k
    if traj.k != k:
        print(
            "Warning, something bad happened (%s i%d f%d-%d) traj.k (%s) != k (%s). kk is %s!!!"
            % (
                colorids[k],
                i,
                traj.firstframe,
                trajlastframe(traj),
                colorids[traj.k],
                colorids[k],
                colorids[kk],
            )
        )
        raise ValueError
        return -1

    chosenoverlap = set()  # set of trajs overlapping as chosen
    deleteoverlap = set()  # set of trajs overlapping to be deleted
    # gather overlapping traj info
    for currentframe in range(traj.firstframe, trajlastframe(traj) + 1):
        for j in trajsonframe[currentframe][kk]:
            if j == i:
                continue
            trajx = trajectories[kk][j]
            if trajx.state == TrajState.CHOSEN:
                # this happens if a previously established connection did not include
                # this traj but this traj's score is good enough to be chosen.
                chosenoverlap.add((kk, j))
            elif (
                trajx.state != TrajState.DELETED and trajx.state != TrajState.CHANGEDID
            ):
                deleteoverlap.add((kk, j))

    # check for overlapping already chosen
    if chosenoverlap:
        for (kkk, j) in chosenoverlap:
            trajx = trajectories[kkk][j]
            print(
                "  Warning: overlapping chosen trajs found (dst %s)." % colorids[kk],
                end=" ",
            )
            print(
                "old:",
                colorids[trajx.k],
                "%d-%d," % (trajx.firstframe, trajlastframe(trajx)),
                end=" ",
            )
            print(
                "new:",
                colorids[traj.k],
                "%d-%d, Deleting new." % (traj.firstframe, trajlastframe(traj)),
            )
        traj.state = TrajState.DELETED
        return -1

    # check for overlapping others that are to be deleted
    if deleteoverlap:
        for (kkk, j) in deleteoverlap:
            trajx = trajectories[kkk][j]
            trajx.state = TrajState.DELETED
            deleted += 1

            # decrease traj score offset if overlapping is also sharedblob (we chose this so other is bad "for sure")
            # get common frame range
            for frame in range(
                max(traj.firstframe, trajx.firstframe),
                min(trajlastframe(traj) + 1, trajlastframe(trajx) + 1),
            ):
                # define good barcode
                barcode = barcodes[frame][k][
                    traj.barcodeindices[frame - traj.firstframe]
                ]
                # get overlapping bad barcode index
                bxi = trajx.barcodeindices[frame - trajx.firstframe]
                # check if they share a blob and if so, decrease bad trajs offset
                for blobi in barcode.blobindices:
                    if blobi is None:
                        continue
                    if bxi in blobs[frame][blobi].barcodeindices:
                        trajx.offset_count -= 1
                        break

    # mark self as CHOSEN (if dst colorid is the same as src)
    if kk == k:
        traj.state = TrajState.CHOSEN
    # or mark for changedid (which will come at a later stage)
    # if dst color is different from src
    else:
        traj.k = kk

    return deleted


def change_colorid(trajectories, k, i, trajsonframe, barcodes, project_settings, blobs):
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
    project_settings -- global project-specific settings
    blobs        -- global list of all color blobs


    """
    # initialize (assuming that traj.k has been set to mark color change)
    colorids = project_settings.colorids
    traj = trajectories[k][i]
    traj.state = TrajState.CHANGEDID
    kk = traj.k
    strid = colorids[k]
    newstrid = colorids[kk]
    MCHIPS = len(strid)
    # check which part should be kept and how
    # We assume that color change was checked with could_be_another_colorid()
    # TODO: we do not yet treat the case of MCHIPS - 1 palindromes, for this
    # we will fail in 50% of the cases with 180 deg disorientation!!!
    if strid[1:] in newstrid:
        reverse = False
        fromc = 0
        toc = 0 if newstrid.index(strid[1:]) else MCHIPS - 1
    elif strid[1:] in newstrid[::-1]:
        reverse = True
        fromc = 0
        toc = 0 if newstrid[::-1].index(strid[1:]) else MCHIPS - 1
    elif strid[:-1] in newstrid:
        reverse = False
        fromc = MCHIPS - 1
        toc = 0 if newstrid.index(strid[:-1]) else MCHIPS - 1
    elif strid[:-1] in newstrid[::-1]:
        reverse = True
        fromc = MCHIPS - 1
        toc = 0 if newstrid[::-1].index(strid[:-1]) else MCHIPS - 1

    # create new barcodes and add them to new trajectory
    i = 0
    for frame in range(traj.firstframe, trajlastframe(traj) + 1):
        # initialize
        barcode = barcodes[frame][k][traj.barcodeindices[i]]
        barcodes[frame][kk].append(
            Barcode(
                barcode.centerx,
                barcode.centery,
                barcode.orientation,
                barcode.mfix,
                MCHIPS,
                list(barcode.blobindices),
            )
        )
        ii = len(barcodes[frame][kk]) - 1
        newbarcode = barcodes[frame][kk][ii]
        # change old barcode params (permanent deletion)
        barcode.mfix = 0  # |= (MFix.DELETED | MFix.CHANGEDID)
        # set new barcode params
        newbarcode.mfix = MFix.PARTLYFOUND_FROM_TDIST
        # chance blobindices
        del newbarcode.blobindices[fromc]
        newbarcode.blobindices.insert(toc, None)
        if reverse:
            newbarcode.blobindices = newbarcode.blobindices[::-1]
        algo_blob.update_blob_barcodeindices(newbarcode, kk, ii, blobs[frame])
        algo_barcode.calculate_params(
            newbarcode, newstrid, blobs[frame], project_settings.AVG_INRAT_DIST
        )
        # append barcode to new traj
        if i == 0:
            start_new_traj(
                trajectories,
                trajsonframe,
                frame,
                kk,
                newbarcode,
                ii,
                newstrid,
                blobs[frame],
            )
            newtraj = trajectories[kk][-1]
            newtrajindex = len(trajectories[kk]) - 1
        else:
            append_barcode_to_traj(
                newtraj,
                trajsonframe[frame][kk],
                newtrajindex,
                newbarcode,
                ii,
                newstrid,
                blobs[frame],
            )
        # iterate
        i += 1


def fill_connection_with_nub(
    conn, k, trajectories, trajsonframe, barcodes, colorids, blobs
):
    """Once a connection was estabilished, try to connect missing frames with
    not used barcodes, blobs, deleted barcodes, etc. In case of no success,
    create virtual barcodes to connect the gap.

    Keyword arguments:
    conn         -- the connection with (k,j) tuples of trajectory indices
    k            -- the colorid of the connection (not used yet, but might be)
    trajectories -- global list of all trajectories
    trajsonframe -- global list of trajectory indices per frame per coloridindex
    barcodes     -- global list of all barcodes
    colorids     -- global colorid database
    blobs        -- global list of all color blobs

    """
    MCHIPS = len(colorids[0])
    count_found = 0
    count_virtual = 0
    (oldkk, oldj) = (conn[0][0], conn[0][1])
    oldtraj = trajectories[oldkk][oldj]
    for (kk, j) in conn[1:]:
        traj = trajectories[kk][j]
        endframe = trajlastframe(oldtraj)
        startframe = traj.firstframe
        # if there is a gap, fill it with not used barcodes or with virtual ones
        if startframe - endframe > 1:
            oldbarcode = barcodes[endframe][oldtraj.k][oldtraj.barcodeindices[-1]]
            startbarcode = barcodes[startframe][traj.k][traj.barcodeindices[0]]
            # iterate all frames
            for frame in range(endframe + 1, startframe):
                found = False
                # search for (deleted) same color barcodes, possibly not part of traj
                mindist = max_allowed_dist_between_trajs()
                for bi in range(len(barcodes[frame][oldkk])):
                    if not algo_barcode.barcode_is_free(
                        barcodes[frame], oldkk, bi, blobs[frame]
                    ):
                        continue
                    barcode = barcodes[frame][oldkk][bi]
                    dist = get_distance(oldbarcode, barcode)
                    if dist < mindist and get_distance(
                        barcode, startbarcode
                    ) < max_allowed_dist_between_trajs(0, 0, oldkk == kk):
                        candidate = barcode
                        cbi = bi
                        mindist = dist
                if mindist < max_allowed_dist_between_trajs():
                    candidate.mfix &= ~MFix.DELETED
                    algo_blob.update_blob_barcodeindices(
                        candidate, oldkk, cbi, blobs[frame]
                    )
                    append_barcode_to_traj(
                        oldtraj,
                        trajsonframe[frame][oldkk],
                        oldj,
                        candidate,
                        cbi,
                        colorids[oldkk],
                        blobs[frame],
                    )
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
                    candidate = Barcode(
                        oldbarcode.centerx,
                        oldbarcode.centery,
                        oldbarcode.orientation,
                        MFix.VIRTUAL | MFix.CHOSEN,
                        MCHIPS,
                    )
                    barcodes[frame][oldkk].append(candidate)
                    append_barcode_to_traj(
                        oldtraj,
                        trajsonframe[frame][oldkk],
                        oldj,
                        candidate,
                        len(barcodes[frame][oldkk]) - 1,
                        colorids[oldkk],
                        blobs[frame],
                    )
                    count_virtual += 1
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
    #        print(kk, j, colorids[traj.k], "%d-%d" % (traj.firstframe, trajlastframe(traj)))

    return (count_found, count_virtual)


def enhance_virtual_barcodes(
    trajectories, trajsonframe, project_settings, barcodes, blobs
):
    """Try to add not used barcodes to virtual barcodes and not used blobs to
    all chosen barcodes (that already have blobs) to enhance their parameters.

    This functions should be called after fill_..._nub() which created the
    virtual barcodes first. Could be called on a later stage as well.

    Adds MFix.DEBUG on possible conflicts (overlapping virtuals, shared, etc.).

    Keyword arguments:
    trajectories -- global list of all trajectories
    trajsonframe -- global list of trajectory indices per frame per coloridindex
    project_settings -- global project-specific settings
    barcodes     -- blobal list of all barcodes
    blobs        -- global list of all color blobs

    """
    colorids = project_settings.colorids
    MCHIPS = len(colorids[0])
    changes = 0
    print("   ", end=" ")
    for k in range(len(colorids)):
        print(colorids[k], end=" ")
        # get first chosen traj
        i = get_chosen_neighbor_traj_perframe(
            None, trajectories, trajsonframe, k, True, None
        )
        while i != -1:
            traj = trajectories[k][i]
            frame = traj.firstframe
            for j in traj.barcodeindices:
                oldbarcode = barcodes[frame][k][j]
                # search around for (deleted) same colorid barcodes
                # for all new virtual barcodes (nothing assigned to them yet)
                if (oldbarcode.mfix & MFix.VIRTUAL) and oldbarcode.blobindices.count(
                    None
                ) == MCHIPS:
                    mindist = max_allowed_dist_between_trajs()
                    for bi in range(len(barcodes[frame][k])):
                        if bi == j:
                            continue
                        if not algo_barcode.barcode_is_free(
                            barcodes[frame], k, bi, blobs[frame]
                        ):  # TODO: first round: only deleted count or all? Not only deleted is not filtered out
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
                        oldbarcode.mfix = candidate.mfix
                        oldbarcode.mfix &= ~MFix.DELETED
                        # note that we do not need to remove old correspondences as there were none...
                        oldbarcode.blobindices = list(candidate.blobindices)
                        algo_blob.update_blob_barcodeindices(
                            oldbarcode, k, j, blobs[frame]
                        )
                        # permanently delete old candidate
                        candidate.mfix = 0  # |= MFix.DELETED
                        #                        oldbarcode.mfix &= ~MFix.VIRTUAL # TODO: might not be needed if further check on virtuals will be done
                        oldbarcode.mfix |= MFix.CHOSEN
                        algo_barcode.calculate_params(
                            oldbarcode,
                            colorids[k],
                            blobs[frame],
                            project_settings.AVG_INRAT_DIST,
                        )
                        if oldbarcode.mfix & MFix.FULLFOUND:
                            traj.fullfound_count += 1
                            if oldbarcode.mfix & MFix.FULLNOCLUSTER:
                                traj.fullnocluster_count += 1
                        # TODO: colorblob count + sharesblob count
                        changes += 1

                # search around for not used blobs (and choose best=closest for each color)
                # for all chosen barcodes (virtual and not virtual) that already have blobs
                # (i.e. they were based on a barcode at the beginning - this way
                # we avoid adding noise blobs to empty virtual barcodes)
                if (
                    oldbarcode.mfix & MFix.CHOSEN
                    and oldbarcode.blobindices.count(None) < MCHIPS
                ):
                    for bi, blobi in enumerate(oldbarcode.blobindices):
                        if blobi is not None:
                            continue
                        # find best not used blob as candidate
                        found = None
                        mindist = project_settings.MAX_INRAT_DIST
                        color = project_settings.color2int(colorids[k][bi])
                        for ii in range(len(blobs[frame])):
                            blob = blobs[frame][ii]
                            if algo_blob.barcodeindices_not_deleted(
                                blob.barcodeindices, barcodes[frame]
                            ):
                                continue
                            if blob.color != color:
                                continue
                            dist = get_distance_at_position(
                                oldbarcode, bi, blob, project_settings.AVG_INRAT_DIST
                            )
                            if dist < mindist:
                                found = ii
                                mindist = dist
                        # add best found not used blob
                        if found is not None:
                            oldbarcode.blobindices[bi] = found
                            algo_blob.update_blob_barcodeindices(
                                oldbarcode, k, j, blobs[frame]
                            )
                            traj.colorblob_count[bi] += 1
                            # set new params
                            changes += 1
                            if None not in oldbarcode.blobindices:
                                oldbarcode.mfix &= ~MFix.PARTLYFOUND_FROM_TDIST
                                oldbarcode.mfix |= MFix.FULLFOUND
                                traj.fullfound_count += 1
                                # TODO: fullnocluster_count is not increased here yet, nor sharesblob count...
                            else:
                                oldbarcode.mfix |= MFix.PARTLYFOUND_FROM_TDIST
                            #                            oldbarcode.mfix &= ~MFix.VIRTUAL # TODO: might not be needed if further check on virtuals will be done
                            algo_barcode.calculate_params(
                                oldbarcode,
                                colorids[k],
                                blobs[frame],
                                project_settings.AVG_INRAT_DIST,
                            )
                # iterate to next frame
                frame += 1
            # get next chosen traj
            i = get_chosen_neighbor_traj_perframe(
                traj, trajectories, trajsonframe, k, True, None
            )
    print()
    return changes


def choose_and_connect_trajs(
    si,
    score_threshold,
    trajectories,
    trajsonframe,
    project_settings,
    barcodes,
    blobs,
    kkkk=None,
    framelimit=1500,
):
    """Helper algo for find_best_trajectories(). Name speaks for itself.

    Keyword arguments:
    si              -- (k, i) index of all trajectories in a sorted list (good scores first)
    score_threshold -- minimum score for good trajectories
    trajectories    -- global list of all trajectories
    trajsonframe    -- global list of trajectory indices per frame per coloridindex
    project_settings -- global project-specific settings
    barcodes        -- global list of all barcodes
    blobs           -- global list of all color blobs
    kkkk            -- optional param to restrict algo for only one coloridindex
    framelimit      -- optional param to define frame limit of traj extentions

    """
    # initialize
    colorids = project_settings.colorids
    chosen = 0
    deleted = 0
    connected = 0
    virtual = 0
    rebirth = 0
    deletedgood = []
    changedcolor = []
    MCHIPS = project_settings.MCHIPS
    # iterate all trajectories
    print("\n  Scores of chosen:", end=" ")
    for i in range(len(si)):
        k = si[i][0]
        ii = si[i][1]
        traj = trajectories[k][ii]
        # end iteration if traj is not good any more
        if not is_traj_good(
            traj,
            MCHIPS,
            project_settings.traj_score_method,
            score_threshold + traj.offset_count,
        ):
            break
        print(
            traj_score(traj, MCHIPS, project_settings.traj_score_method),
            colorids[k],
            "i%d s%d (%d-%d)," % (ii, traj.state, traj.firstframe, trajlastframe(traj)),
            end=" ",
        )
        # skip ones that look good, but are already deleted (by better ones or due to changed score)
        if traj.state == TrajState.DELETED:
            deletedgood.append(
                (
                    colorids[k],
                    traj_score(traj, MCHIPS, project_settings.traj_score_method),
                )
            )
            continue
        # and also skip ones that were chosen for another colorid
        if (
            traj.state == TrajState.CHANGEDID or traj.k != k
        ):  # actually second should not occur here yet
            print(
                "\n  Warning: changed %s traj colorid to %s with score %d, colorblob_count: %s,"
                % (
                    colorids[k],
                    colorids[traj.k],
                    traj_score(traj, MCHIPS, project_settings.traj_score_method),
                    traj.colorblob_count,
                ),
                end=" ",
            )
            continue
        # skip already chosen ones
        if traj.state == TrajState.CHOSEN:
            continue

        # mark best trajectories with CHOSEN flag and delete all that are
        # overlapping, thus are assumed to be false positive detections
        a = mark_traj_chosen(
            trajectories, k, ii, trajsonframe, colorids, barcodes, blobs
        )
        # if an overlapping already chosen one was found, we do not choose this one
        if a == -1:
            continue
        # this one was chosen successfully, increase counters
        deleted += a
        chosen += 1

        # try to connect neighboring (max 1 min) chosen ones forward
        next = get_chosen_neighbor_traj(
            traj, trajectories[k], forward=True, framelimit=framelimit
        )
        if next != -1:
            conn = connect_chosen_trajs(
                traj,
                trajectories[k][next],
                k,
                trajectories,
                trajsonframe,
                barcodes,
                project_settings,
                framelimit=framelimit,
            )
            if conn:
                # fill connection with not used barcodes or new virtual ones
                (a, b) = fill_connection_with_nub(
                    [(k, ii)] + conn + [(k, next)],
                    k,
                    trajectories,
                    trajsonframe,
                    barcodes,
                    colorids,
                    blobs,
                )
                rebirth += a
                virtual += b
                # set CHOSEN property if good connection was found
                for (kk, j) in conn:
                    a = mark_traj_chosen(
                        trajectories, kk, j, trajsonframe, colorids, barcodes, blobs, k
                    )
                    if k != kk:
                        changedcolor.append((kk, j))
                    if a == -1:
                        deleted += 1
                    else:
                        chosen += 1
                        connected += 1
                        deleted += a

        # try to connect neighboring (max 1 min) chosen ones backward
        prev = get_chosen_neighbor_traj(
            traj, trajectories[k], forward=False, framelimit=framelimit
        )
        if prev != -1:
            conn = connect_chosen_trajs(
                trajectories[k][prev],
                traj,
                k,
                trajectories,
                trajsonframe,
                barcodes,
                project_settings,
                framelimit=framelimit,
            )
            if conn:
                # fill connection with not used barcodes or new virtual ones
                (a, b) = fill_connection_with_nub(
                    [(k, prev)] + conn + [(k, ii)],
                    k,
                    trajectories,
                    trajsonframe,
                    barcodes,
                    colorids,
                    blobs,
                )
                rebirth += a
                virtual += b
                # set CHOSEN property if good connection was found
                for (kk, j) in conn:
                    a = mark_traj_chosen(
                        trajectories, kk, j, trajsonframe, colorids, barcodes, blobs, k
                    )
                    if k != kk:
                        changedcolor.append((kk, j))
                    if a == -1:
                        deleted += 1
                    else:
                        chosen += 1
                        connected += 1
                        deleted += a

    print()
    print("    chosen:", chosen, "deleted:", deleted, "connected:", connected)
    print(
        "    deleted trajs with score over the threshold (possibly deleted false positive detections):",
        deletedgood,
    )
    print("    barcodes reanimated to fill gap between chosen trajs:", rebirth)
    print(
        "    virtual barcodes added to trajs to fill gap between static chosen trajs:",
        virtual,
    )

    # change colorids on marked ones
    print("  Changing colorid of some (possibly false detected) trajs...")
    for (k, i) in changedcolor:
        change_colorid(
            trajectories, k, i, trajsonframe, barcodes, project_settings, blobs
        )
    print("    changed:", len(changedcolor))

    # set barcodes chosen/deleted property (first round)
    print("  Set barcode properties (first round)...")
    (chosen, deleted) = mark_barcodes_from_trajs(trajectories, barcodes, colorids, kkkk)
    print("    chosen barcodes:", chosen, " deleted barcodes:", deleted)
    sys.stdout.flush()


def recalculate_score(traj, k, barcodes, blobs, project_settings):
    """Recalculate sharesblob on traj to change its overall score.

    Keyword arguments:
    traj      -- a trajectory
    k         -- coloridindex of the trajectory
    barcodes  -- global list of all barcodes
    blobs     -- global list of all color blobs
    project_settings -- global project-specific settings

    """
    colorids = project_settings.colorids
    frame = traj.firstframe
    traj.sharesblob_count = 0
    for i in traj.barcodeindices:
        a = barcodes[frame][k][i]
        for kk in range(len(colorids)):
            for b in barcodes[frame][kk]:
                if a == b or not b.mfix or b.mfix & MFix.DELETED:
                    continue
                if algo_barcode.could_be_sharesblob(
                    a, b, k, kk, blobs[frame], project_settings
                ):
                    traj.sharesblob_count += 1
                    break
        frame += 1


def find_best_trajectories(
    trajectories, trajsonframe, barcodes, blobs, project_settings
):
    """Sort all trajectories according to their score, keep the best, delete the rest.
    Do this iteratively until all trajs are done.

    Actually trajectories are not deleted, only assigned with
    TrajState.DELETED/TrajState.CHANGEDID flags.

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
    barcodes     -- global list of all barcodes
    blobs        -- global list of all color blobs
    project_settings -- global project-specific settings

    """

    ##########################################################################
    # sort colorids according to total score of trajs and delete peculiar ones

    colorids = project_settings.colorids
    MCHIPS = project_settings.MCHIPS
    best_scores = [0 for k in range(len(colorids))]
    worst_scores = [0 for k in range(len(colorids))]
    sum_scores = [0 for k in range(len(colorids))]
    sum_good_scores = [0 for k in range(len(colorids))]
    for k in range(len(colorids)):
        if trajectories[k]:
            best_scores[k] = max(
                traj_score(x, MCHIPS, project_settings.traj_score_method)
                for x in trajectories[k]
            )
            worst_scores[k] = min(
                traj_score(x, MCHIPS, project_settings.traj_score_method)
                for x in trajectories[k]
            )
            sum_scores[k] = sum(
                traj_score(x, MCHIPS, project_settings.traj_score_method)
                for x in trajectories[k]
            )
            sum_good_scores[k] = sum(
                traj_score(x, MCHIPS, project_settings.traj_score_method)
                if is_traj_good(
                    x,
                    MCHIPS,
                    project_settings.traj_score_method,
                    project_settings.find_best_trajectories_settings.good_score_threshold,
                )
                else 0
                for x in trajectories[k]
            )
    sortedk = sorted(
        list(range(len(colorids))), key=lambda x: sum_scores[x], reverse=True
    )
    for k in sortedk:
        strid = colorids[k]
        deleteit = False
        if (
            best_scores[k]
            < project_settings.find_best_trajectories_settings.might_be_bad_score_threshold
            and sum_good_scores[k]
            < project_settings.find_best_trajectories_settings.might_be_bad_sum_good_score_threshold
        ):
            deleteit = True
            for traj in trajectories[k]:
                traj.state = TrajState.DELETED
        print(
            "  %s trajs: %5d sum: %5d sum_good: %5d best: %5d worst: %5d %s"
            % (
                strid,
                len(trajectories[k]),
                sum_scores[k],
                sum_good_scores[k],
                best_scores[k],
                worst_scores[k],
                "<-- all deleted" if deleteit else "",
            )
        )
    sys.stdout.flush()

    ############################################################################
    # first phase: assign chosen state to very good trajs, regardless of color
    # sort all trajectories according to reverse global score
    # si stands for 'sorted index'
    si = []
    for k in range(len(colorids)):
        si += [(k, i) for i in range(len(trajectories[k]))]
    si.sort(
        key=lambda x: traj_score(
            trajectories[x[0]][x[1]], MCHIPS, project_settings.traj_score_method
        ),
        reverse=True,
    )
    # choose and connect them
    choose_and_connect_trajs(
        si,
        project_settings.find_best_trajectories_settings.good_for_sure_score_threshold,
        trajectories,
        trajsonframe,
        project_settings,
        barcodes,
        blobs,
        kkkk=None,
        framelimit=project_settings.find_best_trajectories_settings.framelimit,
    )

    ############################################################################
    # second phase: interate all remaining trajs according to best colorid
    # and extend them as well after all good have been chosen
    for k in sortedk:
        # recalculate score (sharesblob might have been modified)
        for traj in trajectories[k]:
            recalculate_score(traj, k, barcodes, blobs, project_settings)
        # sort all trajectories in given color according to reverse score
        # si stands for 'sorted index'
        si = sorted(
            [(k, i) for i in range(len(trajectories[k]))],
            key=lambda x: traj_score(
                trajectories[x[0]][x[1]], MCHIPS, project_settings.traj_score_method
            ),
            reverse=True,
        )
        # choose and connect them
        choose_and_connect_trajs(
            si,
            project_settings.find_best_trajectories_settings.good_score_threshold,
            trajectories,
            trajsonframe,
            project_settings,
            barcodes,
            blobs,
            kkkk=k,
            framelimit=project_settings.find_best_trajectories_settings.framelimit,
        )
        # extend all chosen barcodes
        print(
            "  Extending chosen trajs with not yet chosen in both temporal directions..."
        )
        (virtual, rebirth) = extend_chosen_trajs(
            trajectories,
            trajsonframe,
            project_settings,
            barcodes,
            blobs,
            kkkk=k,
            framelimit=project_settings.find_best_trajectories_settings.framelimit,
        )
        print("    new virtual barcodes:", virtual, " barcodes reanimated:", rebirth)

    ############################################################################
    # third phase: cleanup, list, enhance virtual

    # list meta trajs
    print("\n  List meta trajs and gaps between...")
    list_meta_trajs(trajectories, trajsonframe, barcodes, colorids, blobs)

    # try to include not used blobs and not used barcodes to virtual barcodes
    print("  Enhance virtual barcodes with not used barcodes/blobs...")
    # TODO: too slow
    changes = enhance_virtual_barcodes(
        trajectories, trajsonframe, project_settings, barcodes, blobs
    )
    print("    number of changes:", changes)


def extend_chosen_trajs(
    trajectories,
    trajsonframe,
    project_settings,
    barcodes,
    blobs,
    kkkk=None,
    framelimit=1500,
):
    """Extend all chosen trajs in both temporal directions with remaining
    not chosen trajs.

    This function should be called after best trajectories have already been
    chosen and connected, if possible.

    Function calls connect_chosen_trajs(), like find_best_trajectories(),
    but now without specific ending and frame limit. On the other hand,
    there should be less parts to extend. Anyway, algo might take long,
    especially because of unknown number of iterations.

    Actually trajectories are not deleted, only assigned with TrajState.DELETED flag.

    Keyword arguments:
    trajectories -- global list of all trajectories
    trajsonframe -- global list of trajectory indices per frame per coloridindex
    project_settings -- global project-specific settings
    barcodes     -- global list of all barcodes
    blobs        -- global list of all color blobs
    kkkk         -- optional argument to extend only a given colorid
    framelimit   -- optional param to define frame limit of traj extentions

    """

    colorids = project_settings.colorids

    deleted = 0
    chosen = 0
    virtual = 0
    rebirth = 0

    oldchosen = -1
    olddeleted = -1
    it = 0
    klist = range(len(colorids)) if kkkk is None else [kkkk]
    # iteration is needed, because traj states change in between. (TODO: why exactly?)
    while oldchosen != chosen or olddeleted != deleted:
        changedcolor = []
        oldchosen = chosen
        olddeleted = deleted
        print("   ", end=" ")
        for k in klist:
            print(colorids[k], end=" ")
            for i, traj in enumerate(trajectories[k]):
                if traj.state != TrajState.CHOSEN:
                    continue

                # elongate forward
                conn = connect_chosen_trajs(
                    traj,
                    "forward",
                    k,
                    trajectories,
                    trajsonframe,
                    barcodes,
                    project_settings,
                    framelimit=framelimit,
                )
                if conn:
                    # fill connection with not used barcodes or new virtual ones
                    (a, b) = fill_connection_with_nub(
                        [(k, i)] + conn,
                        k,
                        trajectories,
                        trajsonframe,
                        barcodes,
                        colorids,
                        blobs,
                    )
                    rebirth += a
                    virtual += b
                    # set CHOSEN property if good connection was found
                    for (kk, j) in conn:
                        #                        print("forward", colorids[kk], trajectories[kk][j].firstframe, trajlastframe(trajectories[kk][j]))
                        a = mark_traj_chosen(
                            trajectories,
                            kk,
                            j,
                            trajsonframe,
                            colorids,
                            barcodes,
                            blobs,
                            k,
                        )
                        if k != kk:
                            changedcolor.append((kk, j))
                        if a == -1:
                            deleted += 1
                        else:
                            chosen += 1
                            deleted += a

                # elongate backward
                conn = connect_chosen_trajs(
                    traj,
                    "backward",
                    k,
                    trajectories,
                    trajsonframe,
                    barcodes,
                    project_settings,
                    framelimit=framelimit,
                )
                if conn:
                    # fill connection with not used barcodes or new virtual ones
                    (a, b) = fill_connection_with_nub(
                        conn + [(k, i)],
                        k,
                        trajectories,
                        trajsonframe,
                        barcodes,
                        colorids,
                        blobs,
                    )
                    rebirth += a
                    virtual += b
                    # set CHOSEN property if good connection was found
                    for (kk, j) in conn:
                        #                       print("backward", colorids[kk], trajectories[kk][j].firstframe, trajlastframe(trajectories[kk][j]))
                        a = mark_traj_chosen(
                            trajectories,
                            kk,
                            j,
                            trajsonframe,
                            colorids,
                            barcodes,
                            blobs,
                            k,
                        )
                        if k != kk:
                            changedcolor.append((kk, j))
                        if a == -1:
                            deleted += 1
                        else:
                            chosen += 1
                            deleted += a

        # change colorids on marked ones
        for (k, i) in changedcolor:
            change_colorid(
                trajectories, k, i, trajsonframe, barcodes, project_settings, blobs
            )

        # change barcode properties as well
        mark_barcodes_from_trajs(trajectories, barcodes, colorids)

        # iterate next
        it += 1
        print(
            "\n    iteration #%d -" % it,
            "chosen:",
            chosen - oldchosen,
            "deleted:",
            deleted - olddeleted,
            "changed color:",
            len(changedcolor),
        )
        sys.stdout.flush()
    return (virtual, rebirth)


def add_virtual_barcodes_to_gaps(trajectories, trajsonframe, colorids, barcodes):
    """Fill all remaining gaps between chosen trajectories with virtual barcodes.

    Adds MFix.DEBUG on possible conflicts (too large gap between chosens).

    Keyword arguments:
    trajectories -- global list of all trajectories
    trajsonframe -- global list of trajectory indices per frame per coloridindex
    colorids     -- global colorid database
    barcodes     -- blobal list of all barcodes

    Return number of virtual barcodes added.

    TODO: insert time limit to connection

    """
    MCHIPS = len(colorids[0])
    simulate = False
    if simulate:
        print("    Warning: add_virtual_barcodes_to_gaps() is in simulation mode.")
    virtual = 0

    for k in range(len(colorids)):
        strid = colorids[k]

        ########################################
        # get first traj, add virtuals before it
        i = get_chosen_neighbor_traj_perframe(
            None, trajectories, trajsonframe, k, True, None
        )
        if i == -1:
            continue
        # add virtual barcodes to the beginning
        traj = trajectories[k][i]
        barcode = barcodes[traj.firstframe][k][traj.barcodeindices[0]]
        if not simulate:
            for frame in range(traj.firstframe):
                barcodes[frame][k].append(
                    Barcode(
                        barcode.centerx,
                        barcode.centery,
                        barcode.orientation,
                        MFix.VIRTUAL | MFix.CHOSEN,
                        MCHIPS,
                    )
                ),
                trajsonframe[frame][k].add(i)
                virtual += 1
            traj.barcodeindices = [
                len(barcodes[x][k]) - 1 for x in range(traj.firstframe)
            ] + traj.barcodeindices
            traj.firstframe = 0

        ######################################################
        # connect all chosen trajs in the middle with virtuals
        next = get_chosen_neighbor_traj_perframe(
            traj, trajectories, trajsonframe, k, True, None
        )
        while next != -1:
            trajx = trajectories[k][next]
            a = trajlastframe(traj)
            b = trajx.firstframe
            if b > a + 1:
                barcodea = barcodes[a][k][traj.barcodeindices[-1]]
                barcodeb = barcodes[b][k][trajx.barcodeindices[0]]
                dist = get_distance(barcodea, barcodeb)
                debug = False
                if dist > max_allowed_dist_between_trajs(a, b):
                    print(
                        "    Warning: distance between neighboring chosen %s trajs is large (%d)."
                        % (colorids[k], dist),
                        end=" ",
                    )
                    print(
                        "a i%d" % i,
                        "f%d-%d" % (traj.firstframe, trajlastframe(traj)),
                        end=" ",
                    )
                    print(
                        "b i%d" % next,
                        "f%d-%d" % (trajx.firstframe, trajlastframe(trajx)),
                    )
                    if trajx.firstframe - trajlastframe(traj) > 25:
                        debug = True
                    elif dist > 250:
                        debug = True
                if not simulate:
                    dx = (barcodeb.centerx - barcodea.centerx) / (b - a)
                    dy = (barcodeb.centery - barcodea.centery) / (b - a)
                    do = barcodeb.orientation - barcodea.orientation
                    while do > pi:
                        do -= 2 * pi
                    while do < -pi:
                        do += 2 * pi
                    do /= b - a
                    j = 1
                    for frame in range(a + 1, b):
                        barcodes[frame][k].append(
                            Barcode(
                                barcodea.centerx + j * dx,
                                barcodea.centery + j * dy,
                                barcodea.orientation + j * do,
                                MFix.VIRTUAL
                                | MFix.CHOSEN
                                | (MFix.DEBUG if debug else 0),
                                MCHIPS,
                            )
                        )
                        trajsonframe[frame][k].add(i)
                        traj.barcodeindices.append(len(barcodes[frame][k]) - 1)
                        virtual += 1
                        j += 1
            # save params for next iteration
            i = next
            traj = trajectories[k][i]
            next = get_chosen_neighbor_traj_perframe(
                trajx, trajectories, trajsonframe, k, True, None
            )

        # last - add virtual barcodes to the end
        barcode = barcodes[trajlastframe(traj)][k][traj.barcodeindices[-1]]
        if not simulate:
            for frame in range(trajlastframe(traj) + 1, len(trajsonframe)):
                barcodes[frame][k].append(
                    Barcode(
                        barcode.centerx,
                        barcode.centery,
                        barcode.orientation,
                        MFix.VIRTUAL | MFix.CHOSEN,
                        MCHIPS,
                    )
                )
                trajsonframe[frame][k].add(i)
                traj.barcodeindices.append(len(barcodes[frame][k]) - 1)
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
        if (
            barcodes[frame][k][traj.barcodeindices[frame - traj.firstframe]].mfix
            & MFix.FULLFOUND
        ):
            return frame
        frame += 1
    # error, not found
    return -1


def smooth_partlyfound_params(traj, barcodes, k, strid, MAX_PERFRAME_DIST_MD):
    """Smooth the orientation and center of partlyfound barcodes in a trajectory
    with the fullfound orientations and centers.

    Keyword arguments:
    traj     -- a trajectory (supposedly a chosen one)
    barcodes -- global list of barcodes
    k        -- coloridindex
    strid    -- string id corresponding to coloridindex k
    MAX_PERFRAME_DIST_MD -- max distance a blob travels under motion between frames

    Function does not return a value but changes barcode parameters in the trajectory.
    """

    # start smoothing at the first fullfound element
    currentframe = get_next_fullfound_from_traj(traj, traj.firstframe, barcodes, k)
    if currentframe == -1:
        return
    current = barcodes[currentframe][k][
        traj.barcodeindices[currentframe - traj.firstframe]
    ]
    lastframe = trajlastframe(traj)
    # get first fullfound
    while currentframe <= lastframe:
        # get next fullfound
        nextfullframe = get_next_fullfound_from_traj(
            traj, currentframe + 1, barcodes, k
        )
        if nextfullframe == -1:
            return
        next = barcodes[nextfullframe][k][
            traj.barcodeindices[nextfullframe - traj.firstframe]
        ]
        # check if there is at least one partlyfound between them:
        # check properties of current and next fullfound, only change if there is no motion
        if (
            nextfullframe - currentframe == 1
            or get_distance(current, next) > MAX_PERFRAME_DIST_MD
        ):
            currentframe = nextfullframe
            current = next
            continue
        dx = (next.centerx - current.centerx) / (nextfullframe - currentframe)
        dy = (next.centery - current.centery) / (nextfullframe - currentframe)
        do = next.orientation - current.orientation
        while do > pi:
            do -= 2 * pi
        while do < -pi:
            do += 2 * pi
        do /= nextfullframe - currentframe
        for i in range(1, nextfullframe - currentframe):
            barcode = barcodes[currentframe + i][k][
                traj.barcodeindices[currentframe + i - traj.firstframe]
            ]
            barcode.centerx = current.centerx + i * dx
            barcode.centery = current.centery + i * dy
            barcode.orientation = current.orientation + i * do
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
        lastframe = len(barcodes) - 1
    while frame <= lastframe:
        for i in range(len(barcodes[frame][k])):
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
    colorids     -- global colorid database
    blobs        -- global list of all blobs

    """
    changes = 0
    for k in range(len(colorids)):
        print("   ", colorids[k], end=" ")
        # get first chosen traj
        i = get_chosen_neighbor_traj_perframe(
            None, trajectories, trajsonframe, k, True, None
        )
        while i != -1:
            # get next continuous chain of traj indices into chosens
            chosens = [i]
            oldtraj = trajectories[k][i]
            firstframe = oldtraj.firstframe
            while 1:
                i = get_chosen_neighbor_traj_perframe(
                    oldtraj, trajectories, trajsonframe, k, True, None
                )
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
                print(
                    "(d%d)"
                    % get_distance(
                        barcodes[lastframe][k][
                            trajectories[k][chosens[-1]].barcodeindices[-1]
                        ],
                        barcodes[trajectories[k][i].firstframe][k][
                            trajectories[k][i].barcodeindices[0]
                        ],
                    ),
                    end=" ",
                )
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
    colorids     -- global colorid database
    blobs        -- global list of all blobs

    """
    changes = 0
    for k in range(len(colorids)):
        print("   ", colorids[k], end=" ")
        # get first chosen traj
        i = get_chosen_neighbor_traj_perframe(
            None, trajectories, trajsonframe, k, True, None
        )
        while i != -1:
            # get next continuous chain of traj indices into chosens
            chosens = [i]
            oldtraj = trajectories[k][i]
            firstframe = oldtraj.firstframe
            while 1:
                i = get_chosen_neighbor_traj_perframe(
                    oldtraj, trajectories, trajsonframe, k, True, None
                )
                if i == -1:
                    break
                traj = trajectories[k][i]
                if trajlastframe(oldtraj) + 1 != traj.firstframe:
                    break
                chosens.append(i)
                oldtraj = traj
            lastframe = trajlastframe(trajectories[k][chosens[-1]])
            # get first fullfound
            (oldfullframe, ii) = get_next_barcode_with_mfix(
                firstframe, barcodes, k, MFix.CHOSEN | MFix.FULLFOUND
            )
            print("%d-%d" % (firstframe, lastframe), end=" ")
            if i != -1:
                print(
                    "(d%d)"
                    % get_distance(
                        barcodes[lastframe][k][
                            trajectories[k][chosens[-1]].barcodeindices[-1]
                        ],
                        barcodes[trajectories[k][i].firstframe][k][
                            trajectories[k][i].barcodeindices[0]
                        ],
                    ),
                    end=" ",
                )
            # TODOdebug
            #            if colorids[k] == "GOP" and lastframe == 326:
            #                for xx in range(320, 360):
            #                    print("frame", xx)
            #                    for xxx in trajsonframe[xx][k]:
            #                        xxxx = trajectories[k][xxx]
            #                        print("  i%d f%d-%d" % (xxx, xxxx.firstframe, trajlastframe(xxxx)), TrajState(xxxx.state).name)
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
                (fullframe, ii) = get_next_barcode_with_mfix(
                    oldfullframe + 1, barcodes, k, MFix.CHOSEN | MFix.FULLFOUND
                )
                if fullframe > lastframe or fullframe == -1:
                    # no more fullfound until the end of current frame
                    # TODO? what to do with the end?
                    # go to next chain
                    break
                fullbarcode = barcodes[fullframe][k][ii]
                if fullframe > oldfullframe + 1:
                    # initialize params from two fullfound barcodes on the side
                    dx = float(fullbarcode.centerx - oldfullbarcode.centerx) / (
                        fullframe - oldfullframe
                    )
                    dy = float(fullbarcode.centery - oldfullbarcode.centery) / (
                        fullframe - oldfullframe
                    )
                    do = float(fullbarcode.orientation - oldfullbarcode.orientation)
                    while do > pi:
                        do -= 2 * pi
                    while do < -pi:
                        do += 2 * pi
                    do /= fullframe - oldfullframe
                    #                    if colorids[k] == 'GPB':
                    #                        print("oldfull", colorids[k], oldfullframe, oldfullbarcode.centerx, oldfullbarcode.centery, oldfullbarcode.orientation, mfix2str(oldfullbarcode.mfix))
                    oldframe = oldfullframe
                    # set partlyfound params between
                    while 1:
                        (frame, ii) = get_next_barcode_with_mfix(
                            oldframe + 1, barcodes, k, MFix.CHOSEN
                        )
                        # no more partlyfound
                        if frame >= fullframe:
                            break
                        # set params

                        # TODO debug commented out
                        #                        barcode = barcodes[frame][k][ii]
                        #                        barcode.centerx = oldfullbarcode.centerx + (frame-oldfullframe)*dx
                        #                        barcode.centery = oldfullbarcode.centery + (frame-oldfullframe)*dy
                        #                        barcode.orientation = oldfullbarcode.orientation + (frame-oldfullframe)*do
                        #                        barcode.mfix |= MFix.DEBUG
                        #                        while barcode.orientation > pi: barcode.orientation -= 2*pi
                        #                        while barcode.orientation < -pi: barcode.orientation += 2*pi
                        # TODO debug comment ends

                        #                        if colorids[k] == 'GPB':
                        #                            print("barcode", colorids[k], frame, barcode.centerx, barcode.centery, barcode.orientation, mfix2str(barcode.mfix))
                        changes += 1
                        # save old params
                        oldframe = frame
                    # save old params
                #                    if colorids[k] == 'GPB':
                #                        print("full", colorids[k], fullframe, fullbarcode.centerx, fullbarcode.centery, fullbarcode.orientation, mfix2str(fullbarcode.mfix))
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
    colorids     -- global colorid database
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
            if traj.state != TrajState.CHOSEN:
                # mark all barcodes contained by not chosen trajectories with deleted flag
                currentframe = traj.firstframe
                for bi in traj.barcodeindices:
                    barcode = barcodes[currentframe][k][bi]
                    if barcode.mfix and not (barcode.mfix & MFix.DELETED):
                        barcode.mfix |= MFix.DELETED
                        deleted += 1
                    currentframe += 1
        # chosen
        for traj in trajectories[k]:
            if traj.state == TrajState.CHOSEN:
                # mark all barcodes contained by chosen trajectories with chosen flag
                currentframe = traj.firstframe
                for bi in traj.barcodeindices:
                    barcode = barcodes[currentframe][k][bi]
                    barcode.mfix &= ~MFix.DELETED
                    barcode.mfix |= MFix.CHOSEN
                    chosen += 1
                    currentframe += 1

    return (chosen, deleted)


def finalize_trajectories(
    trajectories, trajsonframe, barcodes, blobs, project_settings
):
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
        project_settings -- global project-specific settings

        Function returns number of (chosen, deleted) barcodes
        and writes to keyword parameters barcodes and trajectories.

    """

    colorids = project_settings.colorids

    # TODO: go through all frames, include nub to barcodes,
    # include n.u. barcodes to missing ones, etc.
    # assign possibility to location of all barcodes on all frames

    print("  Extending chosen trajs with not yet chosen in both temporal directions...")
    (virtual, rebirth) = extend_chosen_trajs(
        trajectories,
        trajsonframe,
        project_settings,
        barcodes,
        blobs,
        kkkk=None,
        framelimit=project_settings.find_best_trajectories_settings.framelimit * 2,
    )
    print("    new virtual barcodes:", virtual, " barcodes reanimated:", rebirth)

    # list meta trajs
    print("  List meta trajs and gaps between...")
    list_meta_trajs(trajectories, trajsonframe, barcodes, colorids, blobs)

    print("  Filling gaps between chosen trajectories with virtual barcodes...")
    virtual = add_virtual_barcodes_to_gaps(
        trajectories, trajsonframe, colorids, barcodes
    )
    print("    virtual barcodes:", virtual)

    # list meta trajs
    print("  List meta trajs and gaps between...")
    list_meta_trajs(trajectories, trajsonframe, barcodes, colorids, blobs)

    # try to include not used blobs and not used barcodes to virtual barcodes
    print("  Enhance virtual barcodes with not used barcodes/blobs...")
    # TODO: too slow
    changes = enhance_virtual_barcodes(
        trajectories, trajsonframe, project_settings, barcodes, blobs
    )
    print("    number of changes:", changes)


#    print("  Smooth final trajectories (TODO: good algo not implemented yet)...")
#    changes = smooth_final_trajectories(trajectories, trajsonframe, barcodes, colorids, blobs)
#    print("    number of changes:", changes)
