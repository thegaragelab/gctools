#!/usr/bin/env python
#----------------------------------------------------------------------------
# 29-Jul-2015 ShaneG
#
# Merge multiple NGC files together.
#----------------------------------------------------------------------------
from sys import argv
from optparse import OptionParser
from os.path import splitext
from util import *

#--- Usage information
USAGE = """
Usage:
       %s [options] filename ...

Where options are:

  --image           generate an image of the result
  --output filename the name of the file to write the results to
"""

if __name__ == "__main__":
  # Set up program options
  parser = OptionParser()
  parser.add_option("-o", "--output", action="store", type="string", dest="output")
  parser.add_option("-i", "--image", action="store_true", dest="image", default=False)
  options, args = parser.parse_args()
  # Check positional arguments
  if len(args) < 1:
    print USAGE.strip() % argv[0]
    exit(1)
  # Make sure required arguments are present
  for req in ("output", ):
    if getattr(options, req) is None:
      print "ERROR: Missing required argument '%s'" % req
      print USAGE.strip() % argv[0]
      exit(1)
  # Get the settings (prefix and suffix)
  settings = getSettings(dict(), options)
  gcode = GCode()
  for filename in args:
    source = loadGCode(filename, BoxedLoader(start = GCommand("G00 X0 Y0"), end = GCommand("M02"), inclusive = False))
    gcode.append(source)
  # Save the output
  saveGCode(options.output, gcode, prefix = settings['prefix'], suffix = settings['suffix'])
  print "Generated - %s" % str(gcode)
  if options.image:
    gcode.render(splitext(options.output)[0] + ".png")

