#!/usr/bin/env python
#----------------------------------------------------------------------------
# 16-Jan-2015 ShaneG
#
# Generate a probe file for a given area.
#----------------------------------------------------------------------------
from sys import argv
from optparse import OptionParser
from random import shuffle

#--- Usage information
USAGE = """
Usage:
       %s [--width width] [--height height] [--xstep xstep] [--ystep ystep] [--safe safe_height] [--maxmove maxmove] filename
"""

# Prefix code (use safe)
GCODE_PREFIX = """
G20 (Use inch)
G90 (Set Absolute Coordinates)
(begin initial probe and set Z to 0)
G0 Z%0.4f(Move clear of the board first)
"""

# First probe - use pos, safe, maxmove, safe, maxmove, safe
GCODE_FIRST = """
G0 X%0.4f Y%0.4f
G0 Z%0.4f(Quick move to probe clearance height)
G38.2 Z%0.4f F5
G10 L20 P0 Z0
G0 Z%0.4f
G38.2 Z%0.4f F2.5
G10 L20 P0 Z0
(PROBEOPEN RawProbeLog.txt)
G0 Z%0.4f
"""

# Single probe step - use x, y, maxmove, feedrate, safe
GCODE_STEP = """
G0 X%0.4f Y%0.4f
G38.2 Z%0.4f F%0.4f
G0 Z%0.4f
"""

# Suffix code - use safe
GCODE_SUFFIX = """
(Operation complete)
G0 X0 Y0 Z%0.4f
(PROBECLOSE)
M2
"""

#--- Main program
if __name__ == "__main__":
  # Set up program options
  parser = OptionParser()
  parser.add_option("-w", "--width", action="store", type="float", dest="width")
  parser.add_option("-H", "--height", action="store", type="float", dest="height")
  parser.add_option("-x", "--xstep", action="store", type="int", dest="xstep", default=10)
  parser.add_option("-y", "--ystep", action="store", type="int", dest="ystep", default=10)
  parser.add_option("-m", "--maxmove", action="store", type="float", dest="maxmove", default=-0.5)
  parser.add_option("-s", "--safe", action="store", type="float", dest="safe", default=5.0)
  parser.add_option("-r", "--random", action="store_true", dest="random", default=False)
  parser.add_option("-b", "--backwards", action="store_true", dest="backwards", default=False)
  parser.add_option("-f", "--feedrate", action="store", type="float", dest="feedrate", default=127)
  options, args = parser.parse_args()
  # Make sure required arguments are present
  for req in ("width", "height"):
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
  # Generate the list of probe points
  dx = options.width / options.xstep
  dy = options.height / options.ystep
  points = list()
  for y in range(options.ystep + 1):
    if (y % 2) == 0:
      # Even lines
      for x in range(options.xstep + 1):
        points.append((x * dx / 25.4, y * dy / 25.4, options.maxmove / 25.4))
    else:
      # Odd lines
      for x in range(options.xstep, -1, -1):
        points.append((x * dx / 25.4, y * dy / 25.4, options.maxmove / 25.4))
  # Reverse order if needed
  if options.backwards:
    points = list(reversed(points))
  # Shuffle if needed
  if options.random:
    shuffle(points)
  # Start generating the file
  print "Creating file '%s'" % args[0]
  output = open(args[0], "w")
  output.write(GCODE_PREFIX.strip() % (options.safe / 25.4) + "\n")
  # Do the first move
  output.write(GCODE_FIRST.strip() % (points[0][0], points[0][1], options.safe / 25.4, options.maxmove / 25.4, options.safe / 25.4, options.maxmove / 25.4, options.safe / 25.4) + "\n")
  # Do the individual probes
  for p in points:
    output.write(GCODE_STEP.strip() % (p[0], p[1], options.maxmove / 25.4, options.feedrate / 25.4, options.safe / 25.4) + "\n")
  # Generate the suffix
  output.write(GCODE_SUFFIX.strip() % (options.safe / 25.4) + "\n")
  output.close()

