#!/usr/bin/env python
#----------------------------------------------------------------------------
# 04-Dec-2014 ShaneG
#
# A simple program to determine the dimensions and units of a g-code file.
#----------------------------------------------------------------------------
from sys import argv
from optparse import OptionParser
from os.path import splitext
from util import defaultExtension
import numpy as np
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
from scipy.interpolate import griddata

#--- Usage information
USAGE = """
Usage:
       %s [--image] filename

Where:

  --image           generate an image of the file
"""

class ProbeFile:
  """ Represents a probe file
  """

  def __init__(self, filename):
    """ Initialise from a file
    """
    points = list()
    for line in open(defaultExtension(filename, ".probe"), "r"):
      line = line.strip()
      if len(line) > 0:
        parts = line.split(" ")
        if len(parts) <> 3:
          raise Exception("Unrecognised probe file format")
        parts = list([ float(val) for val in parts ])
        points.append(parts)
    # Do some verification
    if len(points) < 3:
      raise Exception("File appears to be truncated")
    self.xstart, self.xend, self.xsteps = points[0]
    self.ystart, self.yend, self.ysteps = points[1]
    self.zmin, self.zmax, self.feed = points[2]
    points = points[3:]
    if len(points) <> (self.xsteps * self.ysteps):
      raise Exception("File appears to be truncated")
    # Sort points into an X/Y array
    self.points = points
    self.pdict = dict()
    total = 0.0
    for x, y, z in points:
      if not self.pdict.has_key(x):
        self.pdict[x] = dict()
      if not self.pdict[x].has_key(y):
        self.pdict[x][y] = z
      else:
        raise Exception("Duplicate point found - %0.4f, %0.4f, %0.4f" % (x, y, z))
    self.xvals = sorted(self.pdict.keys())
    self.yvals = sorted(self.pdict[self.xvals[0]].keys())
    # Calculate average and median
    self.zlevels = sorted([ p[2] for p in points ])
    self.zcount = len(self.zlevels)
    self.average = sum(self.zlevels) / len(points)
    index = self.zcount // 2
    if len(self.zlevels) % 2:
      self.median = self.zlevels[index]
    else:
      self.median = (self.zlevels[index - 1] + self.zlevels[index]) / 2.0

  def generateImage(self, filename):
    """ Generate a 3D plot of the probe
    """
    fig = plt.figure(figsize=plt.figaspect(0.5))
    ax = fig.add_subplot(1, 1, 1, projection='3d')
    # note this: you can skip rows!
    my_data = np.array(self.points)
    X = my_data[:,0]
    Y = my_data[:,1]
    Z = my_data[:,2]
    xi = np.linspace(X.min(),X.max(),100)
    yi = np.linspace(Y.min(),Y.max(),100)
    # VERY IMPORTANT, to tell matplotlib how is your data organized
    zi = griddata((X, Y), Z, (xi[None,:], yi[:,None]), method='cubic')
#    CS = plt.contour(xi,yi,zi,15,linewidths=0.5,color='k')
#    ax = fig.add_subplot(1, 2, 2, projection='3d')
    xig, yig = np.meshgrid(xi, yi)
    surf = ax.plot_surface(xig, yig, zi, linewidth=0)
    fig.set_size_inches((16, 8))
    plt.savefig(filename, dpi = 100)

#--- Main program
if __name__ == "__main__":
  # Set up program options
  parser = OptionParser()
  parser.add_option("-i", "--image", action="store_true", dest="image", default=False)
  options, args = parser.parse_args()
  # Check positional arguments
  if len(args) <> 1:
    print USAGE.strip() % argv[0]
    exit(1)
  # Load the probe file
#  try:
  probe = ProbeFile(args[0])
#  except Exception , ex:
#    LOG.FATAL("Could not load file '%s' - %s" % (args[0], ex))
  # Display basic information
  print "Probe from X %0.4f -> %0.4f, Y %0.4f -> %0.4f" % (probe.xstart, probe.xend, probe.ystart, probe.yend)
  print "Z levels range from %0.4f to %0.4f" % (min(probe.zlevels), max(probe.zlevels))
  print "  Diff: %0.4f, Avg: %0.4f, Med: %0.4f" % (max(probe.zlevels) - min(probe.zlevels), probe.average, probe.median)
  # Generate a plot if requested
  if options.image:
    probe.generateImage(defaultExtension(args[0], ".png", True))



