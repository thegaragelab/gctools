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

GCODE_PREFIX = """
G21 (Use mm)
G90 (Set Absolute Coordinates)
G17 (XY plane selection)
G00 Z${safe_height}
G00 Y0 X0
(begin drill commands)
"""

GCODE_SUFFIX = """
(end drill commands)
G00 Z${safe_height}
M05 (Stop spindle)
G00 X0 Y0
M02 (Program End)
%
"""

GCODE_DRILL = """
G00 X${x} Y${y}
G01 Z${cut_depth} F${feed_rate}
G00 Z${safe_height}
"""

if __name__ == "__main__":
  # Set up program options
  parser = OptionParser()
  parser.add_option("-s", "--safe", action="store", type="float", default=3, dest="safe_height")
  parser.add_option("-c", "--cut", action="store", type="float", default=-3, dest="cut_depth")
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
    'safe_height': "%0.4f" % options.safe_height,
    'feed_rate': "%0.4f" % options.feed_rate,
    'cut_depth': "%0.4f" % options.cut_depth,
    }
  with open(args[0], "w") as gcode:
    gcode.write(Template(GCODE_PREFIX.strip()).safe_substitute(values) + "\n")
    # Generate drill commands
    for y in sorted(YPOS):
      for x in sorted(XPOS):
        gcode.write(Template(GCODE_DRILL.strip()).safe_substitute(values, x = "%0.4f" % x, y = "%0.4f" % y) + "\n")
    # Add suffix
    gcode.write(Template(GCODE_SUFFIX.strip()).safe_substitute(values) + "\n")

