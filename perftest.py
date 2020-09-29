#!/usr/bin/python

import sys
import piksemel as iks
import xml.dom.minidom as mini
from Ft.Xml.Domlette import NoExtDtdReader
import Ft.Lib
import timeit

def piksor(name):
    a = iks.parse(name)
    total = 0
    for b in a.tags():
        size = b.getTagData("Size")
        if size:
            size = size.strip()
            total += int(size)

def cdom(name):
    doc = NoExtDtdReader.parseUri(Ft.Lib.Uri.OsPathToUri(name))

def suxor(name):
    a = mini.parse(name)

if __name__ == "__main__":
    name = sys.argv[1]
    a = timeit.Timer('piksor("%s")' % name, "from __main__ import piksor")
    b = timeit.Timer('cdom("%s")' % name, "from __main__ import cdom")
    c = timeit.Timer('suxor("%s")' % name, "from __main__ import suxor")
    print "piksemel", a.timeit(1)
    print "cdom", b.timeit(1)
    print "minidom", c.timeit(1)


