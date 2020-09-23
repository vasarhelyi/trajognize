"""
An abstract class for all project specific settings. If a new project is
initiated, this class needs to be instantiated and fed to trajognize at startup.
If any methods in trajognize need to be differentiated according to the new
project, then these methods have to be added to this abstract class and all
project instances.
"""

from abc import ABCMeta, abstractmethod
from collections import namedtuple
from datetime import datetime
import importlib.util
from typing import Iterable


# TODO: this is redundant with init.py but otherwise we have circular imports
Point = namedtuple('Point','x y')


def import_trajognize_settings_from_file(filename):
    """Import the first TrajognizeSettingsBase object instantiation found in the
    given file.

    Parameters:
        filename(Path) - the file that contains preferably one and only
            instantiation of the TrajectorySettings abstract class. In other
            words, this file should contain all your project-specific settings
            in the proper format.

    Return:
        the first proper class found in the file or None if not found.
    """
    spec = importlib.util.spec_from_file_location("", filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name, obj in module.__dict__.items():
        if type(obj).__name__ == "ABCMeta" and \
                name != "TrajognizeSettingsBase" and \
                issubclass(obj, TrajognizeSettingsBase):
            return obj()

    return None


class FindBestTrajectoriesSettings():
    """Class containing parameters for find_best_trajectories() in
    algo_trajectory.py"""
    def __init__(self,
            might_be_bad_score_threshold=100,
            might_be_bad_sum_good_score_threshold=200,
            good_for_sure_score_threshold=500,
            good_score_threshold=100,
            framelimit=1500):
        self.might_be_bad_score_threshold = might_be_bad_score_threshold
        self.might_be_bad_sum_good_score_threshold = might_be_bad_sum_good_score_threshold
        self.good_for_sure_score_threshold = good_for_sure_score_threshold
        self.good_score_threshold = good_score_threshold
        self.framelimit = framelimit


class TrajognizeSettingsBase(metaclass=ABCMeta):
    """This class is the main abstract settings class of trajognize that should
    contain all project specific variables and methods that need to be
    instantiated in every single project. See method documentations for details.
    """

    ############################################################################
    # implemented methods that should NOT be overwritten

    def __init__(self):
        """This is the base class constructor that needs to be called after
        the instantiated class is initialized."""

        # define number of colors (colorid base) based on color names.
        self._MBASE = len(self.color_names)
        # define color lookup table (int -> char)
        self._int2color_lookup = "".join([self.color_names[i].upper()[0]
            for i in range(self._MBASE)
        ])
        # define color lookup table (char -> int)
        self._color2int_lookup = dict([(self.color_names[i].upper()[0], i)
            for i in range(self._MBASE)
        ])

    def color2int(self, color: str) -> int:
        """Return the index of the color initial within your color names."""
        return self._color2int_lookup[color]

    def int2color(self, index) -> str:
        """Return the first capital letter of the indexed color name."""
        return self._int2color_lookup[index]

    @property
    def MBASE(self) -> int:
        """Number of colors (colorid base) based on color names."""
        return self._MBASE

    ############################################################################
    # implemented methods that provide convenient default settings but
    # might be overwritten if needed. These are mostly related to our first
    # large-scale rat experiment (2011) and are not relavant in other projects.

    @property
    def use_cage(self) -> bool:
        """Define whether you would like to use cage-specific data detected
        previously by ratognize. This is not needed most of the time as it was
        introduced for our original project when during 11 months the cage in
        which we kept the rats to be detected got pushed away several times
        and we needed to correct for its position automatically."""
        return False

    @property
    def cage_center(self) -> Point:
        """Define the center of the cage in an ideal/averaged case in pixels.
        If cage-specific code is not used, set it to any value as a placeholder.
        """
        return Point(self.image_size.x // 2, self.image_size.y // 2)

    @property
    def correct_cage(self):
        """Define, whether we should use dynamic cage correction data for
        cage center estimation. Normally, you do not need to play with this
        parameter."""
        return True

    @property
    def filter_for_valid_cage(self):
        """Define, whether we should filter results for valid group cage.
        Note: if not indicated in results file, no filter was used
        Normally, you do not need to play with this parameter."""
        return True

    @property
    def all_light(self) -> Iterable[str]:
        """Define the names of all light conditions that are used in the
        experiments. Usually this should be a single 'NIGHTLIGHT' placeholder
        for convenience, we used multiple light conditions in our first
        experiment..."""
        return ["NIGHTLIGHT"]

    @property
    def good_light(self) -> Iterable[str]:
        """Define the names of good light conditions that are used in the
        experiments. Usually this should be a single 'NIGHTLIGHT' placeholder
        for convenience, we used multiple light conditions in our first
        experiment..."""
        return ["NIGHTLIGHT"]

    ############################################################################
    # abstract methods that need project-specific instantiation

    @property
    @abstractmethod
    def project_name(self) -> str:
        """Define the name of your project here."""
        ...

    @property
    @abstractmethod
    def FPS(self) -> float:
        """Define the main (deinterlaced) framerate of your input video
        in frames per second."""
        ...

    @property
    @abstractmethod
    def image_size(self) -> Point:
        """Define the width and height of your input video in pixels."""
        ...

    @property
    @abstractmethod
    def MCHIPS(self) -> int:
        """Define the number of chips / bins / colored blobs in a colorid
        in your barcodes to be detected."""
        ...

    @property
    @abstractmethod
    def color_names(self) -> Iterable[str]:
        """Define the name of your colors that are used in your barcodes.
        Be careful to have the same order as in ratognize and also be careful
        to define color names with different initials."""
        ...

    @property
    @abstractmethod
    def MAX_INRAT_DIST(self) -> float:
        """Define the maximum distance between two neighboring blobs on the same
        rat (barcode) in pixels.

        Hint: after running ratognize, use the test/check_blob_distributions.py
        script to get some statistics from which this parameter can be set up
        properly.
        """
        ...

    @property
    @abstractmethod
    def AVG_INRAT_DIST(self) -> float:
        """Define the average distance between two neighboring blobs on the same
        rat (barcode) in pixels.

        Hint: after running ratognize, use the test/check_blob_distributions.py
        script to get some statistics from which this parameter can be set up
        properly.
        """
        ...

    @property
    @abstractmethod
    def MAX_PERFRAME_DIST(self) -> float:
        """Define the maximum distance a blob travels between two consecutive
        frames in pixels.

        Hint: after running ratognize, use the test/check_blob_distributions.py
        script to get some statistics from which this parameter can be set up
        properly.
        """
        ...

    @property
    @abstractmethod
    def MAX_PERFRAME_DIST_MD(self) -> float:
        """Define the maximum distance a blob travels between two consecutive
        frames in pixels, when there is an md blob under it.

        Hint: after running ratognize, use the test/check_blob_distributions.py
        script to get some statistics from which this parameter can be set up
        properly.
        """
        ...

    @property
    @abstractmethod
    def MAX_PERFRAME_ANGLE(self) -> float:
        """Define the maximum angle a barcode rotates on a frame in degrees."""
        ...

    @property
    @abstractmethod
    def traj_score_method(self) -> int:
        """Define the index of the method that is used in the traj_score
        calculation. Traj score is a heuristic function, feel free to
        implement more versions based on your project needs.
        Possible values are 1 or 2 currently, see code for details."""
        ...

    @property
    @abstractmethod
    def find_best_trajectories_settings(self) -> FindBestTrajectoriesSettings:
        """Define parameters for the find_best_trajectories() function in
        algo_trajectory.py using the FindBestTrajectoriesSettings class.
        """
        ...

    @abstractmethod
    def get_datetime_from_filename(self, filename):
        """Return datetime object parsed from input video file names.

        It is useful only if you have multiple input files.
        If you do not want to use time, just return some const datetime object.

        Parameters:
            filename(Path): input file name that contains date and time, e.g. using
                format YYYY-MM-DD_HH-MM-SS.SSSSSS
        """
        ...
