# call parameter 0: index in the files to use

# input variables: inputfile, colsumfile, inputfilesum, nID, sumxmax, sumymax


################################################################################
# main plot in the center

set pm3d map corners2color c2
splot inputfile index int(ARG1) matrix # every ::::nID:nID

################################################################################
# row sum plot on the right side

reset
unset ytics
set xrange [0:sumxmax]
if (sumxmax>=200) set xtics rotate by 90 offset 0,-int(log10(sumxmax))/2-1
set xtics 0,sumxmax/2,sumxmax
set yrange [nID:0] reverse
set lmargin at screen 0.78
set rmargin at screen 0.88
set bmargin at screen 0.15
set tmargin at screen 0.78
plot inputfilesum index int(ARG1) u (column(nID+2)):(column(0)-0.5) every ::::nID w linespoints notitle

################################################################################
# column sum plot at the top

reset
unset xtics
set yrange [0:sumymax]
set ytics 0,sumymax/2,sumymax
set xrange [0:nID]
set lmargin at screen 0.15
set rmargin at screen 0.78
set bmargin at screen 0.78
set tmargin at screen 0.88
plot colsumfile u (column(1)-0.5):3 w linespoints notitle

# end of multiplot
unset multiplot
