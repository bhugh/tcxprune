VPrune prunes and splits .tcx files to make them more compatible with Lezyne and other GPS devices that are unable to handle large and complex files.

VPrune can be run as a window GUI program (Windows, MacOS, Linux/Unix) OR from the command line OR via web GUI interface (Android).

Runs under:

 * Windows (.exe included)
 * Any Unix environment (MacOS, etc)
 * Android (under Termux)
 * Anywhere Python runs
 * Online [as a web page at Repl.it](https://repl.it/@bhugh/TCXPrune) - a great way to give it a quick check-out

Please checkout the [project wiki](https://github.com/bhugh/tcxprune/wiki) for detailed information about settings and options, setup instructions for Android and other Unix environments, GUI options, and command-line options.

![tcx-pruner-screenshot](https://user-images.githubusercontent.com/2321668/63480757-aff8e000-c458-11e9-913b-3a2edda90dc4.png)

 - If you simply start (or double click on) vprune.py/vprune.exe, a window will pop up - you can choose the file to process and other options

    --> If using the web version, a web window should open; if not open a browser on your device and navigate to localhost:8081 or 127.0.0.1:8081
    --> You can also run the app online via repl.it: https://repl.it/@bhugh/TCXPrune (Please fork first, then run.)

 - If you start vprune.exe from the command line with arguments as described below, it will run as a command line program

 - The text below describes command line operation but you can choose all the same options via the window

WHAT VPRUNE DOES AND WHY

A .tcx file consists of a long list of Trackpoints and CoursePoints. The files are plain text--open one up in a text editor and take a look.

Trackpoints are the most numerous. They are used to draw the detailed route. There are many fewer CoursePoints, because they are only the places where you get the "turn-by-turn" instructions.

With too few Trackpoints the route becomes "jaggy" and doesn't follow roads or trails exactly.  With too many Trackpoints the file may be too large to upload to your GPS device.

In remove Trackpoints, vprune simply deletes points randomly. It does not attempt to use an optimizing algorithm. This seems to work well enough with RideWithGPS style .tcx files--as long as you don't remove too many points.

Every CoursePoint (ie, point with turn-by-turn direction) must have an corresponding Trackpoint. So Trackpoints that correspond to spots with a turn-by-turn direction are never removed.

Via the entrt screen or command line, you can specify --percent to remove a percentage of Trackpoints.  So, for example, --percent 100 will leave all Trackpoints in place, while --percent 0 will remove all Trackpoints except those corresponding to a turn (remember, those can't be removed or the file won't work any more).

VPrune can also, optionally, split the file into several segments.  This allows the resulting files to be smaller and have better fidelity on the map.

Splitting the route also splits CoursePoints (with turn-by-turn directions) appropriately among the files, meaning that each of these files has far fewer CoursePoints than the original. Many GPS devices have trouble processing .tcx files with too many CoursePoints, so splitting the file into several smaller files is the best way to preserve the turn-by-turn instructions while still allowing these files to work correctly with these devices.

When the file is split into several files, each file overlaps the other at exactly one CoursePoint/turn-by-turn direction point. So when you reach the end of one file, you can simply load the next file to continue from that same point.

By default, output files are named vp_INPUTFILE (if one outputfile) or vp_1_INPUTFILE, vp_2_INPUTFILE, etc, if more than one. You can change the file prefix as desired.

VPrune can also, optionally, clean CoursePoint Notes and/or Generic CoursePoints. This reduces file size, and these features may cause problems with some GPS devices or simply be useless (never displayed) in others.

VPrune is specifically designed process .tcx files created with RideWithGPS and create .tcx files that will work with Lezyne GPS devices, which have problems when .tcx files are too large or have too many turns. It may be useful for .tcx files created by other sources and for other GPS devices as well.

VPrune INPUTFILE - ie, run with default settings, will clean Notes from entries, split the files, and eliminate Trackpoints as needed to create a series of files should upload/run OK with a Lezyne GPS device.

INSTALLING PYTHON AND VPRUNE.PY UNDER PYTHON

VPrune will run on most any platform that Python can run on. That includes Windows, Linux/Unix, MacOS, and some others (maybe iOS with Pythonista--at least as a command line app).  Installation steps:

1. Install Python 3 (3.7+ preferred) from https://www.python.org/downloads/

2. After a fresh Python install, you need to install a few needed libraries. At the command line or console enter these commands in sequence:
    
	pip install docopt
	pip install lxml==4.4.1
	pip install PYSimpleGUI==4.2.0
	pip install PYSimpleGUIWeb==0.28.1

	The first two libraries are needed for all versions.  The second two are needed to run the windowed GUI and web GUI versions.
	
	OR (shorter) just use: pip install -r requirements.txt

3. Depending on your operating system, you may be able to double-click vprune.py to run it (windows mode).  Otherwise at the command line or console type:
	python vprune.py

Depending on your system setup, you may need to use one of these commands instead:
	python 3 vprune.py
	py3 vprune.py
	py vprune.py

4. With those commands, VPrune will run in the windowed version. If you would rather use the command line/console version, just add the command line parameters described below. Example:

	vprune.py mygpsfile.tcx
	vprune.py --help

Depending on your system, you may need to add 'python' to the start of the commands, like this:

	python vprune.py mygpsfile.tcx
	python vprune.py --help

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
