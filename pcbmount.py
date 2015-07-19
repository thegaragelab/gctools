#!/usr/bin/env python
#----------------------------------------------------------------------------
# 19-Jul-2015 ShaneG
#
# This script generates the gcode needed to drill holes in the PCB for
# mounting.
#----------------------------------------------------------------------------
from optparse import OptionParser
from string import Template

# Hole positions
XPOS = [ 3.5, 146.5 ]
YPOS = [ 3.5, 71.5 ]
YPOS_LARGE = [ 146.5 ]

if __name__ == "__main__":
  # Set up program options
  parser = OptionParser()
  parser.add_option("-s", "--safe", action="store", type="float", default=3, dest="safe_height")
  parser.add_option("-f", "--feed", action="store", type="float", default=250, dest="feed_rate")
  parser.add_option("-l", "--large", action="store_true", default=False, dest="large_panel")
  options, args = parser.parse_args()
  # Make sure we have an output file
  if len(args) != 1:
    print "Output file required."
    exit(1)
  # Set up the points to use
  if options.large_panel:
    YPOS.append(YPOS_LARGE)
  # Generate the gcode
  values = {
    'safe_height': options.safe_height,
    'feed_rate': options.feed_rate,
    }
  with open(args[0], "w") as gcode:
    gcode.write(Template(GCODE_PREFIX).safe_substitute(values))
    # Generate drill commands

    gcode.write(Template(GCODE_SUFFIX).safe_substitute(values))

