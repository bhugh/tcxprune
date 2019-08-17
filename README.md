# tcxprune
Prune and split TCX files to make them more compatible with Lezyne and other GPS devices

Runs under Python 3

vprune.py.
Prunes a .tcx file (RideWithGPS-compatible .tcx assumed) to reduce number of Trackpoints without reducing number of CoursePoints
This will reduce the size of .tcx files downloaded from RideWithGPS without eliminating the turn-by-turn instructions included
as CoursePoints in the file
Usage:
  vprune.py [options] INPUTFILE
  
Arguments:
  INPUTFILE         Required .TCX input filename
Options:
  -h --help     Show this.
  --maxturns <max # of turns/CoursePoints per file, will split into separate files if more than this>  Specify  max # turns/CoursePoints of Trackpoints in the resulting file(s).
  --percent <pct 0-100>  Specify percent of points to retain. 100% retains all points, 50% retains half/removes half, 0% removes all points. 
  --maxpoints <# of points 0-1000000>  Specify  max # of Trackpoints in the resulting file. Default is 2000 points.
  --clean  Will strip all Generic CoursePoints and eliminate all Notes in CoursePoints. [Default: No clean]
  You can specify percent OR maxpoints.  maxpoints takes precedence if you specify both.
  
  #vprune.py [--maxturns=<num_turns per file, will split if greater, <= 0, default 150 >][--maxpoints=<num_points <0, default 2000 >] [--percent=<pct 0-100>] [--clean=<BOOL>] INPUTFILE
