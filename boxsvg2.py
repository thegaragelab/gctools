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
<g id="layer1">
${path}
</g>
</svg>
"""

PATH_TEMPLATE = """    <path 
      style="color:#000000;fill:#ff0000;fill-opacity:1;fill-rule:nonzero;stroke:#000000;stroke-width:1;marker:none;visibility:visible;display:inline;overflow:visible;enable-background:accumulate"
      d="${path}"
    />"""

def mkLine(x1, y1, x2, y2):
  x1 = round(x1, 4)
  y1 = round(y1, 4)
  x2 = round(x2, 4)
  y2 = round(y2, 4)
  if (x1 == x2) and (y1 == y2):
    return None
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
    pc = 0
    for p in point[1:]:
      l = mkLine(lx, ly, p[0], p[1])
      if l is not None:
        path.append(l)
        pc = pc + 1
      lx = p[0]
      ly = p[1]
    path.closed = True
    paths.append(t.safe_substitute({ 'strokeWidth': tool, 'path': path.d() }))
    print "Generated path with %d points." % pc
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
# Geometry helpers
#----------------------------------------------------------------------------

def hLine(length, fixed, tool, reverse = False):
  points = list()
  for x in ( -tool / 2, length + (tool / 2)):
    points.append((x, fixed))
  if reverse:
    points = list(reversed(points))
  return points

def vLine(length, fixed, tool, reverse = False):
  points = list()
  for y in ( -tool / 2, length + (tool / 2)):
    points.append((fixed, y))
  if reverse:
    points = list(reversed(points))
  return points

def hTabs(length, fixed, tool, tabs, depth, reverse = False):
  """ Generate a list containing the sequence of points for tabs
  """
  width = length / (tabs * 2)
  pos = width / 2
  points = [ (-tool / 2, fixed), ]
  for p in range(tabs):
    points.append((pos - (tool / 2), fixed))
    points.append((pos - (tool / 2), fixed + depth))
    pos = pos + width
    points.append((pos + (tool / 2), fixed + depth))
    points.append((pos + (tool / 2), fixed))
    pos = pos + width
  # Add the final point and return
  points.append((length + tool / 2, fixed))
  if reverse:
    points = list(reversed(points))
  return points

def vTabs(length, fixed, tool, tabs, depth, reverse = False):
  """ Generate a list containing the sequence of points for tabs
  """
  width = length / (tabs * 2)
  pos = width / 2
  points = [ (fixed, -tool / 2), ]
  for p in range(tabs):
    points.append((fixed, pos - (tool / 2)))
    points.append((fixed + depth, pos - (tool / 2)))
    pos = pos + width
    points.append((fixed + depth, pos + (tool / 2)))
    points.append((fixed, pos + (tool / 2)))
    pos = pos + width
  # Add the final point and return
  points.append((fixed, length + tool / 2))
  if reverse:
    points = list(reversed(points))
  return points

def hSlots(length, fixed, tool, tabs, depth, reverse = False):
  """ Generate a list containing the sequence of points for tabs
  """
  width = length / (tabs * 2)
  pos = width / 2
  points = [ (-tool / 2, fixed), (-tool / 2, fixed + depth), ]
  for p in range(tabs):
    points.append((pos + (tool / 2), fixed + depth))
    points.append((pos + (tool / 2), fixed))
    pos = pos + width
    points.append((pos - (tool / 2), fixed))
    points.append((pos - (tool / 2), fixed + depth))
    pos = pos + width
  # Add the final point and return
  points.append((length + tool / 2, fixed + depth))
  points.append((length + tool / 2, fixed))
  if reverse:
    points = list(reversed(points))
  return points

def vSlots(length, fixed, tool, tabs, depth, reverse = False):
  """ Generate a list containing the sequence of points for tabs
  """
  width = length / (tabs * 2)
  pos = width / 2
  points = [ (fixed, -tool / 2), (fixed + depth, -tool / 2), ]
  for p in range(tabs):
    points.append((fixed + depth, pos + (tool / 2)))
    points.append((fixed, pos + (tool / 2)))
    pos = pos + width
    points.append((fixed, pos - (tool / 2)))
    points.append((fixed + depth, pos - (tool / 2)))
    pos = pos + width
  # Add the final point and return
  points.append((fixed + depth, length + tool / 2))
  points.append((fixed, length + tool / 2))
  if reverse:
    points = list(reversed(points))
  return points

def vSlotOne(length, fixed, tool, width, depth, reverse = False):
  """ Generate a list containing the sequence of points for tabs
  """
  points = [ 
    (fixed, -tool / 2), 
    (fixed, (length - width) / 2 + (tool / 2)),
    (fixed + depth, (length - width) / 2 + (tool / 2)),
    (fixed + depth, (length - width) / 2 + width),
    (fixed, (length - width) / 2 + width),
    (fixed, length + tool / 2)
    ]
  if reverse:
    points = list(reversed(points))
  return points

def vTabOne(length, fixed, tool, width, depth, reverse = False):
  """ Generate a list containing the sequence of points for tabs
  """
  points = [ 
    (fixed, -tool / 2), 
    (fixed, (length - width) / 2 - (tool / 2)),
    (fixed + depth, (length - width) / 2 - (tool / 2)),
    (fixed + depth, (length - width) / 2 + width + tool),
    (fixed, (length - width) / 2 + width + tool),
    (fixed, length + tool / 2)
    ]
  if reverse:
    points = list(reversed(points))
  return points

#----------------------------------------------------------------------------
# Panel generators
#----------------------------------------------------------------------------

def generateBase(width, height, depth, tool, material, base_material):
  base = list()
  base.extend(hTabs(width, -tool / 2, tool, 3, -material))
  base.extend(vTabs(height, width + (tool / 2), tool, 1, material))
  base.extend(hTabs(width, height + (tool / 2), tool, 3, material, reverse = True))
  base.extend(vTabs(height, -tool / 2, tool, 1, -material, reverse = True))
  return [ base, ]
 
def generateBack(width, height, depth, tool, material, base_material):
  back = list()
  back.extend(hLine(width, -tool / 2, tool))
  back.extend(vSlotOne(depth, width + (tool / 2), tool, 10, -material))
  back.extend(hSlots(width, depth + (tool / 2), tool, 3, base_material, reverse = True))
  back.extend(vSlotOne(depth, -tool / 2, tool, 10, material, reverse = True))
  return [ back, ]

def generateStrut(width, height, depth, tool, material, base_material):
  back = list()
  back.extend(hLine(height, -tool / 2, tool))
  back.extend(vTabOne(30, height + (tool / 2), tool, 10, material))
  back.extend(hLine(height, 30 + (tool / 2), tool, reverse = True))
  back.extend(vTabOne(30, -tool / 2, tool, 10, -material, reverse = True))
  return [ back, ]

def generateTop(width, height, depth, tool, material, base_material):
  top = list()
  top.extend(hLine(width, -tool / 2, tool))
  top.extend(vTabs(height, width + (tool / 2), tool, 3, material))
  top.extend(hLine(width, height + (tool / 2), tool, reverse = True))
  top.extend(vTabs(height, -tool / 2, tool, 3, -material, reverse = True))
  return [ top, ]

def generateSide(width, height, depth, tool, material, base_material):
  side = list()
#  side.extend(hLine(height, -tool / 2, tool))
  side.extend(hSlots(height, -tool / 2, tool, 3, -material))
  side.extend(vLine(depth, height + (tool / 2), tool))
#  side.extend(hLine(height, depth + (tool / 2), tool, reverse = True))
  side.extend(hSlots(height, depth + (tool / 2), tool, 1, base_material, reverse = True))
  side.extend(vLine(depth, -tool / 2, tool, reverse = True))
  return [ side, ]
  
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
  # Generate the panels for the bottom
  createSVG(prefix + "base.svg", options.tool, generateBase(options.width + (2 * options.material), options.height, options.depth, options.tool, material, basematerial))
  createSVG(prefix + "back.svg", options.tool, generateBack(options.width + (2 * options.material), options.height, options.depth + options.material, options.tool, material, basematerial))
  createSVG(prefix + "strut.svg", options.tool, generateStrut(options.width + (2 * options.material), options.height, options.depth + options.material, options.tool, material, basematerial))
  # Generate the panels for the top
  createSVG(prefix + "top.svg", options.tool, generateTop(options.width + (2 * options.material), options.height, options.depth, options.tool, material, basematerial))
  createSVG(prefix + "side.svg", options.tool, generateSide(options.width + (2 * options.material), options.height, options.depth, options.tool, material, basematerial))
  