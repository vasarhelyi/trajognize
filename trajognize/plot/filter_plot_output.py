"""This script lists all plotted results that match the given filters from
the full_run__statsum/done directory.

Filtering is applicable for the following variables: stat, experiment, group,
light, real/virt/any, object, name (strid)

Note:

    to remove all symlinks within the symlink folder, run the followings:

    find -L * -xtype l > symlinks.txt
    for f in $(cat symlinks.txt) ; do unlink $f ; done

Note 2:

    to copy all .png results from atlasz to another server, e.g. to biolfiz,
    keeping the directory structure, enter ...results/full_run__statsum/done
    and run the following (that might take long):

    rsync -rav -e ssh --include '*/' --include='*.png' --exclude='*' statsum_* vasarhelyi@biolfiz1.elte.hu:/data2/patekok/results/full_run__statsum
    rsync -rav -e ssh --include '*/' --include='*.png' --exclude='*' meassum_* vasarhelyi@biolfiz1.elte.hu:/data2/patekok/results/full_run__statsum

"""

import glob, os, sys, argparse, socket
try:
    import trajognize.project
    import trajognize.stat.project
    import trajognize.stat.experiments
    import trajognize.stat.init
    import trajognize.stat.util
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(
        os.path.dirname(sys.modules[__name__].__file__), "../..")))
    import trajognize.project
    import trajognize.stat.project
    import trajognize.stat.experiments
    import trajognize.stat.init
    import trajognize.stat.util

# dirs to exclude from search
ignoredirs = ['corr', 'SYMLINK__', 'dailyoutput', 'dist24h']
gooddirs = ['statsum', 'meassum']
goodexts = ['.png']
linkdirprefix = 'SYMLINK__FILTER/SYMLINK__'

# create stat dictionary from implemented stat functions and classes
stats = trajognize.stat.util.get_stat_dict()
# initialize experiments dictionary
exps = trajognize.stat.experiments.get_initialized_experiments()

# collect all possible values for each filter
allexps = sorted(exps.keys())
allstats = sorted(stats.keys() + ['bodymass', 'wounds'])
alllights = sorted(list(trajognize.project.good_light))
allrealvirts = sorted(list(trajognize.stat.init.mfix_types) + ['ANY'])
allobjects = sorted(trajognize.stat.project.object_areas.keys())
allgroups = set()
allnames = set()
for exp in exps:
    for group in exps[exp]['groups']:
        allgroups.add(group)
        allnames.update(exps[exp]['groups'][group])
allgroups = sorted(list(allgroups))
allnames = sorted(list(allnames))


def lower(list):
    return [x.lower() for x in list]

def is_filter_exclusive(filters, subs, strcontains=False, allfilters=[]):
    """Return True if filter is exclusive, i.e. given list does not contain any
    of the given filter elements. Check can be full match or 'contains' type."""
    if not filters:
        return False
    if strcontains:
        # if it contains the filter, it is not exclusive
        if True in [s.find(f) != -1 for s in subs for f in filters]:
            return False
        else:
            # if it contains something else from the same category, it is exclusive
            if not allfilters or True in [s.find(f) != -1 for s in subs for f in allfilters]:
                return True
            else:
                return False
    else:
        # if it contains the filter, it is not exclusive
        if True in [f in subs for f in filters]:
            return False
        else:
            # if it contains something else from the same category, it is exclusive
            if not allfilters or True in [f in subs for f in allfilters]:
                return True
            else:
                return False


def create_symlink_name(name):
    """Create a short version of the filename for symlink name."""
    for exp in allexps:
        name = name.replace("exp_%s" % exp, "e%d" % exps[exp]['number'])
    for group in allgroups:
        name = name.replace("group_%s" % group, group)
    for light in alllights:
        name = name.replace(light, "%cL" % light[0])
        name = name.replace(light.lower(), "%cL" % light[0])
    for realvirt in allrealvirts:
        name = name.replace(realvirt, realvirt[0])
        name = name.replace(realvirt.lower(), realvirt[0])
    name = name.replace("__", "_")
    return name


def main(argv=[]):
    """Main entry point of the script."""
    # print help if no arguments given
    if not argv and len(sys.argv) <= 1: argv.append('-h')
    # parse command line arguments
    argparser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=__doc__)
    argparser.add_argument("-p", "--inputpath", metavar="PATH", dest="inputpath", default='', help="define input path with statsum output")
    argparser.add_argument("-v", "--verboseonly", dest="verbose_only", action="store_true", default=False, help="Do not create real symlinks, only print output.")
    argparser.add_argument("-m", "--maxsymlinks", metavar="num", dest="max_symlinks", type=int, default=100, help="Maximum number of symlinks to create.")
    # filters
    argparser.add_argument("-s", "--statistics", metavar="stat", dest="statistics", nargs="+", choices=allstats, default=[], help="Filter for statistics. Possible values: %s" % allstats)
    argparser.add_argument("-e", "--experiments", metavar="exp", dest="experiments", nargs="+", choices=allexps, default=[], help="Filter for experiments. Possible values: %s" % allexps)
    argparser.add_argument("-g", "--groups", metavar="group", dest="groups", nargs="+", choices=allgroups, default=[], help="Filter for groups. Possible values: %s" % allgroups)
    argparser.add_argument("-l", "--lights", metavar="light", dest="lights", nargs="+", choices=alllights, default=[], help="Filter for light. Possible values: %s" % alllights)
    argparser.add_argument("-r", "--realvirt", metavar="realvirt", dest="realvirts", nargs="+", choices=allrealvirts, default=[], help="Filter for realvirt. Possible values: %s" % allrealvirts)
    argparser.add_argument("-o", "--objects", metavar="object", dest="objects", nargs="+", choices=allobjects, default=[], help="Filter for objects. Possible values: %s" % allobjects)
    argparser.add_argument("-n", "--names", metavar="name", dest="names", nargs="+", choices=allnames, default=[], help="Filter for names. Possible values: %s" % allnames)
    # any further filter that should be or should not be part of the results
    argparser.add_argument("-i", "--include", dest="include", nargs="+", default=[], help="List any further words that should be part of the results")
    argparser.add_argument("-x", "--exclude", dest="exclude", nargs="+", default=[], help="List any further words that should NOT be part of the results")


    # if arguments are passed to main(argv), parse them
    if argv:
        options = argparser.parse_args(argv)
    # else if called from command line or no arguments are passed to main, parse default argument list
    else:
        options = argparser.parse_args()

    # check arguments
    # input path
    if not options.inputpath:
        # get host name
        hostname = socket.gethostname()
        # default on windows (gabor's laptop)
        if sys.platform.startswith('win'):
            if hostname == 'ubi-ELTE':
                options.inputpath = r'd:\ubi\ELTE\patekok\statsum'
        # default on non windows (linux: atlasz or biolfiz1)
        else:
            if hostname == 'biolfiz1':
                options.inputpath = '/data2/patekok/results/full_run__statsum'
            elif hostname == 'atlasz':
                options.inputpath = '/project/flocking/abeld/ratlab/results/full_run__statsum/done'
            elif hostname == 'hal':
                options.inputpath = '/home/nagymate/public_html/sjt/patekfilter/gallery/gal_sshfs_biolfiz1'
    # if names are specified, insert groups that contain those names
    if options.names:
        for exp in options.experiments if options.experiments else allexps:
            for name in options.names:
                group = exps[exp]['groupid'][name]
                if group not in options.groups:
                    print group, "group added to host", name, "in", exp
                    options.groups.append(group)

    # define output directory
    outdir = os.path.join(options.inputpath, linkdirprefix + "_".join(argv))
    print "Using input path: '%s'" % options.inputpath
    print "Using output path: '%s'\n" % outdir

    print "Finding matches for the given filter...",
    symlinks = []
    # check files that match filter
    for root, subfolders, files in os.walk(options.inputpath):
        roottail = root[len(options.inputpath)+1:]
        # ignore dirs that need to be ignored
        if True in [roottail.find(x) != -1 for x in ignoredirs]: continue
        # check good dirs
        if True not in [roottail.startswith(x) for x in gooddirs]: continue
        # only parse dirs that do not contain any more subfolders
        if subfolders: continue
        # only parse dirs that end with a plot dir before categorization
        p = roottail.find("plot_")
        if p == -1: continue
        # create list of subdirs
        subs = [s.lower() for s in roottail[p:].split(os.sep) if s]
        presubs = [s for s in roottail[:p].split(os.sep) if s] + [subs[0]]
        del subs[0]
        # check filters
        for prefix in gooddirs:
            if not is_filter_exclusive(["%s_%s" % (prefix, x.lower()) for x in options.statistics], presubs):
                break
        else:
            continue
        if is_filter_exclusive(["exp_%s" % x.lower() for x in options.experiments], subs): continue
        if is_filter_exclusive(lower(options.groups), subs, False, lower(allgroups)): continue
        if is_filter_exclusive(lower(options.lights), subs, False, lower(alllights)): continue
        if is_filter_exclusive(lower(options.realvirts), subs, False, lower(allrealvirts)): continue
        if is_filter_exclusive(lower(options.objects), subs): continue
        # name filter comes later, because it is part of the file name not the directory name
        # futher general filters
        if options.exclude and not is_filter_exclusive(lower(options.exclude), [roottail], True): continue
        if options.include and is_filter_exclusive(lower(options.include), [roottail], True): continue

        # check files in the current filtered directory
        for filename in files:
            # include only files with proper extension
            if not os.path.splitext(filename)[1] in goodexts: continue
            # exclude thumbnails
            if filename.startswith("_thb_"): continue
            # apply name filter
            if is_filter_exclusive(options.names, [filename], True, allnames): continue # TODO: names need more sophisticated filter
            # apply general filters
            if options.exclude and not is_filter_exclusive(lower(options.exclude), [filename], True): continue
            if options.include and is_filter_exclusive(lower(options.include), [filename], True): continue
            # create symlink name
            symhead = '-'.join(presubs)
            symtail = create_symlink_name(filename)
            # absolute paths
            src = os.path.join(root, filename)
            dst = os.path.join(outdir, symhead + '-' + symtail)
            # relative paths (make sure working directory is outdir when creating symlinks)
            dst = os.path.split(dst)[1]
            src = os.path.relpath(src, outdir)
            # store symlink
            symlinks.append((src, dst))
            print len(symlinks),
            if len(symlinks) > options.max_symlinks and not options.verbose_only:
                print "\nERROR: Too many matches found, exiting without creating symlinks."
                return

    if options.verbose_only:
        print "done\n\nSimulating symlinks..."
        # display symlinks
        for i, x in enumerate(symlinks, 1):
            print
            print "%d. src:" % i, x[0]
            print "%d. dst:" % i, x[1]
    else:
        print "done\n\nCreating symlinks..."
        # create output directory
        if not os.path.isdir(outdir):
            os.makedirs(outdir)
        # change working directory to output dir
        # to allow easy relative symlink creation
        os.chdir(outdir)
        # create symlinks
        for i, x in enumerate(symlinks, 1):
            print
            os.system("ln -v -s %s %s" % x)
        # set permission to all files from SYMLINK__FILTER
        if socket.gethostname() in ['biolfiz1', 'hal']:
            os.system("chmod -R ug+rwX %s" % os.path.split(outdir)[0])


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:])) # pass only real params to main
    except Exception as ex:
        print >>sys.stderr, ex
        import traceback
        traceback.print_exc(ex)
        sys.exit(1)
