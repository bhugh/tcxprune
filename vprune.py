#!/usr/bin/env python

"""vprune.py.

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

Usage examples:
  vprune routefile.tcx
  vprune --maxturns 100 --maxpoints 1000 --cleancourse --nocleannotes routefile.tcx
  vprune --maxturns 60 --maxpoints 400 --prefix new_ routefile.tcx 
  vprune --split 6 --maxpoints 750 routefile.tcx                                 
  vprune --percent 50 routefile.tcx   

Usage:
  vprune [options] INPUTFILE 
  vprune -h
  vprune --help
  
Arguments:
  INPUTFILE         Required .TCX input filename

Options:
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

from __future__ import print_function
import re, sys, random, datetime, math, copy #, pytz
import PySimpleGUI as sg
from docopt import docopt
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

def isInt(s):
    try:
        return float(str(s)).is_integer()
    except:
        return False

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
					print ("Trimming:", elem.text)
					elem.text=elem.text.strip()
					elem.text = (elem.text[:30] + '..') if len(elem.text) > 32 else elem.text
					#elem.text = filter(lambda i: i not in bad_chars, elem_text)
					for i in bad_chars : 
						elem.text = elem.text.replace(i, ' ') 
					print ("Trimmed:", elem.text)



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
	global num_coursepoints, num_trackpoints, num_tracks, num_courses, prefix
	

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


	new_name = prefix + tcxfile
	tree.write(new_name, encoding='utf-8', xml_declaration=True)

	print ("Result written to " + new_name)
	if prnt:
		print ('\n')
		if num_parts>1:
			print ("Trimmed to: %s files, %s courses, %s tracks, %s trackpoints (%s per output file), %s coursepoints (%s per output file)"%(num_parts, num_courses, num_tracks, num_trackpoints, round(num_trackpoints/num_parts), num_coursepoints, round(num_coursepoints/num_parts)))
		else:
			print ("Trimmed to: %s files, %s courses, %s tracks, %s trackpoints, %s coursepoints"%(num_parts, num_courses, num_tracks, num_trackpoints, num_coursepoints))
			
	sys.stderr.write('\n')
	sys.stderr.flush()


def count_file(root, percent, maxpoints, num_parts=1, maxturns=500, split=0, prnt=False, whole=False):
	"""
	Count # of Trackpoints & Coursepoints in the whole TCX file.
	"""
	global num_coursepoints, num_trackpoints, num_tracks, num_courses, orig_total_coursepoints, orig_total_courses,orig_total_trackpoints,orig_total_tracks

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
		if whole:
			maxpoints = orig_total_coursepoints + (orig_total_trackpoints - orig_total_coursepoints)*percent/100
		if prnt:
			print ("Aiming for: %s files, retain %s%% of trackpoints, retain %s total trackpoints in each file"%(temp_num_parts, round(percent), round(maxpoints/temp_num_parts)))
			print ('\n')

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
		process_file(newtree, newroot, "%i_%s"%(i+1,inputfilename), num_parts, segmentpercent, start_turn, end_turn, cleancourse, cleannotes, trimnotes, prnt)


				

def main(argv=None):
	global prefix

	arguments = docopt(__doc__)
	inputfilename = arguments["INPUTFILE"]
	if not inputfilename.endswith('.tcx'):
		print ("input file %s has no .tcx extension" % inputfilename)
		exit(-1)
	
	percent = 50
	maxpoints = 0
	maxturns= 80
	split=0
	cleancourse=False
	cleannotes=False
	trimnotes=False

	if arguments['--maxturns'] and isInt(arguments['--maxturns']):
		maxturns = int(arguments['--maxturns'])
		assert (maxturns >= 0)
		sys.stderr.write('Maximum Turns/Coursepoints in each output file: %d \n' % maxturns)
		sys.stderr.flush()
	elif arguments['--split'] and isInt(arguments['--split']):
		split = int(arguments['--split'])
		assert (split >= 0)
		sys.stderr.write('Split TCX into %d separate output files \n' % maxturns)
		sys.stderr.flush()
	else:
		maxturns=80
		sys.stderr.write('Assuming DEFAULT Maximum Turns/Coursepoints in each output file: %d\n' % maxturns)
		sys.stderr.flush()


	if arguments['--cleancourse']:
		cleancourse=True
		#if clean:
		sys.stderr.write('Will strip all Generic CoursePoints\n')
		#else:
		#	sys.stderr.write('Will not strip Generic CoursePoints and Notes from all CoursePoints')
		sys.stderr.flush()
	else:
		cleancourse=False
		sys.stderr.write('Will not strip Generic CoursePoints\n')
		sys.stderr.flush()
	if arguments['--nocleannotes']:
		cleannotes=False
		#if clean:
		sys.stderr.write('Will not strip Notes from all CoursePoints\n')
		#else:
		#	sys.stderr.write('Will not strip Generic CoursePoints and Notes from all CoursePoints')
		sys.stderr.flush()
	elif not arguments['--trimnotes']:
		cleannotes=True
		sys.stderr.write('Will strip Notes from all CoursePoints\n')
		sys.stderr.flush()
	if arguments['--trimnotes']:
		trimnotes=True
		cleannotes=False #must force this to false or there isn't much reason for --trimnotes
		sys.stderr.write('Will trim Notes to 32 characters\n')	
		sys.stderr.flush()
	else:
		trimnotes=False
		sys.stderr.write('Will not trim Notes to 32 characters\n')
		sys.stderr.flush()

	if arguments['--maxpoints'] and isInt(arguments['--maxpoints']):
		maxpoints = int(arguments['--maxpoints'])
		assert (maxpoints >= 0)
		sys.stderr.write('Maximum Trackpoints in each output file = %d \n' % maxpoints)
		sys.stderr.flush()
	elif arguments['--percent'] and isInt(arguments['--percent']):
		percent = int(arguments['--percent'])
		maxpoints = 0
		assert (percent >= 0 and percent <= 100)
		sys.stderr.write('Percent of Trackpoints to retain = %d \n' % percent)
		sys.stderr.flush()
	else:
		maxpoints = 500
		sys.stderr.write('Assuming DEFAULT maximum Trackpoints in each output file: %i\n'%maxpoints)	
		sys.stderr.flush()

	if arguments['--prefix'] and len(arguments['--prefix'])>0:
		prefix = arguments['--prefix']
	sys.stderr.write('Output file prefix will be %s \n' % prefix)
	sys.stderr.flush()


	
	sys.stderr.write(' \n')
	sys.stderr.flush()

	tree = etree.parse(inputfilename)
	root = tree.getroot()	

	process_file_segments (tree, root, inputfilename, maxturns, split, maxpoints, percent, cleancourse, cleannotes, trimnotes)



if __name__ == "__main__":
	sys.exit(main())
