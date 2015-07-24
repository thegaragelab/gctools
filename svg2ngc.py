#!/usr/bin/env python
#----------------------------------------------------------------------------
# 29-Jun-2015 ShaneG
#
# Convert a collection of SVG paths into a Gcode file.
#----------------------------------------------------------------------------
from lxml import etree
from os.path import splitext, exists
from svg.path import Path, Line, parse_path
from optparse import OptionParser
from gcode import saveGCode

#--- Usage information
USAGE = """
Usage:
       %s [--cut depth] [--safe depth] filename

Where:

  --cut    depth    specify the target cut depth
  --safe   depth    specify the safe distance for moves between cuts
"""

GCODE_PREFIX = """
G21 (Use mm)
G90 (Set Absolute Coordinates)
G0 Z%0.4f (Move clear of the board first)
(end of prefix)
"""

GCODE_SUFFIX = """
(Operation complete)
G0 X0 Y0 Z%0.4f
M2
%
"""

def styleContains(style, values):
  """ Determine if the given properties are set in a style definition.
  """
  # First break up the style into properties
  props = dict()
  for entry in style.split(";"):
    k, v = [ e.strip() for e in entry.split(":") ]
    props[k] = v
  # Now check for a match
  for k in values.keys():
    if props.get(k.strip(), "").strip() <> values[k].strip():
      return False
  return True

def getScaling(doc):
  """ Calculate the scaling from document points to mm
  """
  wmm = float(doc.get("width")[:-2])
  hmm = float(doc.get("height")[:-2])
  vbox = list([ float(n) for n in doc.get("viewBox").split(" ") ])
  return wmm / vbox[2], hmm / vbox[3], vbox[3]

def getXY(point, sx, sy, h):
  return round(point.real * sx, 4), round((h - point.imag) * sy, 4)

def processPath(path, cut, safe, sx, sy, h, precision):
  """ Process a single path, generating the required Gcode to implement it.
  """
  gcode = list()
  tool = False
  lx, ly = None, None
  for segment in path:
    length = segment.length()
    if length == 0.0:
      continue
    gcode.append("(%s,%0.4fmm)" % (segment.__class__.__name__, length * sx))
    # Move the tool head if there is a break in the path
    x, y = getXY(segment.start, sx, sy, h)
    if ((x <> lx) or (y <> ly)):
      if tool:
        gcode.append("G0 Z%0.4f" % safe)
        tool = False
      gcode.append("G0 X%0.4f Y%0.4f" % (x, y))
    # Make sure the tool is down
    if not tool:
      gcode.append("G1 Z%0.4f" % cut)
      tool = True
    # Determine what sort of object we are processing
    consumed = False
    if segment.__class__ == Line:
      # Do the move to the end point
      x, y = getXY(segment.end, sx, sy, h)
      gcode.append("G1 X%0.4f Y%0.4f" % (x, y))
      lx, ly = x, y
      consumed = True
# TODO: Arcs can be done with G2/G3 commands
#    if segment.__class__ == Arc:
#      # Circles can be done with G2
#      if segment.radius.real == segment.radius.imag:
#        x, y = getXY(segment.end, sx, sy, h)
    # Fallback, interpolate as a sequence of straight lines
    if not consumed:
      # Assumes sx == sy so we get 1mm steps
      delta = precision / (sx * length)
      pos = delta
      while pos < 1.0:
        x, y = getXY(segment.point(pos), sx, sy, h)
        gcode.append("G1 X%0.4f Y%0.4f" % (x, y))
        pos = pos + delta
      x, y = getXY(segment.end, sx, sy, h)
      gcode.append("G1 X%0.4f Y%0.4f" % (x, y))
      lx, ly = x, y
      consumed = True
  # Bring the tool up again if needed
  if tool:
    gcode.append("G0 Z%0.4f" % safe)
    tool = False
  return gcode

#--- Main program
if __name__ == "__main__":
  # Set up program options
  parser = OptionParser()
  parser.add_option("-c", "--cut", action="store", type="float", dest="cut_depth")
  parser.add_option("-s", "--safe", action="store", type="float", dest="safe_depth")
  parser.add_option("-p", "--precision", action="store", type="float", dest="precision", default=1.0)
  options, args = parser.parse_args()
  # Check positional arguments
  if len(args) <> 1:
    print USAGE.strip() % argv[0]
    exit(1)
  # Make sure required arguments are present
  for req in ("cut_depth", "safe_depth"):
    if eval("options.%s" % req) is None:
      print "ERROR: Missing required argument '%s'" % req
      print USAGE.strip() % argv[0]
      exit(1)
  source = args[0]
  name, ext = splitext(source)
  if ext == "":
    source = name + ".svg"
  if not exists(source):
    print "ERROR: Could not find source file '%s'" % source
    exit(1)
  # Load the paths
  paths = list()
  svg = etree.parse(source)
  # Process any path elements with a 'd' attribute
  sx, sy, h = 1.0, 1.0, 0.0
  for path in svg.getiterator():
    if (path.tag == "svg") or path.tag.endswith("}svg"):
      sx, sy, h = getScaling(path)
    if (path.tag == "path") or path.tag.endswith("}path"):
      # Ignore 'red' construction lines
      s = path.get("style")
      if s is not None:
        if not styleContains(s, { 'stroke': "#000000" }):
          # Non-black strokes are construction lines
          continue
      d = path.get("d")
      if d is not None:
        paths.append(parse_path(d))
  print "Processing %d paths ..." % len(paths)
  results = list()
  for p in paths:
    results.extend(processPath(p, options.cut_depth, options.safe_depth, sx, sy, h, options.precision))
  # Write the file
  saveGCode(
    name + ".ngc",
    results,
    prefix = GCODE_PREFIX % options.safe_depth,
    suffix = GCODE_SUFFIX % options.safe_depth
    )

