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
from util import LOG, fromJSONFile
from random import randint
from os.path import realpath, splitext, exists
from optparse import OptionParser

#--- Globals
CONFIG = None

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

  def translate(self, dx, dy):
    self.x = self.x + dx
    self.y = self.y + dy

  def overlaps(self, other):
    """ Determine if this board overlaps another
    """
    return not (((self.x + self.width) <= other.x) or
      ((other.x + other.width) <= self.x) or
      ((self.y + self.height) <= other.y) or
      ((other.y + other.height) <= self.y))

  def contains(self, other):
    """ Determine if this board completely contains another
    """
    return ((self.x <= other.x) and
      ((self.x + self.width) >= (other.x + other.width)) and
      (self.y <= other.y) and
      ((self.y + self.height) >= (other.y + other.height)))

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

  def willFit(self, board):
    """ Determine if the board will fit
    """
    if (board.w > (self.w - (2 * self.padding))) and (board.w > (self.h - (2 * self.padding))):
      return False
    if (board.h > (self.w - (2 * self.padding))) and (board.h > (self.h - (2 * self.padding))):
      return False
    return True

  #--------------------------------------------------------------------------
  # Utility methods
  #--------------------------------------------------------------------------

  def createImage(self, filename):
    """ Generate an image for the current layout.
    """
    pass
    """ TODO: Reimplement this

    img = Image.new("RGB", (int(panel.width * 2), int(panel.height * 2)), "white")
    drw = ImageDraw.Draw(img)
    for board in boards:
      drw.rectangle((int(board.x * 2), int(board.y * 2), int((board.x + board.width) * 2), int((board.y + board.height) * 2)), fill = "black")
    img.save(filename)
    """

  def __str__(self):
    return "%s - %0.1f x %0.1f mm" % (self.description, self.w, self.h)

#----------------------------------------------------------------------------
# Layout operations
#----------------------------------------------------------------------------

def getIteration(current, boards):
  """ Generate an iteration.

    We want to test every combination of rotation, this generates an iteration
    using a bit mask.
  """
  results = list()
  for bit in range(len(boards)):
    board = boards[bit].clone()
    if (1 << bit) & current:
      board.rotated = True
    results.append(board)
  return results

def overlaps(placed, board):
  """ Determine if the board overlaps any previously placed board
  """
  for previous in placed:
    if board.overlaps(previous):
      return True
  return False

def layout(panel, boards):
  """ Layout the boards on the given panel
  """
  boards = sorted(boards, cmp = lambda x, y: cmp(x.height, y.height), reverse = True)
  placed = list()
  botright = None
  for board in boards:
    # Make sure the height is valid
    if board.height > panel.height:
      return False
    # First board always goes at bottom left
    if len(placed) == 0:
      placed.append(board)
      botright = board
      continue
    # Will this board fit above any previously placed board ?
    for previous in placed:
      board.x = previous.x
      board.y = previous.y + previous.height
      if panel.contains(board) and not overlaps(placed, board):
        placed.append(board)
        board = None
        break
    # Did we manage to put it somewhere?
    if board is None:
      continue
    # Place it next to the rightmost board
    board.x = botright.x + botright.width
    board.y = 0
    # A higher (in y) board may overlap, adjust for that
    while overlaps(placed, board):
      board.translate(1.0, 0)
    # Make sure it fits
    if not panel.contains(board):
      return False
    placed.append(board)
  # If we make it here we are done for this layout
  return True

def consumedArea(boards):
  """ Determine the area taken by the boards in the current position
  """
  return max([ b.x + b.width for b in boards]) * max([ b.y + b.height for b in boards])

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
      15 + randint(0, 200),
      15 + randint(0, 200)
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
  parser.add_option("-n", "--no-optimise", action="store_false", default=True, dest="optimise")
  parser.add_option("-o", "--output", action="store", type="string", dest="output")
  parser.add_option("-p", "--panel", action="store", type="string", dest="panel")
  options, args = parser.parse_args()
  # Check for required options
  for required in ("output", "panel"):
    if getattr(options, required) is None:
      LOG.FATAL("Missing required option '%s'" % required)
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
"""
  # Process command line
  boards = list()
  index = 1
  while index < len(argv):
    if argv[index] == "--width":
      index = index + 1
      PANEL_WIDTH = float(argv[index])
    elif argv[index] == "--height":
      index = index + 1
      PANEL_HEIGHT = float(argv[index])
    elif argv[index] == "--space":
      index = index + 1
      PANEL_SPACING = float(argv[index])
    elif argv[index] == "--noopt":
      OPTIMISE = False
    else:
      boards.append(loadBoard(argv[index]))
    index = index + 1
  # Make sure we have some boards to work with
  if len(boards) == 0:
    print "ERROR: No boards specified."
    exit(1)
  # Create the panel we want to put the boards in
  panel = Board(PANEL_WIDTH - PANEL_SPACING, PANEL_HEIGHT - PANEL_SPACING)
  # Make sure the boards will fit the panel
  print "Checking dimensions ..."
  failed = False
  if sum([board.area() for board in boards]) > panel.area():
    print "  ERROR: This combination of boards will not fit the given panel"
    failed = True
  for board in boards:
    if ((board.width > panel.width) and (board.width > panel.height)) or ((board.height > panel.height) and (board.height > panel.width)):
      print "  ERROR: Board '%s' is too large for the given panel." % board.name
      print "         Board size is %0.2f x %0.2f, panel is %0.2f x %0.2f." % (board.width, board.height, panel.width, panel.height)
      failed = True
  if failed:
    print "  ERROR: Cannot continue with the current settings."
    exit(1)
  print "  OK"
  # Process each iteration in turn
  print "Laying out boards ..."
  best = None
  for iteration in range(2 ** len(boards)):
    candidate = getIteration(iteration, boards)
    if layout(panel, candidate):
      area = consumedArea(candidate)
      if (best is None) or (area < consumedArea(best)):
        best = candidate
        print "  Selecting iteration #%d with area %0.2f mm2" % (iteration, area)
  # Did we get a usable layout?
  if best is None:
    print "  ERROR: No suitable layout found."
    exit(1)
  # Adjust for spacing
  boards = list()
  for board in best:
    adjust = board.clone(-PANEL_SPACING, -PANEL_SPACING)
    adjust.rotated = board.rotated
    adjust.translate(board.x + PANEL_SPACING, board.y + PANEL_SPACING)
    boards.append(adjust)
  # Show the results
  print "Selected layout:"
  for board in boards:
    print "  '%s' (%0.2f x %0.2f) @ %0.2f, %0.2f - rotated = %s" % (board.name, board.width, board.height, board.x, board.y, board.rotated)
  createLayoutImage(panel, boards, "pcbpack.png")
  print "Layout image saved in 'pcbpack.png'"
  print "Generating combined g-code ..."
  for filetype in range(3):
    lines = list()
    for board in boards:
      lines.extend(board.getAdjustedCode(filetype))
    # Add a program stop
    lines.append("M02 (Program stop)\n")
    # Optimise if requested (except edgemill)
    if OPTIMISE and (filetype <> 2):
      print "  Optimising .."
      lines = runTool(OPTIMISER, "", lines)
      lines.append("M02 (Program stop)\n")
    # Repair arcs
    print "  Repairing arcs ..."
    lines = repairArcs(lines)
    # Save the file
    filename = getCodeFile("pcbpack", filetype)
    print "  %s" % filename
    with open(filename, "w") as gcode:
      for line in lines:
        gcode.write(line)
  print "Operation complete."
"""
