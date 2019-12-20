"""
==========
Trajognize
==========
--------------------------------
Trajectory reconstruction and statistical analysis for high-throughput ethology
--------------------------------

:Author: Gabor Vasarhelyi
"""

import sys
from trajognize.main import main as cli

__author__ = "Gabor Vasarhelyi"
__email__ = "vasarhelyi@angel.elte.hu"

def main(argv=[]):
    if argv:
        cli(argv)
    else:
        sys.exit(cli(argv))

if __name__ == "__main__":
    main(argv)
