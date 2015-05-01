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
from string import Template
from optparse import OptionParser
from svg.path import Path, Line

#--- Usage information
USAGE = """
Usage:
       %s -x|--width width -y|--height height -z|--depth depth [--tool size] [--material size] [--base-material size] [prefix]
"""

#--- SVG templates

SVG_TEMPLATE = """
<svg
   xmlns:svg="http://www.w3.org/2000/svg"
   xmlns="http://www.w3.org/2000/svg"
   version="1.1"
   width="${width}mm"
   height="${height}mm"
   viewBox="${xmin} ${ymin} ${xmax} ${ymax}"
   >
  <g style="fill: none">
${paths}
  </g>

</svg>
"""

PATH_TEMPLATE = '    <path d="${path}" style="fill: none;stroke: #000000;stroke-width:${strokeWidth}"  />'

def createSVG(filename, xmin, ymin, xmax, ymax, paths):
  v = { 'xmin': xmin, 'ymin': ymin, 'xmax': xmax, 'ymax': ymax }
  v['width'] = abs(xmax - xmin)
  v['height'] = abs(ymax - ymin)
  # Generate the paths
  t = Template(PATH_TEMPLATE)
  v['paths'] = "\n".join([ t.substitute({ 'strokeWidth': w, 'path': p }) for w, p in paths ])
  # Build the final output
  t = Template(SVG_TEMPLATE)
  out = t.substitute(v).strip()
  # And write the file
  with open(filename, "w") as svg:
    svg.write(out)

def mkLine(x1, y1, x2, y2, bounds):
  # Update bounds
  bounds[0] = min(bounds[0], x1, x2)
  bounds[1] = max(bounds[1], x1, x2)
  bounds[2] = min(bounds[2], y1, y2)
  bounds[3] = max(bounds[3], y1, y2)
  return Line(complex(x1, y1), complex(x2, y2))

def getTabPoints(x1, x2, y1, y2, tabWidth, tool, tab):
  # Determine direction
  rev = False
  if x2 < x1:
    x2, x1, rev = x1, x2, True
  # Get the points
  start = ((x2 - x1) - (tabWidth * 5)) / 2
  points = [ (x1, y1), ]
  adjust = -tool / 2
  if tab:
    adjust = -adjust
  for p in range(6):
    if (p & 0x01) == 0x01:
      points.append((x1 + start + (p * tabWidth) + adjust, y2))
      points.append((x1 + start + (p * tabWidth) + adjust, y1))
    else:
      points.append((x1 + start + (p * tabWidth) - adjust, y1))
      points.append((x1 + start + (p * tabWidth) - adjust, y2))
  points.append((x2, y1))
  if rev:
    points.reverse()
  return points

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
  bounds = [ 0.0, 0.0, 0.0, 0.0 ]
  # Build the path
  path = Path()
  for x, y in ((width, 0), (width, height), (0, height), (0, 0)):
    if tabs[index] is None:
      # Straight line
      path.append(mkLine(xp, yp, x, y, bounds))
    elif tabs[index]:
      # Protuding tabs
      if xp <> x:
        # Horizontal
        dy = y + tabDepth + (tool / 2)
        if y == 0:
          dy = y - tabDepth - (tool / 2)
        p = getTabPoints(xp, x, y, dy, tabWidth, tool, tabs[index])
      else:
        # Vertical
        dx = x + tabDepth + (tool / 2)
        if x == 0:
          dx = x - tabDepth - (tool / 2)
        p = getTabPoints(yp, y, x, dx, tabWidth, tool, tabs[index])
      for idx in range(1, len(p)):
        path.append(mkLine(p[idx - 1][0], p[idx - 1][1], p[idx][0], p[idx][1], bounds))
    else:
      # Slots
      if xp <> x:
        # Horizontal
        dy = y - tabDepth - (tool / 2)
        if y == 0:
          dy = y + tabDepth + (tool / 2)
        p = getTabPoints(xp, x, y, dy, tabWidth, tool, tabs[index])
      else:
        # Vertical
        dx = x - tabDepth - (tool / 2)
        if x == 0:
          dx = x + tabDepth + (tool / 2)
        p = getTabPoints(yp, y, x, dx, tabWidth, tool, tabs[index])
      for idx in range(1, len(p)):
        path.append(mkLine(p[idx - 1][0], p[idx - 1][1], p[idx][0], p[idx][1], bounds))
    index = index + 1
    xp = x
    yp = y
  path.closed = True
  return bounds, path.d()

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
  # Calculate the size of tabs
  tabWidthW = options.width / 6
  tabWidthH = options.height / 6
  # Generate the base
  bounds, path = generatePanel(options.tool, options.width + (4 * material), options.height + (4 * material), tabWidthW, material, (True, None, True, None))
  paths = ( (
    options.tool,
    path
    ), )
  createSVG(prefix + "base.svg", bounds[0], bounds[2], bounds[1], bounds[3], paths)
  # Generate front panel
  bounds, path = generatePanel(options.tool, options.width + (4 * material), options.depth + (2 * material), tabWidthW, basematerial, (False, None, None, None))
  paths = ( (
    options.tool,
    path
    ), )
  createSVG(prefix + "front.svg", bounds[0], bounds[2], bounds[1], bounds[3], paths)
  # Generate back panel
  bounds, path = generatePanel(options.tool, options.width + (4 * material), options.depth + (2 * material), tabWidthW, basematerial, (None, None, False, None))
  paths = ( (
    options.tool,
    path
    ), )
  createSVG(prefix + "back.svg", bounds[0], bounds[2], bounds[1], bounds[3], paths)
  # TODO: Generate side mounts
  # Generate the top
  bounds, path = generatePanel(options.tool, options.width + (4 * material), options.height + (4 * material), tabWidthW, material, (None, True, None, True))
  paths = ( (
    options.tool,
    path
    ), )
  createSVG(prefix + "top.svg", bounds[0], bounds[2], bounds[1], bounds[3], paths)
  # Generate left panel
  bounds, path = generatePanel(options.tool, options.width + (4 * material), options.depth + (2 * material), tabWidthW, material, (None, False, None, None))
  paths = ( (
    options.tool,
    path
    ), )
  createSVG(prefix + "left.svg", bounds[0], bounds[2], bounds[1], bounds[3], paths)
  # Generate right panel
  bounds, path = generatePanel(options.tool, options.width + (4 * material), options.depth + (2 * material), tabWidthW, material, (None, None, None, False))
  paths = ( (
    options.tool,
    path
    ), )
  createSVG(prefix + "right.svg", bounds[0], bounds[2], bounds[1], bounds[3], paths)
  # TODO: Generate mounts

