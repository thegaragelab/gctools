#!/usr/bin/env python
#----------------------------------------------------------------------------
# 20-Dec-2014 ShaneG
#
# Generate a rectangular area cut.
#----------------------------------------------------------------------------
from sys import argv
from optparse import OptionParser
from gcode import ZLevel, loadGCode, saveGCode

#--- Usage information
USAGE = """
Usage:
       %s [--cut depth] [--safe depth] [--width width] [--height height] [--tool size] filename
"""

# Control information
OVERLAP = 0.2
MOVE_SPEED = 250
CUT_SPEED = 120
INSERT_SPEED = 25.4

# Prefix code
GCODE_PREFIX = """
G21 (Use mm)
G90 (Set Absolute Coordinates)
G17 (XY plane selection)
G00 Z%0.4f
G00 Y0 X0 
M03 (Start spindle)
G04 P1 (Pause to let the spindle start)
"""

# Suffix code
GCODE_SUFFIX = """
(Operation complete)
M05 (Stop spindle)
G00 X0 Y0
M02 (Program End)
"""

#--- Main program
if __name__ == "__main__":
  # Set up program options
  parser = OptionParser()
  parser.add_option("-c", "--cut", action="store", type="float", dest="cut_depth", default=1.0)
  parser.add_option("-s", "--safe", action="store", type="float", dest="safe_depth", default=3.0)
  parser.add_option("-x", "--width", action="store", type="float", dest="width")
  parser.add_option("-y", "--height", action="store", type="float", dest="height")
  parser.add_option("-t", "--tool", action="store", type="float", dest="toolsize", default=3.0)
  options, args = parser.parse_args()
  # Make sure required arguments are present
  for req in ("cut_depth", "safe_depth", "width", "height", "toolsize"):
    if eval("options.%s" % req) is None:
      print "ERROR: Missing required argument '%s'" % req
      print USAGE.strip() % argv[0]
      exit(1)
  # Check positional arguments
  if len(args) <> 1:
    print USAGE.strip() % argv[0]
    exit(1)
  # Show current settings
  print "Selected options:"
  for opt in parser.option_list:
    if opt.dest is not None:
      print "  %s = %s" % (opt.dest, str(eval("options.%s" % opt.dest)))
  # Start generating the file
  print "Creating file '%s'" % args[0]
  output = open(args[0], "w")
  output.write(GCODE_PREFIX.strip() % (options.safe_depth) + "\n")
  # Loop from the outside in
  width = options.width
  height = options.height
  x1 = options.toolsize / 2
  y1 = options.toolsize / 2
  x2 = options.width - (options.toolsize / 2)
  y2 = options.height - (options.toolsize / 2)
  delta = (1 - OVERLAP) * options.toolsize
  while (width >= options.toolsize) and (height >= options.toolsize):
    # Do the circuit
    output.write("(Penetrate)\n")
    output.write("G00 X%0.4f Y%0.4f F%0.4f\n" % (x1, y1, MOVE_SPEED))
    output.write("G01 Z%0.4f F%0.4f\n" % (options.cut_depth, INSERT_SPEED))
    output.write("(Cut)\n")
    output.write("G01 X%0.4f Y%0.4f F%0.4f\n" % (x2, y1, CUT_SPEED))
    output.write("G01 X%0.4f Y%0.4f\n" % (x2, y2))
    output.write("G01 X%0.4f Y%0.4f\n" % (x1, y2))
    output.write("G01 X%0.4f Y%0.4f\n" % (x1, y1))
    output.write("G01 Z%0.4f F%0.4f\n" % (options.safe_depth, MOVE_SPEED))
    # Calculate the next position
    width = width - (2 * delta)
    height = height - (2 * delta)
    x1 = x1 + delta
    x2 = x2 - delta
    y1 = y1 + delta
    y2 = y2 - delta
  # Handle the left over
  if (width > 0) and (height > 0):
    if width < options.toolsize:
      # Vertical cut to finish
      x1 = options.width / 2
      x2 = options.width / 2
    else:
      # Horizontal cut to finish
      y1 = options.height / 2
      y2 = options.height / 2
    output.write("(Penetrate)\n")
    output.write("G00 X%0.4f Y%0.4f F%0.4f\n" % (x1, y1, MOVE_SPEED))
    output.write("G01 Z%0.4f F%0.4f\n" % (options.cut_depth, INSERT_SPEED))
    output.write("(Cut)\n")
    output.write("G01 X%0.4f Y%0.4f F%0.4f\n" % (x2, y2, CUT_SPEED))
    output.write("G01 Z%0.4f F%0.4f\n" % (options.safe_depth, MOVE_SPEED))
  # Finish generating the file
  output.write(GCODE_SUFFIX.strip() + "\n")
  output.close()
  