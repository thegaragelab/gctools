#!/usr/bin/env python
#----------------------------------------------------------------------------
# 28-Jul-2015 ShaneG
#
# Updated to use new framework.
#
# 04-Dec-2014 ShaneG
#
# A simple program to adjust the Z level (cutting depth and safe depth) for
# a g-code file.
#----------------------------------------------------------------------------
from sys import argv
from optparse import OptionParser
from os.path import splitext
from util import loadGCode, saveGCode, ZLevel

#--- Usage information
USAGE = """
Usage:
       %s [--cut depth] [--safe depth] [--output filename] filename
"""

#--- Main program
if __name__ == "__main__":
  # Set up program options
  parser = OptionParser()
  parser.add_option("-c", "--cut", action="store", type="float", dest="cut_depth")
  parser.add_option("-s", "--safe", action="store", type="float", dest="safe_depth")
  parser.add_option("-o", "--output", action="store", type="string", dest="output_file")
  options, args = parser.parse_args()
  # Check for required options
  for required in ("output_file", ):
    if getattr(options, required, None) is None:
      print "Missing required option '%s'" % required
      print USAGE.strip() % argv[0]
      exit(1)
  # Check positional arguments
  if len(args) <> 1:
    print USAGE.strip() % argv[0]
    exit(1)
  # Set up the source file and collect the depth information
  source = args[0]
  if (options.cut_depth is None) and (options.safe_depth is None):
    print "You haven't asked me to do anything!"
    exit(1)
  # Now process the file
  gcode = loadGCode(source)
  gcode = gcode.clone(ZLevel(cut = options.cut_depth, safe = options.safe_depth))
  saveGCode(options.output_file, gcode)

