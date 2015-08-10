#!/usr/bin/env python
#----------------------------------------------------------------------------
# 10-Aug-2015 ShaneG
#
# Tool path optimisation. This creates new gcode that performs the same
# cutting operations while minimising the amount of non-cutting movement.
#----------------------------------------------------------------------------
from gcode import GCode, GCommand

def optimise(source):
  """ Return an optimised copy of the given gcode
  """
  # Build up a sequence of cutting operations
  x, y, z = 0.0, 0.0, 0.0
  cut, safe = source.minz, source.maxz
  prefix = list()
  movements = list()
  airtime = 0.0
  cutting = False
  for cmd in source.lines:
    if cmd.command in ("G01", "G02", "G03"):
      cutting = True
    if not cutting:
      prefix.append(cmd)
  return source.clone()

