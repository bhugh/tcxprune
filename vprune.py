#!/usr/bin/env python

"""VPRUNE.EXE/VPRUNE.PY HELP FILE


VPrune can be run from the command line OR as a windows program (Windows) OR via web interface (Android)

 - If you simply start (or double click on) vprune.py/vprune.exe, a window will pop up - you can choose the file to process and other options

    - If using the web version, a web window should open; if not open a browser on your device and navigate to localhost:8081 or 127.0.0.1:8081

 - If you start vprune.exe from the command line with arguments as described below, it will run as a command line program

 - The text below describes command line operation but you can choose all the same options via the window

WHAT VPRUNE DOES AND WHY

Trackpoints are the points that indicate the path of the route on the map. With too few Trackpoints the route becomes "jaggy" and doesn't follow roads or trails exactly.  With too many Trackpoints the file may be too large to upload to your GPS device.

In remove Trackpoints, vprune simply deletes points randomly. It does not attempt to use an optimizing algorithm. This seems to work well enough with RideWithGPS .tcx files. 

Every CoursePoint (ie, point with turn-by-turn direction) must have an corresponding Trackpoint. So Trackpoints that correspond to spots with a turn-by-turn direction are never removed.

When you specify --percent to remove a percentage of Trackpoints, the trackpoints that correspond to a turn (CoursePoint) cannot be removed.  So, for example, --percent 0 will remove all Trackpoints except those corresponding to a turn.

vprune can also, optionally, split the file into several segments.  This allows the resulting files to be smaller and have better fidelity on the map, and also splits CoursePoints (with turn-by-turn directions) appropriately among the files. Many GPS devices will load smaller files with fewer CoursePoints more easily.

When the file is split into several files, each file overlaps the other at one CoursePoint (turn-by-turn direction point). So when you reach that turn you can simply load the next file to continue.

By default, output files are named vp_INPUTFILE (if one outputfile) or vp_1_INPUTFILE, vp_2_INPUTFILE, etc, if more than one. You can change the file prefix as desired.

VPrune can also, optionally, clean CoursePoint Notes and/or Generic CoursePoints. This reduces file size, and these features may cause problems with some GPS devices or simply be useless (never displayed) in others.

VPrune is specifically designed process .tcx files created with RideWithGPS and create .tcx files that will work with Lezyne GPS devices, which have problems when .tcx files are too large or have too many turns. It may be useful for .tcx files created by other sources and for other GPS devices as well.

VPrune INPUTFILE - ie, run with default settings, will clean Notes from entries, split the files, and eliminate Trackpoints as needed to create a series of files should upload/run OK with a Lezyne GPS device.

COMMAND LINE USAGE EXAMPLES:
  vprune routefile.tcx
  vprune --maxturns 100 --maxpoints 1000 --cleancourse --nocleannotes routefile.tcx
  vprune --maxturns 60 --maxpoints 400 --prefix new_ routefile.tcx 
  vprune --split 6 --maxpoints 750 routefile.tcx                                 
  vprune --percent 50 routefile.tcx   

Usage:
  vprune [options] [INPUTFILE]
  vprune -h
  vprune --help    

Options:
  INPUTFILE         .TCX input filename.  If none supplied on command line a GUI window will pop up to ask you to find the file.
  -h --help     Show this.

  --maxturns <max # of turns/CoursePoints before file is split>  [Default: --maxturns 80]
  --split <# of files to split into>                             [Specify --maxturns OR --split, not both]

  --maxpoints <# of Trackpoints in each output file>      [Default: --maxpoints 500]
  --percent <pct 0-100 of Trackpoints to retain>          [Specify --maxpoints OR --percent, not both]

  --cleancourse   Strip all Generic CoursePoints.      [Default: No cleancourse]
  --nocleannotes  Do not eliminate all Notes in CoursePoints. [Default: Eliminate all Notes]
  --trimnotes     Trim notes to 32 characters and remove any potentially troublesome characters (also forces --nocleannotes)

  --prefix <string>   Prefix output files with this string [Default: vp_]
      
"""
#vprune.py [--maxturns=<num_turns per file, will split if greater, <= 0, default 150 >][--maxpoints=<num_points <0, default 2000 >] [--percent=<pct 0-100>] [--clean=<BOOL>] INPUTFILE

#from __future__ import print_function

import re, sys, os,random, datetime, math, copy, html, time, platform #, pytz
from docopt import docopt
from io import StringIO

#will run as gui on Windows or other platforms and web on android
#will run as command line prg on either one
weborgui = 'gui'
platform=platform.system()
if platform=='android':
	weborgui = 'web'

#weborgui = 'web' #use to force web or gui for testing purposes

print(platform, weborgui)

if weborgui=='web':
	import PySimpleGUIWeb as sg
else:
	import PySimpleGUI as sg

try:
  from lxml import etree
  print("running with lxml.etree")
except ImportError:
	try:
		# Python 2.5
		import xml.etree.cElementTree as etree
		print("running with cElementTree on Python 2.5+")
	except ImportError:
		try:
			# Python 2.5
			import xml.etree.ElementTree as etree
			print("running with ElementTree on Python 2.5+")
		except ImportError:
			try:
				# normal cElementTree install
				import cElementTree as etree
				print("running with cElementTree")
			except ImportError:
				try:
					# normal ElementTree install
					import elementtree.ElementTree as etree
					print("running with ElementTree")
				except ImportError:
					print("Failed to import ElementTree from any known place")


ns1 = 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'
ns2 = 'http://www.garmin.com/xmlschemas/ActivityExtension/v2'
prefix = "vp_"
num_courses = 0
num_tracks = 0
num_trackpoints = 0
num_coursepoints = 0
orig_total_courses = 0
orig_total_tracks = 0
orig_total_trackpoints = 0
orig_total_coursepoints = 0
progress_window = []
progress_bar = []
progress = 0
gui = False

def isInt(s):
    try:
        return float(str(s)).is_integer()
    except:
        return False


def checkbox_to_radio(window, event, values, delimiter='_'):
	"""
	Make a sequence of checkboxes act like linked radio buttons, in PySimpleGUI
	You include a unique portion at the beginning of the key for the linked checkboxes, ending with a delimiter
	So keys 1_checkup 1_checkdown 1_checkacross 1_checkover are all linked, as are 2_checkin 2_checkout
	They are like radio buttons, so only one can be on at a time and you can't turn one off by clicking it, but by another choice
	make sure one choice is clicked to start for best results.
	This is necessary because radio buttons are not working in PySimpleGUIWeb, for now
	"""
	del_pos = (event.find('_'))
	if del_pos == -1:
		return
	if (values[event] == False):
		window.FindElement(event).Update(True) # can't turn an element off by clicking it (they're radios)
		return
	for value in values:
		if event == value:
			continue
		vdel_pos = (event.find('_'))
		if vdel_pos < 0:
			continue
		#print (event[:del_pos+1], value[:vdel_pos+1])
		if event[:del_pos+1] == value[:vdel_pos+1]:
			try:
				window.FindElement(value).Update(False)
			except:
				print (value, "couldn't find or update element")



# from https://stackoverflow.com/questions/26523929/add-update-elements-at-position-using-lxml-python
def upsert_entry(parent, index, insertdict, begindict, enddict):
	entry_template = """
      <Lap>
        <TotalTimeSeconds>{0}</TotalTimeSeconds>
        <DistanceMeters>{1}</DistanceMeters>
        <BeginPosition>
          <LatitudeDegrees>{2}</LatitudeDegrees>
          <LongitudeDegrees>{3}</LongitudeDegrees>
        </BeginPosition>
        <EndPosition>
          <LatitudeDegrees>{4}</LatitudeDegrees>
          <LongitudeDegrees>{5}</LongitudeDegrees>
        </EndPosition>
        <Intensity>Active</Intensity>
      </Lap>
    """
	entries = parent.findall('./{%s}Lap'%ns1)
	#entries = parent.findall('./Lap')
    # update if entry already exists.
	#print(entries)
	if index <= len(entries):
		entry = entries[index - 1]
		#for child in entry.iter():
			#print (type(child))

			#print(child.tag, child.text, child.tail)

		#print(entry.text)
		#print(entry.tag)
		for key in insertdict:
			#print (key)
			if (entry.find(key) is not None):
				entry.find(key).text = insertdict[key]
				#print ("Inserted into Lap: Key", key, "Value", insertdict[key])
			#else:
				#print ("Key", key, "not found")

	# insert at the end (only if the index is exactly after the last entry)
	#elif index == len(entries) + 1:
		#entry = etree.fromstring(entry_template.format(insertdict['TotalTimeSeconds'], insertdict['DistanceMeters'],begindict['LatitudeDegrees'],begindict['LongitudeDegrees'],enddict['LatitudeDegrees'],enddict['LongitudeDegrees']))
		#parent.append(entry)
		#print ("no match found")

def s2p(speed, lever=5):
	assert (lever > 0 and lever < 11)
	# The array factor contains power at 60km/h at lever positions 1 to 10
	factor1 =  [200.0,281.0,366.0,447.0,532.0,614.0,702.0,787.0,868.0,953.0]
	# The array factor contains power at 29.9km/h at lever positions 1 to 10
	factor2 =  [85.0,121.0,162.0,196.0,236.0,272.0,307.0,347.0,382.0,417.0]
	w = int(round(factor2[lever-1]+(speed-29.9)/30.1*(factor1[lever-1]-factor2[lever-1])))
	return w if w > 0 else 0

def check_time(track, time, times):
	#print (time) 
	#print ('\n')
	#print (times)
	#print ('\n')

	if (time in times):
		#print ('must keep \n')
		return 'must keep'		
	return 'may eliminate'
	

def process_trackpoint(track, trackpoint, percent, times, startT, endT, first_distance, first):
	global num_trackpoints
	returndict={}
	for child in trackpoint:
		#print ("child")
		for elem in child.iter():
			#print ("elem")
			#print (elem.tag)
			if (elem.tag == '{%s}Time'%ns1):
				time=elem.text
				returndict['{%s}Time'%ns1] = time
				#print (time)
				courseT = datetime.datetime.strptime(time, "%Y-%m-%dT%H:%M:%SZ")
				if (courseT < startT or courseT > endT):
					trackpoint.getparent().remove(trackpoint)
					return {} # return empty dictionary if we're deleting this point
				elif ((random.randint(1,100) > percent) and (check_time(track, time, times) == "may eliminate")):
					trackpoint.getparent().remove(trackpoint)
					return {} # return empty dictionary if we're deleting this point
				else:
					num_trackpoints += 1
			#if ( elem.tag == '{%s}AltitudeMeters'%ns1 or elem.tag == '{%s}DistanceMeters'%ns1 ):
			
			if  (elem.tag == '{%s}DistanceMeters'%ns1):
				returndict['{%s}DistanceMeters'%ns1] = elem.text
				if (first):
					elem.text = "0"
				else:
					elem.text = str(round(float(elem.text)-float(first_distance),2))
				#print (elem.text)
				#trackpoint.remove(elem)
			if  (elem.tag == '{%s}LatitudeDegrees'%ns1):
				returndict['{%s}LatitudeDegrees'%ns1] = elem.text
				#print (elem.text)
			if  (elem.tag == '{%s}LongitudeDegrees'%ns1):
				returndict['{%s}LongitudeDegrees'%ns1] = elem.text
				#print (elem.text)
			if ( elem.tag == '{%s}AltitudeMeters'%ns1):
				trackpoint.remove(elem)

			"""
				#elem.attrib['xmlns'] = ns2
				for node in elem.iter():
					if node.tag == '{%s}Speed'%ns2:
						speed_in_m_per_sec = float(node.text)
						speed_km_per_h = speed_in_m_per_sec /1000.0 * 60 *60
						power = s2p(speed_km_per_h, lever)
						# add power to trackpoint
						w = etree.SubElement(elem, '{%s}Watts'%ns2)
						w.text = str(power)
						w.tail = '\n'
			"""
	return returndict


def update_lap(course, start_returndict, end_returndict):

	startT = datetime.datetime.strptime(start_returndict["{%s}Time"%ns1], "%Y-%m-%dT%H:%M:%SZ")
	endT = datetime.datetime.strptime(end_returndict["{%s}Time"%ns1], "%Y-%m-%dT%H:%M:%SZ")
	deltaT = endT-startT
	#As a rule we're chopping existing files into parts, and they have a running total of distance in each trackpoint
	#So we can just subtract end-finish distance totals to get the total for our segmented file
	#More accurate perhaps would be to calculate it via lat&long for each point
	deltaD = str(round(float(end_returndict['{%s}DistanceMeters'%ns1]) - float(start_returndict['{%s}DistanceMeters'%ns1])))

	insertdict={} #start_returndict
	insertdict[("{%s}TotalTimeSeconds"%ns1)] = str(deltaT.total_seconds()) #str(int(differenceT.total_seconds()))
	insertdict["{%s}DistanceMeters"%ns1] = deltaD
	insertdict["{%s}BeginPosition/{%s}LatitudeDegrees"%(ns1,ns1)] = start_returndict["{%s}LatitudeDegrees"%ns1]
	insertdict["{%s}BeginPosition/{%s}LongitudeDegrees"%(ns1,ns1)] = start_returndict["{%s}LongitudeDegrees"%ns1]
	insertdict["{%s}EndPosition/{%s}LatitudeDegrees"%(ns1,ns1)] = end_returndict["{%s}LatitudeDegrees"%ns1]
	insertdict["{%s}EndPosition/{%s}LongitudeDegrees"%(ns1,ns1)] = end_returndict["{%s}LongitudeDegrees"%ns1]
	#insertdict = [("{%s}TotalTimeSeconds"%ns1) : '232', "{%s}TotalTimeSeconds"%ns1: '232', "{%s}BeginPosition/{%s}LatitudeDegrees"%(ns1,ns1): '232', "{%s}BeginPosition/{%s}LongitudeDegrees"%(ns1,ns1): '232', 
	#		   "{%s}EndPosition/{%s}LatitudeDegrees"%(ns1,ns1): '232', "{%s}EndPosition/{%s}LongitudeDegrees"%(ns1,ns1): '232']

	upsert_entry(course,1,insertdict,start_returndict, end_returndict)
	return

def cleanup_course(course, cleancourse, cleannotes, trimnotes):
	#print ("Course cleanup . . . ")
	bad_chars = ["\n", "\p", "--"]
	for child in course:
		
		if child.tag == '{%s}CoursePoint'%ns1:
			for elem in child.iter():
				#remove all notes (for now, testing)
				if cleannotes and elem.tag == '{%s}Notes'%ns1  and isinstance(elem.text, str):
					#print ("Removing:", elem.text)
					elem.text=""
					child.remove(elem)  #remove it entirely
				if trimnotes and elem.tag == '{%s}Notes'%ns1 and isinstance(elem.text, str):
					#print ("Trimming:", elem.text)
					elem.text=elem.text.strip()
					elem.text = (elem.text[:30] + '..') if len(elem.text) > 32 else elem.text
					#elem.text = filter(lambda i: i not in bad_chars, elem_text)
					for i in bad_chars : 
						elem.text = elem.text.replace(i, ' ') 
					#print ("Trimmed:", elem.text)



				#remove any generic CoursePoints, may cause problems
				if cleancourse and elem.tag == '{%s}PointType'%ns1 and elem.text == "Generic":
					#print ("Deleting:", elem.text)
					child.getparent().remove(child)



def process_track(course, track, percent, times, start_time, end_time):
	"""
	Process a TCX file track element.
	"""

	'''
	   <Lap>
        <TotalTimeSeconds>9449</TotalTimeSeconds>
        <DistanceMeters>197862.0</DistanceMeters>
        <BeginPosition>
          <LatitudeDegrees>39.13473</LatitudeDegrees>
          <LongitudeDegrees>-94.42453</LongitudeDegrees>
        </BeginPosition>
        <EndPosition>
          <LatitudeDegrees>39.13536</LatitudeDegrees>
          <LongitudeDegrees>-94.42447</LongitudeDegrees>
        </EndPosition>
        <Intensity>Active</Intensity>
      </Lap>

	  '''
	first = True
	start_returndict = {}
	end_returndict = {}
	#make sure we have something at least reasonably sensible in these dictionaries as there is a chance they won't ever be updated if the file is corrupted or something
	start_returndict[("{%s}TotalTimeSeconds"%ns1)] = "0"
	start_returndict["{%s}DistanceMeters"%ns1] = "0"
	start_returndict["{%s}BeginPosition/{%s}LatitudeDegrees"%(ns1,ns1)] = "0"
	start_returndict["{%s}BeginPosition/{%s}LongitudeDegrees"%(ns1,ns1)] = "0"
	start_returndict["{%s}EndPosition/{%s}LatitudeDegrees"%(ns1,ns1)] = "0"
	start_returndict["{%s}EndPosition/{%s}LongitudeDegrees"%(ns1,ns1)] = "0"
	end_returndict = start_returndict

	startT = datetime.datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%SZ")
	endT = datetime.datetime.strptime(end_time, "%Y-%m-%dT%H:%M:%SZ")

	for child in track:
		#print (child.tag)
		if child.tag == '{%s}Trackpoint'%ns1:
			#print ('working')
			returndict = process_trackpoint(track, child, percent, times, startT, endT, start_returndict["{%s}DistanceMeters"%ns1], first )
			#print (returndict)
			if (returndict != {} and first):
				start_returndict = returndict
				first = False
			if (returndict != {}):end_returndict = returndict
	update_lap(course, start_returndict, end_returndict)


def process_file(tree, root, tcxfile, num_parts, percent, first, last, cleancourse, cleannotes, trimnotes, prnt):
	"""
	Process the whole TCX file.
	"""
	global num_coursepoints, num_trackpoints, num_tracks, num_courses, prefix, gui, progress_window, mystdout
	

	for element in root.iter():
		if element.tag == '{%s}Course'%ns1:
			num_courses += 1
			#print (element)
			#print (element.tag)
			#print ('\n')
			times = []
			times_elem = element.findall('{%s}CoursePoint/{%s}Time'% (ns1,ns1))
			times_count=0
			times_included_count = 0
			start_time = ""
			end_time = ""
			times_first = True

			for elem in times_elem:
					#print(elem.text)
					times_count += 1
					if (times_count >= first and times_count <= last):
						if (times_first):
							start_time = elem.text
						times.append(elem.text)
						end_time = elem.text
						times_included_count += 1
						times_first = False
					else:
						#remove all course points not within the given range
						elem.getparent().getparent().remove(elem.getparent())

			#print (times)

			num_coursepoints += times_included_count

			tracks = []

			for element2 in element.iter():
				#print (element2.tag)
				#print ('element2 \n')
				if element2.tag == '{%s}Track'%ns1:
					tracks.append(element2)	
					#print ('appended track \n')
														
			num_tracks += len(tracks)
			for track in tracks:
				#print ('processing track \n')
				process_track(element, track, percent, times, start_time, end_time)
				#update_lap(track)
		
			if cleancourse or cleannotes or trimnotes:
				cleanup_course(element, cleancourse, cleannotes, trimnotes)


	#new_name = prefix + tcxfile
	new_name = os.path.join (os.path.dirname(tcxfile), prefix + os.path.basename(tcxfile))
	tree.write(new_name, encoding='utf-8', xml_declaration=True)

	print ("Result written to " + new_name)
	if prnt:
		print ('\n')
		if num_parts>1:
			print ("Trimmed to: %s files, %s courses, %s tracks, %s trackpoints (%s per output file), %s coursepoints (%s per output file)"%(num_parts, num_courses, num_tracks, num_trackpoints, round(num_trackpoints/num_parts), num_coursepoints, round(num_coursepoints/num_parts)))
		else:
			print ("Trimmed to: %s files, %s courses, %s tracks, %s trackpoints, %s coursepoints"%(num_parts, num_courses, num_tracks, num_trackpoints, num_coursepoints))
			
	print('\n')
	if gui:
		result_string = mystdout.getvalue()			
		progress_window.FindElement('progresstext').Update(result_string)
		progress_window.Refresh()
	#sys.stderr.flush()


def count_file(root, percent, maxpoints, num_parts=1, maxturns=500, split=0, prnt=False, whole=False):
	"""
	Count # of Trackpoints & Coursepoints in the whole TCX file.
	"""
	global num_coursepoints, num_trackpoints, num_tracks, num_courses, orig_total_coursepoints, orig_total_courses,orig_total_trackpoints,orig_total_tracks, gui, progress_window, mystdout

	orig_total_courses = 0
	orig_total_tracks = 0
	orig_total_trackpoints = 0
	orig_total_coursepoints = 0


	for element in root.iter():
		if element.tag == '{%s}Course'%ns1:
			orig_total_courses += 1
			#print (element)
			#print (element.tag)
			#print ('\n')
			times = []
			#print ('{%s}CoursePoint/{%s}Time'% (ns1,ns1))
			times_elem = element.findall('{%s}CoursePoint/{%s}Time'% (ns1,ns1))

			for elem in times_elem:
					#print(elem.text)
					times.append(elem.text)
			#print (times)

			orig_total_coursepoints += len(times_elem) #slightly wonky way of counting course points, could be updated to just count <coursepoint> elements

			tracks = []

			for element2 in element.iter():
				#print (element2.tag)
				#print ('element2 \n')
				if element2.tag == '{%s}Track'%ns1:
					tracks.append(element2)	
					#print ('appended track \n')
					'''
					expr = "count(//{%s}Track/{%s}Trackpoint)"%(ns1,ns1)
					expr = "count(//TrainingCenterDatabase/Courses/Course/Track/Trackpoint)"
					expr = "count(//Trackpoint)"
					print (expr)
					#orig_total_trackpoints = root.xpath(expr)
					#print (orig_total_trackpoints)
					'''
			orig_total_tracks += len(tracks)
			for track in tracks:
				'''
				#NOT SURE why none of these counting methods work!
				track_elem = element.findall('{%s}Trackpoint/{%s}Time'%(ns1,ns1))
				orig_total_trackpoints += len(track_elem)
				print (orig_total_trackpoints)
				print (len(track_elem))
				#print (root.xpath('count(/{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}Trackpoint)'))
				#orig_total_trackpoints += track.xpath('count(//Trackpoint)')
				'''
				
				for child in track:
					#print (child.tag)
					if child.tag == '{%s}Trackpoint'%ns1:
						#print ('working')
						orig_total_trackpoints += 1

	temp_num_parts = num_parts
	if whole:
		temp_num_parts = math.ceil(orig_total_coursepoints/maxturns)
		if split>0:
			temp_num_parts = split
			maxturns = math.ceil(orig_total_coursepoints/split)
		
	if prnt:
		print ("Original file: %s courses, %s tracks, %s trackpoints, %s coursepoints"%(orig_total_courses, orig_total_tracks, orig_total_trackpoints, orig_total_coursepoints))
		print ("Minimum trackpoints possible: %s trackpoints"%(orig_total_coursepoints))
	if (maxpoints > 0):
		#print ('B')
		if (maxpoints < orig_total_coursepoints/temp_num_parts):
			maxpoints = orig_total_coursepoints/temp_num_parts
		#assert (orig_total_coursepoints != 0, "Number of course)
		if ((orig_total_trackpoints - orig_total_coursepoints ) == 0 ):
			percent = 0
		else:
			percent = (maxpoints-orig_total_coursepoints/temp_num_parts)*100/(orig_total_trackpoints/temp_num_parts-orig_total_coursepoints/temp_num_parts)
			if whole:
				#print ("Whole")
				percent = (maxpoints*temp_num_parts-orig_total_coursepoints)*100/(orig_total_trackpoints-orig_total_coursepoints)
		if prnt:
			print ("Aiming for: %s files, retain %s%% of trackpoints, retain %s total trackpoints in each file"%(temp_num_parts, round(percent), maxpoints))
			print ('\n')
	else:
		maxpoints = orig_total_coursepoints/temp_num_parts + orig_total_trackpoints/temp_num_parts*percent/100
		#maxpoints = orig_total_trackpoints/temp_num_parts*percent/100
		#print ('A')
		if whole:
			maxpoints = orig_total_coursepoints + (orig_total_trackpoints - orig_total_coursepoints)*percent/100
		if prnt:
			print ("Aiming for: %s files, retain %s%% of trackpoints, retain %s total trackpoints in each file"%(temp_num_parts, round(percent), round(maxpoints/temp_num_parts)))
			print ('\n')
	if gui:
		result_string = mystdout.getvalue()			
		progress_window.FindElement('progresstext').Update(result_string)
		progress_window.Refresh()
	return {'percent':percent,'maxturns':maxturns}

#Return a tree with course elements x to y and all others, including corresponding track elements, removed

"""
def tree_prune(tree, root, first, last):

	for element in root.iter():
		if element.tag == '{%s}Course'%ns1:

			times = []
			times_elem = element.findall('{%s}CoursePoint/{%s}Time'% (ns1,ns1))

			for elem in times_elem:
					#print(elem.text)
					times.append(elem.text)
			#print (times)			

			tracks = []

			for element2 in element.iter():
				#print (element2.tag)
				#print ('element2 \n')
				if element2.tag == '{%s}Track'%ns1:
					tracks.append(element2)	
					#print ('appended track \n')
														
			num_tracks += len(tracks)
			for track in tracks:
				#print ('processing track \n')
				process_track(element, track, percent, times)
				#update_lap(track)

	new_name = "vprune_" + tcxfile
	tree.write(new_name, encoding='utf-8', xml_declaration=True)

	print ("Result written to " + new_name)
	print ("Trimmed to: %s courses, %s tracks, %s trackpoints, %s coursepoints"%(num_courses, num_tracks, num_trackpoints, num_coursepoints))
"""
def process_file_segments (tree, root, inputfilename, maxturns, split, maxpoints, percent, cleancourse, cleannotes, trimnotes):
	global gui, progress_window, progress_bar, progress, mystdout
	#num_parts = math.ceil(orig_total_coursepoints/maxturns)
	ret = count_file(root, percent, maxpoints, 1, maxturns, split, True, True)
	maxturns = ret['maxturns']
	num_parts = math.ceil(orig_total_coursepoints/maxturns)
	turns_per_part = math.floor(orig_total_coursepoints/num_parts)
	total_coursepoints = orig_total_coursepoints
	for i in range(num_parts):
		start_turn = i * turns_per_part
		end_turn = (i+1) * turns_per_part
		prnt=False
		if (i+1==num_parts):
			end_turn = total_coursepoints
			prnt=True
		newtree = copy.deepcopy(tree)
		newroot = newtree.getroot()
		ret = count_file(newroot, percent, maxpoints, num_parts, maxturns, False)	
		segmentpercent = ret ['percent']
		segment_filename = os.path.join(os.path.dirname(inputfilename), "%i_%s"%(i+1,os.path.basename(inputfilename)))
		process_file(newtree, newroot, segment_filename, num_parts, segmentpercent, start_turn, end_turn, cleancourse, cleannotes, trimnotes, prnt)
		if gui:
			result_string = mystdout.getvalue()			
			progress_window.FindElement('progresstext').Update(result_string)
			progress_window.Refresh()
			progress= 100/num_parts*(i+1)			
			if weborgui != 'web':
				progress_bar.UpdateBar(progress)
		#sys.stderr.flush()


				

def main(argv=None):
	global prefix, progress_window, progress_bar, progress, gui, mystdout, weborgui

	arguments = docopt(__doc__)
	inputfilename = arguments["INPUTFILE"]
	
	saveprint = print
	percent = 25
	maxpoints = 500
	maxturns= 80
	split=4
	cleancourse=False
	cleannotes=False
	trimnotes=False
	gui=False
	progress_debug=False
	window_bcolor='lightgray'
	multiline_bcolor='white'
	sg.SetOptions(
		background_color=window_bcolor, text_element_background_color=window_bcolor, 
		element_background_color=window_bcolor, scrollbar_color=None,		
		input_elements_background_color=multiline_bcolor
		)
	

	layout = [[sg.Text('                                    VPrune will simplify your .tcx files by trimming points and splitting the file into several smaller files')],
				[sg.Text('                         With default options it will produce files suitable for use with Lezyne GPS units and perhaps other GPS units as well')],
				[sg.Text('')],				

				[sg.Frame('',[
					[sg.Text('                                               SPLIT THE FILE',font=('default',19,'italic'), justification='center')],
					[sg.Text('                       '),sg.Checkbox('Use Max Turns                                                                                     ', default=True,enable_events=True,key='1_usemaxturns'), sg.Checkbox('Use File Split #                      ', enable_events=True,key='1_usesplit')],
					[sg.Text('            Max Turns per output file'), sg.InputText(key='maxturns', size=[5,1], default_text="80"), sg.Text('                                    OR                        Split original file into '), sg.InputText('4', key='split', size=[4,1]), sg.Text('new files                  ') ],
					[sg.Text('')],
				], background_color=window_bcolor)],
				[sg.Frame('',[
					[sg.Text('                                        REDUCE TRACKPOINTS',font=('default',18,'italic'),justification='center')],
					[sg.Text('                  '),sg.Checkbox('Use Max Trackpoints                                                                          ', enable_events=True, default=True,key='2_usemaxpoints'), sg.Checkbox('Use Percentage of Trackpoints               ', enable_events=True, key='2_usepercent')],
					[sg.Text('    Max number of Trackpoints in each output file'), sg.InputText('500',key='maxpoints', size=[5,1]), sg.Text('             OR                        Percent of Trackpoints to retain '), sg.InputText('25',key='percent', size=[3,1]), sg.Text('(0-100)') ],
					[sg.Text('')],
					[sg.Text('File prefix for processed files'), sg.InputText('vp_',key='prefix', size=[15,1]), sg.Text('If more than one file, names will be, ie, vp_1_yourfilename.tcx, vp_2_yourfilename.tcx, ...') ],
					[sg.Text('')],
				], background_color=window_bcolor)],
				[sg.Frame('',[
					[sg.Text('                                      CLEAN THE OUTPUT FILES',font=('default',18,'italic'),justification='center')],
					[sg.Text('                                                                    '),sg.Checkbox('Strip all "Generic" CoursePoints', key='cleancourse')],				  
					[sg.Text('                                           '),sg.Checkbox('Remove all Notes     ', default=True,enable_events=True, key='3_cleannotes'), sg.Checkbox('Trim/clean Notes', enable_events=True, key='3_trimnotes'), sg.Checkbox('Leave Notes alone                                                   ', enable_events=True, key='3_nocleannotes')],
				#[sg.Checkbox('Show progress Debug Window', key='progress_debug')],
					[sg.Text('')],
				], background_color=window_bcolor)],

				[sg.Frame('',[
					[sg.Text('                                       CHOOSE THE DOCUMENT',font=('default',18,'italic'))],
				#[sg.In(key='inputfile', size=[50,1], focus=True)],
					[sg.Text('                                      '),sg.In(key='inputfile', size=[70,1], focus=True), sg.FileBrowse(), sg.Text('                    ')],
					#Can try sg.FileBrowse OR sg.FilesBrowse
				], background_color=window_bcolor)],
				[sg.Text('')],
				[sg.Text('                                                                                  '),sg.Open('Process File'),sg.Text(' '), sg.Exit(), sg.Text('                                                                   '), sg.Help("Help")],
				[sg.Text('')],
				[sg.Multiline('', visible=False, key='webnotes', size=(700,200))],

				]
	
	if weborgui=='web':
		main_window = sg.Window('VPrune', layout, text_justification='center', use_default_focus=False, background_color=window_bcolor, web_port=8081)
	else:
		main_window = sg.Window('VPrune', layout, text_justification='center', use_default_focus=False, background_color=window_bcolor)
	

	main_window.Finalize()	

	
	if weborgui == 'web':
		webnotes = '''VPrune - Special Notes for Web Edition:

		 * Light gray numbers in text fields will not be entered - you MUST manually type a number in each field (for the values you will use)

		 * The BROWSE button will not work - you will have to manually type the filename in the input field

		 * To avoid typing directory names, run VPrune in the same directory as your .tcx files

		 * To avoid typing long filenames, rename your .tcx to a short, simple name
		'''
		main_window.FindElement('webnotes').Update(webnotes, visible=True)
		main_window.FindElement('maxturns').Update(str(maxturns))
		main_window.FindElement('split').Update(str(split))
		main_window.FindElement('maxpoints').Update(str(maxpoints))
		main_window.FindElement('percent').Update(str(percent))
		main_window.FindElement('prefix').Update(prefix)
		main_window.FindElement('inputfile').Update('.tcx')
	


	main_window_disabled=False

	while True:
		if not isinstance(inputfilename, str) or len(inputfilename)==0 or gui==True:
			if main_window_disabled:
				if weborgui != 'web':
					main_window.Enable()
				main_window_disabled=False

			while True:
				event, values = main_window.Read()
				#print (event, values)
				checkbox_to_radio(main_window, event, values, "_")
				if event in (None, 'Exit', 'Process File', 'Help'):
					break


			gui=True


			#print(event, values)
			#sys.stderr.flush()
			if (event=="Exit") or event is None:
				main_window.Close()
				exit()
				break
			elif event == "Help":
				#sg.PopupScrolled(__doc__,title='VPrune - Help',non_blocking=True)
				#sg.PopupScrolled(__doc__,size=(600,400))				
				#continue

				if weborgui=='web':
					sx=600
					sy=600
				else:
					sx=80
					sy=40

				layout = [[sg.Text('VPrune Help')],					 						   						  
						 [sg.Multiline('', size=(sx,sy), key='helptext', background_color=multiline_bcolor)],
						 [sg.Submit('Close')]
						 ]
								
				if weborgui=='web':
					help_window = sg.Window('VPrune - Help', layout, keep_on_top=True, disable_minimize=True, background_color = window_bcolor, web_port=8081)
				else:
					help_window = sg.Window('VPrune - Help', layout, keep_on_top=True, disable_minimize=True)

				#help_window = sg.Window('VPrune - Help', layout, keep_on_top=True, disable_minimize=True, web_port=8081)
				help_window.Finalize()
				help_window.FindElement('helptext').Update(html.escape(__doc__, quote=True))
				help_window.Read()
				help_window.Close()
				continue
			
			if weborgui != 'web':
				main_window.Disable()
				main_window_disabled=True
			inputfilename = values['inputfile']


				
			if not inputfilename:
				sg.Popup("VPrune - No filename", "No filename supplied; please try again", keep_on_top=True)
				#raise SystemExit("Cancelling: no filename supplied")
				time.sleep(0.05)
				if weborgui != 'web':
					main_window.BringToFront()
				continue

			elif not inputfilename.lower().endswith('.tcx'):				
					sg.Popup("VPrune - File not .tcx", "File must have .tcx extension; please try again", keep_on_top=True)
					time.sleep(0.05)
					if weborgui != 'web':
						main_window.BringToFront()
					continue
					#raise SystemExit("Cancelling: filename must have .tcx extension")
			elif not os.path.isfile(inputfilename):
				sg.Popup("VPrune - File does not exist", "Sorry, this file does not exist; please try again", keep_on_top=True)
				time.sleep(0.05)
				if weborgui != 'web':
					main_window.BringToFront()
				continue
				#raise SystemExit("Cancelling: filename must have .tcx extension")
			else:

				if weborgui=='web':
					sx=690
					sy=430
				else:
					sx=80
					sy=18

				layout = [[sg.Text('Confirm document to open and options',font=('default',18,'italic'))],					 
						   
						  #[sg.Output(size=(80, 18))],
						 [sg.Multiline("",key='confirmtext', size=(sx,sy), background_color=multiline_bcolor)],
						 [sg.Submit('Confirm'), sg.Cancel()]]

				#confirm_window = sg.Window('VPrune - Confirm file name and options', layout, keep_on_top=True, disable_minimize=True, web_port=8081)
				if weborgui=='web':
					confirm_window = sg.Window('VPrune - Confirm file name and options', layout, keep_on_top=True, disable_minimize=True, background_color = window_bcolor, web_port=8081)
				else:
					confirm_window = sg.Window('VPrune - Confirm file name and options', layout, keep_on_top=True, disable_minimize=True)

				confirm_window.Finalize()
				
				

				#inputfilename = values[0]
				#print(values)

				#sg.Popup('The filename you chose was', inputfilename)
			
			# start capturing all text output
			old_stdout = sys.stdout
			sys.stdout = mystdout = StringIO()
			print ("Input file:", inputfilename, "\n")


			if values['1_usemaxturns'] and len(values['maxturns']) > 0 and int(round(float(values['maxturns']))) > 0:
				maxturns = int(round(float(values['maxturns'])))
				assert (maxturns >= 0)
				print('Maximum Turns/Coursepoints in each output file: %d \n' % maxturns)
				#sys.stderr.flush()
			elif values['1_usesplit'] and len(values['split']) > 0 and int(round(float(values['split']))) > 0:
				split = int(round(float(values['split'])))
				assert (split >= 0)
				print('Split TCX into %d separate output files \n' % split)
				#sys.stderr.flush()
			else:
				maxturns=80
				print('Assuming DEFAULT Maximum Turns/Coursepoints in each output file: %d\n' % maxturns)
				#sys.stderr.flush()

			if values['cleancourse']:
				cleancourse=True
				#if clean:
				print('Will strip all Generic CoursePoints\n')
				#else:
				#	print('Will not strip Generic CoursePoints and Notes from all CoursePoints')
				#sys.stderr.flush()
			else:
				cleancourse=False
				print('Will not strip Generic CoursePoints\n')
				#sys.stderr.flush()

			if values['3_nocleannotes']:
				cleannotes=False
				trimnotes=False
				#if clean:
				print('Will leave Notes in CoursePoints unchanged\n')
				#else:
				#	print('Will not strip Generic CoursePoints and Notes from all CoursePoints')
				#sys.stderr.flush()
			elif values['3_trimnotes']:
				cleannotes=False
				trimnotes=True
				print('Will trim Notes in CoursePoints to 32 characters\n')	
				#sys.stderr.flush()
			elif values['3_cleannotes']:
				trimnotes=False
				cleannotes=True 
				print('Will completely strip Notes from all CoursePoints\n')
				#sys.stderr.flush()

			if values['2_usemaxpoints'] and len(values['maxpoints']) > 0 and int(round(float(values['maxpoints']))) > 0:
				maxpoints = int(round(float(values['maxpoints'])))
				assert (maxpoints >= 0)
				print('Maximum Trackpoints in each output file = %d \n' % maxpoints)
				#sys.stderr.flush()
			elif values['2_usepercent'] and len(values['percent']) > 0 and int(round(float(values['percent']))) >= 0 and int(round(float(values['percent']))) <= 100:
				percent = int(round(float(values['percent'])))
				maxpoints = 0
				assert (percent >= 0 and percent <= 100)
				print('Percent of Trackpoints to retain = %d \n' % percent)
				#sys.stderr.flush()
			else:
				maxpoints = 500
				print('Assuming DEFAULT maximum Trackpoints in each output file: %i\n'%maxpoints)	
				#sys.stderr.flush()

			if values['prefix'] and len(values['prefix'])>0:
				prefix = values['prefix']
			print('Output file prefix will be %s \n' % prefix)
			#sys.stderr.flush()

			sys.stdout = old_stdout
						
			result_string = mystdout.getvalue()
			
			confirm_window.FindElement('confirmtext').Update(result_string)

			event, values = confirm_window.Read()
			confirm_window.Close()
			if event=="Cancel":
				time.sleep(0.05)
				if weborgui != 'web':
					main_window.BringToFront()
				continue



		if not gui:
			if arguments['--maxturns'] and isInt(arguments['--maxturns']):
				maxturns = int(arguments['--maxturns'])
				assert (maxturns >= 0)
				sys.stderr.write('Maximum Turns/Coursepoints in each output file: %d \n' % maxturns)
				#sys.stderr.flush()
			elif arguments['--split'] and isInt(arguments['--split']):
				split = int(arguments['--split'])
				assert (split >= 0)
				sys.stderr.write('Split TCX into %d separate output files \n' % maxturns)
				#sys.stderr.flush()
			else:
				maxturns=80
				sys.stderr.write('Assuming DEFAULT Maximum Turns/Coursepoints in each output file: %d\n' % maxturns)
				#sys.stderr.flush()


			if arguments['--cleancourse']:
				cleancourse=True
				#if clean:
				sys.stderr.write('Will strip all Generic CoursePoints\n')
				#else:
				#	sys.stderr.write('Will not strip Generic CoursePoints and Notes from all CoursePoints')
				#sys.stderr.flush()
			else:
				cleancourse=False
				sys.stderr.write('Will not strip Generic CoursePoints\n')
				#sys.stderr.flush()
			if arguments['--nocleannotes']:
				cleannotes=False
				#if clean:
				sys.stderr.write('Will not strip Notes from all CoursePoints\n')
				#else:
				#	sys.stderr.write('Will not strip Generic CoursePoints and Notes from all CoursePoints')
				#sys.stderr.flush()
			elif not arguments['--trimnotes']:
				cleannotes=True
				sys.stderr.write('Will strip Notes from all CoursePoints\n')
				#sys.stderr.flush()
			if arguments['--trimnotes']:
				trimnotes=True
				cleannotes=False #must force this to false or there isn't much reason for --trimnotes
				sys.stderr.write('Will trim Notes to 32 characters\n')	
				#sys.stderr.flush()
			else:
				trimnotes=False
				if not cleannotes: # don't need to print this if the Notes are going to be totally eliminated
					sys.stderr.write('Will not trim Notes to 32 characters\n')
					#sys.stderr.flush()

			if arguments['--maxpoints'] and isInt(arguments['--maxpoints']):
				maxpoints = int(arguments['--maxpoints'])
				assert (maxpoints >= 0)
				sys.stderr.write('Maximum Trackpoints in each output file = %d \n' % maxpoints)
				#sys.stderr.flush()
			elif arguments['--percent'] and isInt(arguments['--percent']):
				percent = int(arguments['--percent'])
				maxpoints = 0
				assert (percent >= 0 and percent <= 100)
				sys.stderr.write('Percent of Trackpoints to retain = %d \n' % percent)
				#sys.stderr.flush()
			else:
				maxpoints = 500
				sys.stderr.write('Assuming DEFAULT maximum Trackpoints in each output file: %i\n'%maxpoints)	
				#sys.stderr.flush()

			if arguments['--prefix'] and len(arguments['--prefix'])>0:
				prefix = arguments['--prefix']
			sys.stderr.write('Output file prefix will be %s \n' % prefix)
			#sys.stderr.flush()

			if not inputfilename.lower().endswith('.tcx') and not gui:			
					print ("input file %s has no .tcx extension" % inputfilename)
					#sys.stderr.flush()
					exit(-1)
			elif not os.path.isfile(inputfilename):
					print ("input file %s does not exist" % inputfilename)
					#sys.stderr.flush()
					exit(-1)


	
			sys.stderr.write(' \n')
			#sys.stderr.flush()


		if gui:
				time.sleep(0.05)

				if weborgui=='web':
					sx=600
					sy=600
				else:
					sx=80
					sy=20

				if weborgui != 'web':
					main_window.BringToFront()

				layout = [#[sg.Text('Working . . . please wait')],					 
						  #[sg.Text('')],					 
						  [sg.Text('Processing file:', font=('default',19,'italic'))],					 
						  [sg.Text(inputfilename, size=(75,1))],
						  [sg.Multiline("",size=(sx,sy), key='progresstext', background_color=multiline_bcolor, autoscroll=True)],
						  #[sg.Output(size=(80, 20))],
						  [sg.ProgressBar(100, orientation='h', size=(55, 15), key='progressbar')],
						  [sg.Submit('Wait . . .', key='submit', disabled=True)],
						  
						 ]
			
				#progress_window = sg.Window('VPrune - Processing . . . ', layout, keep_on_top=True, disable_minimize=True,web_port=8081)
				if weborgui=='web':
					progress_window = sg.Window('VPrune - Processing . . . ', layout, keep_on_top=True, disable_minimize=True, background_color = window_bcolor, web_port=8081)
				else:
					progress_window = sg.Window('VPrune - Processing . . . ', layout, keep_on_top=True, disable_minimize=True)

				progress_bar = progress_window.FindElement('progressbar')
				progress=0
				#event, values = window.Read()
				progress_window.Finalize()
				#if progress_debug:
					#sg.Print(do_not_reroute_stdout=False)
				tree = etree.parse(inputfilename)
				root = tree.getroot()	

				# start capturing all text output
				old_stdout = sys.stdout
				sys.stdout = mystdout = StringIO()

				process_file_segments (tree, root, inputfilename, maxturns, split, maxpoints, percent, cleancourse, cleannotes, trimnotes)

				print ("PROCESSING COMPLETED")
				print ("\n\nProcessed file(s) will start with", prefix," and are in the same directory as your original .tcx file \n" + os.path.dirname(inputfilename))
				sys.stdout = old_stdout
						
				result_string = mystdout.getvalue()			
				progress_window.FindElement('progresstext').Update(result_string)

				progress_window.FindElement('submit').Update('Finished',disabled=False)
				#progress_window.Refresh()
				event, values = progress_window.Read()
				
				progress_window.Close()		
				time.sleep(0.05)
				if weborgui != 'web':
					main_window.BringToFront()
				#sg.Popup("VPrune - Completed!", "File Processed!\nFile is in the same file as your original .tcx file \n" + os.path.dirname(inputfilename))			
		else:
			tree = etree.parse(inputfilename)
			root = tree.getroot()	

			process_file_segments (tree, root, inputfilename, maxturns, split, maxpoints, percent, cleancourse, cleannotes, trimnotes)
			break
	if gui:
		main_window.Close()


if __name__ == "__main__":
	sys.exit(main())
exit()