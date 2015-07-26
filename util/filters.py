#!/usr/bin/env python
#----------------------------------------------------------------------------
# 22-Jul-2015 ShaneG
#
# A simple set of filters.
#----------------------------------------------------------------------------
from gcode import Filter, GCommand
from math import sin, cos, radians

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
    return result

class Rotate(Filter):
  """ Rotate around the origin
  """

  def __init__(self, angle):
    """ Set the rotation angle
    """
    self.angle = radians(angle)

  def apply(self, command):
    result = command.clone()
    if (command.X is not None) and (command.Y is not None):
      result.X = (command.X * cos(self.angle)) - (command.Y * sin(self.angle))
      result.Y = (command.X * sin(self.angle)) + (command.Y * cos(self.angle))
    if (command.I is not None) and (command.J is not None):
      result.I = (command.I * cos(self.angle)) - (command.J * sin(self.angle))
      result.J = (command.I * sin(self.angle)) + (command.J * cos(self.angle))
    return result

class Flip(Filter):
  """ Flip X and or Y points around a given center point
  """

  def __init__(self, xflip = None, yflip = None):
    """ Set the rotation angle
    """
    self.xflip = xflip
    self.yflip = yflip

  def apply(self, command):
    result = command.clone()
    if self.xflip is not None:
      if command.X is not None:
        result.X = self.xflip - (command.X - self.xflip)
      if command.I is not None:
        result.I = self.xflip - (command.I - self.xflip)
    if self.yflip is not None:
      if command.Y is not None:
        result.Y = self.yflip - (command.Y - self.yflip)
      if command.J is not None:
        result.J = self.yflip - (command.J - self.yflip)
    return result

