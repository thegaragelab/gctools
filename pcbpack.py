#!/usr/bin/env python
#----------------------------------------------------------------------------
# 21-Jul-2015 ShaneG
#
# Major refactoring and updates to make it part of the 'gctools' suite.
#
# 13-Nov-2014 ShaneG
#
# Some slight changes to the code for consistancy with the output generated
# by 'linegrinder'. The origin is now in the lower left corner, x increments
# upwards, y increments to the right. The boards are now treated with the
# same origin location (this is what linegrinder generates).
#
# Rotations are in the counter clockwise direction with the working origin
# at the bottom left corner which moves the source origin to the bottom
# right.
#
# 11-Nov-2014 ShaneG
#
# Tool to pack multiple PCB g-code files into a single panel.
#----------------------------------------------------------------------------
from util import LOG, Logger, fromJSONFile
from random import randint
from os.path import realpath, splitext, exists
from optparse import OptionParser
from PIL import Image, ImageDraw

#--- Globals
CONFIG = None

#----------------------------------------------------------------------------
# Helper functions
#----------------------------------------------------------------------------

def area(*args):
  """ Calculate the combined area of a number of elements

    Each element is expected to have a 'w' and 'h' attribute.
  """
  return sum([ float(a.w) * float(a.h) for a in args ])

def rotations(boards):
  """ Generator to walk through all rotation combinations
  """
  for iteration in range(2 ** len(boards)):
    candidate = list()
    flag = 1
    for index in range(len(boards)):
      board = boards[index].clone()
      if iteration & flag:
        board.rotated = True
      candidate.append(board)
    yield sorted(candidate, cmp = lambda x, y: cmp(x.h, y.h), reverse = True)

#----------------------------------------------------------------------------
# Manage board positioning
#
# The width and height of the board must include any spacing required and
# will be taken into account when modifying the gcode.
#----------------------------------------------------------------------------

class BoardPosition:
  """ Represents a board.

    Each board has a fixed size (width and height), a mutable location and
    a rotation flag.
  """

  def __init__(self, name, w, h):
    """ Constructor with dimensions
    """
    self.name = name
    self._width = w
    self._height = h
    self.reset()

  def __str__(self):
    return "Board %0.2f x %0.2f @ %0.2f, %0.2f (Rot = %s)" % (self.w, self.h, self.x, self.y, self.rotated)

  @property
  def w(self):
    if self.rotated:
      return self._height
    return self._width

  @w.setter
  def w(self, value):
    raise Exception("Cannot modify width after creation")

  @property
  def h(self):
    if self.rotated:
      return self._width
    return self._height

  @h.setter
  def h(self, value):
    raise Exception("Cannot modify height after creation")

  def reset(self):
    """ Restore to original (unrotated, untranslated) state
    """
    self.x = 0.0
    self.y = 0.0
    self.rotated = False

  def overlaps(self, other):
    """ Determine if this board overlaps another
    """
    return not (((self.x + self.w <= other.x) or
      ((other.x + other.w) <= self.x) or
      ((self.y + self.h) <= other.y) or
      ((other.y + other.h) <= self.y)))

  def contains(self, other):
    """ Determine if this board completely contains another
    """
    return ((self.x <= other.x) and
      ((self.x + self.w) >= (other.x + other.w)) and
      (self.y <= other.y) and
      ((self.y + self.h) >= (other.y + other.h)))

  def intersects(self, other):
    """ Determine if this board intesects another
    """
    return self.overlaps(other) or self.contains(other) or other.contains(self)

  def area(self):
    """ Return the area of the board
    """
    return self.width * self.height

  def clone(self):
    copy = BoardPosition(self.name, self.w, self.h)
    copy.x = self.x
    copy.y = self.y
    return copy

#----------------------------------------------------------------------------
# Manage panel layout
#
# A panel has a fixed size and (optionally) a set of fixed zones that cannot
# be used (mounting screws for example).
#----------------------------------------------------------------------------

class Panel:
  """ Represents a single panel
  """

  def __init__(self, name):
    """ Create the panel from the named configuration
    """
    global CONFIG
    # Set up state
    self.w = CONFIG['panels'][name]['width']
    self.h = CONFIG['panels'][name]['height']
    self.padding = CONFIG['panels'][name].get('padding', 2)
    self.description = CONFIG['panels'][name].get('description', "(undefined)")
    self.locked = list()
    if CONFIG['panels'][name].has_key("locked"):
      for lockInfo in CONFIG['panels'][name]['locked']:
        lock = BoardPosition("_lock_", lockInfo['w'], lockInfo['h'])
        lock.x = lockInfo['x']
        lock.y = lockInfo['y']
        self.locked.append(lock)

  def area(self):
    return area(self) - area(*self.locked)

  def consumed(self, boards):
    """ Determine the consumed area
    """
    w, h = 0, 0
    for b in boards:
      if b.name != "_lock_":
        w = max(w, b.x + b.w)
        h = max(h, b.y + b.h)
    return w * h

  def willFit(self, board):
    """ Determine if the board will fit
    """
    if (board.w > (self.w - (2 * self.padding))) and (board.w > (self.h - (2 * self.padding))):
      return False
    if (board.h > (self.w - (2 * self.padding))) and (board.h > (self.h - (2 * self.padding))):
      return False
    return True

  def findPosition(self, layout, board):
    LOG.DEBUG("Positioning %s" % board)
    for x in range(0, int(self.w - board.w - 1)):
      for y in range(0, int(self.h - board.h - 1)):
        LOG.DEBUG("  Testing %d, %d" % (x, y))
        board.x = x
        board.y = y
        # Does it overlap ?
        safe = True
        for existing in layout:
          LOG.DEBUG("Checking against %s" % existing)
          if board.intersects(existing):
            safe = False
        if safe:
          LOG.DEBUG("  Position is safe")
          return True
    return False

  def layout(self, *boards):
    """ Layout the set of boards on the panel
    """
    best = None
    for candidate in rotations(boards):
      # This is an ugly brute force approach
      current = list(self.locked)
      placed = True
      for board in candidate:
        if self.findPosition(current, board):
          LOG.DEBUG("Placed %s" % board)
          current.append(board)
        else:
          placed = False
          break
      # Did we place all the boards ?
      if placed:
        # Update the 'best' solution
        if (best is None) or (self.consumed(current) < self.consumed(best)):
          best = current
    self.layout = best
    return self.layout is not None

  #--------------------------------------------------------------------------
  # Utility methods
  #--------------------------------------------------------------------------

  def createImage(self, filename):
    """ Generate an image for the current layout.
    """
    img = Image.new("RGB", (int(self.w * 4), int(self.h * 4)), "white")
    drw = ImageDraw.Draw(img)
    for board in self.layout:
      color = "green"
      if board.name == "_lock_":
        color = "red"
      rect = (int(board.x * 4), int(board.y * 4), int((board.x + board.w) * 4), int((board.y + board.h) * 4))
      drw.rectangle(rect, fill = "black")
      rect = (rect[0] + 1, rect[1] + 1, rect[2] - 1, rect[3] - 1)
      drw.rectangle(rect, fill = color)
    img.save(filename)

  def __str__(self):
    return "%s - %0.1f x %0.1f mm" % (self.description, self.w, self.h)

#----------------------------------------------------------------------------
# Helpers
#----------------------------------------------------------------------------

BOARD_CACHE = dict()

def loadBoard(name):
  """ Load the named board from the repository
  """
  # TODO: Implement this. For now we generate a random board if we haven't
  #       seen the name before
  global BOARD_CACHE
  board = BOARD_CACHE.get(name, None)
  if board is None:
    # Create a new one and cache it
    board = BoardPosition(
      name,
      15 + randint(0, 45),
      15 + randint(0, 45)
      )
    LOG.DEBUG(str(board))
    BOARD_CACHE[name] = board
  # Done
  return board

#----------------------------------------------------------------------------
# Main program
#----------------------------------------------------------------------------

if __name__ == "__main__":
  # Load the configuration
  cfg = splitext(realpath(__file__))[0] + ".json"
  if not exists(cfg):
    LOG.FATAL("Could not find configuration file '%s'" % cfg)
  try:
    CONFIG = fromJSONFile(cfg)
  except Exception, ex:
    LOG.FATAL("Could not load configuration file '%s' - %s" % (cfg, ex))
  # Process command line arguments
  parser = OptionParser()
  parser.add_option("-d", "--debug", action="store_true", default=False, dest="debug")
  parser.add_option("-n", "--no-optimise", action="store_false", default=True, dest="optimise")
  parser.add_option("-o", "--output", action="store", type="string", dest="output")
  parser.add_option("-p", "--panel", action="store", type="string", dest="panel")
  options, args = parser.parse_args()
  # Check for required options
  for required in ("output", "panel"):
    if getattr(options, required) is None:
      LOG.FATAL("Missing required option '%s'" % required)
  if options.debug:
    LOG.severity = Logger.MSG_DEBUG
  else:
    LOG.severity = Logger.MSG_INFO
  # Set up the panel
  try:
    panel = Panel(options.panel)
  except Exception, ex:
    LOG.FATAL("Could not load panel defintion '%s'" % options.panel)
  LOG.DEBUG("Panel - %s" % panel)
  # Load boards
  boards = list()
  for name in args:
    board = loadBoard(name)
    if board is None:
      LOG.FATAL("Could not find board '%s' in repository" % name)
    if not panel.willFit(board):
      LOG.FATAL("Board %s will not fit on this panel" % name)
    boards.append(board)
  if len(boards) == 0:
    LOG.FATAL("No boards specified on command line")
  # Make sure they can reasonably fit
  if area(*boards) > panel.area():
    LOG.FATAL("This board combination cannot fit on the selected panel - board area = %0.2f, panel area = %0.2f" % (area(*boards), panel.area()))
  # Do the layout
  if not panel.layout(*boards):
    LOG.FATAL("Unable to find a combination that will fit")
  # Show the current layout
  panel.createImage("%s.png" % options.output)
  LOG.INFO("Selected layout ...")
  for board in panel.layout:
    if board.name <> "_lock_":
      LOG.INFO("  %s" % board)

