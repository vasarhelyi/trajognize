# call parameter 0: index of first file of common cb range
# call parameter 1: index of second file of common cb range

# input variables: inputfile
# output variables: 'cbmin' and 'cbmax' for using in 'set cbrange [cbmin:cbmax]'

reset

set out "/dev/null"
set pm3d map corners2color c2
#set data missing 'nan'
set autoscale fix
set cbrange [*:*]
cbmin = 0
cbmax = 0
splot inputfile index $0 matrix
if (cbmin>GPVAL_CB_MIN) cbmin = GPVAL_CB_MIN  
if (cbmax<GPVAL_CB_MAX) cbmax = GPVAL_CB_MAX  
splot inputfile index $1 matrix
if (cbmin>GPVAL_CB_MIN) cbmin = GPVAL_CB_MIN  
if (cbmax<GPVAL_CB_MAX) cbmax = GPVAL_CB_MAX  
