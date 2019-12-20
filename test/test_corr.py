try:
    import trajognize.corr.util
    import trajognize.corr.corr
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(
        os.path.dirname(sys.modules[__name__].__file__), "..")))
    import trajognize.corr.corr
    import trajognize.corr.util


filename = r'd:\ubi\ELTE\patekok\video\random_sample_trial_run__trajognize\done\corr\exp_all\all\pairparams_plot_aa.corr'
print "Parsing corr file..."
headers, data = trajognize.corr.util.parse_corr_file(filename)
print "Calculating Pearson correlations between %d lines..." % len(data)
R, P = trajognize.corr.corr.calculate_all_pearsonr(data)
print "a b pearsonr pvalue"
for a in sorted(R):
    for b in sorted(R):
        print a, b, R[a][b], P[a][b]