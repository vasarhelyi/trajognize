"""Methods for performing the main correlation analysis on the patek data."""

import scipy.stats.stats
from collections import defaultdict

def calculate_all_pearsonr(data):
    """
    Calculate Pearson correlation between all lines of data dict.
    """
    pearsonr = defaultdict(defaultdict)
    pvalue = defaultdict(defaultdict)
    keys = data.keys()
    for i in range(0,len(keys)):
        a = keys[i]
        for j in range(0, i+1):
            b = keys[j]
            # do not perform corr with self
            if i == j:
                pearsonr[a][b], pvalue[a][b] = 1, 0
            else:
                # same values --> no corr
                if min(data[a]) == max(data[a]) or min(data[b]) == max(data[b]):
                    pearsonr[a][b], pvalue[a][b] = 0, 1
                # good ones --> perform pearson
                else:
                    pearsonr[a][b], pvalue[a][b] = scipy.stats.stats.pearsonr(data[a], data[b])
                pearsonr[b][a], pvalue[b][a] = pearsonr[a][b], pvalue[a][b]
    return pearsonr, pvalue

