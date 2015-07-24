#!/usr/bin/env python
#----------------------------------------------------------------------------
# 04-Dec-2014 ShaneG
#
# A simple program to determine the dimensions and units of a g-code file.
#----------------------------------------------------------------------------
from sys import argv
from optparse import OptionParser
from os.path import splitext
from util.gcode import loadGCode

#--- Usage information
USAGE = """
Usage:
       %s [--image] filename

Where:

  --image           generate an image of the file
"""

#--- Main program
if __name__ == "__main__":
  # Set up program options
  parser = OptionParser()
  parser.add_option("-i", "--image", action="store_true", dest="image", default=False)
  options, args = parser.parse_args()
  # Check positional arguments
  if len(args) <> 1:
    print USAGE.strip() % argv[0]
    exit(1)
  # Load the Gcode and describe it
  name, ext = splitext(args[0])
  if ext == "":
    ext = ".ngc"
  filename = name + ext
  gcode = loadGCode(filename)
  print "For g-code file '%s' ...\n" % filename
  print "  X min = %f, max = %f, size = %f (mm)" % (gcode.minx, gcode.maxx, gcode.maxx - gcode.minx)
  print "  Y min = %f, max = %f, size = %f (mm)" % (gcode.miny, gcode.maxy, gcode.maxy - gcode.miny)
  print "  Z min = %f, max = %f, size = %f (mm)" % (gcode.minz, gcode.maxz, gcode.maxz - gcode.minz)
  print "\n  Area: %f mm^2" % ((gcode.maxx - gcode.minx) * (gcode.maxy - gcode.miny))
  # Generat an image if requested
  if options.image:
    filename = name + ".png"
    gcode.render(filename)

