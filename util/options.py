#!/usr/bin/env python
#----------------------------------------------------------------------------
# 24-Jul-2015 ShaneG
#
# Manage Gcode options
#----------------------------------------------------------------------------
from os.path import exists, realpath, join, dirname
from string import Template
from jsonhelp import fromJSONFile
from logger import LOG

def getSettings(control, options):
  """ Get settings from a mix of sources

    Settings are determined from a range of sources in order of preference.
    This includes:

      1. The command line parameters (as processed by optparse)
      2. The global configuration file (gcode.json)
      3. Defaults specified by the application

    This function uses a dictionary (control) containing the application
    defaults which will be updated from the other sources if they are available.

    The function also populates the 'prefix' and 'suffix' control options with
    the globally defined GCode prefix and suffix
  """
  # Load the configuration
  cfgfile = join(dirname(dirname(realpath(__file__))), "gcode.json")
  config = None
  defaults = None
  if exists(cfgfile):
    config = fromJSONFile(cfgfile)
    defaults = config.get("defaults", None)
  # Update the variables required
  for k in control.keys():
    opt = getattr(options, k, None)
    if (opt is None) and (defaults is not None):
      opt = defaults.get(k, None)
    control[k] = opt or  control[k]
    if control[k] is None:
      LOG.FATAL("No value specified for option '%s'" % k)
  # Get the prefix and suffix
  if config is not None:
    insertions = dict()
    for k in control.keys():
      if type(control[k]) == float:
        insertions[k] = "%0.4f" % control[k]
      else:
        insertions[k] = str(control[k])
    control['prefix'] = Template("\n".join(config.get("prefix", ( "", )))).safe_substitute(insertions)
    control['suffix'] = Template("\n".join(config.get("suffix", ( "", )))).safe_substitute(insertions)
  # Done
  return control

