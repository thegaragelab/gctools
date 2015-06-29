#!/usr/bin/env python
#----------------------------------------------------------------------------
# 29-Jun-2015 ShaneG
#
# Convert a NGC file into multiple passes to achieve the cut.
#----------------------------------------------------------------------------
from sys import argv
from optparse import OptionParser
from gcode import ZLevel, loadGCode, saveGCode

#--- Usage information
USAGE = """
Usage:
       %s [--cut depth] [--safe depth] [--step depth] [--output filename] filename

Where:

  --cut    depth    specify the target cut depth
  --safe   depth    specify the safe distance for moves between cuts
  --step   depth    the maximum depth to cut during a single pass
  --output filename the name of the file to write the results to
"""

#--- Main program
if __name__ == "__main__":
  # Set up program options
  parser = OptionParser()
  parser.add_option("-c", "--cut", action="store", type="float", dest="cut_depth")
  parser.add_option("-s", "--safe", action="store", type="float", dest="safe_depth")
  parser.add_option("-t", "--step", action="store", type="float", dest="step_depth")
  parser.add_option("-o", "--output", action="store", type="string", dest="output_file")
  options, args = parser.parse_args()
  # Check positional arguments
  if len(args) <> 1:
    print USAGE.strip() % argv[0]
    exit(1)
  # Make sure required arguments are present
  for req in ("cut_depth", "safe_depth", "step_depth"):
    if eval("options.%s" % req) is None:
      print "ERROR: Missing required argument '%s'" % req
      print USAGE.strip() % argv[0]
      exit(1)
  source = args[0]
  # Determine the size of each step
  steps = 1
  while (options.cut_depth / steps) > options.step_depth:
    steps = steps + 1
  delta = options.cut_depth / steps
  depth = delta
  # Now process the file
  # TODO: Load stripped (no prefix or suffix)
  original = loadGCode(source)
  result = list()
  for x in range(steps):
    processor = ZLevel(depth, options.safe_depth)
    result.extend(processor.apply(original))
    depth = depth + delta
  # Write the output
  if options.output_file is None:
    print "\n".join(result)
  else:
    # TODO: Add prefix and suffix
    saveGCode(options.output_file, result)

