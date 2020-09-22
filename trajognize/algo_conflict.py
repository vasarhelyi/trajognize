"""
All kinds of algorithms used by trajognize.main() that are related to
detecting and resolving all kind of conflicts on final chosen barcode database.

TODOs:

- use it with reloaded barcode database to save debug time

"""

from .project import *
from .init import *
from .algo import get_distance_at_position, is_point_inside_ellipse

from . import algo_barcode
from . import algo_blob
from . import algo_trajectory


def list_conflicts(conflicts, colorids):
    """List conflicts.

    Keyword arguments:
    conflicts -- list of all conflicts ...[k] = conflict_t
    barcodes     -- global list of all barcodes
    blobs        -- global list of all blobs
    colorids     -- global colorid database created by parse_colorid_file()

    """
    for k in range(len(colorids)):
        strid = colorids[k].strid
        for conflict in conflicts[k]:
            print("   ", conflict.ctype, strid, "f%d-%d" % (conflict.firstframe, \
                    algo_trajectory.trajlastframe(conflict)), \
                    conflict.cwith if conflict.cwith is None else [colorids[x].strid for x in conflict.cwith], \
                    STATE_STR[conflict.state])


def list_conflicted_trajs(conflicted_trajs, colorids, trajectories):
    """List conflicted trajectories.

    Keyword arguments:
    conflicted_trajs -- list of trajs that are conflicted ...[k][i] = traj index
    colorids         -- global colorid database created by parse_colorid_file()
    trajectories     -- global list of all trajectories

    """
    si = [] # si stands for 'sorted index'
    for k in range(len(colorids)):
        si += [(k, t) for t in conflicted_trajs[k]]
    si.sort(key=lambda x: algo_trajectory.traj_score(trajectories[x[0]][x[1]]),
        reverse=True
    )
    for (k, t) in si:
        traj = trajectories[k][t]
        print("   ", colorids[k].strid, "f%d-%d s%d" % (traj.firstframe,
                algo_trajectory.trajlastframe(traj),
                algo_trajectory.traj_score(traj)), \
                STATE_STR[traj.state])


def get_gap_conflicts(barcodes, colorids):
    """Return all gap conflicts, i.e. when two neighboring chosen trajs are
    very far away in space.

    This state is actually pre-stamped with MFIX_DEBUG so far.

    Conflict is marked as the gap but actually trajs before or after also
    need to be resolved.

    Keyword arguments:
    barcodes     -- global list of all barcodes
    colorids     -- global colorid database created by parse_colorid_file()

    """
    conflicts = [[] for k in range(len(colorids))]
    for frame in range(len(barcodes)):
        chosenindices = algo_barcode.get_chosen_barcode_indices(barcodes[frame])
        for k in range(len(colorids)):
            if chosenindices[k] is None: continue # TODO: is there a case like this at all?
            i = chosenindices[k]
            chosen = barcodes[frame][k][i]
            # check debug state
            if chosen.mfix & MFIX_DEBUG:
                # create new conflict
                if not conflicts[k] or algo_trajectory.trajlastframe(conflicts[k][-1]) < frame - 1:
                    conflicts[k].append(conflict_t("gap", frame))
                # add barcode to current conflict
                conflicts[k][-1].barcodeindices.append(i)

    return conflicts


def get_overlap_conflicts(barcodes, blobs, colorids):
    """Return all overlap conflicts, i.e. when two barcodes fully overlap.

    MFIX_SHAREDBLOB should be assigned to all such cases, even though
    blobs are not actually shared. See algo_barcode.set_shared_mfix_flags()
    for more details.

    Keyword arguments:
    barcodes     -- global list of all barcodes
    blobs        -- global list of all blobs
    colorids     -- global colorid database created by parse_colorid_file()

    """
    conflicts = [[] for k in range(len(colorids))]
    for frame in range(len(barcodes)):
        chosenindices = algo_barcode.get_chosen_barcode_indices(barcodes[frame])
        for k in range(len(colorids)):
            if chosenindices[k] is None: continue
            i = chosenindices[k]
            chosen = barcodes[frame][k][i]
            # check sharesblob state
            if chosen.mfix & MFIX_SHARESBLOB:
                # create new conflict
                if not conflicts[k] or algo_trajectory.trajlastframe(conflicts[k][-1]) < frame - 1:
                    conflicts[k].append(conflict_t("overlap", frame, set()))
                # add barcode to current conflict
                conflicts[k][-1].barcodeindices.append(i)
                # get barcode that is conflicted with this one
                # TODO: now we only save coloridindex, could be organized in a better way...
                for kk in range(len(colorids)):
                    if k == kk or kk in conflicts[k][-1].cwith: continue
                    if chosenindices[kk] is None: continue
                    ii = chosenindices[kk]
                    chosenx = barcodes[frame][kk][ii]
                    if (chosenx.mfix & MFIX_SHARESBLOB) and algo_barcode.could_be_sharesblob(
                            chosen, chosenx, k, kk, blobs[frame], colorids)[0]:
                        conflicts[k][-1].cwith.add(kk)

    return conflicts


def resolve_overlap_conflicts(conflicts, barcodes, blobs, colorids):
    """Try to solve overlap conflicts by the following:

    1. find not used blobs around with same color as conflicted, and try to
       assign this instead of conflicted if it is under barcode on previous frame
    2. TODO: somehow check which is MFIX_VIRTUAL or MFIX_DEBUG, etc. without nub

    Keyword arguments:
    conflicts    -- list of all overlap conflicts
    barcodes     -- global list of all barcodes
    blobs        -- global list of all blobs
    colorids     -- global colorid database created by parse_colorid_file()

    """
    resolved = 0
    for k in range(len(colorids)):
        strid = colorids[k].strid
        for conflict in conflicts[k]:
            if conflict.state == STATE_DELETED: continue
            frame = conflict.firstframe - 1
            if frame == -1: continue # TODO: so far we do not resolve conflicts on first frame
            chosenindices = algo_barcode.get_chosen_barcode_indices(barcodes[frame])
            oldresolved = resolved
            for i in conflict.barcodeindices:
                frame += 1
                oldchosenindices = chosenindices
                oldbarcode = barcodes[frame-1][k][oldchosenindices[k]]
                chosenindices = algo_barcode.get_chosen_barcode_indices(barcodes[frame])
                barcode = barcodes[frame][k][i]
                nub = algo_blob.get_not_used_blob_indices(blobs[frame], barcodes[frame])
                allsharedblobs = []
                allresolvedblobs = []
                for kk in conflict.cwith:
                    if chosenindices[kk] is None: continue
                    ii = chosenindices[kk]
                    bwith = barcodes[frame][kk][ii]
                    if not (bwith.mfix & MFIX_SHARESBLOB): continue
                    sharedblobs, sharedpositions = algo_barcode.could_be_sharesblob(
                            barcode, bwith, k, kk, blobs[frame], colorids)
                    if not sharedblobs: continue
                    allsharedblobs += sharedblobs
                    # no more check, try to resolve conflict
                    # TODO: all the above is more or less the same as in list_conflicts,
                    # code could be optimized if moved there for in place solution
                    if oldchosenindices[k] is None: continue
                    if oldchosenindices[kk] is None: continue
                    for sbi, sbpi in zip(sharedblobs, sharedpositions):
                        # double check if sharesblob is at the right place
                        # if not, we skip this conflict
                        if sbi in barcode.blobindices and barcode.blobindices.index(sbi) != sbpi:
                            continue
                        # check if sharedblob's place is used already if it is
                        # not used yet. If so, we do not resolve this conflict.
                        if sbi not in barcode.blobindices and \
                                barcode.blobindices[sbpi] is not None:
                            continue
                        sharedblob = blobs[frame][sbi]
                        for bi in nub:
                            nublob = blobs[frame][bi]
                            if nublob.color != sharedblob.color: continue
                            # if not used blob is not under previous barcode position, skip
                            if not is_point_inside_ellipse(nublob, rat_blob_t(oldbarcode.centerx,
                                    oldbarcode.centery, MAX_INRAT_DIST * MCHIPS / 2, MAX_INRAT_DIST / 2,
                                    oldbarcode.orientation)):
                                continue
                            # if not used blob is not under current barcode position, skip
                            if get_distance_at_position(barcode, sbpi, nublob) > MAX_INRAT_DIST:
                                continue
                            # create new barcode temporarily
                            newbarcode = barcode_t(barcode.centerx, barcode.centery,
                                    barcode.orientation, barcode.mfix,
                                    list(barcode.blobindices))
                            # store new blob in barcode at sharesblob's place
                            newbarcode.blobindices[sbpi] = bi
                            # if all blobs are there, check consistency
                            if None not in newbarcode.blobindices:
                                blobchain = [blobs[frame][x] for x in newbarcode.blobindices]
                                if not algo_blob.is_blob_chain_appropriate_as_barcode(
                                    blobchain, MAX_INRAT_DIST + 10): continue
                            # if not all blobs are there, check no motion from last frame,
                            # TODO: is there a better method?
                            # TODO: might be that multiple shares blobs could be resolved,
                            # in this case algo could fail... getting toooooo complicated...
                            else:
                                skip = False
                                for x in newbarcode.blobindices:
                                    if x is None: continue
                                    blobx = blobs[frame][x]
                                    if not is_point_inside_ellipse(blobx, rat_blob_t(oldbarcode.centerx,
                                            oldbarcode.centery, MAX_INRAT_DIST * MCHIPS / 2, MAX_INRAT_DIST / 2,
                                            oldbarcode.orientation)):
                                        skip = True
                                        break
                                if skip: continue
                            # all checks passed, nublob is a good replacement of sharesblob('s position)
                            # remove old correspondence with sharedblob
                            algo_blob.remove_blob_barcodeindex(sharedblob, k, i)
                            # replace shared blob with new not used blob in barcode
                            barcode.blobindices[sbpi] = bi
                            algo_blob.update_blob_barcodeindices(barcode, k, i, blobs[frame])
                            algo_barcode.calculate_params(barcode, strid, blobs[frame])
                            allresolvedblobs.append(sbi)
                            break
                # if all conflicts have been solved or there were no conflicts by now, set resolved state
                if len(allsharedblobs) == len(allresolvedblobs):
                    resolved += 1
                    barcode.mfix &= ~MFIX_SHARESBLOB
            # if all frames have been resolved in conflict
            # TODO: this is not accurate because it might happen that
            # in one conflict structure there are conflicts caused by more members simultaneously...
            if resolved - oldresolved == frame - conflict.firstframe + 1:
                conflict.state = STATE_DELETED

    return resolved


def get_nub_conflicts(trajectories, barcodes, blobs, colorids):
    """Return all not-used-barcode conflicts.

    Check on traj level to separate more possible conflicts of same color,
    but store on barcode level.

    Keyword arguments:
    trajectories -- global list of all trajectories
    barcodes     -- global list of all barcodes
    blobs        -- global list of all blobs
    colorids     -- global colorid database created by parse_colorid_file()

    """
    conflicts = [[] for k in range(len(colorids))]
    conflicted_trajs = [set() for k in range(len(colorids))]
    for k in range(len(colorids)):
        for t in range(len(trajectories[k])):
            traj = trajectories[k][t]
            # skip non-deleted
            if traj.state != STATE_DELETED: continue
            frame = traj.firstframe - 1
            for i in traj.barcodeindices:
                frame += 1
                # skip non free barcodes
                if not algo_barcode.barcode_is_free(
                        barcodes[frame], k, i, blobs[frame]):
                    continue
                barcode = barcodes[frame][k][i]
                chosenindices = algo_barcode.get_chosen_barcode_indices(barcodes[frame])
                # skip barcodes overlapping with chosen ones
                # Note that this is a stricter condition than barcode_is_free()
                skip = False
                for kk in range(len(colorids)):
                    ii = chosenindices[kk]
                    if ii is None: continue
                    if algo_barcode.could_be_sharesblob(
                            barcode, barcodes[frame][kk][ii],
                            k, kk, blobs[frame], colorids):
                        skip = True
                        break
                if skip: continue
                # no more check, traj is conflicted (store only conflicted part)
                # create new conflict
                if not conflicts[k] or algo_trajectory.trajlastframe(conflicts[k][-1]) < frame - 1:
                    conflicts[k].append(conflict_t("nub", frame))
                # add barcode to current conflict
                conflicts[k][-1].barcodeindices.append(i)
                conflicted_trajs[k].add(t)

    return (conflicts, conflicted_trajs)


def create_conflict_database_and_try_resolve(trajectories, barcodes, blobs, colorids):
    """List and store barcodes and trajs that are in conflicted state.

    Conflicts are the following:

*   1. too large gap between trajs --> stamped with MFIX_DEBUG in add_virtual_barcodes_to_gaps()
*   2. sharesblobs between trajs
*?  3. not used "blob trajectories"
*   4. not used barcodes during no chosen (or only virtual) periods
*   5. fully overlapping barcodes, shares or one is virtual or sum blobs < 5 ... --> same as shares
    6. G and O that does not belong to anything, but there is a lot of them, suspicious, get rid of it...
    7. flashing, big noise in dx/dy/do, suspicious

    Notes on how to resolve (mostly TODO):
     - database of the errors, but how? What is needed?
     - new traj database, connected, not virtual, not broken by "shared",
       score on that, measure of space/time at breaks
     - where is the conflict? Which barcode? From where to where?


    Keyword arguments:
    trajectories -- global list of all trajectories
    trajsonframe -- global list of trajectory indices per frame per coloridindex
    barcodes     -- global list of all barcodes
    blobs        -- global list of all blobs
    colorids     -- global colorid database created by parse_colorid_file()

    """

    print("  Get total number of chosen barcodes...")
    numchosen = 0
    for frame in range(len(barcodes)):
        chosens = algo_barcode.get_chosen_barcode_indices(barcodes[frame])
        for k in range(len(chosens)):
            if chosens[k] is not None:
                numchosen += 1
    print("    found", numchosen)
    if numchosen == 0: return

    print("  Searching for all gap conflicts...")
    gap_conflicts = get_gap_conflicts(barcodes, colorids)
    num = sum(sum(len(x.barcodeindices) for x in confsamecolor) for confsamecolor in gap_conflicts)
    print("    found %d gap conflicted barcodes (%1.2f%% of all chosen)" % (num, 100.0 * num / numchosen))
    list_conflicts(gap_conflicts, colorids)

    print("  Searching for all overlap conflicts...")
    overlap_conflicts = get_overlap_conflicts(barcodes, blobs, colorids)
    num = sum(sum(len(x.barcodeindices) for x in confsamecolor) for confsamecolor in overlap_conflicts)
    print("    found %d overlap conflicted barcodes (%1.2f%% of all chosen), trying to resolve them..." % (num, 100.0 * num / numchosen))
    resolved = resolve_overlap_conflicts(overlap_conflicts, barcodes, blobs, colorids)
    print("   ", resolved, "overlap conflicts resolved")
    list_conflicts(overlap_conflicts, colorids)

    print("  Searching for all not-used-barcode conflicts...")
    (nub_conflicts, nub_conflicted_trajs) = get_nub_conflicts(trajectories, barcodes, blobs, colorids)
    num = sum(sum(len(x.barcodeindices) for x in confsamecolor) for confsamecolor in nub_conflicts)
    print("    found %d nub conflicted barcodes (%1.2f%% of all chosen)" % (num, 100.0 * num / numchosen))
#    list_conflicts(nub_conflicts, colorids)
    list_conflicted_trajs(nub_conflicted_trajs, colorids, trajectories)


