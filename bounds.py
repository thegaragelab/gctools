#!/usr/bin/env python
#----------------------------------------------------------------------------
# 04-Dec-2014 ShaneG
#
# A simple program to determine the dimensions and units of a g-code file.
#----------------------------------------------------------------------------
from sys import argv
from gcode import Bounds, loadGCode

#--- Usage information
USAGE = """
Usage:
       %s filename
"""

#--- Main program
if __name__ == "__main__":
  # Check the command line arguments
  if len(argv) <> 2:
    print USAGE.strip() % argv[0]
    exit(1)
  # Now get the information
  bounds = Bounds()
  bounds.apply(loadGCode(argv[1]))
  print "For g-code file '%s' ..." % argv[1]
  if bounds.units is None:
    print "  Units: undefined or multiple"
  else:
    print "  Units: %s" % bounds.units
  print "  X min = %f, max = %f, size = %f" % (bounds.minx, bounds.maxx, bounds.maxx - bounds.minx)
  print "  Y min = %f, max = %f, size = %f" % (bounds.miny, bounds.maxy, bounds.maxy - bounds.miny)
  print "  Z min = %f, max = %f, size = %f" % (bounds.minz, bounds.maxz, bounds.maxz - bounds.minz)
  print ""
  print "  Area: %f" % ((bounds.maxx - bounds.minx) * (bounds.maxy - bounds.miny))
