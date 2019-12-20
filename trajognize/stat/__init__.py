"""
===============
Trajognize stat
===============
--------------------------------
Submodule to calculate all kind of statistics on main modules's barcode output.
--------------------------------

:Author: Gabor Vasarhelyi
"""

import sys
from trajognize.stat.main import main as cli

__author__ = "Gabor Vasarhelyi"
__email__ = "vasarhelyi@angel.elte.hu"
__version__ = "0.1"

def main(argv=[]):
    if argv:
        cli(argv)
    else:
        sys.exit(cli(argv))

if __name__ == "__main__":
    main(argv)
