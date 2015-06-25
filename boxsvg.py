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

#----------------------------------------------------------------------------
# SVG generation
#----------------------------------------------------------------------------

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
${path}
  </g>
</svg>
"""

PATH_TEMPLATE = '    <path d="${path}" style="fill: none;stroke: #000000;stroke-width:${strokeWidth}"  />'

def mkLine(x1, y1, x2, y2):
  return Line(complex(x1, y1), complex(x2, y2))

def createSVG(filename, tool, points):
  # Generate the paths
  allPoints = list()
  paths = list()
  t = Template(PATH_TEMPLATE)
  for point in points:
    allPoints.extend(point)
    path = Path()
    lx, ly = point[0]
    for p in point[1:]:
      path.append(mkLine(lx, ly, p[0], p[1]))
      lx = p[0]
      ly = p[1]
    path.closed = True
    paths.append(t.safe_substitute({ 'strokeWidth': tool, 'path': path.d() }))
  # Build the final output
  v = { 
    'xmin': min([ x for x, y in allPoints ]) - (tool / 2),
    'ymin': min([ y for x, y in allPoints ]) - (tool / 2),
    'xmax': max([ x for x, y in allPoints ]) + (tool / 2),
    'ymax': max([ y for x, y in allPoints ]) + (tool / 2)
    }
  v['width'] = abs(v['xmax'] - v['xmin'])
  v['height'] = abs(v['ymax'] - v['ymin'])
  v['path'] = "\n".join(paths)
  out = Template(SVG_TEMPLATE).substitute(v).strip()
  # And write the file
  with open(filename, "w") as svg:
    svg.write(out)

#----------------------------------------------------------------------------
# Co-ordinate generation
#----------------------------------------------------------------------------

def getLine(length, tool, reverse = False):
  """ Generate a list of points for a single line
  """
  points = [ (-tool / 2, 0), (length + (tool / 2), 0) ]
  if reverse:
    points = list(reversed(points))
  return points
  
def getTabLine(length, tool, tabs, depth, reverse = False):
  """ Generate a list containing the sequence of points for tabs
  """
  width = length / (tabs * 2)
  pos = width / 2
  points = [ (-tool / 2, 0), ]
  for p in range(tabs):
    points.append((pos - (tool / 2), 0))
    points.append((pos - (tool / 2), depth))
    pos = pos + width
    points.append((pos + (tool / 2), depth))
    points.append((pos + (tool / 2), 0))
    pos = pos + width
  # Add the final point and return
  points.append((length + tool / 2, 0))
  if reverse:
    points = list(reversed(points))
  return points
  
def getSlotLine(length, tool, tabs, depth, reverse = False):
  """ Generate a list containing the sequence of points for tabs
  """
  width = length / (tabs * 2)
  pos = width / 2
  points = [ (-tool / 2, 0), ]
  for p in range(tabs):
    points.append((pos - (1.5 * tool), 0))
    points.append((pos - (1.5 * tool), -depth))
    pos = pos + width
    points.append((pos + (1.5 * tool), -depth))
    points.append((pos + (1.5 * tool), 0))
    pos = pos + width
  # Add the final point and return
  points.append((length + tool / 2, 0))
  if reverse:
    points = list(reversed(points))
  return points
  
def translate(line, dx, dy):
  """ Return a line translated in x and y
  """
  return list([ (x + dx, y + dy) for x, y in line ])
  
def rotate(line):
  """ Rotate a line 90 degrees
  """
  return list([ (y, x) for x, y in line ])

#----------------------------------------------------------------------------
# Panel generation
#----------------------------------------------------------------------------

def generateBase(width, height, depth, tool, material, base_material):
  base = list()
  base.extend(translate(getTabLine(width, tool, 3, material), 0, -(tool / 2)))
  base.extend(translate(rotate(getLine(height, tool)), width + (tool / 2), 0))
  base.extend(translate(getTabLine(width, tool, 3, -material, True), 0, height + (tool / 2)))
  base.extend(translate(rotate(getLine(height, tool, True)), -(tool / 2), 0))
  return (base, )

def generateBack(width, height, depth, tool, material, base_material):
  back = list()
  back.extend(translate(getLine(width, tool), 0, -(tool / 2)))
  back.extend(translate(rotate(getLine(height, tool)), width + (tool / 2), 0))
  back.extend(translate(getSlotLine(width, tool, 3, -base_material, True), 0, height + tool / 2))
  back.extend(translate(rotate(getLine(height, tool, True)), -tool / 2, 0))
  return (back, )
  
def generateTop(width, height, depth, tool, material, base_material):
  # Adjust sizes
#  width = width + (2 * material)
#  height = height + (2 * material)
#  depth = depth + base_material + material
  # Now generate the paths
  top = list()
  top.extend(translate(getLine(width, tool), 0, -(tool / 2)))
  top.extend(translate(rotate(getTabLine(height, tool, 3, material)), width + (tool / 2), 0))
  top.extend(translate(getLine(width, tool, True), 0, height + (tool / 2)))
  top.extend(translate(rotate(getTabLine(height, tool, 3, -material, True)), -(tool / 2), 0))
  return (top, )

#----------------------------------------------------------------------------
# Main program
#----------------------------------------------------------------------------

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
  # Generate the base
  createSVG(prefix + "base.svg", options.tool, generateBase(options.width, options.height, options.depth, options.tool, material, basematerial))
  createSVG(prefix + "back.svg", options.tool, generateBack(options.width, options.height, options.depth, options.tool, material, basematerial))
  createSVG(prefix + "top.svg", options.tool, generateTop(options.width, options.height, options.depth, options.tool, material, basematerial))
  