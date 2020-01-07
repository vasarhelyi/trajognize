"""
Miscellaneous statistical functions for dominance hierarchy analysis.
"""

import collections, math


def feedback_arc_set_eades(W, max_noedge_value=0):
    """Calculates a feedback arc set of the graph using the Eades algorithm

    source: http://bazaar.launchpad.net/~igraph/igraph/0.6-main/view/head:/src/feedback_arc_set.c#L190

    A feedback arc set is a set of edges whose removal makes the graph acyclic.
    We are usually interested in minimum feedback arc sets, i.e. sets of edges
    whose total weight is minimal among all the feedback arc sets.

    The Eades algorithm:
    Finds a feedback arc set using the heuristic of Eades, Lin and
    Smyth (1993). This is guaranteed to be smaller than |E|/2 - |V|/6,
    and it is linear in the number of edges (i.e. O(|E|)).
    For more details, see Eades P, Lin X and Smyth WF: A fast and effective
    heuristic for the feedback arc set problem. In: Proc Inf Process Lett
    319-323, 1993.

    TODO: Check for is_number(.) and exclude not valid elements from calculation, but how?

    Keyword arguments:
    W                -- input weight matrix (square 2D dict/list), where W[IDfrom][IDto] = weight
    max_noedge_value -- maximum value for not treating a matrix element as an edge (0,0.5,etc.)

    Return value:
    ordered list of IDs (keys/indices of W)

    """
    n = len(W)
    if isinstance(W, dict):
        keys = list(W) # keys of input data dict
    elif isinstance(W, list):
        keys = range(n) # indices in the input data list matrix
    else:
        0/0

    ordering = collections.defaultdict() # ordering[ID] = order value (source bottom, sink top)

    order_next_pos = 0
    order_next_neg = -1
    sources = []
    sinks = []
    indegrees = collections.defaultdict() # [ID]
    outdegrees = collections.defaultdict() # [ID]
    instrengths = collections.defaultdict() # [ID]
    outstrengths = collections.defaultdict() # [ID]
    nodes_left = n

    # initialize values
    for j in keys:
        outdegrees[j] = 0
        outstrengths[j] = 0
        indegrees[j] = 0
        instrengths[j] = 0

    # calculate degrees and strengths (only >0 values)
    for j in keys:
        for k in keys:
            if W[j][k] > max_noedge_value:
                outdegrees[j] += 1
                outstrengths[j] += W[j][k]
                indegrees[k] += 1
                instrengths[k] += W[j][k]

    # Find initial sources and sinks
    for j in keys:
        if not indegrees[j]:
            if not outdegrees[j]:
                # Isolated vertex, we simply ignore it (push to bottom)
                ordering[j] = order_next_neg
                order_next_neg -= 1
                nodes_left -= 1
                # Exclude the node from further searches
                indegrees[j] = -1
                outdegrees[j] = -1
            else:
                sources.append(j)
        elif not outdegrees[j]:
            sinks.append(j)

    # sort initial sources and sinks
    sources.sort(lambda x, y: cmp(outstrengths[y] - instrengths[y], outstrengths[x] - instrengths[x])) # descending
    sinks.sort(lambda x, y: cmp(outstrengths[x] - instrengths[x], outstrengths[y] - instrengths[y])) # ascending

    # While we have any nodes left...
    while nodes_left:
        # (1) Remove the sources one by one
        while sources:
            j = sources.pop(0) # TODO: any ordering for independent sources?
            # Add the node to the ordering
            ordering[j] = order_next_pos
            order_next_pos += 1
            nodes_left -= 1
            # Exclude the node from further searches
            indegrees[j] = -1
            outdegrees[j] = -1
            # Get the neighbors and decrease their degrees
            for k in keys:
                if W[j][k] > max_noedge_value: # k = neighbor below
                    # Already removed, continue
                    if indegrees[k] <= 0: continue
                    indegrees[k] -= 1
                    instrengths[k] -= W[j][k]
                    if not indegrees[k]:
                        sources.append(k)

        # (1) Remove the sinks one by one
        while sinks:
            j = sinks.pop(0) # TODO: any ordering for independent sinks?
            # Maybe the vertex became sink and source at the same time, hence it
            # was already removed in the previous iteration. Check it.
            if indegrees[j] < 0: continue
            # Add the node to the ordering
            ordering[j] = order_next_neg
            order_next_neg -= 1
            nodes_left -= 1
            # Exclude the node from further searches
            indegrees[j] = -1
            outdegrees[j] = -1
            # Get the neighbors and decrease their degrees
            for k in keys:
                if W[k][j] > max_noedge_value: # k = neighbor above
                    # Already removed, continue
                    if outdegrees[k] <= 0: continue
                    outdegrees[k] -= 1
                    outstrengths[k] -= W[k][j]
                    if not outdegrees[k]:
                        sinks.append(k)


        # (3) No more sources or sinks. Find the node with the largest
        # difference between its out-strength and in-strength
        v = None
        maxdiff = -float('Inf')
        for j in keys:
            if outdegrees[j] < 0: continue
            diff = outstrengths[j] - instrengths[j]
            if diff > maxdiff:
                maxdiff = diff
                v = j
        if v:
            # Remove vertex v
            ordering[v] = order_next_pos
            order_next_pos += 1
            nodes_left -= 1
            # Exclude the node from further searches
            indegrees[v] = -1
            outdegrees[v] = -1;
            # Remove outgoing edges
            for k in keys:
                if W[v][k] > max_noedge_value: # k = neighbor below
                    # Already removed, continue
                    if indegrees[k] <= 0: continue
                    indegrees[k] -= 1
                    instrengths[k] -= W[v][k]
                    if not indegrees[k]:
                        sources.append(k)
            # Remove incoming edges
            for k in keys:
                if W[k][v] > max_noedge_value: # k = neighbor above
                    # Already removed, continue
                    if outdegrees[k] <= 0: continue
                    outdegrees[k] -= 1
                    outstrengths[k] -= W[k][v]
                    if not outdegrees[k]:
                        sinks.append(k)

    # Tidy up the ordering
    for j in keys:
        if ordering[j] < 0:
            ordering[j] += n

    # Find the feedback edges based on the ordering
    # TODO: implement if needed
    # http://bazaar.launchpad.net/~igraph/igraph/0.6-main/view/head:/src/feedback_arc_set.c#L366

    # If we have also requested a layering, return that as well
    # TODO: implement if needed
    # http://bazaar.launchpad.net/~igraph/igraph/0.6-main/view/head:/src/feedback_arc_set.c#L377

    # create ordering in changed format (from [ID] = order to [order] = ID)
    tmp = range(len(ordering))
    for j in ordering:
        tmp[ordering[j]] = j

    # return ordering
    return tmp


def dominance_transitivity(W, idorder=None, max_noedge_value=0):
    """Calculates the upper triangle weights with respect to the lower triangle weights
    Only valid numbers are included in the calculation.

    Keyword arguments:
    W                -- input weight matrix (square 2D dict/list), where W[IDfrom][IDto] = weight.
    idorder          -- order of keys/indices of W, where order[i] = ID
    max_noedge_value -- maximum value for not treating a matrix element as an edge (0,0.5,etc.)

    Return value:
    transitivity = ( sum Wup>0 / ( sum Wup>0 + sum Wdown>0) )

    """
    n = len(W)
    upper = 0
    lower = 0
    if idorder is None:
        if isinstance(W, dict):
            idorder = list(W) # TODO: this case is not defined well!!!
        elif isinstance(W, list):
            idorder = range(n)
        else:
            0/0
    for j in range(0, n-1): # from
        for k in range(j+1, n): # to
            if W[idorder[j]][idorder[k]] > max_noedge_value:
                upper += W[idorder[j]][idorder[k]]
            if W[idorder[k]][idorder[j]] > max_noedge_value:
                lower += W[idorder[k]][idorder[j]]

    # return efficiency (based on only the >max_noedge_value weights)
    if not upper and not lower:
        return 0
    elif not upper + lower:
        print("WARNING: TODO dominance_transitivity: what to do if upper+lower == 0?")
        return 0
    else:
        return upper/(upper+lower)


def decompose_CD(W, idorder=None, s_index_power = 1):
    """Calculate Common - Dominant matrix decomposition

    Warning: works well for positive matrices
    Check for NaN is included, not valid elements are excluded from calculation.

    W = C + D
    C_ij = min(w_ij,w_ji)
    D_ij = W_ij>W_ji?W_ij-W_ji:0
    s_index = sum_i!=j(C_ij**x)/sum_i!=j(W_ij**x), where x should be 1 or 2

    Keyword arguments:
    W             -- input weight matrix (square 2D dict/list), where W[IDfrom][IDto] = weight.
    idorder       -- order of keys/indices of W, where order[i] = ID
    s_index_power -- x in the equation of s_index above, should be 1 or 2

    Return value is a tuple (C, D, s_index, R):
    C       -- common activity matrix C (common part with reversals)
    D       -- dominance matrix D (dominant part without reversals)
    s_index -- global symmetry index (0.5-1) (-1 on error)
    R       -- competitive relationship matrix R ( min(i,j) * min(i,j)/max(i,j) )

    """
    n = len(W)
    if idorder is None:
        if isinstance(W, dict):
            idorder = list(W) # TODO: this case is not defined well!!!
        elif isinstance(W, list):
            idorder = range(n)
        else:
            0/0

    C = collections.defaultdict(collections.defaultdict)
    D = collections.defaultdict(collections.defaultdict)
    R = collections.defaultdict(collections.defaultdict)
    s_index = [0, 0]

    # calculate D, C and s_index
    for i in idorder:
        for j in idorder:
            # check for NaN
            if W[i][j] != W[i][j] or W[j][i] != W[j][i]:
                D[i][j] = float('nan')
                C[i][j] = float('nan')
                R[i][j] = float('nan')
                continue
            # D and C
            if W[i][j] > W[j][i]:
                D[i][j] = W[i][j] - W[j][i] # max - min
                C[i][j] = W[j][i] # min
                k = W[i][j] # max
            else:
                D[i][j] = 0
                C[i][j] = W[i][j] # min
                k = W[j][i] # max
            # R
            if i != j and k:
                R[i][j] = C[i][j] * C[i][j] / k
            else:
                R[i][j] = 0
            # s_index
            if i!= j:
                s_index[0] += C[i][j]**s_index_power
                s_index[1] += W[i][j]**s_index_power

    # s_index correction
    if not s_index[1]:
        s_index[0] = -1
        s_index[1] = 1

    return (C, D, s_index[0]/s_index[1], R)


def BBS_scale_score(W):
    """Batchelder-Bershad-Simpson Scaling Method taken from the article:
    Finding an appropriate order for a hierarchy based on probabilistic dominance
    Jameson KA, Appleby MC, Freeman LC., 1999, Animal Behaviour
    http://www.ncbi.nlm.nih.gov/pubmed/10328784

    modification compared to the article:
    average scale scores are substracted in every iteration to have zero mean normal distribution
    this step does not affect the calculation of the relative scores...

    Algo excludes not valid elements (e.g. nan) from calculation

    Keyword arguments:
    W   -- input weight matrix (square 2D dict/list), where W[IDfrom][IDto] = weight.

    Returns dictionary with keys from W keys and values of BBS score.

    """

    if isinstance(W, dict):
        idorder = list(W)
    elif isinstance(W, list):
        idorder = range(len(W))
    else:
        0/0

    # params for each ID
    wins = dict([(i, 0) for i in idorder]) # wins
    loses = wins.copy()                    # loses
    all = wins.copy()                      # all agonistic encounters

    # other params
    errorlimit = 1e-6 # TODO: what is the error limit to reach???
    error = errorlimit + 1 # > errorlimit for sure
    iteration = 0

    # calculate wins and loses
    for i in idorder:
        for j in idorder:
            if i == j: continue
            if W[i][j] != W[i][j]: continue # nan excluded
            wins[i] += W[i][j]
            loses[j] += W[i][j]

    # calculate total number of events for all IDs
    for i in idorder:
        all[i] = wins[i] + loses[i]

    # calculate initial scale scores
    scores = {}
    for i in idorder:
        if all[i]:
            scores[i] = math.sqrt(2*math.pi) * (wins[i] - all[i]/2) / all[i]
        else:
            scores[i] = 0
    olds = scores.copy()

    # iterate until scale scores become invariant (error is only the average additive part)
    while iteration < 30 and error > errorlimit:
        # calculate mean scale score of others
        means = dict([(i, 0) for i in idorder])
        for i in idorder:
            k = 0
            for j in idorder:
                if i == j: continue
                if W[i][j] != W[i][j] or W[j][i] != W[j][i]: continue # nan excluded
                if W[i][j] or W[j][i]:
                    means[i] += scores[j]
                    k += 1
            if k > 0:
                means[i] /= k
        # calculate new scale scores and error
        oldolds = olds.copy()  # store old old
        olds = scores.copy() # store old
        error = 0
        for i in idorder:
            # calculate new s
            if all[i]:
                scores[i] = 2*(wins[i] - loses[i])/all[i] + means[i]
            # calculate error
            error += abs(abs(oldolds[i] - olds[i]) - abs(olds[i] - scores[i]))
        # increase iteration count
        iteration += 1
        # debug
        # print("BBS iteration %d, total error = %g" % (iteration, error))

    #if error <= errorlimit:
    #    print("BBS iteration %d, error limit of %g reached" % (iteration, errorlimit))

    ############################
    # New step not present in the article: substract avgS from S
    # NOTE: average is taken only from ones that are involved in interactions
    # Since additive S parts do not affect relative scores,
    # this step is straightforward to have the whole distribution normalized
    j = 0
    k = 0
    for i in idorder:
        if not all[i]: continue
        j += 1
        k += scores[i]
    if j: k /= j
    for i in idorder:
        if not all[i]: continue
        scores[i] -= k

    return scores


def deVries_modified_Davids_score(W, mode=4):
    """Modified David's Score to obtain dominance rank and steepness. Source article:
    Measuring and testing the steepness of dominance hierarchies
    Han de Vries, Jeroen M. G. Stevens, Hilde Vervaecke, 2006, Animal Behaviour
    http://igitur-archive.library.uu.nl/bio/2006-1215-203400/UUindex.html

    Algo excludes not valid elements (e.g. nan) from calculation

    Keyword arguments:
    W     -- input weight matrix (square 2D dict/list), where W[IDfrom][IDto] = weight.
    mode  -- 0: original David's score
             1: deVrie modified score
             2: normalized original score
             3: modified-normalized score
             4: Mate's normalization of original score (using max-min)

    Returns tuple, including:
        - dictionary with keys from W keys and values of David's score
        - scalar representing the steepness of the hierarchy

    """

    if isinstance(W, dict):
        idorder = list(W)
    elif isinstance(W, list):
        idorder = range(len(W))
    else:
        0/0

    # params for each ID
    wins = dict([(i, 0) for i in idorder]) # wins
    loses = wins.copy()                    # loses
    wins2 = wins.copy()                    # weighted wins
    loses2 = wins.copy()                   # weighted loses
    all = wins.copy()                      # all agonistic encounters

    # calculate Dij (old: Pij) and Dji (old: Pji) for all IDs
    nans = 0
    for i in idorder:
        for j in idorder:
            if i == j: continue
            if W[i][j] != W[i][j] or W[j][i] != W[j][i]:
                nans += 1
                continue
            n = W[i][j] + W[j][i]
            if mode in [0,2,4]: # original David's score
                if n:
                    wins[i] += W[i][j]/n
                    loses[i] += W[j][i]/n
            elif mode in [1,3]: # modified David's score
                if n != -1:
                    wins[i] += (W[i][j]+0.5)/(n+1)
                    loses[i] += (W[j][i]+0.5)/(n+1)
    nans /= 2
    if nans: print("Warning: there are %d not number elements, normDS calculation will be somewhat wrong..." % nans)

    # calculate weighted Dij (old: Pij) and Dji (old: Pji) for all IDs
    for i in idorder:
        for j in idorder:
            if i == j: continue
            if W[i][j] != W[i][j] or W[j][i] != W[j][i]: continue
            n = W[i][j] + W[j][i]
            if mode in [0,2,4]: # original David's score
                if n:
                    wins2[i] += wins[i] * W[i][j]/n
                    loses2[i] += loses[i] * W[j][i]/n
            elif mode in [1,3]: # modified David's score
                if n != -1:
                    wins2[i] += wins[i] * (W[i][j]+0.5)/(n+1)
                    loses2[i] += loses[i]* (W[j][i]+0.5)/(n+1)

    # calculate modified David's score and normalized modified David's score
    n = len(idorder)
    DS = {}     # David's score
    normDS = {} # Normalized David's score
    minDS = float('inf')
    maxDS = -minDS
    for i in idorder:
        DS[i] = wins[i] + wins2[i] - loses[i] - loses2[i]
        if DS[i] < minDS: minDS = DS[i]
        if DS[i] > maxDS: maxDS = DS[i]
    for i in idorder:
        if mode in [2,3]:
            normDS[i] = (DS[i] + n*(n-1)/2 - nans)/n
        elif mode in [4]:
            if maxDS != minDS:
                # this will get values in the range of 0-n at all times
                normDS[i] = (DS[i] - minDS)/(maxDS-minDS) * (n-1)
            else:
                normDS[i] = 0

    # return score
    if mode in [0,1]:
        return DS
    elif mode in [2,3,4]:
        return normDS


def Lindquist_dominance_index(W):
    """Lindquist Dominance Index taken from the article:
    Data-Based Analysis of Winner-Loser Models of Hierarchy Formation in Animals
    W. Brent Lindquist and Ivan D. Chase, 2009, Bulletin of Mathematical Biology
    http://dx.doi.org/10.1007/s11538-008-9371-9

    Algo excludes not valid elements (e.g. nan) from calculation

    Keyword arguments:
    W   -- input weight matrix (square 2D dict/list), where W[IDfrom][IDto] = weight.

    Returns dictionary with keys from W keys and values of BBS score.
    (score is 0 (=mean) for passive IDs (no events at all))

    """

    if isinstance(W, dict):
        idorder = list(W)
    elif isinstance(W, list):
        idorder = range(len(W))
    else:
        0/0

    # params for each ID
    wins = dict([(i, 0) for i in idorder]) # wins
    loses = wins.copy()                    # loses
    scores = wins.copy()                   # scale scores

    # calculate total number of events for all IDs
    for i in idorder:
        for j in idorder:
            if i == j: continue
            if W[i][j] != W[i][j] or W[j][i] != W[j][i]: continue
            wins[i] += W[i][j]
            loses[j] += W[i][j]

    # calculate dominance indices
    scores = {}
    for i in idorder:
        n = wins[i] + loses[i]
        if n:
            scores[i] = wins[i]/n
        else:
            scores[i] = 0

    # return scale score dict
    return scores


def row_sum(W):
    """Return the row sum values for each line.

    Algo excludes not valid elements (e.g. nan) from calculation

    Keyword arguments:
    W   -- input weight matrix (square 2D dict/list), where W[IDfrom][IDto] = weight.

    Returns dictionary with keys from W keys and values of row sum.

    """

    if isinstance(W, dict):
        idorder = list(W)
    elif isinstance(W, list):
        idorder = range(len(W))
    else:
        0/0

    # initialize
    rowsum = {}
    for i in idorder:
        rowsum[i] = 0
    # calculate total number of events for all IDs
    for i in idorder:
        for j in idorder:
            if i == j: continue
            if W[i][j] != W[i][j] or W[j][i] != W[j][i]: continue
            rowsum[i] += W[i][j]
    # return rowsum dict
    return rowsum

def win_above_average(W):
    """Return the number of columns for each row that have
    values above full matrix average
    (i.e. number of pairwise winning above average fight level)

    Algo excludes not valid elements (e.g. nan) from calculation

    Keyword arguments:
    W   -- input weight matrix (square 2D dict/list), where W[IDfrom][IDto] = weight.

    Returns dictionary with keys from W keys and values of calculated score.

    """

    if isinstance(W, dict):
        idorder = list(W)
    elif isinstance(W, list):
        idorder = range(len(W))
    else:
        0/0

    # calculate average
    avgW = 0
    n = 0
    for i in idorder:
        for j in idorder:
            if i == j: continue
            if W[i][j] != W[i][j] or W[j][i] != W[j][i]: continue
            avgW += W[i][j]
            n += 1
    if n: avgW /= n
    # initialize output
    wins = {}
    for i in idorder:
        wins[i] = 0
    # calculate number of pairwise winning above threshold fight
    for i in idorder:
        for j in idorder:
            if i == j: continue
            if W[i][j] != W[i][j] or W[j][i] != W[j][i]: continue
            if W[i][j] > avgW:
                wins[i] += 1
    return wins

def lose_above_average(W):
    """Return the number of rows for each column that have
    values above full matrix average
    (i.e. number of pairwise losing above average fight level)

    Algo excludes not valid elements (e.g. nan) from calculation

    Keyword arguments:
    W   -- input weight matrix (square 2D dict/list), where W[IDfrom][IDto] = weight.

    Returns dictionary with keys from W keys and values of calculated score.

    """

    if isinstance(W, dict):
        idorder = list(W)
    elif isinstance(W, list):
        idorder = range(len(W))
    else:
        0/0

    # calculate average
    avgW = 0
    n = 0
    for i in idorder:
        for j in idorder:
            if i == j: continue
            if W[i][j] != W[i][j] or W[j][i] != W[j][i]: continue
            avgW += W[i][j]
            n += 1
    if n: avgW /= n
    # initialize output
    loses = {}
    for i in idorder:
        loses[i] = 0
    # calculate number of pairwise winning above threshold fight
    for i in idorder:
        for j in idorder:
            if i == j: continue
            if W[i][j] != W[i][j] or W[j][i] != W[j][i]: continue
            if W[i][j] > avgW:
                loses[j] += 1
    return loses
