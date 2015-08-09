#!/usr/bin/env python
#----------------------------------------------------------------------------
# 19-Jul-2015 ShaneG
#
# This script generates the gcode needed to drill holes in the PCB for
# mounting.
#----------------------------------------------------------------------------
from optparse import OptionParser
from string import Template
from util import GCode, saveGCode, getSettings

# Hole positions
XPOS = [ 3.5, 146.5 ]
YPOS = [ 3.5, 71.5 ]
YPOS_LARGE = [ 146.5 ]

# Defaults
CONTROL = {
  "cut": -2.0,
  "safe": 3.0,
  "feed": 128,
  }

if __name__ == "__main__":
  # Set up program options
  parser = OptionParser()
  parser.add_option("-s", "--safe", action="store", type="float", default=3, dest="safe")
  parser.add_option("-c", "--cut", action="store", type="float", default=-3, dest="cut")
  parser.add_option("-f", "--feed", action="store", type="float", default=250, dest="feed")
  parser.add_option("-l", "--large", action="store_true", default=False, dest="large")
  options, args = parser.parse_args()
  # Make sure we have an output file
  if len(args) != 1:
    print "Output file required."
    exit(1)
  # Get settings
  CONTROL = getSettings(CONTROL, options)
  # Set up the points to use
  if options.large:
    YPOS.extend(YPOS_LARGE)
  # Generate the gcode
  gcode = GCode()
  # Generate drill commands
  for y in sorted(YPOS):
    for x in sorted(XPOS):
      gcode.append("G00 X%0.4f Y%0.4f" % (x, y))
      gcode.append("G01 Z%0.4f F%0.4f" % (CONTROL['cut'], CONTROL['feed']))
      gcode.append("G00 Z%0.4f" % CONTROL['safe'])
  # Write the output file
  saveGCode(args[0], gcode, prefix = CONTROL['prefix'], suffix = CONTROL['suffix'])

