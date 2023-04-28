"""
An abstract class for all project specific settings. If a new project is
initiated, this class needs to be instantiated and fed to trajognize at startup.
If any methods in trajognize need to be differentiated according to the new
project, then these methods have to be added to this abstract class and all
project instances.
"""


from abc import ABCMeta, abstractmethod
from datetime import datetime
import importlib.util
from itertools import chain
from typing import Any, Callable, Dict, Sequence
import os

from trajognize.init import Point


def import_trajognize_settings_from_file(filename):
    """Import the first TrajognizeSettingsBase class found in the given file
    and return its instantiation.

    Parameters:
        filename(Path) - the file that contains preferably one and only
            subclass of the TrajectorySettingsBase abstract class. In other
            words, this file should contain all your project-specific settings
            in the proper format.

    Return:
        instantiation of first proper class found in the file
        or None if file or class not found.
    """
    spec = importlib.util.spec_from_file_location("", filename)
    if spec is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name, obj in module.__dict__.items():
        if (
            type(obj).__name__ == "ABCMeta"
            and name != "TrajognizeSettingsBase"
            and issubclass(obj, TrajognizeSettingsBase)
        ):
            return obj()

    return None


class AASettings:
    """Class containing parameters of the approach-avoidance statistic."""

    def __init__(
        self,
        distance_threshold=400,  # 200 # [px]
        approacher_velocity_threshold=3,  # [px/frame]
        avoider_velocity_threshold=3,  # [px/frame]
        min_event_count=3,  # 1 <= min_event_count <= min_event_length
        cos_approacher_threshold=0.8,
        cos_avoider_threshold=0.5,
        min_event_length=10,
    ):
        self.distance_threshold = distance_threshold
        self.approacher_velocity_threshold = approacher_velocity_threshold
        self.avoider_velocity_threshold = avoider_velocity_threshold
        self.min_event_count = min_event_count
        self.cos_approacher_threshold = cos_approacher_threshold
        self.cos_avoider_threshold = cos_avoider_threshold
        self.min_event_length = min_event_length


class FindBestTrajectoriesSettings:
    """Class containing parameters for find_best_trajectories() in
    algo_trajectory.py"""

    def __init__(
        self,
        might_be_bad_score_threshold=100,
        might_be_bad_sum_good_score_threshold=200,
        good_for_sure_score_threshold=500,
        good_score_threshold=100,
        framelimit=1500,
    ):
        self.might_be_bad_score_threshold = might_be_bad_score_threshold
        self.might_be_bad_sum_good_score_threshold = (
            might_be_bad_sum_good_score_threshold
        )
        self.good_for_sure_score_threshold = good_for_sure_score_threshold
        self.good_score_threshold = good_score_threshold
        self.framelimit = framelimit


class ExperimentInitializer:
    """Class for initializing experiments."""

    def __init__(
        self, experiments: Dict, get_wall_polygons: Callable[[Dict, Dict], Dict]
    ):
        """Constructor. Experiments is a dict defined as in
        TrajognizeSettingsBase.experiment."""
        self._experiments = self._initialize_experiments(experiments, get_wall_polygons)

    def _initialize_experiments(
        self, experiments: Dict, get_wall_polygons: Callable[[Dict, Dict], Dict]
    ) -> Dict:
        """This functions should be called once on init to add some important
        automatically calculated parameters to the experiments dictionary.
        """
        # add lookup table to get group identifiers for strids quickly
        for name in experiments:
            experiment = experiments[name]
            experiment["name"] = name
            experiment["groupid"] = dict()
            experiment["wall"] = dict()  # flat ground territory without cage + home
            experiment["wallall"] = dict()  # full territory including cage + home
            experiment["area"] = dict()  # flat ground territory without cage + home
            experiment["areaall"] = dict()  # full territory including cage + home
            colorids = []
            for group in experiment["groups"]:
                colorids += experiment["groups"][group]
                for strid in experiment["groups"][group]:
                    experiment["groupid"][strid] = group
                (
                    experiment["wall"][group],
                    experiment["wallall"][group],
                ) = get_wall_polygons(experiments[name], group)
                experiment["area"][group] = self._get_polygonlist_area(
                    experiment["wall"][group]
                )
                experiment["areaall"][group] = self._get_polygonlist_area(
                    experiment["wallall"][group]
                )
            experiment["colorids"] = sorted(list(set(colorids)))

        # TODO: add anything else that is useful to have in the experiments dict itself

        return experiments

    def _get_polygonlist_area(self, polys):
        """Return the summarized area of the polygon list.

        Parameters:
            polys - polys returned by get_wall_polygons()

        Return:
            summarized area of all polys in list

        """
        return sum(
            0.5
            * abs(
                sum(
                    x0 * y1 - x1 * y0 for ((x0, y0), (x1, y1)) in zip(p, p[1:] + [p[0]])
                )
            )
            for p in polys
        )

    def asdict(self):
        """Return the experiments (which is the core of this class)
        as a dictionary."""
        return self._experiments


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
        self._int2color_lookup = "".join(
            [self.color_names[i].upper()[0] for i in range(self._MBASE)]
        )
        # define color lookup table (char -> int)
        self._color2int_lookup = dict(
            [(self.color_names[i].upper()[0], i) for i in range(self._MBASE)]
        )
        # re-initialize experiments
        self.experiments = ExperimentInitializer(
            self.experiments, self.get_wall_polygons
        ).asdict()
        # initialize colorids
        self._colorids = sorted(
            list(
                set(
                    chain.from_iterable(
                        exp["colorids"] for exp in self.experiments.values()
                    )
                )
            )
        )

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
    def colorids(self) -> Sequence[str]:
        """Define the colorids of your project as a list of barcode color
        abbreviations (first capital letter of each color in proper order).
        Example: ["RGB", "GRB"], if you are about to recognize two barcodes,
        one as Red-Green-Blue, the other one as Green-Red-Blue. Be careful to
        avoid definitions that result in existing colorids if read backwards.

        By default, colorids is initialized automatically as a union of all
        colorids defined in the experiment database (value of self._colorids).
        """
        return self._colorids

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
    def all_light(self) -> Sequence[str]:
        """Define the names of all light conditions that are used in the
        experiments. Usually this should be a single 'NIGHTLIGHT' placeholder
        for convenience, we used multiple light conditions in our first
        experiment..."""
        return ["NIGHTLIGHT"]

    @property
    def good_light(self) -> Sequence[str]:
        """Define the names of good light conditions that are used in the
        experiments. Usually this should be a single 'NIGHTLIGHT' placeholder
        for convenience, we used multiple light conditions in our first
        experiment..."""
        return ["NIGHTLIGHT"]

    @property
    def weekly_feeding_times(self) -> dict:
        """Weekly feeding times in long experiments. Dict keys should be days.
        The value for each day should be a list containing a list of tuples
        of (start, duration) expressed in hours. Day is same as
        datetime.weekday(), 0 is Monday, 6 is Sunday.
        list imported (but reformatted) from
        SVN: rat-project/hdpvr_recorder/feeder_daemon.py

        Leave it empty like below if you do not know why this is relevant.
        """
        return {
            "monday": [],
            "tuesday": [],
            "wednesday": [],
            "thursday": [],
            "friday": [],
            "saturday": [],
            "sunday": [],
        }

    @property
    def object_types(self) -> Sequence[str]:
        """Define names of interesting fixed objects on the scene."""
        return []

    @property
    def object_areas(self) -> dict:
        """Define areas of objects. Dictionary keys should be the object names,
        their area should be defined as dict values using Rectangle or Circle
        namedtuples/dataclasses. Center (and arc) is defined in the experiment,
        these objects should be placed on those centers concentrically.
        """
        return {}

    @property
    def object_queuing_areas(self) -> dict:
        """Define queuing areas of objects similarly to object_areas.
        Center is defined in the experiment, object areas are defined above.
        These objects should be placed on these concentrically, except when
        center (offset) is defined here.
        If so, it is - if above midline, + if below
        if queuing is not used, all params are zero.
        """
        return {}

    def get_unique_output_filename(self, outputpath: str, inputfile: str) -> str:
        """Get unique output filename for statsum if '-u' is specified, meaning
        that daily results will be written to this filename returned.

        Parameters:
            outputpath(Path) - the path where the file will be written
            inputfile(Path) - the trajognize stat .zip output file from which
                we are going to create a unique output

        Return:
            filename with full path pointing to unique output to be created
        """
        return os.path.join(
            outputpath,
            os.path.split(os.path.split(os.path.split(inputfile)[0])[0])[1]
            + "__"
            + os.path.splitext(os.path.split(inputfile)[1])[0]
            + ".txt",
        )

    def get_wall_polygons(self, experiment: Dict, group: str):
        """Get two wall polygons for a given experiment, possibly using
        object definitions. This needed to be automated in our first long-term
        rat experiment, since then it is not really used...

        Parameters:
            experiment - an experiment from self.experiments
            group - the name of a group within the given experiment

        Return:
            The first poly, 'wall'/'area' will be the flat territory enabled
            for the animals to move on, for distance from wall stat
            The second poly, 'wallall'/'areaall' will be the full territory
        """
        polys = [[]]
        polysall = [[]]
        i = 0

        # define better if needed, this is the full image frame

        # top left
        polys[i].append(Point(0, 0))
        polysall[i].append(Point(0, 0))
        # top right
        polys[i].append(Point(self.image_size.x, 0))
        polysall[i].append(Point(self.image_size.x, 0))
        # bottom right
        polys[i].append(Point(self.image_size.x, self.image_size.y))
        polysall[i].append(Point(self.image_size.x, self.image_size.y))
        # bottom left
        polys[i].append(Point(0, self.image_size.y))
        polysall[i].append(Point(0, self.image_size.y))

        return (polys, polysall)

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
    def color_names(self) -> Sequence[str]:
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
    def stat_aa_settings(self) -> AASettings:
        """Define parameters for the AA() approach-avoidance stat class."""
        ...

    @property
    @abstractmethod
    def find_best_trajectories_settings(self) -> FindBestTrajectoriesSettings:
        """Define parameters for the find_best_trajectories() function in
        algo_trajectory.py using the FindBestTrajectoriesSettings class.
        """
        ...

    @abstractmethod
    def get_datetime_from_filename(self, filename) -> datetime:
        """Return datetime object parsed from input video file names.

        If you have multiple input files, this function enables you to associate
        each input file with a given date and thus a given experiment, to be
        able to create experiment-specific statistics automatically.

        If you do not want to use multiple experiments or time-dependent
        analysis, just return some const datetime object that does not hurt.

        Parameters:
            filename(Path): input file name that contains date and time, e.g.
                using format YYYY-MM-DD_HH-MM-SS.SSSSSS

        Return:
            datetime object parsed from the file, corresponding to video start
        """
        ...

    @property
    @abstractmethod
    def max_day(self) -> int:
        """Define maximum number of days in an experiment."""
        ...

    @property
    @abstractmethod
    def experiments(self) -> Dict[str, Dict[str, Any]]:
        """Experiment dictionary. Each key should be the name of the given
        experiment, each value is a sub-dictionary, containing the following
        required string key descriptors for each experiment:

            'number' (int) - the number of the experiment
            'description' (str) - a long description of the experiment
            'start' (datetime) - the starting time of the experiment
            'stop'  (datetime) - the ending time of the experiment
            'groups' (Dict[List[str]]) - colorids according to barcode subgroups
                if no subgroups are used, all colorids should be placed in one
                group.

        Any other string key description is treated as an object:

            'object' (List[Union[Circle, Point]]) - any object, where
                Points and Circle origins define object center coordinates
                in a top-left = 0,0 , x --> right, y --> down coordinate system,
                angles for Circle are defined along --> CW [deg],
                i.e. >0, v90, <180, ^270. Object areas and queuing areas are
                defined separately, with the same object names as defined here.
        """
        ...
