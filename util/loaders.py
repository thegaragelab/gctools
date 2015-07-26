#!/usr/bin/env python
#----------------------------------------------------------------------------
# 26-Jul-2015 ShaneG
#
# A simple set of loaders.
#----------------------------------------------------------------------------
from gcode import Loader, GCommand

class BoxedLoader(Loader):
  """ This loader allows filtering between recognised lines
  """

  def __init__(self, start = None, end = None, inclusive = False):
    self.start = start
    self.end = end
    self.inclusive = inclusive
    self.accepting = start is None

  def _compareLine(self, line, command, match):
    """ Compare the given line with the requested match
    """
    if isinstance(match, GCommand):
      return match.matches(command)
    return str(line) == str(match)

  def parse(self, line):
    """ Parse the line and return a GCommand instance for it

      This method can return None to indicate that the line should be ignored.
    """
    command = GCommand(line)
    if self.accepting:
      # Should we stop accepting ?
      if (self.end is not None) and (self._compareLine(line, command, self.end)):
        self.accepting = False
        if not self.inclusive:
          command = None
    else:
      # Should we start accepting ?
      if (self.start is not None) and (self._compareLine(line, command, self.start)):
        self.accepting = True
        if not self.inclusive:
          command = None
      else:
        command = None
    return command

