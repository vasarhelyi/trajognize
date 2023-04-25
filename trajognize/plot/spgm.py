"""This is a file for some common functions for plotting into SPGM galleries.

Note that this version is optimized for the original atlasz usage together
with the queue_jobs scripts so it might not work in a general setting yet."""

import os

PATH_TO_REMOVE = "/done/"
PATH_TO_ADD = "gal_sshfs_atlasz"
THUMBNAIL_PREFIX = "_thb_"
GAL_DESC_FILE = "gal-desc.txt"
PIC_DESC_FILE = "pic-desc.txt"
PIC_DESC_PREFIX = "; Do not remove this comment (used for UTF-8 compliance)\n\n"
PIC_DESC_TEMPLATE = "%s | %s"
ANCHOR_TEMPLATE = ' <a href="%s">%s</a>'
NEWLINE = "<br />"
MULTILINE = "\n>"
ENDOFLINE = "\n"


def _change_path(filename):
    """Change path of filename on atlasz to one on hal.

    Function assumes that statsum_* directories are the first level that are common,
    which can be found in a directory on atlasz named as PATH_TO_REMOVE.
    """
    tokens = filename.split(PATH_TO_REMOVE, 1)
    if len(tokens) != 2:
        print("WARN: Path is probably different from what is expected on atlasz+hal.")
        i = 0
    else:
        i = 1
    return os.path.join(PATH_TO_ADD, tokens[i])


def create_gallery_description(path, text, mode="w"):
    """Create gallery description in a given directory.

    :param path: full path of the gallery
    :param text: gallery caption text, can be multiline
    :param mode: use 'w' for write and 'a' for append

    """
    galfile = os.path.join(path, GAL_DESC_FILE)
    f = open(galfile, mode)
    if mode == "a":
        f.write("<br \>Post processed results added:<br \>\n")
    f.write(text + "\n")
    f.close()


def create_picture_description(filename, textlist, sourcefile=None, gnufile=None):
    """Add picture description for a given filename (with full path).

    :param filename: full path of a picture file
    :param textlist: list of text lines for the caption
    :param sourcefile: optional param to include source file path into description
    :param gnufile: optional param to include gnuplot file path into description

    """
    # create file if does not exist
    head, tail = os.path.split(filename)
    picfile = os.path.join(head, PIC_DESC_FILE)
    if not os.path.isfile(picfile):
        f = open(picfile, "w")
        f.write(PIC_DESC_PREFIX)
    else:
        f = open(picfile, "a")
    f.write(PIC_DESC_TEMPLATE % (tail, NEWLINE.join(textlist)))
    if sourcefile is not None or gnufile is not None:
        f.write(NEWLINE)
        if sourcefile is not None:
            f.write(MULTILINE + ANCHOR_TEMPLATE % (_change_path(sourcefile), "txt"))
        if gnufile is not None:
            f.write(MULTILINE + ANCHOR_TEMPLATE % (_change_path(gnufile), "gnu"))
    f.write(ENDOFLINE)
    f.close()


def create_thumbnail_description(filename, textlist, sourcefile=None, gnufile=None):
    """Add thumbnail description for a given picture (with full path).

    :param filename: full path of a (picture) file (not its thumbnail)
    :param textlist: list of text lines for the caption
    :param sourcefile: optional param to include source file path into description
    :param gnufile: optional param to include gnuplot file path into description

    """
    head, tail = os.path.split(filename)
    create_picture_description(os.path.join(head, THUMBNAIL_PREFIX + tail), textlist)


def remove_picture_descriptions(path):
    """Remove picture description file from a given path."""
    picfile = os.path.join(path, PIC_DESC_FILE)
    if os.path.isfile(picfile):
        os.remove(picfile)
