#!/usr/bin/env python
#----------------------------------------------------------------------------
# 21-Jul-2015 ShaneG
#
# Reworking the gcode loader and filter process.
#----------------------------------------------------------------------------
import re
from PIL import Image, ImageDraw
from math import degrees, atan2, sqrt

# Set up the regular expression for processing G-Code
REGCODE = re.compile("(([A-Z])((-?[0-9]+)\.?([0-9]+)?))|(\(.*\))")

# Supported parameter words
PARAMS = ("X", "Y", "Z", "I", "J", "K", "R", "F", "P")

#----------------------------------------------------------------------------
# Public classes
#----------------------------------------------------------------------------

class GCommand:
  """ Represents a single command (or parameter)
  """

  def __init__(self, line = ""):
    """ Construct from a line
    """
    line = line.strip()
    # Extract any comments
    self.comment = ""
    i = line.find("(")
    if i >= 0:
      self.comment = line[i:]
      line = line[:i - 1]
    line = line.strip()
    self.command = ""
    for p in PARAMS:
      setattr(self, p, None)
    if len(line) > 0:
      # Now we should just have command and arguments
      #
      # The regex will split it into parts like this ...
      # (u'X10.768569', u'X', u'10.768569', u'10', u'768569', u'')
      parts = list([ list(cmd) for cmd in REGCODE.findall(line) ])
      if len(parts) > 0:
        # Make sure the command looks like Gnn or Gnn.n
        if float(parts[0][2]) == float(parts[0][3]):
          self.command = "%s%02d" % (parts[0][1], int(parts[0][3]))
        else:
          self.command = "%s%02.1f" % (parts[0][1], float(parts[0][2]))
        # Process the rest
        for p in parts[1:]:
          if p[1] in PARAMS:
            setattr(self, str(p[1]), float(p[2]))

  def clone(self):
    """ Create a copy of this instance
    """
    result = GCommand()
    result.command = self.command
    result.comment = self.comment
    for p in PARAMS:
      setattr(result, p, getattr(self, p))
    return result

  def matches(self, other):
    """ Determine if this command matches the other
    """
    if self.command <> other.command:
      return False
    for p in PARAMS:
      if getattr(self, p) <> getattr(other, p):
        return False
    return True

  def __str__(self):
    """ Convert the command back into a string
    """
    result = self.command
    for param in PARAMS:
      p = getattr(self, param)
      if p is not None:
        result = "%s %s%0.4f" % (result, param, p)
    result = "%s %s" % (result, self.comment)
    return result.strip()

class Loader:
  """ A loader is used to filter raw gcode while loading
  """

  def parse(self, line):
    """ Parse the line and return a GCommand instance for it

      This method can return None to indicate that the line should be ignored.
    """
    return GCommand(line)

class Filter:
  """ A filter is used to make modifications to the gcode
  """

  def apply(self, command):
    """ Called with a GCommand instance the filter can return None to remove
        the command, a replacement command or a list of replacements.
    """
    return command

class FilterChain(Filter):
  """ A wrapper for a group of filters
  """

  def __init__(self, *filters):
    """ Store the filters
    """
    self.filters = filters

  def apply(self, command):
    """ Called with a GCommand instance the filter can return None to remove
        the command, a replacement command or a list of replacements.
    """
    for f in self.filters:
      if command is None:
        return None
      if isinstance(command, GCommand):
        command = f.apply(command)
      else:
        results = list()
        for cmd in command:
          response = f.apply(cmd)
          if response is not None:
            if isinstance(response, GCommand):
              results.append(response)
            else:
              results.extend(response)
        if len(results) == 0:
          command = None
        else:
          command = results
    return command

class GCode(Loader):
  """ Represents a gcode file
  """

  # Units
  INCH = "G20"
  MM   = "G21"

  def __init__(self, loader = None):
    self.loader = loader
    self.units = None
    self.lines = list()
    self.minx, self.maxx = None, None
    self.miny, self.maxy = None, None
    self.minz, self.maxz = None, None

  def _minVal(self, a, b):
    """ Get the minimum of two values allowing for None
    """
    if (a is None) and (b is None):
      return None
    if (a is None) and (b is not None):
      return b
    if (b is None) and (a is not None):
      return a
    return min(a, b)

  def _maxVal(self, a, b):
    """ Get the maximum of two values allowing for None
    """
    if (a is None) and (b is None):
      return None
    if (a is None) and (b is not None):
      return b
    if (b is None) and (a is not None):
      return a
    return max(a, b)

  def append(self, cmd):
    """ Append a command the file

      The cmd parameter may be a GCommand instance or a string representing
      a command. If it is a string it will be converted to a GCommand
    """
    if cmd is None:
      return
    if isinstance(cmd, GCode):
      for c in cmd.lines:
        self.append(c)
    else:
      if not isinstance(cmd, GCommand):
        cmd = GCommand(str(cmd))
      self.lines.append(cmd)
      # Update bounds
      self.minx = self._minVal(self.minx, cmd.X)
      self.maxx = self._maxVal(self.maxx, cmd.X)
      self.miny = self._minVal(self.miny, cmd.Y)
      self.maxy = self._maxVal(self.maxy, cmd.Y)
      self.minz = self._minVal(self.minz, cmd.Z)
      self.maxz = self._maxVal(self.maxz, cmd.Z)

  def parse(self, line):
    """ Parse the line and return a GCommand instance for it

      This method can return None to indicate that the line should be ignored.
    """
    # We always parse ourselves, we want to check for units
    cmd = GCommand(line)
    if cmd.command in (GCode.INCH, GCode.MM):
      self.units = cmd.command
    # If we have a different loader parse it again with that
    if self.loader is not None:
      cmd = self.loader.parse(line)
    if cmd is not None:
      # Convert to MM
      if self.units == GCode.INCH:
        for param in PARAMS:
          p = getattr(cmd, param)
          if p is not None:
            setattr(cmd, param, p * 25.4)
      if cmd.command == GCode.INCH:
        cmd.command = GCode.MM
        cmd.comment = "(use mm)"
      self.append(cmd)
    return cmd

  def clone(self, *filters):
    """ Make a copy of this gcode object with optional filtering

      If filters are provided they are executed in order.
    """
    chain = FilterChain(*filters)
    result = GCode()
    result.units = self.units
    for cmd in self.lines:
      cmd = cmd.clone()
      # Apply filters
      cmd = chain.apply(cmd)
      if cmd is not None:
        if isinstance(cmd, GCommand):
          result.append(cmd)
        else:
          for c in cmd:
            result.append(c)
    # All done
    return result

  def render(self, filename, cutdepth = 0.0, showall = False):
    """ Render the gcode to an image file for visualisation
    """
    pixelsPerMM = 10.0
    # Calculate size
    width = int(pixelsPerMM * (10.0 + self.maxx - min(self.minx, 0.0)))
    height = int(pixelsPerMM * (10.0 + self.maxy - min(self.miny, 0.0)))
    # Calculate translation (in pixels)
    dx = int(pixelsPerMM * (5.0 + abs(min(self.minx, 0.0))))
    dy = int(pixelsPerMM * (5.0 + abs(min(self.miny, 0.0))))
    # Create the image
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    drw = ImageDraw.Draw(img)
    # Draw the axis
    drw.line((0, dy, width, dy), fill = "black", width = 1)
    drw.line((dx, 0, dx, height), fill = "black", width = 1)
    # Draw the actual image
    x, y, z = 0.0, 0.0, 0.0
    for cmd in self.lines:
      if cmd.command in ("G00", "G01", "G02", "G03"):
        # Check for X/Y movement
        nx = cmd.X or x
        ny = cmd.Y or y
        if (x <> nx) or (y <> ny):
          path = (
            dx + (pixelsPerMM * x),
            dy + (pixelsPerMM * y),
            dx + (pixelsPerMM * nx),
            dy + (pixelsPerMM * ny)
            )
          if cmd.command in ("G00", "G01"):
            if z < 0.0:
              # Cutting movement
              drw.line(path, fill = "blue", width = 1)
            elif showall:
              # Positioning
              drw.line(path, fill = "red", width = 1)
          elif z < 0.0:
            # Draw an arc
            cx, cy = x + cmd.I, y + cmd.J
            r = sqrt(cmd.I ** 2 + cmd.J ** 2)
            a1 = int(degrees(atan2(x - cx, y - cy)) + 360.0) % 360
            a2 = int(degrees(atan2(nx - cx, ny - cy)) + 360.0) % 360
            path = (
              dx + (pixelsPerMM * (cx - r)),
              dy + (pixelsPerMM * (cy - r)),
              dx + (pixelsPerMM * (cx + r)),
              dy + (pixelsPerMM * (cy + r))
              )
            print "ARC: S %0.4f, %0.4f E %0.4f, %0.4f C %0.4f, %0.4f, a1 = %d, a2 = %d" % (x, y, nx, ny, cx, cy, a1, a2)
            if cmd.command == "G03":
              # Clockwise
              drw.arc(path, a2, a1)
            else:
              # Anticlockwise
              drw.arc(path, a2, a1)
        # Check for touchdowns (or drill commands)
        nz = cmd.Z or z
        if (nz < 0.0) and (z > 0):
          points = (
            dx + (pixelsPerMM * nx) - 1,
            dy + (pixelsPerMM * ny) - 1,
            dx + (pixelsPerMM * nx) + 1,
            dy + (pixelsPerMM * ny) + 1
            )
          drw.ellipse(points, fill = "blue")
        # Save new position
        x, y, z = nx, ny, nz
    # Save the image
    img = img.transpose(Image.FLIP_TOP_BOTTOM)
    img.save(filename)

  def __str__(self):
    def floatStr(val):
      if val is not None:
        return "%0.4f" % val
      return "?"
    # Represent as a string
    bounds = ( self.minx, self.maxx, self.miny, self.maxy, self.minz, self.maxz )
    bounds = tuple([ floatStr(x) for x in bounds ])
    return "X: %s, %s Y: %s, %s Z: %s, %s" % bounds

#----------------------------------------------------------------------------
# File operations
#----------------------------------------------------------------------------

def loadGCode(filename, *loaders):
  """ Load a gcode file (with optional filters)
  """
  results = list()
  for loader in loaders:
    results.append(GCode(loader))
  if len(results) == 0:
    results.append(GCode())
  # Now read the file
  with open(filename, "r") as source:
    for line in source.readlines():
      for loader in results:
        loader.parse(str(line))
  # Set all units to MM for each object
  for r in results:
    r.units = GCode.MM
  # Return the results
  if len(results) == 1:
    return results[0]
  return results

def saveGCode(filename, gcode, prefix = None, suffix = None):
  """ Save a gcode file
  """
  with open(filename, "w") as target:
    if prefix is not None:
      target.write(str(prefix).strip() + "\n")
    for line in gcode.lines:
      target.write(str(line) + "\n")
    if suffix is not None:
      target.write(str(suffix).strip() + "\n")

#----------------------------------------------------------------------------
# Testing
#----------------------------------------------------------------------------

if __name__ == "__main__":
  gc1 = loadGCode("C:\\Shane\\Sandbox\\gctools\\samples\\attiny84_EDGEMILL_GCODE.ngc")
  gc2 = gc1.clone()
  gc3 = loadGCode("C:\\Shane\\Sandbox\\gctools\\samples\\attiny84_ISOLATION_GCODE.ngc")
  print gc1
  print gc2
  print gc3
  saveGCode("C:\\Shane\\Sandbox\\gctools\\samples\\attiny84_EDGEMILL_GCODE.1.ngc", gc1)
  gc1.render("C:\\Shane\\Sandbox\\gctools\\samples\\attiny84_EDGEMILL_GCODE.1.png")
  saveGCode("C:\\Shane\\Sandbox\\gctools\\samples\\attiny84_EDGEMILL_GCODE.2.ngc", gc2)
  gc2.render("C:\\Shane\\Sandbox\\gctools\\samples\\attiny84_EDGEMILL_GCODE.2.png", showall = True)
  saveGCode("C:\\Shane\\Sandbox\\gctools\\samples\\attiny84_ISOLATION_GCODE.1.ngc", gc2)
  gc3.render("C:\\Shane\\Sandbox\\gctools\\samples\\attiny84_ISOLATION_GCODE.1.png")


