"""
All kinds of general algorithms used by trajognize.main().
"""

from math import hypot, cos, sin, degrees
import numpy
from .project import AVG_INRAT_DIST
from .init import int2color


def calculate_running_avg(new, k, prevavg, prevstd):
    """Running average and standard deviation calculation.

    Source:
        http://en.wikipedia.org/wiki/Standard_deviation#Rapid_calculation_methods

    Parameters:
        new   -- new element to take into account
        k     -- index of element (starting from 1)
        prevavg -- previous average
        prevstd -- previous "standard deviation"

    Return:
        new running avg and std

    Note: real standard deviation at all times is sqrt(std/n)

    """
    avg = prevavg + (new - prevavg) / k
    std = prevstd + (new - prevavg) * (new-avg)

    return (avg, std)


def distance_matrix(X, Y=None):
    """Pairwise distances between rows of X or between rows of X and Y
    if Y is not None."""
    # method 0: too much scipy overhead, memory usage, and not even fast enough
    # if Y is None:
    #     return scipy.spatial.distance.pdist(X)
    # else:
    #     return scipy.spatial.distance.cdist(X, Y)

    if Y is None:
        # method 1: on self, fast and simple
        B = numpy.dot(X, X.T)
        q = numpy.diag(B)[:, None]
        return numpy.sqrt(q + q.T - 2 * B)
    else:
        # method 2: between two set of points, a bit slower
        return numpy.sqrt(numpy.sum((Y[None, :] - X[:, None]) ** 2, -1))


def get_angle_deg(a, b):
    """Calculate the angle between two blobs or barcodes -
    anything that has .orientation parameters and return it in [deg]."""
    angle = degrees(a.orientation) - degrees(b.orientation)
    while angle < 0:
        angle += 360
    while angle >= 360:
        angle -= 360
    return angle if angle < 180 else 360 - angle

def get_distance(a, b):
    """Calculate the distance between two blobs or barcodes -
    anything that has .centerx and .centery parameters."""
    return hypot(a.centerx - b.centerx, a.centery - b.centery)

def get_blob_center_on_barcode(barcode, position):
    """Calculate the center of a blob on a barcode at a given position."""
    centerx = barcode.centerx
    centery = barcode.centery
    d = position - (len(barcode.blobindices) - 1) / 2
    centerx += d * AVG_INRAT_DIST * cos(barcode.orientation)
    centery += d * AVG_INRAT_DIST * cos(barcode.orientation)

    return (centerx, centery)

def get_distance_at_position(barcode, position, blob):
    """Calculate the distance between a blob at a given position on a barcode
    and a blob."""
    centerx, centery = get_blob_center_on_barcode(barcode, position)

    return hypot(centerx - blob.centerx, centery - blob.centery)

def is_point_inside_ellipse(point, ellipse, mul=1.2):
    """Return true if point center is contained by ellipse (e.g. md blob over barcode/blob).

    TODO: if criteria is to loose, set mul back to 1.0

    Keyword arguments:
    point   -- any object that contains centerx and centery members
    ellipse -- any object that contains centerx, centery, axisA, axisB and orientation members
    mul     -- multiplicator factor to allow for enlargement of ellipse, if needed

    """
    dx = ellipse.centerx - point.centerx
    dy = ellipse.centery - point.centery
    d = hypot(dx, dy)
    # check trivial: very far
    if d > ellipse.axisA:
        return 0
    # check trivial: very close
    if d < ellipse.axisB:
        return 1
    # somewhere between close and far -> more calculations needed
    # rotate into ellipse coordinate system
    x = dx * cos(ellipse.orientation) - dy * sin(ellipse.orientation)
    y = dx * sin(ellipse.orientation) + dy * cos(ellipse.orientation)
    # check if within equation of ellipse
    if x*x/ellipse.axisA/ellipse.axisA + y*y/ellipse.axisB/ellipse.axisB <= mul*mul:
        return True
    else:
        return False


def find_md_under_blobs(color_blobs, md_blobs):
    """Fill blob's mdindices list if there is a motion blob under the blob.

    Keyword arguments:
    color_blobs -- list of all blobs (ColorBlob) from the current frame
    md_blobs -- list of all blobs (ColorBlob) from the current frame

    """
    mdindices = [-1 for i in range(len(color_blobs))]

    for i in range(len(color_blobs)):
        for j in range(len(md_blobs)):
            if is_point_inside_ellipse(color_blobs[i], md_blobs[j]):
                mdindices[i] = j
                break

    return mdindices