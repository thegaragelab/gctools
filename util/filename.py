#!/usr/bin/env python
#----------------------------------------------------------------------------
# 10-Aug-2015 ShaneG
#
# Helper functions for manipulating filenames
#----------------------------------------------------------------------------
from os.path import splitext

def defaultExtension(filename, extension, force = False):
  """ Add a default extension (optionally replacing the existing one)
  """
  name, ext = splitext(filename)
  if (ext == "") or force:
    ext = extension
  return name + ext

