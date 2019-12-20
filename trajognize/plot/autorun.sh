#!/bin/sh

python plot_accdist.py ~/results/full_run__statsum/done/statsum_accdist/stat_*.txt
python plot_veldist.py ~/results/full_run__statsum/done/statsum_veldist/stat_*.txt
python plot_sdist.py ~/results/full_run__statsum/done/statsum_sdist/stat_*.txt
python plot_nearestneighbor.py ~/results/full_run__statsum/done/statsum_nearestneighbor/stat_*.txt
python plot_neighbor.py ~/results/full_run__statsum/done/statsum_neighbor/stat_*.txt
python plot_aa.py ~/results/full_run__statsum/done/statsum_aa/stat_*.txt
python plot_heatmap.py ~/results/full_run__statsum/done/statsum_aamap/stat_*.txt
python plot_fqobj.py ~/results/full_run__statsum/done/statsum_fqobj/stat_*.txt
python plot_fqfood.py ~/results/full_run__statsum/done/statsum_fqfood/stat_*.txt
python plot_dailyobj.py ~/results/full_run__statsum/done/statsum_dailyobj/stat_*.txt
python plot_distfromwall.py ~/results/full_run__statsum/done/statsum_distfromwall/stat_*.txt
python plot_bodymass.py ~/results/full_run__statsum/done/meassum_bodymass/meas_*.txt
python plot_wounds.py ~/results/full_run__statsum/done/meassum_wounds/meas_*.txt



python plot_dailyfqobj.py ~/results/full_run__statsum/done/statsum_dailyfqobj/stat_*.txt
python plot_dailyranks.py ~/results/full_run__statsum/done/statsum_dailyfqobj/reorder_matrixfile_eades/stat_*.txt

python ../calc/calc_heatmap_dailyoutput.py ~/results/full_run__statsum/done/statsum_heatmap_dailyoutput
python plot_heatmap_dailyoutput.py ~/results/full_run__statsum/done/statsum_heatmap_dailyoutput/calc_heatmap_dailyoutput/calc_heatmap_dailyoutput*.txt

# create symbolic links for all subclass dist24h files in the common directory before plotting
ln -s -t ~/results/full_run__statsum/done/statsum_dist24h/  ~/results/full_run__statsum/done/statsum_dist24h/statsum_dist24h.*/stat_*.txt
python plot_dist24h.py ~/results/full_run__statsum/done/statsum_dist24h/stat_*.txt

# create symbolic links for all subclass dist24hobj files in the common directory before plotting
ln -s -t ~/results/full_run__statsum/done/statsum_dist24hobj/  ~/results/full_run__statsum/done/statsum_dist24hobj/statsum_dist24hobj.*/stat_*.txt
python plot_dist24hobj.py ~/results/full_run__statsum/done/statsum_dist24hobj/stat_*.txt
# create symbolic links for .zip also for avgfooddist24hobj calculation
ln -s -t ~/results/full_run__statsum/done/statsum_dist24hobj/  ~/results/full_run__statsum/done/statsum_dist24hobj/statsum_dist24hobj.*/stat_*.zip
python ../calc/calc_dist24hobj_avgfood.py ~/results/full_run__statsum/done/statsum_dist24hobj/
python plot_avgfooddist24hobj.py ~/results/full_run__statsum/done/statsum_dist24hobj/calc_dist24hobj_avgfood/calc_avgfood*.txt

# create symbolic links for all subclass heatmap files in the common directory before plotting
ln -s -t ~/results/full_run__statsum/done/statsum_heatmap/  ~/results/full_run__statsum/done/statsum_heatmap/statsum_heatmap.*/stat_*.txt
python plot_heatmap.py ~/results/full_run__statsum/done/statsum_heatmap/stat_*.txt
python ../calc/calc_heatmap_corroutput.py ~/results/full_run__statsum/done/statsum_heatmap/

# create symbolic links for .zip files, too, because they are needed for heatmapdiff
ln -s -t ~/results/full_run__statsum/done/statsum_heatmap/  ~/results/full_run__statsum/done/statsum_heatmap/statsum_heatmap.*/stat_*.zip
python ../calc/calc_heatmapdiff.py ~/results/full_run__statsum/done/statsum_heatmap/stat_*.txt
python plot_heatmap.py ~/results/full_run__statsum/done/statsum_heatmap/calc_heatmapdiff/stat_*.txt

# create symbolic links for all subclass motionmap files in the common directory before plotting
ln -s -t ~/results/full_run__statsum/done/statsum_motionmap/  ~/results/full_run__statsum/done/statsum_motionmap/statsum_motionmap.*/stat_*.txt
python plot_heatmap.py ~/results/full_run__statsum/done/statsum_motionmap/stat_*.txt
python ../calc/calc_motionmap_corroutput.py ~/results/full_run__statsum/done/statsum_motionmap/

# create symbolic links for .zip files, too, because they are needed for heatmapdiff
ln -s -t ~/results/full_run__statsum/done/statsum_motionmap/  ~/results/full_run__statsum/done/statsum_motionmap/statsum_motionmap.*/stat_*.zip
python ../calc/calc_heatmapdiff.py ~/results/full_run__statsum/done/statsum_motionmap/stat_*.txt
python plot_heatmap.py ~/results/full_run__statsum/done/statsum_motionmap/calc_heatmapdiff/stat_*.txt


