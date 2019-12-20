# trajognize

Trajognize is a set of python tools developed for the automated tracking of
objects with colored barcodes and additional statistical analysis tools for
high-throughput ethology.

It was developed at Eötvös University, Department of Biological Physics,
throughout the [EU ERC COLLMOT Research Grant](https://hal.elte.hu/flocking)
for tracking painted animals for several hours, days or even months.

Trajognize uses [ratognize](https://github.com/vasarhelyi/ratognize) output
as input, i.e., lists of individually colored blobs identified on each frame
of input videos. It creates barcodes from cohesive groups of individual blobs
on each frame and reconstructs trajectories of barcodes on series of frames.

Output generation (trajectories, statistics and plots) are also part of the
trajognize toolset.

Trajognize is designed to be efficient on computer clusters if multiple videos
are to be analyzed in parallel. The only inherently non-parallel step is the
statistical summary 'statsum', but it should be very fast.

# install

Trajognize is a python package, installation should be as simple as running:

```
python setup.py install
```

or

```
pip install -r requirements.txt
```

# usage

The final workflow of trajognize should be something like this below in order:

| **command**                  | **description**                                    | **related `queue_jobs` script on atlasz (ELTE)** |
|------------------------------|----------------------------------------------------|--------------------------------------------------|
| ratognize                    | create blob database for all videos separately     | full_run.py                                      |
| trajognize                   | create barcode database for all videos separately  | full_run__trajognize.py                          |
| trajognize stat              | create statistics for all videos separately        | full_run__statistics.py                          |
| trajognize statsum           | create summarized results for all stats            | full_run__statsum.py                             |
| trajognize plot/calc         | plot stats and create arbitrary analysis results   | -                                                |
| trajognize corr              | perform correlation analysis between the results   | -                                                |
| collect_good_params.py       | collect all correlation outputs                    | manual work needed                               |
| extract_group_descriptors.py | groupify correlation outputs                       | manual work needed                               |

Detailed help on usage is available for all python commands with '-h' or '--help'.

**Note**: In case of ELTE-specific usage, 'queue_jobs' scripts at
[hal.elte.hu/flocking](https://hal.elte.hu/flocking) are
available to run everything parallely on
[atlasz](https://hpc.iig.elte.hu/dokuwiki/doku.php).

## List of statistics implemented

| **name**        | **description**                                     |
|-----------------|-----------------------------------------------------|
| aa              | approach-avoidance behaviour                        |
| aamap           | approach-avoidance spatial distribution             |
| accdist         | distribution of accelerations                       |
| basic           | basic numeric statistics, like no. of frames etc.   |
| butthead        | heads close to other's butts                        |
| dailyfqobj      | feeding-queuing around objects on a daily basis     |
| dailyobj        | close to objects on a daily basis                   |
| dist24h         | daily distribution of barcode visibility            |
| dist24hobj      | daily distribution of visibility around objects     |
| distfromwall    | distance from wall statistics                       |
| fqfood          | feeding-queueing stat during feeding times          |
| fqobj           | feeding-queueing around objects                     |
| fqwhilef        | feeding while others are feeding or queueing        |
| heatmap         | spatial distribution of positions                   |
| motionmap       | spatial distribution of motion                      |
| nearestneighbor | nearest neighbor statistics                         |
| neighbor        | number of neighbor and pairwise neighbor statistics |
| sameiddist      | debug stat for counting false positive barcodes     |
| sdist           | distance distribution between barcodes              |
| veldist         | distribution of velocities                          |

## static pairwise parameters

The following plots are available after correlation analysis as a pairwise
summary for each experiment:

| **name**                | **description**                                     |
|-------------------------|-----------------------------------------------------|
| plot_aa.py              | approach-avoidance matrix                           |
| plot_dailyfqobj.py      | daily feeding-queuing around objects matrix         |
| plot_fqobj.py           | feeding-queueing around objects matrix              |
| plot_fqfood.py          | feeding-queuing during feeding times                |
| plot_nearestneighbor.py | nearest neighbor matrix                             |
| plot_neighbor.py        | neighbor matrix                                     |

**Note**: These plots generate a lot of output, see corr/good_params.py
 for more details on what is the suggested usable part of it.


## static params

The following outputs are available after correlation analysis as individual
descriptors for each experiment:

| **name**             | **comment**                                          |
|--------------------- |------------------------------------------------------|
| fqobj, aa, nearestn  | --> params from pairparams (normDS, LDI, BBS)        |
| plot_heatmap.py      | --> simplified stats with calc_heatmap_corroutput.py |
| plot_distfromwall.py | <-- averaged over all days                           |
| plot_dailyobj.py     | <-- averaged over all days                           |


## daily params / pairparams

The following outputs are available as dynamic output, i.e as time evolution:

| **name**                    | **comment**                                 |
|-----------------------------|---------------------------------------------|
| plot_dailyfqobj.py          | correlation output is available             |
| plot_distfromwall.py        | allday average is calculated only so far    |
| plot_dailyobj.py            | allday average is calculated only so far    |
| plot_heatmap_dailyoutput.py | allday average is calculated only so far    |
| aa, nearestneighbor         | daily stat probably contains too few events |

## outputs that cannot really be used in correlation analysis

* plot_veldist.py
* plot_sdist.py
* plot_accdist.py
* plot_dist24h.py
* plot_dist24hobj.py
* motionmap
* heatmapdiffs
* aamap
* basic