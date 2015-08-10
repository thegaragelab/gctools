#!/usr/bin/env python
#----------------------------------------------------------------------------
# 27-Jul-2015 ShaneG
#
# Updated to work with the new framework
#
# 21-Jul-2015 ShaneG
#
# Line Grinder can generate files with invalid arc commands (the end-point
# radius differs from the start-point radius). This code implements a filter
# to repair that. Original: https://github.com/blinkenlight/LineBender
#----------------------------------------------------------------------------
from gcode import Filter
from math import sqrt, atan, sin, cos, radians

#----------------------------------------------------------------------------
# Calculations
#----------------------------------------------------------------------------

def sqr(x):
  """ Return number squared
  """
  return(x*x);

def dist(Xa, Ya, Xb, Yb):
  """ Calculate distance between two points.
  """
  return(sqrt(sqr(Xa - Xb) + sqr(Ya - Yb)));

def bendThatArc(X0, Y0, X1, Y1, X2, Y2):
  """ Does the actual math to recalculate the arc's center

    Note: X0,Y0 = arc start, X1,Y1 = arc end, X2,Y2 = original arc center
    Also, the proverbial compulsory bug in every software probably lives in here

    To briefly explain what's going on below, try to imagine solving it this way:
    In a custom coordinate system where both arc endpoints are on the "X" axis
    and the "Y" axis passes exactly halfway between them, the solution for the
    center of the arc is trivial: X=0, and Y is found as one side in the right
    angled triangle in which the distance to the arc endpoints is the hypotenuse
    and is fixed as the arc radius, while the other side is half the distance
    between the endpoints. Once we have this (X, Y) for the center, it's just a
    matter of (roto-)translating our custom coordinate system onto the actual
    frame of reference - not hard once we find the coordinates of the middle
    point of the segment connecting the arc's endpoints and the angle that
    segment makes with the horizontal ("X"-axis) of the "real" reference frame.
    In fact, some of you might recognize the trigonometric bit towards the end
    as a specific form of the general equations for transforming coordinate
    systems. There are two possible solutions - we pick the one we like more...
  """
  R = dist(X0, Y0, X2, Y2);                        # Radius we want to keep for the arc (equal to the original arc's radius)
  T = dist(X0, Y0, X1, Y1) / 2;                    # Half of the distance between the arc's endpoints (half length of the segment connecting them)
  S = sqrt(abs(sqr(R) - sqr(T)));                       # Center's distance from the midpoint on the perpendicular that goes through it (in either direction)
  Xm = (X0 + X1) / 2;                              # Coordinates of the above-mentioned midpoint of the segment connecting the arc's endpoints
  Ym = (Y0 + Y1) / 2;                              # These are our translation coordinates for the reference frame transformation
  if X0 == X1:                                     # Now we just need the angle between our custom and the global reference frame
      alfa = radians(90);                          # We'd rather avoid a division by zero for the alfa = 90 degrees case (endpoints on the same vertical)
  else:
      alfa = atan((Y1 - Y0) / (X1 - X0));          # Otherwise, the "slope" of the segment connecting the arc endpoints is the angle we want
  X3 = Xm + S * sin(alfa);                         # The actual coordinate system transformation of the point (X=0, Y=S) into the real reference frame
  Y3 = Ym - S * cos(alfa);
  X4 = Xm - S * sin(alfa);                         # The other possible solution.
  Y4 = Ym + S * cos(alfa);
  if dist(X2, Y2, X3, Y3) < dist(X2, Y2, X4, Y4):  # Cheating bigtime: there are inherently two centers that would fit two endpoints and a radius.
    return(X3, Y3);                                # Finding the proper one would entail figuring out the tangents at the endpoints of the arc
  else:                                            # which in turn would mean looking behind and ahead further for the adjoining segments.
    return(X4, Y4);                                # Instead, we simply choose the solution closer to the original center...

#----------------------------------------------------------------------------
# Filter
#----------------------------------------------------------------------------

class CorrectArc(Filter):
  """ Correct the center point of arcs
  """

  def __init__(self):
    """ Constructor
    """
    self.x = 0.0
    self.y = 0.0

  def apply(self, command):
    """ Calculate the correct center point for an arc command
    """
    # Make sure it is an arc command
    for p in ("X", "Y", "I", "J"):
      if getattr(command, p, None) is None:
        # Store the last X/Y position
        self.x = command.X or self.x
        self.y = command.Y or self.y
        return command
    # Recalculate the center point
    if dist(self.x, self.y, command.X, command.Y) > 0.0:
      command = command.clone()
      i, j = bendThatArc(self.x, self.y, command.X, command.Y, self.x + command.I, self.y + command.J)
      command.I = i - self.x
      command.J = j - self.y
    # Store the last X/Y position
    self.x = command.X or self.x
    self.y = command.Y or self.y
    # Done
    return command

