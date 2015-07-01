#!/bin/env python
#----------------------------------------------------------------------------
# 04-Dec-2014 ShaneG
#
# A simple set of g-code filters.
#----------------------------------------------------------------------------
import re
from subprocess import Popen, PIPE

# Set up the regular expression for processing G-Code
REGCODE = re.compile("(([A-Z])((-?[0-9]+)\.?([0-9]+)?))|(\(.*\))")

# Unit names
INCHES = "in"
MM = "mm"

#----------------------------------------------------------------------------
# Helper functions
#----------------------------------------------------------------------------

def minValue(a, b):
  """ Determine the minimum allowing the first value to be None
  """
  if a is None:
    return b
  return min(a, b)

def maxValue(a, b):
  """ Determine the minimum allowing the first value to be None
  """
  if a is None:
    return b
  return max(a, b)

def floatVal(value):
  """ Format a floating point value with sufficient detail for the router
  """
  return "%0.5f" % float(value)

#----------------------------------------------------------------------------
# Top level filter classes
#----------------------------------------------------------------------------

class Filter:
  """ Base class for all filter operations
  """

  def apply(self, source):
    """ Apply the filter to the source data

      The source is supplied as a list of lines. The data returned is also
      a list of lines.
    """
    return source

class ExternalFilter(Filter):
  """ Extends filter to invoke an external command
  """

  def __init__(self, command, args):
    """ Constructor with command and arguments
    """
    self.command = command
    self.args = args

  def apply(self, source):
    """ Apply the filter and return the results
    """
    cmdline = "%s %s" % (self.command, self.args)
    prog = Popen(cmdline, stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)
    out, err = prog.communicate("\n".join(source))
    # Turn the output into a list of lines
    lines = list()
    for line in out.split('\n'):
      lines.append(line.strip())
    # Done
    return lines

class NativeFilter(Filter):
  """ A 'native' filter (implemented in Python)
  """

  def __init__(self, transform = None):
    """ Constructor with an (optional) transformation function

      The transform must be a callable. See documentation for the 'transform()'
      method for details.
    """
    self._transform = transform

  def transform(self, line):
    """ Apply the transform and return the modified command list

      The command is supplied as a list of components like this:

      (u'X10.768569', u'X', u'10.768569', u'10', u'768569', u'')

      The filter should only modify the components 1 and 2 (command letter
      and numeric code) as these are what the filter uses to create the output.
    """
    if callable(self._transform):
      return self._transform(line)
    return line

  def apply(self, source):
    """ Apply the filter and return the results
    """
    results = list()
    for line in source:
      # Split it into components and pass to the filter
      parts = list([ list(cmd) for cmd in REGCODE.findall(line) ])
      result = self.transform(parts)
      if result is not None:
        # Reconstruct as text
        results.append(" ".join([ "%s%s%s" % (cmd[1], cmd[2], cmd[5]) for cmd in result]))
    # All done
    return results

class FilterChain(Filter):
  """ A sequence of filters that are run in order.
  """

  def __init__(self, *args):
    """ Constructor with a list of filters to run.
    """
    self._filters = list()
    for arg in args:
      if isinstance(arg, Filter):
        self._filters.append(arg)
      elif callable(arg):
        self._filters.append(NativeFilter(arg))
      else:
        raise Exception("One or more arguments cannot be used as a filter.")

  def apply(self, source):
    """ Apply the filters to the source data

      This applies each filter in turn in the order they were given in the
      constructor.
    """
    for child in self._filters:
      source = child.apply(source)
    return source

#----------------------------------------------------------------------------
# Useful filters
#----------------------------------------------------------------------------

class Optimise(ExternalFilter):
  """ Optimise the non-cutting moves

    Uses the 'opti' tool to do this which it expects to find on the path
  """

  def __init__(self):
    """ Constructor
    """
    ExternalFilter.__init__(self, "opti", "")

class Overlay(ExternalFilter):
  """ Overlay (translate and rotate).

    Uses the 'grecode' external tool which it expects to find on the path.
  """

  def __init__(self, source, target):
    """ Define the source and target points

      The source and target parameters are 4-tuples of floating point values
      (x1, y1, x2, y2). The filter will adjust the code such that source.x1
      is mapped to target.x1, source.y1 to target.y1, etc.
    """
    ExternalFilter.__init__(self, "grecode", "-overlay %s %s" % ("%0.2f %0.2f %0.2f %0.2f" % source, "%0.2f %0.2f %0.2f %0.2f" % target))
    # Save the values in case they are needed later
    self.source = source
    self.target = target

class Bounds(NativeFilter):
  """ Determine the bounds of the object
  """

  def __init__(self):
    NativeFilter.__init__(self)
    self.minx = None
    self.miny = None
    self.minz = None
    self.maxx = None
    self.maxy = None
    self.maxz = None
    self.units = None

  def transform(self, line):
    """ Apply the transform and return the modified command list

      The command is supplied as a list of components like this:

      (u'X10.768569', u'X', u'10.768569', u'10', u'768569', u'')

      The filter should only modify the components 1 and 2 (command letter
      and numeric code) as these are what the filter uses to create the output.
    """
    for code in line:
      if code[1] == 'X':
        self.minx = minValue(self.minx, float(code[2]))
        self.maxx = maxValue(self.maxx, float(code[2]))
      elif code[1] == 'Y':
        self.miny = minValue(self.miny, float(code[2]))
        self.maxy = maxValue(self.maxy, float(code[2]))
      elif code[1] == 'Z':
        self.minz = minValue(self.minz, float(code[2]))
        self.maxz = maxValue(self.maxz, float(code[2]))
      elif code[0] == 'G20':
        self.units = INCHES
      elif code[0] == 'G21':
        self.units = MM
    # No actual transform done
    return line

class XFlip(FilterChain):
  """ Flip the X axis around the horizontal center of the object

    This is a two pass filter - first it determines the bounds of the object
    being engraved/cut and then it modifies the X co-ordinates to flip that
    object around the horizontal center of the object. This leaves the objects
    bounds the same but looks at it from the opposite Z direction.
  """

  def __init__(self):
    """ Constructor

      Sets up the two filters to apply
    """
    self.bounds = Bounds()
    FilterChain.__init__(self, self.bounds, NativeFilter(self.transform))

  def transform(self, line):
    """ Flip the X value around the object midpoint
    """
    midpoint = self.bounds.minx + ((self.bounds.maxx - self.bounds.minx) / 2)
    for code in line:
      if code[1] == 'X':
        code[2] = floatVal((2 * midpoint) - float(code[2]))
    return line

class YFlip(FilterChain):
  """ Flip the Y axis around the vertical center of the object

    This is a two pass filter - first it determines the bounds of the object
    being engraved/cut and then it modifies the Y co-ordinates to flip that
    object around the horizontal center of the object. This leaves the objects
    bounds the same but looks at it from the opposite Z direction.
  """

  def __init__(self):
    """ Constructor

      Sets up the two filters to apply
    """
    self.bounds = Bounds()
    FilterChain.__init__(self, self.bounds, NativeFilter(self.transform))

  def transform(self, line):
    """ Flip the Y value around the object midpoint
    """
    midpoint = self.bounds.miny + ((self.bounds.maxy - self.bounds.miny) / 2)
    for code in line:
      if code[1] == 'Y':
        code[2] = floatVal((2 * midpoint) - float(code[2]))
    return line

class ZLevel(NativeFilter):
  """ Change the cutting level and/or safe level for Z

    Use with caution. This filter assume any Z value less than zero is cutting
    and all others are safe.
  """

  def __init__(self, cutting = None, safe = None):
    """ Save the (optional) parameters
    """
    NativeFilter.__init__(self)
    self.cutting = cutting
    self.safe = safe

  def transform(self, line):
    """ Apply the transform and return the modified command list

      The command is supplied as a list of components like this:

      (u'X10.768569', u'X', u'10.768569', u'10', u'768569', u'')

      The filter should only modify the components 1 and 2 (command letter
      and numeric code) as these are what the filter uses to create the output.
    """
    for code in line:
      if code[1] == 'Z':
        val = float(code[2])
        if (val < 0.0) and (self.cutting is not None):
          code[2] = floatVal(self.cutting)
        if (val > 0.0) and (self.safe is not None):
          code[2] = floatVal(self.safe)
    # Done
    return line

class Translate(NativeFilter):
  """ Translate the cutting moves in X, Y and Z
  """

  def __init__(self, dx = None, dy = None, dz = None):
    NativeFilter.__init__(self)
    self.dx = dx
    self.dy = dy
    self.dz = dz

  def transform(self, line):
    """ Do the transformation on the co-ordinates
    """
    for code in line:
      if (code[1] == 'X') and (self.dx is not None):
        code[2] = floatVal(float(code[2]) + self.dx)
      if (code[1] == 'Y') and (self.dy is not None):
        code[2] = floatVal(float(code[2]) + self.dy)
      if (code[1] == 'Z') and (self.dz is not None):
        code[2] = floatVal(float(code[2]) + self.dz)
    # Done
    return line

class Strip(NativeFilter):
  """ Strip header/footer commands
  """

  def __init__(self):
    NativeFilter.__init__(self)

  def transform(self, line):
    """ Do the transformation on the co-ordinates
    """
    if len(line) == 0:
      return None
    # Spindle control and program stop
    if (line[0][1] == 'M') and (float(line[0][2]) in (2.0, 3.0, 5.0)):
      return None
    if (line[0][1] == 'G') and (float(line[0][2]) == '0'):
      # Rapid movement, see if it is to home
      ignore = True
      for code in line[1:]:
        if (code[1] == 'X') and (float(code[2]) <> 0.0):
          ignore = False
        if (code[1] == 'Y') and (float(code[2]) <> 0.0):
          ignore = False
        if (code[1] == 'Z') and (float(code[2]) <> 0.0):
          ignore = False
      if ignore:
        return None
    # Done
    return line

#----------------------------------------------------------------------------
# Top level helpers
#----------------------------------------------------------------------------

def loadGCode(filename, strip = False):
  """ Load g-code from a file as a list of lines
  """
  result = None
  with open(filename, "r") as input:
    result = list([ line.strip() for line in input.readlines() ])
  if strip:
    # Remove common header/footer commands
    result = Strip().apply(result)
  return result

def saveGCode(filename, lines, prefix = None, suffix = None):
  """ Save a list of lines to a file
  """
  with open(filename, "w") as output:
    if prefix is not None:
      output.write(prefix.strip() + "\n")
    output.writelines([ line + "\n" for line in lines])
    if suffix is not None:
      output.write(suffix.strip() + "\n")

def combine(*args, **kwargs):
  """ Combine multiple g-code sequences

    This takes multiple g-code sequences (lists of lines) and merges them
    together into a single sequence. During the process it removes common
    header and footer operations (like M03, M05, M02 and G00 for x = 0, y = 0).

    When the files are combined it then adds a custom header and footer. The
    following values can be overwritten with named arguments:

      header - the header (as a list of lines) to use instead of the default
      footer - the footer (as a list of lines) to use instead of the default
  """
  pass
#  results = list()
#  if kwargs.haskey('header'):
#    results.extend(kwargs['header'])
#  else:
#    results.extend(DEFAULT_HEADER)
#  # Our filter function to strip unwanted codes
#  def transform(line):
#    # Check for 'go home' commands
#    # Check for spindle and stop program commands
#    for code in line:
#      if code[0] in ("M02", "M03", "M05"):
#        code[1] = ""
#        code[2] = ""
#  footer =

