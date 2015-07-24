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
  """
  # Start with a center line
  center = options.width / 2
  output.write("(Center line)\n")
  output.write("G00 X%0.4f Y%0.4f F%0.4f\n" % (center, options.height - (options.toolsize / 2), MOVE_SPEED))
  output.write("(Penetrate)\n")
  output.write("G01 Z%0.4f F%0.4f\n" % (options.cut_depth, INSERT_SPEED))
  output.write("(Cut)\n")
  output.write("G01 X%0.4f Y%0.4f F%0.4f\n" % (center, options.toolsize / 2, CUT_SPEED))
  output.write("(Retract)\n")
  output.write("G00 Z%0.4f F%0.4f\n" % (options.safe_depth, MOVE_SPEED))
  # Now do alternating cuts from the center line to each edge
  left = options.toolsize / 2
  right = options.width - (options.toolsize / 2)
  top = options.height - (options.toolsize / 2)
  current = options.toolsize / 2
  while current < top:
    # Do the left side
    output.write("G00 X%0.4f Y%0.4f F%0.4f\n" % (center, current, MOVE_SPEED))
    output.write("(Penetrate)\n")
    output.write("G01 Z%0.4f F%0.4f\n" % (options.cut_depth, INSERT_SPEED))
    output.write("(Cut)\n")
    output.write("G01 X%0.4f Y%0.4f F%0.4f\n" % (left, current, CUT_SPEED))
    output.write("(Retract)\n")
    output.write("G00 Z%0.4f F%0.4f\n" % (options.safe_depth, MOVE_SPEED))
    # Do the right side
    output.write("G00 X%0.4f Y%0.4f F%0.4f\n" % (center, current, MOVE_SPEED))
    output.write("(Penetrate)\n")
    output.write("G01 Z%0.4f F%0.4f\n" % (options.cut_depth, INSERT_SPEED))
    output.write("(Cut)\n")
    output.write("G01 X%0.4f Y%0.4f F%0.4f\n" % (right, current, CUT_SPEED))
    output.write("(Retract)\n")
    output.write("G00 Z%0.4f F%0.4f\n" % (options.safe_depth, MOVE_SPEED))
    # Move up
    current = current + ((1 - OVERLAP) * options.toolsize)
  # Do an additional pass for the final line if needed
  if current != top:
    current = top
    # Do the left side
    output.write("G00 X%0.4f Y%0.4f F%0.4f\n" % (center, current, MOVE_SPEED))
    output.write("(Penetrate)\n")
    output.write("G01 Z%0.4f F%0.4f\n" % (options.cut_depth, INSERT_SPEED))
    output.write("(Cut)\n")
    output.write("G01 X%0.4f Y%0.4f F%0.4f\n" % (left, current, CUT_SPEED))
    output.write("(Retract)\n")
    output.write("G00 Z%0.4f F%0.4f\n" % (options.safe_depth, MOVE_SPEED))
    # Do the right side
    output.write("G00 X%0.4f Y%0.4f F%0.4f\n" % (center, current, MOVE_SPEED))
    output.write("(Penetrate)\n")
    output.write("G01 Z%0.4f F%0.4f\n" % (options.cut_depth, INSERT_SPEED))
    output.write("(Cut)\n")
    output.write("G01 X%0.4f Y%0.4f F%0.4f\n" % (right, current, CUT_SPEED))
    output.write("(Retract)\n")
    output.write("G00 Z%0.4f F%0.4f\n" % (options.safe_depth, MOVE_SPEED))
  """
  pass

def areaCut(gcode):
  """ Do an area cut from outside to center
  """
  """
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
  """
  pass

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
    gcode.render(filename, showAll = True)
    print "Generated image '%s'" % filename
