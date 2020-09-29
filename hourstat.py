#!/usr/bin/python

import piksemel
import sys

def generate_hourly_stats(log, name=None):
    hours = {}
    total = 0
    for item in log.tags("logentry"):
        if name and item.getTagData("author") != name:
            pass
        else:
            hour = int(item.getTagData("date")[11:13])
            hours[hour] = hours.get(hour, 0) + 1
            total += 1
    for hour in range(0, 24):
        print "%d: %d commit" % (hour, hours.get(hour, 0))
    print "total of %d commits" % total

doc = piksemel.parse(sys.argv[1])
if len(sys.argv) == 3:
    generate_hourly_stats(doc, sys.argv[2])
else:
    generate_hourly_stats(doc)
