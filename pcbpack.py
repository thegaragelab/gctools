#!/usr/bin/env python
#----------------------------------------------------------------------------
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

def logDebug(msg):
  #print "DEBUG: %s" % msg
  pass

def logError(msg):
  print "ERROR: %s" % msg



#----------------------------------------------------------------------------
# Class wrapper to manage boards
#----------------------------------------------------------------------------

class Board:
  """ Represents a board.

    Each board has a fixed size (width and height), a mutable location and
    a rotation flag.
  """

  def __init__(self, width, height, name = "", xoff = 0.0, yoff = 0.0):
    """ Constructor with dimensions
    """
    self.name = name
    self._width = width
    self._height = height
    self._xoff = xoff
    self._yoff = yoff
    self.reset()

  def __str__(self):
    return "Board %0.2f x %0.2f @ %0.2f, %0.2f (Rot = %s)" % (self.width, self.height, self.x, self.y, self.rotated)

  @property
  def width(self):
    if self.rotated:
      return self._height
    return self._width

  @width.setter
  def width(self, value):
    raise Exception("Cannot modify 'width' after creation")

  @property
  def height(self):
    if self.rotated:
      return self._width
    return self._height

  @height.setter
  def height(self, value):
    raise Exception("Cannot modify 'height' after creation")

  def reset(self):
    """ Restore to original (unrotated, untranslated) state
    """
    self.x = 0
    self.y = 0
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

  def clone(self, dw = 0, dh = 0):
    return Board(self._width + dw, self._height + dh, self.name, self._xoff, self._yoff)

  def getAdjustedCode(self, filetype):
    """ Apply the current translation to the code
    """
    data = None
    if filetype <> 1:
      with open(getCodeFile(self.name, filetype), "r") as f:
        data = f.readlines()
# TODO: Edgemill files need to be flipped. For now just use rectangles
#      if filetype == 2:
#        # Edgemill files need to be flipped in X
#        data = runTool(GRECODE, "-xflip", data)
#        x, y, w, h = getBoardSize(self.name)
#        print "DEBUG: Edgemill (raw)"
#        print self.name
#        print x, y, w, h
#        data = runTool(GRECODE, "-shift %0.2f 0.0" % w, data)
    else:
      # Drill files get generated, not loaded
      data = generateDrillFile(self.name)
    # Determine the translation we need
    source = ( self._xoff, self._yoff, self._xoff + self._width, self._yoff + self._height )
    if self.rotated:
      target = ( self.x + self.width, self.y, self.x, self.y + self.height )
    else:
      target = ( self.x, self.y, self.x + self.width, self.y + self.height)
    # Do the translation/rotation
    data = runTool(GRECODE, "-overlay %s %s" % ("%0.2f %0.2f %0.2f %0.2f" % source, "%0.2f %0.2f %0.2f %0.2f" % target), data)
    return data

def loadBoard(name):
  """ Create a board instance from a file
  """
  if not checkFiles(name):
    raise Exception("Missing required g-code file for board '%s'" % self.name)
  # Get the board dimensions and create the instance
  xoff, yoff, width, height = getBoardSize(name)
  return Board(width + PANEL_SPACING, height + PANEL_SPACING, name, xoff, yoff)

#----------------------------------------------------------------------------
# Generate an image of the layout
#----------------------------------------------------------------------------

def createLayoutImage(panel, boards, filename):
  img = Image.new("RGB", (int(panel.width * 2), int(panel.height * 2)), "white")
  drw = ImageDraw.Draw(img)
  for board in boards:
    drw.rectangle((int(board.x * 2), int(board.y * 2), int((board.x + board.width) * 2), int((board.y + board.height) * 2)), fill = "black")
  img.save(filename)

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
# Main program
#----------------------------------------------------------------------------

if __name__ == "__main__":
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
