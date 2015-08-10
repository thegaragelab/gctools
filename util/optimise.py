#!/usr/bin/env python
#----------------------------------------------------------------------------
# 10-Aug-2015 ShaneG
#
# Tool path optimisation. This creates new gcode that performs the same
# cutting operations while minimising the amount of non-cutting movement.
#----------------------------------------------------------------------------
from gcode import GCode, GCommand
from logger import LOG
from math import sqrt

def distance(x1, y1, x2, y2):
  """ Calculate the distance between two points
  """
  return sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
  
class Point:
  """ Represent a single point
  """
  
  def __init__(self, x, y):
    self.x = x
    self.y = y
    
class Line(Point):
  """ Represents a line
  """
  
  def __init__(self, x, y, tx, ty):
    Point.__init__(self, x, y)
    self.tx = tx
    self.ty = ty
    
class Arc(Line):
  """ Represents an arc
  """
  
  def __init__(self, x, y, tx, ty, cx, cy, cmd):
    Line.__init__(self, x, y, tx, ty)
    self.cx = cx
    self.cy = cy
    self.cmd = cmd
    
def optimise(source):
  """ Return an optimised copy of the given gcode
  """
  # Build up a sequence of cutting operations
  x, y, z = 0.0, 0.0, 0.0
  cut, safe = source.minz, source.maxz
  prefix = list()
  movements = list()
  airtime = 0.0
  insert = False
  cutting = False
  for cmd in source.lines:
    # Look for insertion or retraction. Note that we assume that these moves
    # only change the Z axis
    nz = cmd.Z or z
    if (nz < 0.0) and (z >= 0.0):
      z = nz
      insert = True
      cutting = True
      continue
    if (nz >= 0.0) and (z < 0.0):
      z = nz
      cutting = False
      if insert:
        # Add as a point
        movements.append(Point(x, y))
        insert = False
      continue
    # Figure out the new position
    nx = cmd.X or x
    ny = cmd.Y or y
    if cutting:
      if cmd.command == "G01":
        # Line
        movements.append(Line(x, y, nx, ny))
      elif cmd.command in ("G02", "G03"):
        # Arc
        movements.append(Arc(x, y, nx, ny, cmd.I, cmd.J, cmd.command))
      insert = False
    else:
      airtime = airtime + distance(x, y, nx, ny)
    # Update position
    x, y = nx, ny
  LOG.INFO("    Original - %d operations, %dmm air travel" % (len(movements), int(airtime)))
  return source.clone()

