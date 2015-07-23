#!/usr/bin/env python
#----------------------------------------------------------------------------
# 23-Jul-2015 ShaneG
#
# Rotate a gcode file around the X/Y origin.
#----------------------------------------------------------------------------
from sys import argv
from optparse import OptionParser
from os.path import splitext
from util import loadGCode, saveGCode, Rotate

#--- Usage information
USAGE = """
Usage:
       %s [--angle angle] [--output filename] [--image] filename

Where:

  --angle  angle    the angle to rotate (in degrees)
  --image           generate an image of the result
  --output filename the name of the file to write the results to
"""

if __name__ == "__main__":
  # Set up program options
  parser = OptionParser()
  parser.add_option("-a", "--angle", action="store", type="float", dest="angle")
  parser.add_option("-o", "--output", action="store", type="string", dest="output")
  parser.add_option("-i", "--image", action="store_true", dest="image", default=False)
  options, args = parser.parse_args()
  # Check positional arguments
  if len(args) <> 1:
    print USAGE.strip() % argv[0]
    exit(1)
  # Make sure required arguments are present
  for req in ("output", "angle"):
    if not hasattr(options, req):
      print "ERROR: Missing required argument '%s'" % req
      print USAGE.strip() % argv[0]
      exit(1)
  source = args[0]
  # Process the file
  gcode = loadGCode(source)
  print "Loaded - %s" % str(gcode)
  gcode = gcode.clone(Rotate(options.angle))
  print "Generated - %s" % str(gcode)
  # Generate an image if required
  name, ext = splitext(options.output)
  if options.image:
    filename = name + ".png"
    gcode.render(filename)
  # Generate the output file
  if ext == "":
    ext = ".ngc"
  saveGCode(name + ext, gcode)

