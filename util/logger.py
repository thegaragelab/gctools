#!/usr/bin/env python
#----------------------------------------------------------------------------
# 21-Jul-2015 ShaneG
#
# Very simple logging - adapted from Sensaura.
#----------------------------------------------------------------------------
from datetime import datetime

class Logger:
  """ A simple logger that writes to the console
  """

  #--------------------------------------------------------------------------
  # Globals
  #--------------------------------------------------------------------------

  MSG_DEBUG = 0
  MSG_INFO = 1
  MSG_WARN = 2
  MSG_ERROR = 3
  MSG_FATAL = 4

  _SEVERITY = ( "DEBUG", "INFO", "WARN", "ERROR", "FATAL" )

  #--------------------------------------------------------------------------
  # Properties
  #--------------------------------------------------------------------------

  @property
  def severity(self):
    return self._severity

  @severity.setter
  def severity(self, value):
    self._severity = min(Logger.MSG_FATAL, max(Logger.MSG_DEBUG, severity))

  def __init__(self, severity = 0):
    self.severity = severity

  def write(self, timestamp, severity, message):
    """ Actually write the message
    """
    severity = min(Logger.MSG_FATAL, max(Logger.MSG_DEBUG, severity))
    print "%s: %s" % (Logger._SEVERITY[severity], message)

  def DEBUG(self, message):
    """ Write a DEBUG message
    """
    if Logger.MSG_DEBUG >= self.severity:
      self.write(datetime.now(), Logger.MSG_DEBUG, message)

  def INFO(self, message):
    """ Write an INFO message
    """
    if Logger.MSG_INFO >= self.severity:
      self.write(datetime.now(), Logger.MSG_INFO, message)

  def WARN(self, message):
    """ Write a WARNING message
    """
    if Logger.MSG_WARN >= self.severity:
      self.write(datetime.now(), Logger.MSG_WARN, message)

  def ERROR(self, message):
    """ Write a error message
    """
    if Logger.MSG_ERROR >= self.severity:
      self.write(datetime.now(), Logger.MSG_ERROR, message)

  def FATAL(self, message):
    """ Write a FATAL message and exit
    """
    self.write(datetime.now(), Logger.MSG_FATAL, message)
    exit(1)

LOG = Logger()

