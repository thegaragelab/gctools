#!/usr/bin/env python
#----------------------------------------------------------------------------
# 28-Jul-2015 ShaneG
#
# Updated for the new framework
#
# 29-Jun-2015 ShaneG
#
# Convert a NGC file into multiple passes to achieve the cut.
#----------------------------------------------------------------------------
from sys import argv
from optparse import OptionParser
from util import *

#--- Usage information
USAGE = """
Usage:
       %s [--cut depth] [--safe depth] [--step depth] [--output filename] filename

Where:

  --cut    depth    the total cut depth
  --safe   depth    specify the safe distance for moves between cuts
  --step   depth    the maximum depth to cut during a single pass
  --output filename the name of the file to write the results to
"""

#--- Defaults
CONTROL = {
  "cut": -2.0,
  "safe": 3.0,
  "step": -1.0,
  }

#--- Main program
if __name__ == "__main__":
  # Set up program options
  parser = OptionParser()
  parser.add_option("-c", "--cut", action="store", type="float", dest="cut")
  parser.add_option("-s", "--safe", action="store", type="float", dest="safe")
  parser.add_option("-t", "--step", action="store", type="float", dest="step")
  parser.add_option("-o", "--output", action="store", type="string", dest="output")
  options, args = parser.parse_args()
  # Check positional arguments
  if len(args) <> 1:
    print USAGE.strip() % argv[0]
    exit(1)
  # Make sure required arguments are present
  for req in ("step", "output"):
    if getattr(options, req, None) is None:
      print "ERROR: Missing required argument '%s'" % req
      print USAGE.strip() % argv[0]
      exit(1)
  source = args[0]
  # Get defaults and load the file
  CONTROL = getSettings(CONTROL, options)
  original = loadGCode(source, BoxedLoader(start = GCommand("G00 X0 Y0"), end = GCommand("M02"), inclusive = False))
  # Determine the size of each step
  steps = 1
  if CONTROL['cut'] < CONTROL['step']:
    steps = int(round(0.5 + (CONTROL['cut'] / CONTROL['step']), 0))
  delta = CONTROL['cut'] / steps
  depth = delta
  # Now process the file
  result = GCode()
  for x in range(steps):
    print "  Generating pass at Z = %0.4f" % depth
    result.append(original.clone(ZLevel(safe = CONTROL['safe'], cut = depth)))
    depth = depth + delta
  # Write the output
  saveGCode(
    options.output,
    result,
    prefix = CONTROL['prefix'],
    suffix = CONTROL['suffix']
    )

