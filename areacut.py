#!/usr/bin/env python
#----------------------------------------------------------------------------
# 20-Dec-2014 ShaneG
#
# Generate a rectangular area cut.
#----------------------------------------------------------------------------
from sys import argv
from os.path import splitext
from optparse import OptionParser
from util import GCode, saveGCode, getSettings

#--- Usage information
USAGE = """
Usage:
       %s [options] filename

Where options are:

  --safe    depth   Safe depth for movements
  --cut     depth   Cutting depth
  --feed    rate    Feedrate for cutting operations
  --tool    size    Tool diameter (in mm)
  --width   width   Width of area to cut (mm)
  --height  height  Height of are to cut (mm)
  --overlap percent Percentage of overlap between cuts
  --center          Start in the center of the area
  --image           Generate an image of the final result
"""

# Set up the control dictionary
CONTROL = {
  "safe":    3,
  "cut":     -1,
  "feed":    254,
  "tool":    None,
  "width":   None,
  "height":  None,
  "overlap": 20.0
  }

def centerCut(gcode):
  """ Do a cut from the center outwards
  """
  global control
  width, height = CONTROL['width'], CONTROL['height']
  tool, overlap = CONTROL['tool'], CONTROL['overlap']
  cut, safe, feed = CONTROL['cut'], CONTROL['safe'], CONTROL['feed']
  # Calculate dimensions
  x1, y1 = tool / 2, tool / 2
  x2, y2 = width - x1, height - y1
  # Start with a center line
  center = (x2 - x1) / 2
  gcode.append("G00 X%0.4f Y%0.4f" % (center, y1))
  gcode.append("G01 Z%0.4f F%0.4f" % (cut, feed))
  gcode.append("G01 X%0.4f Y%0.4f F%0.4f" % (center, y2, feed))
  # Do the right hand side first (+ve of center)
  y = y2
  delta = tool * (1.0 - (overlap / 100.0))
  while delta > 0.0:
    gcode.append("G01 X%0.4f Y%0.4f F%0.4f" % (x2, y, feed))
    delta = min(y - y1, delta)
    y = y - delta
    gcode.append("G00 Z%0.4f" % safe)
    gcode.append("G00 X%0.4f Y%0.4f" % (center, y))
    gcode.append("G01 Z%0.4f F%0.4f" % (cut, feed))
  gcode.append("G01 X%0.4f Y%0.4f F%0.4f" % (x2, y, feed))
  gcode.append("G00 Z%0.4f" % safe)
  # Move to the next position
  gcode.append("G00 X%0.4f Y%0.4f" % (center, y1))
  gcode.append("G00 Z%0.4f F%0.4f" % (cut, feed))
  # Do the left hand side (-ve of center)
  y = y1
  delta = tool * (1.0 - (overlap / 100.0))
  while delta > 0.0:
    gcode.append("G01 X%0.4f Y%0.4f F%0.4f" % (x1, y, feed))
    delta = min(y2 - y, delta)
    y = y + delta
    gcode.append("G00 Z%0.4f" % safe)
    gcode.append("G00 X%0.4f Y%0.4f" % (center, y))
    gcode.append("G01 Z%0.4f F%0.4f" % (cut, feed))
  gcode.append("G01 X%0.4f Y%0.4f F%0.4f" % (x1, y, feed))
  gcode.append("G00 Z%0.4f" % safe)

def areaCut(gcode):
  """ Do an area cut from outside to center
  """
  global CONTROL
  width, height = CONTROL['width'], CONTROL['height']
  tool, overlap = CONTROL['tool'], CONTROL['overlap']
  cut, safe, feed = CONTROL['cut'], CONTROL['safe'], CONTROL['feed']
  # Calculate starting point
  x1, y1 = tool / 2, tool / 2
  x2, y2 = width - x1, height - y1
  delta = tool * (1.0 - (overlap / 100.0))
  # Do the insertion
  gcode.append("G00 X%0.4f Y%0.4f" % (x1, y1))
  gcode.append("G01 Z%0.4f F%0.4f" % (cut, feed))
  while delta > 0.0:
    gcode.append("G01 X%0.4f Y%0.4f F%0.4f" % (x2, y1, feed))
    gcode.append("G01 X%0.4f Y%0.4f F%0.4f" % (x2, y2, feed))
    gcode.append("G01 X%0.4f Y%0.4f F%0.4f" % (x1, y2, feed))
    gcode.append("G01 X%0.4f Y%0.4f F%0.4f" % (x1, y1 + delta, feed))
    # Update the delta
    delta = min(y2 - y1, x2 - x1, delta)
    # Update the target points
    x1 = x1 + delta
    y1 = y1 + delta
    x2 = x2 - delta
    y2 = y2 - delta
  # Move to safe point
  gcode.append("G00 Z%0.4f" % safe)

#--- Main program
if __name__ == "__main__":
  # Set up program options
  parser = OptionParser()
  parser.add_option("-s", "--safe", action="store", type="float", dest="safe")
  parser.add_option("-c", "--cut", action="store", type="float", dest="cut")
  parser.add_option("-f", "--feed", action="store", type="float", dest="feed")
  parser.add_option("-t", "--tool", action="store", type="float", dest="tool")
  parser.add_option("-x", "--width", action="store", type="float", dest="width")
  parser.add_option("-y", "--height", action="store", type="float", dest="height")
  parser.add_option("-o", "--overlap", action="store", type="float", dest="overlap")
  parser.add_option("-n", "--center", action="store_true", dest="center", default=False)
  parser.add_option("-i", "--image", action="store_true", dest="image", default=False)
  options, args = parser.parse_args()
  # Make sure required arguments are present
  for req in ("width", "height", "tool"):
    if getattr(options, req, None) is None:
      print "ERROR: Missing required argument '%s'" % req
      print USAGE.strip() % argv[0]
      exit(1)
  # Check positional arguments
  if len(args) <> 1:
    print "ERROR: Missing output file"
    print USAGE.strip() % argv[0]
    exit(1)
  # Load defaults
  getSettings(CONTROL, options)
  # Show current settings
  print "Selected options:"
  for k in sorted(CONTROL.keys()):
    if not (k in ("prefix", "suffix")):
      print "  %-10s: %s" % (k, str(CONTROL[k]))
  # Get the filename
  name, ext = splitext(args[0])
  if ext == "":
    ext = ".ngc"
  filename = name + ext
  # Generate the gcode
  print "\nCreating file '%s'" % args[0]
  gcode = GCode()
  if options.center:
    centerCut(gcode)
  else:
    areaCut(gcode)
  # Save the result
  saveGCode(filename, gcode, prefix = CONTROL['prefix'], suffix = CONTROL['suffix'])
  print "  %s" % str(gcode)
  # Save the image (if requested)
  if options.image:
    filename = name + ".png"
    gcode.render(filename, showall = True)
    print "Generated image '%s'" % filename
