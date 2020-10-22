"""
All kinds of algorithms used by trajognize.main() that are related to blobs.
"""

from math import degrees, acos
import numpy

from .init import MFix, BarcodeIndex
from .algo import distance_matrix, get_distance, is_point_inside_ellipse

# global variables
chainlists = [] # chains of possible ids with blob indices


def create_spatial_distlists(blobs, MAX_INRAT_DIST):
    """Return a list for all blobs containing blob indices
    that are close enough to be on the same rat on a given frame.

    Keyword arguments:
    blobs -- list of all blobs (ColorBlob) from a given frame
    MAX_INRAT_DIST -- max distance between rats on the same frame

    """
    n = len(blobs)
    if not n:
        return []

    distmatrix = distance_matrix(numpy.array([[b.centerx, b.centery] for b in blobs]))
    a = [numpy.where(distmatrix[i] <= MAX_INRAT_DIST)[0] for i in range(n)]
    b = [numpy.where((distmatrix[i] <= 2 * MAX_INRAT_DIST) & (distmatrix[i] > MAX_INRAT_DIST))[0] for i in range(n)]
    sdistlists = [[numpy.ndarray.tolist(a[i]), numpy.ndarray.tolist(b[i])] for i in range(n)]

    return sdistlists


def create_temporal_distlists(prevblobs, blobs, prevmd_blobs, md_blobs,
    prevmdindices, mdindices, project_settings):
    """Return a list for all blobs containing prevblob indices
    that are close enough to be the same blobs as on the previous frame.

    Function uses two thresholds, a lower one for static cases and
    a higher one for cases when there are motion blobs under the blobs.
#    If motion blob is present on both frames, shift of centers can be calculated
#    easily and distance calculation is corrected with this shift.

    TODO: better algo would be nice, checking orientation of md blobs, etc.

    Keyword arguments:
    prevblobs     -- list of all blobs (ColorBlob) from the previous frame
    blobs         -- list of all blobs (ColorBlob) from the current frame
    prevmd_blobs  -- list of all motion blobs (motion_blob_t) from the previous frame
    md_blobs      -- list of all motion blobs (motion_blob_t) from the current frame
    prevmdindices -- motion blob index for blobs of the previous frame
    mdindices     -- motion blob index for blobs of the current frame
    project_settings -- global project-specific settings

    Backward compatible - simply feed with 'next*' as prev*.

    """
    n = len(blobs)
    m = len(prevblobs)
    if not n:
        return []
    if not m:
        return [[] for i in range(n)]
    # include color in third coordinate to be 0 if match and too large if not
    pn = numpy.array([[b.centerx, b.centery, project_settings.MAX_PERFRAME_DIST_MD * b.color] for b in blobs])
    pm = numpy.array([[b.centerx, b.centery, project_settings.MAX_PERFRAME_DIST_MD * b.color] for b in prevblobs])
    distmatrix = distance_matrix(pn, pm)
    a = [numpy.where(distmatrix[i] <= project_settings.MAX_PERFRAME_DIST)[0] for i in range(n)]
    b = [numpy.where((distmatrix[i] <= 2 * project_settings.MAX_PERFRAME_DIST_MD) & \
        (distmatrix[i] > project_settings.MAX_PERFRAME_DIST))[0] for i in range(n)]
    # tdistlist is initialized with closeby prevblobs with lower threshold
    tdistlists = [numpy.ndarray.tolist(a[i]) for i in range(n)]
    # higher threshold closeby prevblobs are added if other conditions are met
    for i in range(n):
        for j in b[i]:
            # full dynamic case, both frames contain moving blobs - we correct with motion blob motion:
            # both frames contain motion blob, higher threshold is satisfactory,
            # there are rarely any motion blobs closer than MAX_PERFRAME_DIST_MD
            if mdindices[i] > -1 and prevmdindices[j] > -1:
                # dx = md_blobs[mdindices[i]].centerx - prevmd_blobs[prevmdindices[j]].centerx
                # dy = md_blobs[mdindices[i]].centery - prevmd_blobs[prevmdindices[j]].centery
                # corrected_prevblob = ColorBlob(0, prevblobs[j].centerx+dx, prevblobs[j].centery+dy, 0, [])
                # d = get_distance(corrected_prevblob, blobs[i])
                tdistlists[i].append(j)
            # start of motion: prevframe is static, frame is dynamic:
            # if prev is under current motion blob, keep it
            elif mdindices[i] > -1 and prevmdindices[j] == -1 and \
                    is_point_inside_ellipse(prevblobs[j], md_blobs[mdindices[i]]):
                tdistlists[i].append(j)
            # end of motion: prevframe is dynamic, frame is static
            # if current is under prev motion blob, keep it
            elif mdindices[i] == -1 and prevmdindices[j] > -1 and \
                    is_point_inside_ellipse(blobs[i], prevmd_blobs[prevmdindices[j]]):
                tdistlists[i].append(j)

    return tdistlists


def find_chains_in_sdistlists(blobs, sdistlists, project_settings):
    """Find all color blob chains on a frame that could be real colorids
    and return them in lists for all colorids separately.

    Constraint #1: small distance between blobs in a chain
    Constraint #2: chain must be straigh enough (>120deg) to count.

    Keyword arguments:
    blobs      -- list of all blobs (ColorBlob) from the current frame
    sdistlists -- possible chain connections, created in advance by
                  create_spatial_distlists()
    project_settings -- global project-specific settings

    Uses the recursive function find_chains_in_sdistlists_recursively()

    """
    colorids = project_settings.colorids
    chainlists = [[] for x in range(len(colorids))]
    lastit = [-1 for x in range(project_settings.MCHIPS)]
    # iterate all colorids
    for k in range(len(colorids)):
        color0 = project_settings.color2int(colorids[k][0])
        # iterate all from given color (from) to find all good chains for that colorid
        fr = -1
        while fr < len(blobs) - 1:
            fr += 1
            if blobs[fr].color != color0: continue
            # store blob index (last iteration of current level)
            lastit[0] = fr
            # iterate all that are chained to the first element and find the rest recursively
            color1 = project_settings.color2int(colorids[k][1])
            for distto in sdistlists[fr][0]:
                # if the colors match
                if blobs[distto].color == color1:
                    # store blob index (last iteration of current level)
                    lastit[1] = distto
                    # iterate through all possibilities and save chains
                    find_chains_in_sdistlists_recursively(blobs, sdistlists,
                        chainlists, project_settings, lastit, k, distto, 2
                    )

    return chainlists


def find_chains_in_sdistlists_recursively(blobs, sdistlists, chainlists,
    project_settings, lastit, k, fr, i):
    """Helper function to find chains recursively.

    Should be called by itself and find_chains_in_sdistlists() only.

    Keyword arguments:
    chainlists -- the list of good chains
    k          -- colorid index
    fr         -- blob index
    i          -- current level (digit) of MCHIPS

    """
    colorids = project_settings.colorids
    # if no more chain elements needed, check good order and store chain
    if i == project_settings.MCHIPS:
        # bad order: do not store (next one is further than a later one)
        blobchain = [blobs[lastit[x]] for x in range(project_settings.MCHIPS)]
        if not is_blob_chain_appropriate_as_barcode(blobchain, project_settings.MCHIPS):
            return
        # good order: store
        chainlists[k].append([lastit[j] for j in range(project_settings.MCHIPS)])
        return

    # if more chain elements needed, call self recursively
    color = project_settings.color2int(colorids[k][i])
    for distto in sdistlists[fr][0]:
        # if the colors match
        if blobs[distto].color == color:
            # store blob index (last iteration of current level)
            lastit[i] = distto
            # increase common counter and go to next level
            find_chains_in_sdistlists_recursively(
                blobs, sdistlists, chainlists, project_settings,
                lastit, k, distto, i+1
            )


def is_blob_chain_appropriate_as_barcode(blobchain, MCHIPS, check_distance=None):
    """Decice whether a (full) chain of blobs is appropriate as a barcode.

    Keyword arguments:
    blobchain      -- list/tuple of blobs as a chain
    MCHIPS         -- number of chips / bins in a barcode
    check_distance -- optional argument to check for distance between blobs

    """
    # check absolute distance if needed
    if check_distance:
        for j in range(MCHIPS - 1):
            if get_distance(blobchain[j], blobchain[j+1]) > check_distance:
                return False

    # check for good order according to distance between blobs
    for j in range(MCHIPS - 2):
        for jj in range(j+2, MCHIPS):
            d12 = get_distance(blobchain[j], blobchain[j+1])  # 1,2
            d1x = get_distance(blobchain[j], blobchain[jj])   # 1,3
            d2x = get_distance(blobchain[j+1], blobchain[jj]) # 2,3
            if d1x < d12 or d1x < d2x:
                return False

    # bad angle: do not store (too small angle in the middle)
    for j in range(1, MCHIPS - 1):
        v1 = (blobchain[j-1].centerx - blobchain[j].centerx, blobchain[j-1].centery - blobchain[j].centery)
        v2 = (blobchain[j+1].centerx - blobchain[j].centerx, blobchain[j+1].centery - blobchain[j].centery)
        av12 = ((v1[0]**2 + v1[1]**2)**0.5) * ((v2[0]**2 + v2[1]**2)**0.5)
        if not av12:
            return False
        angle = acos(min(max((v1[0] * v2[0] + v1[1] * v2[1]) / av12, -1), 1))
        if degrees(angle) < 100:
            return False
    # no error, chain is appropriate
    return True


def find_clusters_in_sdistlists(blobs, sdistlists, level=0):
    """Find all color blob clusters on a frame that are connected
    through sdistlists and return them in lists.

    Algo also modifies the clusterindex variable of all blobs

    Keyword arguments:
    blobs      -- list of all blobs (ColorBlob) from the current frame
    sdistlists -- possible cluster connections, created in advance by
                  create_spatial_distlists()
    level      -- optional parameter to check only closest neighbors or
                  second neighbors as well (in distance)

    Uses the recursive function find_clusters_in_sdistlists_recursively()

    Returns clusterlist and clusterindex
    """
    clusterlist = []
    clusterindex = [-1 for x in range(len(blobs))]
    clusternum = -1
    # iterate all blobs
    for i in range(len(blobs)):
        # skip ones that has already been clustered
        if clusterindex[i] > -1: continue
        # create new cluster
        clusternum += 1
        clusterlist.append([])
        # add element to cluster
        clusterindex[i] = clusternum
        clusterlist[clusternum].append(i)
        for j in sdistlists[i][0] if not level else sdistlists[i][0] + sdistlists[i][1]:
            # skip ones that has already been clustered
            if clusterindex[j] > -1: continue
            # store blob in current cluster
            clusterindex[j] = clusternum
            clusterlist[clusternum].append(j)
            find_clusters_in_sdistlists_recursively(blobs, sdistlists, level,
                    clusterlist, clusterindex, clusternum, j)

    return (clusterlist, clusterindex)


def find_clusters_in_sdistlists_recursively(blobs, sdistlists, level,
        clusterlist, clusterindex, clusternum, j):
    """Helper function to find clusters recursively.

    Should be called by itself and find_clusters_in_sdistlists() only.

    Keyword arguments:
    clusterlist -- the cluster list that is returned by the parent algo
    clusternum  -- the current cluster number
    j           -- blob index to start the iteration from


    """
    for jj in sdistlists[j][0] if not level else sdistlists[j][0] + sdistlists[j][1]:
        # skip ones that has already been clustered
        if clusterindex[jj] > -1: continue
        # store blob in current cluster
        clusterindex[jj] = clusternum
        clusterlist[clusternum].append(jj)
        # call self to recursively find all cluster members
        find_clusters_in_sdistlists_recursively(blobs, sdistlists, level,
                clusterlist, clusterindex, clusternum, jj)


def barcodeindices_not_deleted(barcodeindices, barcodes, mfix=None):
    """Return subset of barcodeindices (as list) that contains non-deleted barcodes.

    Keyword arguments:
    barcodeindices -- list of barcode indices (e.g. of a blob) of BarcodeIndex
    barcodes       -- list of all barcodes (Barcode) for current frame
    mfix           -- an mfix value for and operation if needed

    """
    good = []
    for ki in barcodeindices:
        mf = barcodes[ki.k][ki.i].mfix
        if mf and not (mf & MFix.DELETED):
            if mfix is None or (mf & mfix):
                good.append(ki)
    return good


def get_not_used_blob_indices(blobs, barcodes):
    """Return subset of blobs that are not used yet.

    Keyword arguments:
    barcodes -- list of all barcodes (Barcode) for current frame
    blobs    -- list of all blobs on current frame

    """
    nub = []
    for i in range(len(blobs)):
        blob = blobs[i]
        if not barcodeindices_not_deleted(blob.barcodeindices, barcodes):
            nub.append(i)

    return nub


def update_blob_barcodeindices(barcode, k, i, blobs):
    """Update blob's barcodeindices from barcode's blobindices."""
    ki = BarcodeIndex(k, i)
    for blobi in barcode.blobindices:
        if blobi is None: continue
        if blobi not in blobs[blobi].barcodeindices:
            blobs[blobi].barcodeindices.append(ki)


def remove_blob_barcodeindex(blob, k, i):
    """Remove a given index from the blobs barcodeindices list."""
    ki = BarcodeIndex(k, i)
    while ki in blob.barcodeindices:
        del blob.barcodeindices[blob.barcodeindices.index(ki)]
