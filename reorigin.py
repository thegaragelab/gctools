#!/usr/bin/env python
#----------------------------------------------------------------------------
# 28-Jul-2015 ShaneG
#
# Updated to use the new framework.
#
# 04-Dec-2014 ShaneG
#
# A simple program to reset the origin of the work.
#----------------------------------------------------------------------------
from sys import argv
from optparse import OptionParser
from os.path import splitext
from util import loadGCode, saveGCode, Translate

#--- Usage information
USAGE = """
Usage:
       %s [--image] [--output filename] filename
"""

#--- Main program
if __name__ == "__main__":
  # Set up program options
  parser = OptionParser()
  parser.add_option("-o", "--output", action="store", type="string", dest="output_file")
  parser.add_option("-i", "--image", action="store_true", dest="image", default=False)
  options, args = parser.parse_args()
  # Check for required options
  for required in ("output_file", ):
    if getattr(options, required, None) is None:
      print "Missing required option '%s'" % required
      print USAGE.strip() % argv[0]
      exit(1)
  # Check positional arguments
  if len(args) <> 1:
    print USAGE.strip() % argv[0]
    exit(1)
  # Process the file
  gcode = loadGCode(args[0])
  if (gcode.minx <> 0) or (gcode.miny <> 0):
    print "Translating file by dx = %0.4f, dy = %0.4f" % (-gcode.minx, -gcode.miny)
    gcode = gcode.clone(Translate(-gcode.minx, -gcode.miny))
  else:
    print "No translation required."
  saveGCode(options.output_file, gcode)
  if options.image:
    gcode.render(splitext(options.output_file)[0] + ".png")

