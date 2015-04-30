#!/usr/bin/env python
#----------------------------------------------------------------------------
# 30-Apr-2015 ShaneG
#
# Create the shapes needed to cut panels for a 2U style box with a CNC. This
# script does not generate the g-code, it creates the SVG paths needed for
# each unique panel so additional elements (such as decorations and/or
# mounting holes) can be added prior to running it through gcodetools in
# Inkscape.
#----------------------------------------------------------------------------
from sys import argv
from optparse import OptionParser
from svg.path import Path, Line

#--- Usage information
USAGE = """
Usage:
       %s -x|--width width -y|--height height -z|--depth depth [--tool size] [--material size] [--base-material size] [prefix]
"""

def generatePanel(tool, width, height, tabWidth, tabDepth, tabs):
  """ Generate a panel of the given size
  """
  # Adjust for tool size
  width = width + tool
  height = height + tool
  # Set starting point
  xp = 0
  yp = 0
  index = 0
  # Build the path
  path = Path()
  for x, y, dx, dy in ((width, 0, 0, -1), (width, height, 1, 0), (0, height, 0, 1), (0, 0, -1, 0)):
    if tabs[index] is None:
      # Straight line
      path.append(Line(complex(xp, yp), complex(x, y)))
    elif tabs[index]:
      # Protuding tabs
      path.append(Line(complex(xp, yp), complex(x, y)))
    else:
      # Slot
      path.append(Line(complex(xp, yp), complex(x, y)))
    index = index + 1
    xp = x
    yp = y
  path.closed = True
  return path.d()

# Main program
if __name__ == "__main__":
  # Set up program options
  parser = OptionParser()
  parser.add_option("-x", "--width", action="store", type="float", dest="width")
  parser.add_option("-y", "--height", action="store", type="float", dest="height")
  parser.add_option("-z", "--depth", action="store", type="float", dest="depth")
  parser.add_option("-t", "--tool", action="store", type="float", dest="tool", default=3.0)
  parser.add_option("-m", "--material", action="store", type="float", dest="material", default=1.5)
  parser.add_option("-b", "--base-material", action="store", type="float", dest="basematerial")
  options, args = parser.parse_args()
  # Make sure required arguments are present
  for req in ("width", "height", "depth"):
    if eval("options.%s" % req) is None:
      print "ERROR: Missing required argument '%s'" % req
      print USAGE.strip() % argv[0]
      exit(1)
  # Check positional arguments
  if len(args) <> 1:
    prefix = "box_"
  else:
    prefix = args[0].strip() + "_"
  # Get material and base material size
  material = options.material
  if options.basematerial is None:
    basematerial = material
  else:
    basematerial = options.basematerial
  # TODO: Calculate the size of tabs
  tabWidthW = options.width / 6
  tabWidthH = options.height / 6
  # TODO: Generate base, front and back panels and the side mounts
  print generatePanel(options.tool, options.width + (4 * material), options.height + (4 * material), tabWidthW, material, (False, None, True, None))
  print generatePanel(options.tool, options.width + (4 * material), options.depth + (2 * material), tabWidthW, basematerial, (True, None, None, None))

  # TODO: Generate top, left and right panels and the side mounts

