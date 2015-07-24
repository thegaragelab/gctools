#!/usr/bin/env python
#----------------------------------------------------------------------------
# 11-Jan-2015 ShaneG
#
# Turn the results of the autoprobe log into a PNG file for visualisation.
#----------------------------------------------------------------------------
from sys import argv
from os.path import splitext
from random import random
from PIL import Image

HEIGHT_MIN = None
HEIGHT_MAX = None
STEP_X     = None
STEP_Y     = None
VALUES     = list()
SPREAD     = 1.6

def makeValues(xsteps, ysteps):
  """ Generate a set of random values for testing
  """
  global HEIGHT_MIN, HEIGHT_MAX, STEP_X, STEP_Y, VALUES
  for i in range(xsteps * ysteps):
    z = (random() * 3.2) - 1.6
    # Check min and max height first
    if (HEIGHT_MIN is None) or (z < HEIGHT_MIN):
      HEIGHT_MIN = z
    if (HEIGHT_MAX is None) or (z > HEIGHT_MAX):
      HEIGHT_MAX = z
    # Add to the list
    VALUES.append(z)
  # Set steps
  STEP_X = xsteps
  STEP_Y = ysteps

def loadValues(filename):
  """ Load the values from the log probe into an array, calculate the min and
      max heights found as well as the number of X and Y steps.
  """
  global VALUES, STEP_X, STEP_Y
  xvals = dict()
  yvals = dict()
  results = dict()
  # Helper to add a single value to the dictionary
  def addValue(x, y, z):
    global HEIGHT_MIN, HEIGHT_MAX
    # Check min and max height first
    if (HEIGHT_MIN is None) or (z < HEIGHT_MIN):
      HEIGHT_MIN = z
    if (HEIGHT_MAX is None) or (z > HEIGHT_MAX):
      HEIGHT_MAX = z
    # Update X and Y vals
    if not xvals.has_key(x):
      xvals[x] = 1
    else:
      xvals[x] = xvals[x] + 1
    if not yvals.has_key(y):
      yvals[y] = 1
    else:
      yvals[y] = yvals[y] + 1
    # Flesh out the dictionary
    if not results.has_key(y):
      results[y] = dict()
    results[y][x] = z
  # Process the input file
  with open(filename, "r") as input:
    for line in input:
      position = [ round(25.4 * float(x), 4) for x in line.split(" ")[:3] ]
      addValue(*position)
  # Get the number of x and y values
  STEP_X = len(xvals)
  STEP_Y = len(yvals)
  # Get the center point so we have a comparable reference
  global HEIGHT_MIN, HEIGHT_MAX
  mid = HEIGHT_MIN + (HEIGHT_MAX - HEIGHT_MIN) / 2
  # Generate a csv file
  with open(splitext(filename)[0] + ".csv", "w") as output:
    output.write("," + ",".join([ "%0.4f" % x for x in sorted(xvals.keys()) ]) + "\n")
    for y in sorted(yvals.keys(), reverse = True):
      output.write("%0.4f,%s\n" % (y, ",".join([ "%0.4f" % results[y][x] for x in sorted(xvals.keys()) ])))
  # Turn it into an array
  for y in sorted(yvals.keys(), reverse = True):
    for x in sorted(xvals.keys()):
      if not results.has_key(y):
        print "Error: Missing expected value for %0.4f,%0.4f" % (x, y)
        exit(1)
      if not results[y].has_key(x):
        print "Error: Missing expected value for %0.4f,%0.4f" % (x, y)
        exit(1)
      VALUES.append(results[y][x] - mid)
  # Update min and max height
  HEIGHT_MIN = min(VALUES)
  HEIGHT_MAX = max(VALUES)

def getColor(v):
  global SPREAD
  c = (0, 0, 0)
  if v < 0.0:
    c = (0, 0, int(abs(v / SPREAD * 255)))
  else:
    c = (0, int(v / SPREAD * 255), 0)
  return c

def avg(*args):
  return sum(args) / (1.0 * len(args))

def expandVals(width, height, values):
  results = list()
  # Get a particular value
  def getValue(xc, yc):
    return values[yc * width + xc]
  # Walk through interpolating the middle points
  for y in range(height - 1):
    # New even line - Interpolate center points only
    results.append(getValue(0, y))
    for x in range(1, width):
      results.append(avg(getValue(x - 1, y), getValue(x, y)))
      results.append(getValue(x, y))
    # New odd lines - interpolate above, below and center
    for x in range(width - 1):
      results.append(avg(getValue(x, y), getValue(x, y + 1)))
      results.append(avg(getValue(x, y), getValue(x + 1, y), getValue(x, y + 1), getValue(x + 1, y + 1)))
    results.append(avg(getValue(width - 1, y), getValue(width - 1, y + 1)))
  # And add the last line
  results.append(getValue(0, height - 1))
  for x in range(1, width):
    results.append(avg(getValue(x - 1, height - 1), getValue(x, height - 1)))
    results.append(getValue(x, height - 1))
  # All done
  return 2 * width - 1, 2 * height - 1, results

def generateImage(filename):
  """ Generate a height map image
  """
  global STEP_X, STEP_Y, VALUES
  # Interpolate values
  width = STEP_X
  height = STEP_Y
  points = VALUES
  for i in range(5):
    width, height, points = expandVals(width, height, points)
  # Create the image
  img = Image.new("RGB", (width, height), (0, 0, 0))
  for y in range(height):
    for x in range(width):
      img.putpixel((x, y), getColor(points[y * width + x]))
  # Save the file
  img.save(filename)

if __name__ == "__main__":
  # Check arguments
  if len(argv) != 2:
    print "Usage:"
    print "       %s <filename>" % argv[0]
    exit(1)
  # Load the values
  loadValues(argv[1])
#  makeValues(16, 10)
  # Show some stats and check the heights
  print "Min height: %0.4f" % HEIGHT_MIN
  print "Max height: %0.4f" % HEIGHT_MAX
  print "%d unique X values, %d unique y values" % (STEP_X, STEP_Y)
  if HEIGHT_MIN > SPREAD or HEIGHT_MIN < -SPREAD or HEIGHT_MAX > SPREAD or HEIGHT_MAX < -SPREAD:
    print "Error: Cannot generate image, height variation is too large"
  else:
    generateImage(splitext(argv[1])[0] + ".jpg")

