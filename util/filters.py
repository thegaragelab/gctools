#!/usr/bin/env python
#----------------------------------------------------------------------------
# 22-Jul-2015 ShaneG
#
# A simple set of filters.
#----------------------------------------------------------------------------
from gcode import Filter, GCommand

class SwapXY(Filter):
  """ Swap X/Y (and I/J) co-ordinates
  """

  def apply(self, command):
    result = command.clone()
    result.X, result.Y = command.Y, command.X
    result.I, result.J = command.J, command.Y
    return result

class Translate(Filter):
  """ Translate on one or more axis
  """

  def __init__(self, dx = 0.0, dy = 0.0, dz = 0.0):
    self.dx = dx
    self.dy = dy
    self.dz = dz

  def apply(self, command):
    result = command.clone()
    for p in ("X", "I"):
      if getattr(command, p) is not None:
        setattr(result, p, getattr(command, p) + self.dx)
    for p in ("Y", "J"):
      if getattr(command, p) is not None:
        setattr(result, p, getattr(command, p) + self.dy)
    for p in ("Z", "K"):
      if getattr(command, p) is not None:
        setattr(result, p, getattr(command, p) + self.dz)

