# tcxprune
Prune and split TCX files to make them more compatible with Lezyne and other GPS devices

Runs under Python 3

vprune.py and vprune.exe

Run vprune -h for built-in help

Prunes a .tcx file (RideWithGPS-compatible .tcx assumed) to reduce the number of Trackpoints (which draw the course on the map) without reducing number of CoursePoints (which give turn-by-turn directions)
This will reduce the size of .tcx files downloaded from RideWithGPS without eliminating the turn-by-turn instructions included as CoursePoints in the file.

Trackpoints are the points that indicate the path of the route on the map. With too few Trackpoints the route becomes "jaggy" and doesn't follow roads or trails exactly.  With too many Trackpoints the file may be too large to upload to your GPS device.

In remove Trackpoints, vprune simply deletes points randomly. It does not attempt to use an optimizing algorithm. This seems to work well enough with RideWithGPS .tcx files. 

Every CoursePoint (ie, point with turn-by-turn direction) must have an corresponding Trackpoint. So Trackpoints that correspond to spots with a turn-by-turn direction are never removed.

When you specify --percent to remove a percentage of Trackpoints, the trackpoints that correspond to a turn (CoursePoint) cannot be removed.  So, for example, --percent 0 will remove all Trackpoints except those corresponding to a turn.

vprune can also, optionally, split the file into several segments.  This allows the resulting files to be smaller and have better fidelity on the map, and also splits CoursePoints (with turn-by-turn directions) appropriately among the files. Many GPS devices will load smaller files with fewer CoursePoints more easily.

When the file is split into several files, each file overlaps the other at one CoursePoint (turn-by-turn direction point). So when you reach that turn you can simply load the next file to continue.

Output files are named vp_INPUTFILE (if one outputfile) or vp_1_INPUTFILE, vp_2_INPUTFILE, etc, if more than one.

vprune can also, optionally, clean CoursePoint Notes and/or Generic CoursePoints. This reduces file size, and these features may cause problems with some GPS devices or simply be useless (never displayed) in others.

vprune is specifically designed process .tcx files created with RideWithGPS and create .tcx files that will work with Lezyne GPS devices, which have problems when .tcx files are too large or have too many turns. It may be useful for .tcx files created by other sources and for other GPS devices as well.

vprune INPUTFILE - ie, run with default settings, will clean Notes from entries, split the files, and eliminate Trackpoints as needed to create a series of files should upload/run OK with a Lezyne GPS device.

RUNNING AS A WEB GUI UNDER ANDROID

Now vprune.py runs as command line OR windowed app (Windows, Mac, Linux, etc) OR as a web GUI (android)

Uses PySimpleGUI or PySimpleGuiWeb

For Android, you'll need to use Termux or similar and pip install lxml, docopt, PySimpleGUI and PySimpleGUIWeb.

On Termux there can be trouble installing lxml due to missing file dependencies. 

Installing some combination of these files seemed to fix it:

   pkg install libxml2-dev libxslt-dev libiconv-dev libxml2 libxslt libiconv

There are some limitations to the web GUI version for now. Particularly, the "Browse Files" button doesn't work.  You will need to type the filename manually.

Typically you'll follow this procedure on Android:

 - Downloady your .tcx to the Download directory
 - Rename the file something short and friendly like 123.tcx
 - Also copy vprune.py to the Download directory
 - Using Termux, switch to the Download directory and run 
        python vprune.py
 - Now go your your Android browser and navigate to localhost:8081 to operate vprune and process your files
   
vprune might work similarly on other phone and table operating systems.  However you would have to edit near the start of the files these lines:

    if platform=='android':
	    weborgui = 'web'

Change 'android' to whatever platform.system() returns for your operating system
