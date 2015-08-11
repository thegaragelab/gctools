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

  def distanceFrom(self, x, y):
    return distance(self.x, self.y, x, y)

  def generate(self, gcode, feed):
    return self.x, self.y

class Line(Point):
  """ Represents a line
  """

  def __init__(self, x, y, tx, ty):
    Point.__init__(self, x, y)
    self.tx = tx
    self.ty = ty

  def distanceFrom(self, x, y):
    d1 = distance(self.x, self.y, x, y)
    d2 = distance(self.tx, self.ty, x, y)
    if d2 < d1:
      self.tx, self.x = self.x, self.tx
      self.ty, self.y = self.y, self.ty
      return d2
    return d1

  def generate(self, gcode, feed):
    gcode.append("G01 X%0.4f Y%0.4f F%0.4f" % (self.tx, self.ty, feed))
    return self.tx, self.ty

class Arc(Line):
  """ Represents an arc
  """

  def __init__(self, x, y, tx, ty, i, j, cmd):
    Line.__init__(self, x, y, tx, ty)
    self.cx = x + i
    self.cy = y + j
    self.cmd = cmd

  def distanceFrom(self, x, y):
    d1 = distance(self.x, self.y, x, y)
    d2 = distance(self.tx, self.ty, x, y)
    if d2 < d1:
      self.tx, self.x = self.x, self.tx
      self.ty, self.y = self.y, self.ty
      if self.cmd == "G02":
        self.cmd = "G03"
      else:
        self.cmd = "G02"
      return d2
    return d1

  def generate(self, gcode, feed):
    gcode.append("%s X%0.4f Y%0.4f I%0.4f J%0.4f F%0.4f" % (self.cmd, self.tx, self.ty, self.cx - self.x, self.cy - self.y, feed))
    return self.tx, self.ty

def optimise(source):
  """ Return an optimised copy of the given gcode
  """
  # Build up a sequence of cutting operations
  x, y, z = 0.0, 0.0, 0.0
  cut, safe = source.minz, source.maxz
  insert_feed = 250
  feed = 500
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
      insert_feed = cmd.F or insert_feed
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
        feed = cmd.F or feed
      elif cmd.command in ("G02", "G03"):
        # Arc
        movements.append(Arc(x, y, nx, ny, cmd.I, cmd.J, cmd.command))
        feed = cmd.F or feed
      insert = False
    else:
      airtime = airtime + distance(x, y, nx, ny)
    # Update position
    x, y = nx, ny
  LOG.INFO("    Original - %d operations, %dmm air travel" % (len(movements), int(airtime)))
  if len(movements) == 0:
    LOG.INFO("    No optimisation can be performed.")
    return source
  # Now generate an optimised order of operations
  x, y, nair = 0.0, 0.0, 0.0
  first = True
  optimised = GCode()
  while len(movements) > 0:
    # Sort by distance to current point
    movements.sort(cmp = lambda a, b: cmp(a.distanceFrom(x, y), b.distanceFrom(x, y)))
    current = movements[0]
    movements = movements[1:]
    # Do we need to do a retraction and insertion ?
    if first or (x <> current.x) or (y <> current.y):
      if not first:
        # Retract
        optimised.append("G00 Z%0.4f" % safe)
      first = False
      if (x <> current.x) or (y <> current.y):
        # Move to co-ordinate
        optimised.append("G00 X%0.4f Y%0.4f" % (current.x, current.y))
        nair = nair + distance(x, y, current.x, current.y)
        x, y = current.x, current.y
      # Insert
      optimised.append("G01 Z%0.4f F%0.4f" % (cut, insert_feed))
    # Do the movement
    x, y = current.generate(optimised, feed)
  # Retract
  optimised.append("G00 Z%0.4f" % safe)
  # See what we came up with
  LOG.INFO("    Optimised - %dmm air travel, %d %% of original." % (int(nair), int((100.0 * nair) / airtime)))
  return optimised
