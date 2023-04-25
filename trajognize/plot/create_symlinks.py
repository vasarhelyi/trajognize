"""The aim of this script is to create symlinks for all plotted results with a
new categorization: first by experiment, group, light, realvirt and than for
result type. This is the opposite of the normal/original directory structure...

Usage:

    python create_symlinks.py projectfile inputdir [outputdir]

Note:

    to remove all symlinks within the symlink folder, run the followings:

    find -L * -xtype l > symlinks.txt
    for f in $(cat symlinks.txt) ; do unlink $f ; done

"""

import glob, os, sys, re

try:
    import trajognize.settings
    import trajognize.stat.experiments
    import trajognize.stat.init
except ImportError:
    sys.path.insert(
        0,
        os.path.abspath(
            os.path.join(os.path.dirname(sys.modules[__name__].__file__), "../..")
        ),
    )
    import trajognize.settings
    import trajognize.stat.experiments
    import trajognize.stat.init

# dirs to exclude from search
ignoredirs = ["corr"]
linkdirprefix = "SYMLINK__"
# order of the output directories
# directory_order = ['exp', 'group', 'light', 'realvirt', 'obj']
directory_order = ["light", "realvirt", "exp", "group", "obj"]
linkdir = linkdirprefix + "_".join([x.upper() for x in directory_order])


def main(argv=[]):
    """Main entry point of the script."""
    if len(argv) not in [2, 3]:
        print(__doc__)
        return
    projectfile = argv[0]
    inputdir = argv[1]
    if len(argv) == 2:
        outputdir = os.path.join(inputdir, linkdir)
    elif len(argv) == 3:
        outputdir = argv[2]

    print("Input dir:", inputdir)
    print("Output dir:", outputdir)

    project_settings = trajognize.settings.import_trajognize_settings_from_file(
        projectfile
    )
    if project_settings is None:
        print("Could not load project settings.")
        return
    exps = project_settings.experiments

    for root, subfolders, files in os.walk(inputdir):
        x = root[len(inputdir) + 1 :]
        # ignore symlink dirs
        if x.find(linkdirprefix) != -1:
            continue
        # only parse dirs that do not contain any more subfolders
        if subfolders:
            continue
        # only parse dirs that end with a plot dir before categorization
        p = x.find("plot_")
        if p == -1:
            continue
        # create list of subdirs
        subs = [s.lower() for s in x[p:].split(os.sep) if s]
        presubs = [s for s in x[:p].split(os.sep) if s] + [subs[0]]
        del subs[0]
        # ignore ignore dirs
        if True in [x in subs or x in presubs for x in ignoredirs]:
            continue

        # check experiment
        for exp in exps:
            if "exp_%s" % exp.lower() in subs:
                found_exp = exp
                break
        else:
            if "exp_all" in subs:
                found_exp = "all"
            else:
                found_exp = "unknown_exp"

        # check group
        if found_exp in ["all", "unknown_exp"]:
            groups = ["all"]
        else:
            groups = exps[found_exp]["groups"].keys()
        for group in groups:
            if group.lower() in subs:
                found_group = group
                break
        else:
            found_group = "unknown_group"

        # check light
        for light in project_settings.good_light:
            if light.lower() in subs:
                found_light = light.lower()
                break
        else:
            found_light = "anylight"

        # check realvirt
        for realvirt in trajognize.stat.init.mfix_types + ["ANY"]:
            if realvirt.lower() in subs:
                found_realvirt = realvirt
                break
        else:
            found_realvirt = "ANY"

        # check object:
        for obj in project_settings.object_areas.keys():
            if obj in subs:
                found_obj = obj
                break
        else:
            found_obj = ""

        # create symlinks
        suborder = [eval("found_%s" % x) for x in directory_order]
        dst = os.path.join(outputdir, *suborder)
        if not os.path.isdir(dst):
            os.makedirs(dst)
        dst = os.path.join(dst, "-".join(presubs))
        if os.path.isdir(dst):
            print("Warning: existing destination:", dst)
        else:
            #            print("ln -v -s %s %s" % (root, dst))
            os.system("ln -v -s %s %s" % (root, dst))


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))  # pass only real params to main
    except Exception as ex:
        print(ex, file=sys.stderr)
        import traceback

        traceback.print_exc(ex)
        sys.exit(1)
