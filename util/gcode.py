#!/usr/bin/env python
#----------------------------------------------------------------------------
# 21-Jul-2015 ShaneG
#
# Reworking the gcode loader and filter process.
#----------------------------------------------------------------------------
import re

# Set up the regular expression for processing G-Code
REGCODE = re.compile("(([A-Z])((-?[0-9]+)\.?([0-9]+)?))|(\(.*\))")

# Supported parameter words
PARAMS = ("X", "Y", "Z", "I", "J", "K", "R", "F")

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
    if len(line) > 0:
      # Now we should just have command and arguments
      #
      # The regex will split it into parts like this ...
      # (u'X10.768569', u'X', u'10.768569', u'10', u'768569', u'')
      parts = list([ list(cmd) for cmd in REGCODE.findall(line) ])
      if len(parts) > 0:
        self.command = parts[0][0]
        for p in parts[1:]:
          if p[1] in PARAMS:
            setattr(self, str(p[1]), float(p[2]))

  def __str__(self):
    """ Convert the command back into a string
    """
    result = self.command
    for param in PARAMS:
      if hasattr(self, param):
        result = "%s %s%0.4f" % (result, param, getattr(self, param))
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
    """ Called with a GCommand instance, must return a new (or the same)
        instance to replace it.
    """
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
        for p in PARAMS:
          if hasattr(cmd, p):
            setattr(cmd, p, getattr(cmd, p) * 2.54)
      if cmd.command == GCode.INCH:
        cmd.command = GCode.MM
        cmd.comment = "(use mm)"
      self.lines.append(cmd)
    return cmd

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
  gcode = loadGCode("C:\\Shane\\Sandbox\\gctools\\samples\\attiny84_EDGEMILL_GCODE.ngc")
  saveGCode("C:\\Shane\\Sandbox\\gctools\\samples\\attiny84_EDGEMILL_GCODE.2.ngc", gcode)


