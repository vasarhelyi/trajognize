""""
Constants and main classes are defined here, like blob, barcode, trajectory.
"""

from collections import namedtuple
from enum import IntEnum
from math import atan2, sin, cos, pi

################################################################################
class MFix(IntEnum):
    """mFIX values of barcodes.
    All can be bitwise OR-ed, some are mutually exclusive.
    """

    #: mfix = 0: final deletion, do not use for any reason!!!
    # ZERO = 0
    #: mfix value when a barcode is fully found (i.e. all blobs are found in it)
    FULLFOUND = 1
    #: mfix value for multiple barcodes simultaneously having the same ID
    SHARESID = 2
    #: mfix value for multiple barcodes containing the same blob
    SHARESBLOB = 4
    #: mfix value for a barcode that was found only partly, but was assigned an id based on the previous/next frame data
    PARTLYFOUND_FROM_TDIST = 8
    #: mfix value for barcodes that are probably false positive recognitions and are not needed
    DELETED = 16
    #: mfix value for barcodes that are chosen as part of the final trajectory
    CHOSEN = 32
    #: mfix value when a barcode is fully found and there is no other blobs around
    FULLNOCLUSTER = 64
    #: mfix value when a barcode is deleted and has changed id. This is the old one (kept)
    CHANGEDID = 128
    #: mfix value when a barcode is created as an elongation of a chosen traj, without blobs
    VIRTUAL = 256
    #: mfix value when a barcode is created as an elongation of a chosen traj, without blobs
    DEBUG = 512
    #: temporary mfix used for any debugging reason to see where it took effect during visualization
    DUMMY_LAST = 1024


################################################################################
class TrajState(IntEnum):
    """possible state values of trajectories (and conflicts)."""

    #: enum for a deleted trajectory
    DELETED = 0
    #: enum for a trajectory that is not yet deleted/chosen, but exists
    INITIALIZED = 1
    #: enum for a trajectory that is forced to end (e.g. at a junction)
    FORCED_END = 2
    #: enum for a trajectory that is chosen as part of the final global trajectory
    CHOSEN = 3
    #: enum for a trajectory that was false detection and color has changed
    CHANGEDID = 4


################################################################################
# named tuples for shapes
# (0,0)=(top, left) >0, v90, <180, ^270

Point = namedtuple("Point", "x y")
Circle = namedtuple(
    "Circle", "x y r a1 a2"
)  # arc1 and arc2 should be in CW [deg] from -->
Ellipse = namedtuple("Ellipse", "x y a b o")
Rectangle = namedtuple("Rectangle", "x y w h")


################################################################################
# named tuples for blob file input
ColorBlob = namedtuple("ColorBlob", "color centerx centery radius barcodeindices")
ColorBlobE = namedtuple(
    "ColorBlobE", "color centerx centery radius axisA axisB orientation barcodeindices"
)  # extended type introduced for PROJECT_FISH

MDBlob = namedtuple("MDBlob", "centerx centery axisA axisB orientation")
RatBlob = namedtuple("RatBlob", "centerx centery axisA axisB orientation")

# named tuples for color codes and other useful things
BarcodeIndex = namedtuple(
    "BarcodeIndex", "k i"
)  # k = coloridindex, i = second (final) index


################################################################################
class Variables:
    """A class for all dynamic variables as a common placeholder for quick
    load and save operations at the middle of execution.
    """

    __slots__ = (
        "colorids",
        "project_settings",
        "color_blobs",
        "md_blobs",
        "rat_blobs",
        "barcodes",
        "sdistlists",
        "tdistlists",
        "clusterlists",
        "clusterindices",
        "mdindices",
        "trajectories",
        "trajsonframe",
    )

    def __init__(self):
        """Empty initialization."""
        #: global colorid database as part of project_settings. This remaind
        #: here separately only for compatibility with older code...
        #: colorids[coloridindex] is a string with color capitals such as 'RGB'
        self.colorids = 0
        #: global project settings created by
        #: import_trajognize_settings_from_file()
        self.project_settings = None
        #: global list of all color blobs
        #: color_blobs[framenum][index] is a 'ColorBlob' object
        self.color_blobs = 0
        #: global list of all motion blobs
        #:md_blobs[framenum][index] is a 'MDBlob' object
        self.md_blobs = 0
        #: global list of all rat blobs
        #: rat_blobs[framenum][index] is a 'RatBlob' object
        self.rat_blobs = 0
        #: global list of all barcodes
        #: barcodes[framenum][coloridindex][index] is a 'Barcode' object
        self.barcodes = 0
        #: spatial distance list for all blobs containing blob indices
        #: that are close enough to be on the same rat on a given frame.
        #: sdistlists[framenum][blobindex][0,1] = [ list of blobindices ]
        self.sdistlists = 0
        #: temporal distance list for all blobs containing blob indices
        #: from the previous frame that are close enough to be the same.
        #: tdistlists[framenum][blobindex] = [ list of prev blobindices ]
        self.tdistlists = 0
        #: list of blob indices in closeness clusters
        #: clusterlists[framenum][clusterindex] = [ list of blobindices ]
        self.clusterlists = 0
        #: cluster index list for all blobs
        #: clusterindices[framenum][blobindex] = clusterindex
        self.clusterindices = 0
        #: motion blob index for all blobs (-1 if none)
        #: mdindices[framenum][blobindex] = md blob index
        self.mdindices = 0
        #: global list of all candidate trajectories
        #: trajectories[coloridindex][index] is a 'Trajectory' object
        self.trajectories = 0
        #: trajectory indices on each frame to allow quicker search, easier access
        #: trajsonframe[framenum][coloridindex] = [set of trajs present]
        #: this structure should always be consistent with trajectories structure
        self.trajsonframe = 0


class Barcode:
    """A colored barcode, consisting of (three) blobs.

    Note that the ID of the barcode is not contained in the object, it should be
    the index (coloridindex) in the array holding this object.

    """

    # Keep memory requirements low by preventing the creation of instance dictionaries.
    __slots__ = ("centerx", "centery", "orientation", "mfix", "blobindices")

    def __init__(
        self,
        centerx=0.0,
        centery=0.0,
        orientation=0.0,
        mfix=0,
        MCHIPS=3,
        blobindices=[],
    ):
        self.centerx = centerx  # [pixel]
        self.centery = centery  # [pixel]
        self.orientation = orientation  # [rad]
        self.mfix = mfix  # nobody expects the Spanish inquisition!
        self.blobindices = (
            list(blobindices) if blobindices else [None] * MCHIPS
        )  # create new list


class Trajectory:
    """A trajectory, consisting of barcodes of the same ID on consecutive frames.

    Note that the ID of the trajectory should be the index (coloridindex) in the
    array holding this object, but it is also defined in self.coloridindex to
    allow for changing the ID of false positive trajectory detections.

    Note that the frame number is not contained in the barcodeindices structure,
    because it can be calculated as firstframe + list index.

    """

    # Keep memory requirements low by preventing the creation of instance dictionaries.
    __slots__ = (
        "k",
        "firstframe",
        "barcodeindices",
        "fullfound_count",
        "fullnocluster_count",
        "colorblob_count",
        "sharesblob_count",
        "offset_count",
        "state",
    )

    def __init__(self, firstframe, coloridindex, MCHIPS):
        self.k = coloridindex  # coloridindex of the trajectory
        self.firstframe = firstframe
        self.barcodeindices = []
        self.fullfound_count = 0  # number of fullfound barcodes
        self.fullnocluster_count = (
            0  # number of fullfound barcodes that are not part of a larger cluster
        )
        self.colorblob_count = [
            0 for x in range(MCHIPS)
        ]  # number of found blobs at a given position in the barcode
        self.sharesblob_count = (
            0  # number of barcodes that share blobs with other barcodes
        )
        self.offset_count = (
            0  # arbitrary count that modifies traj score. Could decrease or increase.
        )
        self.state = TrajState.INITIALIZED


class Connections:
    """Object used by connect_chosen_trajs(), containing all info about possible
    good connections between two chosen trajs."""

    def __init__(self, fromframelimit):
        self.data = []  # list of possible connections with (k,i) traj elements
        self.fromframelimit = fromframelimit
        self.recursionlimitreached = False


class Conflict:
    """A conflict object."""

    __slots__ = ("ctype", "cwith", "firstframe", "barcodeindices", "state")

    def __init__(self, ctype, firstframe, cwith=None):
        self.ctype = ctype  # conflict type (string so far)
        self.firstframe = firstframe  # start of conflict (int)
        self.cwith = cwith  # conflict with (list of coloridindices)
        self.barcodeindices = []  # barcodes involved
        self.state = (
            TrajState.INITIALIZED
        )  # state is defined for trajs but could be used here as well


class MetaTraj:
    """A meta-trajectory, consisting of consecutive trajectories."""

    __slots__ = ("trajs", "score")

    def __init__(self, trajs):
        self.trajs = trajs
        self.score = 0
