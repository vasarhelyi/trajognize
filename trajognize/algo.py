"""
All kinds of general algorithms used by trajognize.main().
"""

from math import hypot, cos, sin
from trajognize.init import int2color


def calculate_running_avg(new, k, prevavg, prevstd):
    """Running average and standard deviation calculation.
    
    Source:
    http://en.wikipedia.org/wiki/Standard_deviation#Rapid_calculation_methods

    Keyword arguments:
    new   -- new element to take into account
    k     -- index of element (starting from 1)
    prevavg -- previous average
    prevstd -- previous "standard deviation"
    
    Return value is new running avg and std.
    Note: real standard deviation at all times is sqrt(std/n)

    """
    avg = prevavg + (new - prevavg)/k
    std = prevstd + (new - prevavg)*(new-avg)
    
    return (avg, std)


def get_distance(a, b):
    """Calculate the distance between two blobs or barcodes -
    anything that has .centerx and .centery parameters."""
    return hypot(a.centerx - b.centerx, a.centery - b.centery)
    

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
    color_blobs -- list of all blobs (color_blob_t) from the current frame
    md_blobs -- list of all blobs (color_blob_t) from the current frame

    """
    mdindices = [-1 for i in xrange(len(color_blobs))]
    
    for i in xrange(len(color_blobs)):
        for j in xrange(len(md_blobs)):
            if is_point_inside_ellipse(color_blobs[i], md_blobs[j]):
                mdindices[i] = j
                break

    return mdindices