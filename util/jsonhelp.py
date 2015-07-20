#!/usr/bin/env python
#----------------------------------------------------------------------------
# 15-Jul-2015 ShaneG
#
# Helpers to process JSON data
#----------------------------------------------------------------------------
from json import dumps, loads, JSONEncoder

class ExtendedEncoder(JSONEncoder):
  """ Encoder extension to allow classes to implement their own JSON encoding
  """

  def default(self, o):
    translator = getattr(o, "toJSON", None)
    if (translator is None) or (not callable(translator)):
      return JSONEncoder.default(self, o)
    return translator()

def toJSON(obj, **kw):
  """ Convert an object to JSON format
  """
  return dumps(obj, cls = ExtendedEncoder, **kw)

def fromJSON(json, **kw):
  """ Deserialise JSON strings
  """
  return loads(json, **kw)

def fromJSONFile(filename, **kw):
  """ Deserialise JSON from a file
  """
  lines = list()
  with open(filename, "r") as config:
    for line in config:
      clean = line.strip()
      if clean.startswith("#") or clean.startswith("//"):
        lines.append("")
      else:
        lines.append(line)
  return fromJSON("\n".join(lines))

