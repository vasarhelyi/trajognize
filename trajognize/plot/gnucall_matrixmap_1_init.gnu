# call parameter ARG1: index in the sum file to use
# call parameter ARG2: output file

# input variables: inputfile, colsumfile, inputfilesum, nID
# output variables: sumxmax, sumymax

reset

# general settings
set term png size 640,640 font "arial,12"
set encoding utf8
#set data missing 'nan'
set label 1 noenhanced 
set label 2 noenhanced
set title noenhanced
set key noenhanced

# get max values of sums
set table colsumfile
splot inputfilesum index int(ARG1) matrix every ::1:nID+1:nID:nID+1 
unset table
set out "/dev/null"
plot inputfilesum index int(ARG1) u (column(nID+2)):(column(0)-0.5) every ::::nID
sumxmax = GPVAL_X_MAX
plot colsumfile u 1:3
sumymax = GPVAL_Y_MAX

# set output with multiplot
set out ARG2
set multiplot

################################################################################
# default settings for the main plot

set lmargin at screen 0.15
set rmargin at screen 0.78
set bmargin at screen 0.15
set tmargin at screen 0.78
# use smooth palette
set palette model HSV defined ( 0 0.65 1 0, 5 0.65 1 1, 100 0 1 1) # HSV 0-300 degrees (300-360 excluded)
set cbrange [0:*]
set cbtics offset -1,0
set colorbox vertical user origin 0.89,0.15 size 0.04,(0.78-0.15)
# ranges, size
set autoscale fix
set yrange [*:*] reverse
set xrange [*:*]
set size ratio -1 1.15,1.15
#set origin -0.08,-0.05
# tics
set ytics scale 0 offset 1,0
set xtics scale 0 rotate by 90 offset 0,-0.5
set for [i=1:nID] ytics (ID(i) i-0.5)
set for [i=1:nID] xtics (ID(i) i-0.5)
unset key
# set labels
set ylabel "ID (dominant)" offset -0.5,0
set xlabel "ID (subordinate)" offset 0,-1.4
set label 1 at screen 0.5,0.96 center # title first line
set label 2 at screen 0.5,0.92 center # title second line
set label 3 "SUM" at screen 0.83,0.83 center
