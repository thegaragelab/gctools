#!/usr/bin/env python
#----------------------------------------------------------------------------
# 04-Dec-2014 ShaneG
#
# A simple program to reset the origin of the work.
#----------------------------------------------------------------------------
from sys import argv
from optparse import OptionParser
from gcode import Bounds, Translate, loadGCode, saveGCode, floatVal

#--- Usage information
USAGE = """
Usage:
       %s [--output filename] filename
"""

#--- Main program
if __name__ == "__main__":
  # Set up program options
  parser = OptionParser()
  parser.add_option("-o", "--output", action="store", type="string", dest="output_file")
  options, args = parser.parse_args()
  # Check positional arguments
  if len(args) <> 1:
    print USAGE.strip() % argv[0]
    exit(1)
  # Set up the source file and collect the depth information
  source = args[0]
  # First get the bounds of the file and determine the translation
  data = loadGCode(source)
  bounds = Bounds()
  bounds.apply(data)
  # Now translate so that minx and miny become 0
  print "Translating by X = %s, Y = %s" % (floatVal(-bounds.minx), floatVal(-bounds.miny))
  translate = Translate(dx = -bounds.minx, dy = -bounds.miny)
  result = translate.apply(data)
  if options.output_file is None:
    print "\n".join(result)
  else:
    saveGCode(options.output_file, result)
