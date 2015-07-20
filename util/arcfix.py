#!/usr/bin/env python
#----------------------------------------------------------------------------
# 21-Jul-2015 ShaneG
#
# Line Grinder can generate files with invalid arc commands (the end-point
# radius differs from the start-point radius). This code implements a filter
# to repair that. Original: https://github.com/blinkenlight/LineBender
#----------------------------------------------------------------------------

TextLinesHandled = 0;                                                           # Number of lines of g-code analyzed (should match the number of lines of text in the file)
TextLinesIgnored = 0;                                                           # Number of lines of g-code ignored (because no G0/G1/G2/G3 or X/Y/Z was found on the line)

PathLinesHandled = 0;                                                           # Number of path lines analyzed (number of lines found containing a G0/G1/G2/G3)
PathLinesDropped = 0;                                                           # Number of path lines removed as too short (Line Grinder uses these). Not implemented in 0.1
PathArcsAdjusted = 0;                                                           # Number of arc path lines recalculated (all arcs, currently, whether really needed or not)
PathArcsUnedited = 0;                                                           # Number of arc path lines NOT recalculated: any full circles (sole exceptions, see above )

UnitsMode = None;                                                               # Tracks current units mode (metric/imperial). Not implemented in 0.1
CoordsMode = None;                                                              # Tracks current coordinate mode (absolute/relative). Not implemented in 0.1
WorkPlane = None;                                                               # Tracks current work plane (XY/XZ/YZ). Not implemented in 0.1

CurrentPosition = {'X': None, 'Y': None, 'Z': None};                            # This tracks current X/Y/Z position at all times to be used as starting point for arcs

def sqr(x):
  """ Return number squared
  """
  return(x*x);

def dist(Xa, Ya, Xb, Yb):
  """ Calculate distance between two points.
  """
  return(sqrt(sqr(Xa - Xb) + sqr(Ya - Yb)));

def BendThatArc(X0, Y0, X1, Y1, X2, Y2):
  """ Does the actual math to recalculate the arc's center

    Note: X0,Y0 = arc start, X1,Y1 = arc end, X2,Y2 = original arc center
    Also, the proverbial compulsory bug in every software probably lives in here

    To briefly explain what's going on below, try to imagine solving it this way:
    In a custom coordinate system where both arc endpoints are on the "X" axis
    and the "Y" axis passes exactly halfway between them, the solution for the
    center of the arc is trivial: X=0, and Y is found as one side in the right
    angled triangle in which the distance to the arc endpoints is the hypotenuse
    and is fixed as the arc radius, while the other side is half the distance
    between the endpoints. Once we have this (X, Y) for the center, it's just a
    matter of (roto-)translating our custom coordinate system onto the actual
    frame of reference - not hard once we find the coordinates of the middle
    point of the segment connecting the arc's endpoints and the angle that
    segment makes with the horizontal ("X"-axis) of the "real" reference frame.
    In fact, some of you might recognize the trigonometric bit towards the end
    as a specific form of the general equations for transforming coordinate
    systems. There are two possible solutions - we pick the one we like more...
  """
  R = dist(X0, Y0, X2, Y2);                        # Radius we want to keep for the arc (equal to the original arc's radius)
  T = dist(X0, Y0, X1, Y1) / 2;                    # Half of the distance between the arc's endpoints (half length of the segment connecting them)
  S = sqrt(abs(sqr(R) - sqr(T)));                       # Center's distance from the midpoint on the perpendicular that goes through it (in either direction)
  Xm = (X0 + X1) / 2;                              # Coordinates of the above-mentioned midpoint of the segment connecting the arc's endpoints
  Ym = (Y0 + Y1) / 2;                              # These are our translation coordinates for the reference frame transformation
  if X0 == X1:                                     # Now we just need the angle between our custom and the global reference frame
      alfa = radians(90);                          # We'd rather avoid a division by zero for the alfa = 90 degrees case (endpoints on the same vertical)
  else:
      alfa = atan((Y1 - Y0) / (X1 - X0));          # Otherwise, the "slope" of the segment connecting the arc endpoints is the angle we want
  X3 = Xm + S * sin(alfa);                         # The actual coordinate system transformation of the point (X=0, Y=S) into the real reference frame
  Y3 = Ym - S * cos(alfa);
  X4 = Xm - S * sin(alfa);                         # The other possible solution.
  Y4 = Ym + S * cos(alfa);
  if dist(X2, Y2, X3, Y3) < dist(X2, Y2, X4, Y4):  # Cheating bigtime: there are inherently two centers that would fit two endpoints and a radius.
    return(X3, Y3);                                # Finding the proper one would entail figuring out the tangents at the endpoints of the arc
  else:                                            # which in turn would mean looking behind and ahead further for the adjoining segments.
    return(X4, Y4);                                # Instead, we simply choose the solution closer to the original center...

def AdjustArc(Position, Values, Params):
  """ AdjustArc() - recalculate origin (I,J) to match start and end points better

  Note: Arcs in non-XY planes...? K...? Heeey, where is everyone going...?!?
  """
  global PathArcsUnedited;
  Xs = Position['X'];                                                         # Coordinates of the starting point for the arc
  Ys = Position['Y'];
  if Values['X'] is not None:                                                 # Update the arc end point X coordinate if there is one on this line of code,
    Xe = Values['X'];
  else:                                                                       # otherwise just use the current one
    Xe = Xs;
  if Values['Y'] is not None:                                                 # Update the arc end point Y coordinate if there is one on this line of code,
    Ye = Values['Y'];
  else:
    Ye = Ys;                                                                # otherwise just use the current one
  if Values['I'] is not None:                                                 # Calculate the absolute arc center X coordinate from the relative I if there is one on this line of code,
    Xc = Xs + Values['I'];
  else:
    Xc = Xs;                                                                # otherwise just use the current X
  if Values['J'] is not None:                                                 # Calculate the absolute arc center Y coordinate from the relative I if there is one on this line of code,
    Yc = Ys + Values['J'];
  else:
    Yc = Ys;                                                                # otherwise just use the current Y
  if  dist(Xs, Ys, Xe, Ye) > 0:                                               # Cannot recalculate full circle arcs from endpoint(s) and radius; thankfully, there's no need either - they're always valid
    NewXc, NewYc = BendThatArc(Xs, Ys, Xe, Ye, Xc, Yc);                     # Do the magic, get some new center coordinates
    NewI = NewXc - Xs;                                                      # Calculate the relative I/J members from the absolute center X/Y
    NewJ = NewYc - Ys;
    if Params['N'] is None:                                                 # If there is no line number,
      LineNumberString = "";                                              # set the line number string to empty
    else:                                                                   # If there is one,
      LineNumberString = " (aka \"N" + Params['N'] + "\")";               # form a string to be included in any messages referring to this line
    OldCoordString = "[{0:.4f}, {1:.4f}]".format(Xc, Yc);
    NewCoordString = "[{0:.4f}, {1:.4f}]".format(NewXc, NewYc);
    logDebug("Adjusting center of arc from line {0}".format(TextLinesHandled) + LineNumberString + " from " + OldCoordString + " to " + NewCoordString);
    CommentString = " (Center moved by Line Bender from " + OldCoordString + " to " + NewCoordString + ")\n";
  else:                                                                       # If this arc is a full circle, we have to skip it
    NewI = Values['I'];                                                     # so the original center is preserved as the "new" one
    NewJ = Values['J'];
    PathArcsUnedited += 1;                                                  # Count this arc as skipped
    if Params['N'] is None:                                                 # If there is no line number,
      LineNumberString = "";                                              # set the line number string to empty
    else:                                                                   # If there is one,
      LineNumberString = " (aka \"N" + Params['N'] + "\")";               # form a string to be included in any messages referring to this line
    logDebug("Preserving center of arc from line {0}".format(TextLinesHandled) + LineNumberString + " - center cannot be determined for full circles");
    CommentString = " (Center preserved by Line Bender - center cannot be determined for full circles)\n";
  # *** This is also fudged(more corner cutting). It could use a bit of customization depending on which params are present and/or unchanged, no?
  NewLine = "G" + Params['G'] + " X{0:.4f} Y{1:.4f} I{2:.4f} J{3:.4f}".format(Xe, Ye, NewI, NewJ) + CommentString;
  return(NewLine);                                                            # Return the newly recalculated arc as a text line to replace the old line of g-code

def ScanForParams(WorkLine):
  """ Split the line into code words, return a dictionary of them

  Note: Only one instance of each word per line is handled right now even though
  multiple ones are quite legal (but not common in machine-generated g-code);
  The elements in the dictionary are either 'None' or the single string value.
  Also, it's hardly optimal to look for everyting on every line. I know. Sorry.
  """
  WorkLine = re.sub(";.*", "", WorkLine);                                     # Zap any semicolon-type comments (from semicolon to the end of the line)
  WorkLine = re.sub("\(.*?\)", "", WorkLine);                                 # Yank any parentheses-based comments (only whatever is between any parenthesis sets)
  WorkLine = re.sub(" |\t", "", WorkLine);                                    # We also Kick all tabs and spaces (why? BECAUSE WE CAN...!)
  # *** N-words **********************
  NWords = re.search("N(\d+)", WorkLine, re.IGNORECASE);                      # Search for a "Nxx" style line number. Only the first occurence, sorry...
  if NWords is None:                                                          # If no N-word is found,
    NParam = None;                                                          # set the return value to 'None',
    LineNumberString = "";                                                  # and the line number string to empty
  else:                                                                       # If one is found,
    NParam = NWords.group(1);                                               # store its parameter to be returned,
    LineNumberString = " (aka \"N" + NParam + "\")";                        # and form a string to be included in any messages referring to this line
  CommonErrorString = " on line {0}".format(TextLinesHandled) + LineNumberString + ", exiting.";
  # *** G-words **********************
  GWords = re.findall("G(\d+)", WorkLine, re.IGNORECASE);                     # Find all "Gxx" style codes (just the values)
  if len(GWords) > 1:                                                         # If there are multiple G-words on this line, we're busted, sorry...
    logError("Multiple \"G\" words found" + CommonErrorString);
    sys.exit(1);
  elif len(GWords) > 0:                                                       # If there is one, store its parameter to be returned,
    GParam = GWords[0];
  else:                                                                       # If there are none, set the return value accordingly
    GParam = None;
  # *** M-words **********************
  MWords = re.findall("M(\d+)", WorkLine, re.IGNORECASE);                     # Find all "Mxx" style codes (just the values)
  if len(MWords) > 1:                                                         # If there are multiple M-words on this line, we're busted, sorry...
    logError("Multiple \"M\" words found" + CommonErrorString);
    sys.exit(1);
  elif len(MWords) > 0:                                                       # If there is one, store its parameter to be returned,
    MParam = MWords[0];
  else:                                                                       # If there are none, set the return value accordingly
    MParam = None;
  # *** F-words **********************
  FWords = re.findall("F([+-]{,1}[\d.]+)", WorkLine, re.IGNORECASE);          # Find all "Fxx" style codes possibly including sign and decimal point (only values)
  if len(FWords) > 1:                                                         # If there are multiple F-words on this line, we're busted, sorry...
    logError("Multiple \"F\" words found" + CommonErrorString);
    sys.exit(1);
  elif len(FWords) > 0:                                                       # If there is one, store its parameter to be returned,
    FParam = FWords[0];
  else:                                                                       # If there are none, set the return value accordingly
    FParam = None;
  # *** X-words **********************
  XWords = re.findall("X([+-]{,1}[\d.]+)", WorkLine, re.IGNORECASE);          # Find all "Xxxx" style codes possibly including sign and decimal point (only values)
  if len(XWords) > 1:                                                         # If there are multiple X-words on this line, we're busted, sorry...
    logError("Multiple \"X\" words found" + CommonErrorString);
    sys.exit(1);
  elif len(XWords) > 0:                                                       # If there is one, store its parameter to be returned,
    XParam = XWords[0];
  else:                                                                       # If there are none, set the return value accordingly
    XParam = None;
  # *** Y-words **********************
  YWords = re.findall("Y([+-]{,1}[\d.]+)", WorkLine, re.IGNORECASE);          # Find all "Yxxx" style codes possibly including sign and decimal point (only values)
  if len(YWords) > 1:                                                         # If there are multiple Y-words on this line, we're busted, sorry...
    logError("Multiple \"Y\" words found" + CommonErrorString);
    sys.exit(1);
  elif len(YWords) > 0:                                                       # If there is one, store its parameter to be returned,
    YParam = YWords[0];
  else:                                                                       # If there are none, set the return value accordingly
    YParam = None;
  # *** Z-words **********************
  ZWords = re.findall("Z([+-]{,1}[\d.]+)", WorkLine, re.IGNORECASE);          # Find all "Zxxx" style codes possibly including sign and decimal point (only values)
  if len(ZWords) > 1:                                                         # If there are multiple Z-words on this line, we're busted, sorry...
    logError("Multiple \"Z\" words found" + CommonErrorString);
    sys.exit(1);
  elif len(ZWords) > 0:                                                       # If there is one, store its parameter to be returned,
    ZParam = ZWords[0];
  else:                                                                       # If there are none, set the return value accordingly
    ZParam = None;
  # *** I-words **********************
  IWords = re.findall("I([+-]{,1}[\d.]+)", WorkLine, re.IGNORECASE);          # Find all "Ixxx" style codes possibly including sign and decimal point (only values)
  if len(IWords) > 1:                                                         # If there are multiple I-words on this line, we're busted, sorry...
    logError("Multiple \"I\" words found" + CommonErrorString);
    sys.exit(1);
  elif len(IWords) > 0:                                                       # If there is one, store its parameter to be returned,
    IParam = IWords[0];
  else:                                                                       # If there are none, set the return value accordingly
    IParam = None;
  # *** J-words **********************
  JWords = re.findall("J([+-]{,1}[\d.]+)", WorkLine, re.IGNORECASE);          # Find all "Jxxx" style codes possibly including sign and decimal point (only values)
  if len(JWords) > 1:                                                         # If there are multiple J-words on this line, we're busted, sorry...
    logError("Multiple \"J\" words found" + CommonErrorString);
    sys.exit(1);
  elif len(JWords) > 0:                                                       # If there is one, store its parameter to be returned,
    JParam = JWords[0];
  else:                                                                       # If there are none, set the return value accordingly
    JParam = None;
  # *** K-words **********************
  KWords = re.findall("K([+-]{,1}[\d.]+)", WorkLine, re.IGNORECASE);          # Find all "Kxxx" style codes possibly including sign and decimal point (only values)
  if len(KWords) > 1:                                                         # If there are multiple K-words on this line, we're busted, sorry...
    logError("Multiple \"K\" words found" + CommonErrorString);
    sys.exit(1);
  elif len(KWords) > 0:                                                       # If there is one, store its parameter to be returned,
    KParam = KWords[0];
  else:                                                                       # If there are none, set the return value accordingly
    KParam = None;
  # *** R-words **********************
  RWords = re.findall("R([+-]{,1}[\d.]+)", WorkLine, re.IGNORECASE);          # Find all "Rxxx" style codes possibly including sign and decimal point (only values)
  if len(RWords) > 0:                                                         # If there are any R-words on this line, it's the wrong arc format, sorry...
    logError("Radius format arc found" + CommonErrorString);
    sys.exit(1);
  Params = dict({'N': NParam, 'G': GParam, 'M': MParam, 'F': FParam, 'X': XParam, 'Y': YParam, 'Z': ZParam, 'I': IParam, 'J': JParam, 'K': KParam});
  return(Params);

def WordsToValues(Params):
  """ Convert relevant string G-word parameters to numeric ones
  """
  if Params['N'] is None:                                                     # If there is no N-word,
    LineNumberString = "";                                                  # set the line number string to empty
  else:                                                                       # If there is one,
    LineNumberString = " (aka \"N" + Params['N'] + "\")";                   # form a string to be included in any messages referring to this line
  CommonErrorString = " on line {0}".format(TextLinesHandled) + LineNumberString + ", exiting.";
  try:
    if Params['G'] is None:                                                 # If it exists, convert the parameter to a number
      GValue = None;
    else:
      GValue = int(Params['G']);
    if Params['M'] is None:                                                 # If it exists, convert the parameter to a number
      MValue = None;
    else:
      MValue = int(Params['M']);
    if Params['X'] is None:                                                 # If it exists, convert the parameter to a number
      XValue = None;
    else:
      XValue = float(Params['X']);
    if Params['Y'] is None:                                                 # If it exists, convert the parameter to a number
      YValue = None;
    else:
      YValue = float(Params['Y']);
    if Params['Z'] is None:                                                 # If it exists, convert the parameter to a number
      ZValue = None;
    else:
      ZValue = float(Params['Z']);
    if Params['I'] is None:                                                 # If it exists, convert the parameter to a number
      IValue = None;
    else:
      IValue = float(Params['I']);
    if Params['J'] is None:                                                 # If it exists, convert the parameter to a number
      JValue = None;
    else:
      JValue = float(Params['J']);
    if Params['K'] is None:                                                 # If it exists, convert the parameter to a number
      KValue = None;
    else:
      KValue = float(Params['K']);
  except:
    logError("A numeric conversion failed" + CommonErrorString);
    sys.exit(1);
  Values = dict({'G': GValue, 'M': MValue, 'X': XValue, 'Y': YValue, 'Z': ZValue, 'I': IValue, 'J': JValue, 'K': KValue});
  return(Values);

# ******************************************************************************
# ******************************************************************************

def ParseLine(CurrentLine):
  """ Parse a single line, return an adjusted arc or the original line

  I'm well aware exiting like this on any error without closing stuff is not
  exactly nice but I'm learning all of this right now, and I have a half-done
  PCB I can't engrave waiting (hopefully still aligned) on the mill table, ok?
  """
  global TextLinesHandled;                                                    # Stuff to be updated from this function needs to be declared
  global TextLinesIgnored;
  global PathLinesHandled;
  global PathLinesDropped;
  global PathArcsAdjusted;
  global UnitsMode;
  global CoordsMode;
  global WorkPlane;
  global CurrentPosition;
  TextLinesHandled += 1;                                                      # Mark processing another line of text
  IgnoringThisLine = True;                                                    # Assume it will be ignored unless found otherwise
  GParams = ScanForParams(CurrentLine);                                       # Retrieve any relevant G-words from the line (values only, as string)
  GValues = WordsToValues(GParams);                                           # Some parameters are more useful as numbers, some as strings: converting
  # *** OK, really starting to cut corners here. This should be rather more generalized. Needs rewriting AFTER that PCB is done.
  # *** For now, I'm assuming arc start point is never "unset" / imperial, absolute mode in plane XY, full stop. Sorry.
  if GValues['G'] == 0 or GValues['G'] == 1:                                  # Handle G0/G1 lines (does nothing as of 0.1)
    PathLinesHandled += 1;
    IgnoringThisLine = False;
  if GValues['G'] == 2 or GValues['G'] == 3:                                  # Handle G2/G3 lines (the point of all this)
    CurrentLine = AdjustArc(CurrentPosition, GValues, GParams);             # Get a new line instead of the old one with a recalculated center
    PathArcsAdjusted += 1;
    IgnoringThisLine = False;
  if GValues['X'] is not None:                                                # Harvest any new X-coordinate to update the current position
    CurrentPosition['X'] = GValues['X'];
    IgnoringThisLine = False;
  if GValues['Y'] is not None:                                                # Harvest any new Y-coordinate to update the current position
    CurrentPosition['Y'] = GValues['Y'];
    IgnoringThisLine = False;
  if GValues['Z'] is not None:                                                # Harvest any new Z-coordinate to update the current position
    CurrentPosition['Z'] = GValues['Z'];
    IgnoringThisLine = False;
  if IgnoringThisLine:                                                        # Count the line as ignored if nothing above triggered
    TextLinesIgnored += 1;
  # *** Done cutting corners. Seriously, this is supposed to be way more elaborate and discerning...
  return(CurrentLine);                                                        # Return an output line for every input line of g-code

#----------------------------------------------------------------------------
# Helper functions
#----------------------------------------------------------------------------

def repairArcs(data):
  """ Uses the routines above to repair any 'bad' arcs in the source.
  """
  # Initialise state for arc fixing
  global UnitsMode, CoordsMode, WorkPlane, CurrentPosition
  UnitsMode = None
  CoordsMode = None
  WorkPlane = None
  CurrentPosition = {'X': None, 'Y': None, 'Z': None}
  # TODO: Remove line count initialisation at a later date
  global TextLinesHandled, TextLinesIgnored, PathLinesHandled, PathLinesDropped
  global PathArcsAdjusted, PathArcsUnedited
  TextLinesHandled = 0
  TextLinesIgnored = 0
  PathLinesHandled = 0
  PathLinesDropped = 0
  PathArcsAdjusted = 0
  PathArcsUnedited = 0
  # Now process the data
  result = list()
  for line in data:
    result.append(ParseLine(line))
  # TODO: Remove this later, I want to see what it is doing for now
  print u"Text lines handled: {0:>8}".format(TextLinesHandled);                # Display some processing stats
  print u"Text lines ignored: {0:>8}".format(TextLinesIgnored);
  print u"Path lines handled: {0:>8}".format(PathLinesHandled);
  print u"Path lines dropped: {0:>8}".format(PathLinesDropped);
  print u"Path arcs adjusted: {0:>8}".format(PathArcsAdjusted);
  print u"Path arcs unedited: {0:>8}".format(PathArcsUnedited);
  print;
  return result

