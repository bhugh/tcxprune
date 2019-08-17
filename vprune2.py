#!/usr/bin/env python

"""vprune.py.

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

"""
from __future__ import print_function
import re, sys, random, datetime, math, copy #, pytz
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
num_courses = 0
num_tracks = 0
num_trackpoints = 0
num_coursepoints = 0
orig_total_courses = 0
orig_total_tracks = 0
orig_total_trackpoints = 0
orig_total_coursepoints = 0

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

def cleanup_course(course):
	print ("Course cleanup . . . ")
	for child in course:
		
		if child.tag == '{%s}CoursePoint'%ns1:
			for elem in child.iter():
				#remove all notes (for now, testing)
				#if elem.tag == '{%s}Notes'%ns1:
					#print ("Removing:", elem.text)
				#	elem.text=""

				#remove any generic CoursePoints, may cause problems
				if elem.tag == '{%s}PointType'%ns1 and elem.text == "Generic":
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


def process_file(tree, root, tcxfile, num_parts, percent, first, last, clean, prnt):
	"""
	Process the whole TCX file.
	"""
	global num_coursepoints, num_trackpoints, num_tracks, num_courses
	

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
		
			if clean:
				cleanup_course(element)


	new_name = "vp_" + tcxfile
	tree.write(new_name, encoding='utf-8', xml_declaration=True)

	print ("Result written to " + new_name)
	if prnt:
		print ('\n')
		print ("Trimmed to: %s files, %s courses, %s tracks, %s trackpoints, %s coursepoints"%(num_parts, num_courses, num_tracks, num_trackpoints, num_coursepoints))
	sys.stderr.write('\n')
	sys.stderr.flush()


def count_file(root, percent, maxpoints, num_parts=1, maxturns=2000, prnt=False, whole=False):
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
			print ("Aiming for: Retain %s%% of trackpoints, retain %s total trackpoints in each file"%(round(percent), maxpoints))
			print ('\n')
	else:
		maxpoints = orig_total_coursepoints/temp_num_parts + orig_total_trackpoints/temp_num_parts*percent/100
		if whole:
			maxpoints = orig_total_coursepoints + orig_total_trackpoints*percent/100
		if prnt:
			print ("Aiming for: Retain %s%% of trackpoints, retain %s total trackpoints in each file"%(round(percent), maxpoints))
			print ('\n')

	return percent

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
def process_file_segments (tree, root, inputfilename, maxturns, maxpoints, percent, clean):
	
	#num_parts = math.ceil(orig_total_coursepoints/maxturns)
	count_file(root, percent, maxpoints, 1, maxturns, True, True)
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

		segmentpercent = count_file(newroot, percent, maxpoints, num_parts, maxturns, False)	
		process_file(newtree, newroot, "%i_%s"%(i+1,inputfilename), num_parts, segmentpercent, start_turn, end_turn, clean, prnt)


				

def main(argv=None):
	arguments = docopt(__doc__)
	inputfilename = arguments["INPUTFILE"]
	if not inputfilename.endswith('.tcx'):
		print ("input file %s has no .tcx extension" % inputfilename)
		exit(-1)
	
	percent = 50
	maxpoints = 0
	maxturns= 150
	clean=False

	if arguments['--maxturns']:
		maxturns = int(arguments['--maxturns'])
		assert (maxturns >= 0)
		sys.stderr.write('Maximum Turns/Coursepoints in each TCX file = %d \n' % maxturns)
		sys.stderr.flush()
	else:
		maxturns=150
		sys.stderr.write('Assuming DEFAULT Maximum Turns/Coursepoints in each TCX file at %d\n' % maxturns)
		sys.stderr.flush()
	if arguments['--clean']:
		clean=True
		#if clean:
		sys.stderr.write('Will strip Generic CoursePoints and Notes from all CoursePoints')
		#else:
		#	sys.stderr.write('Will not strip Generic CoursePoints and Notes from all CoursePoints')
		sys.stderr.flush()
	else:
		clean=False
		sys.stderr.write('Will not strip Generic CoursePoints and Notes from all CoursePoints')
		sys.stderr.flush()
	if arguments['--maxpoints']:
		maxpoints = int(arguments['--maxpoints'])
		assert (maxpoints >= 0)
		sys.stderr.write('Maximum Trackpoints in TCX = %d \n' % maxpoints)
		sys.stderr.flush()
	elif arguments['--percent']:
		percent = int(arguments['--percent'])
		assert (percent >= 0 and percent <= 100)
		sys.stderr.write('Percent to retain = %d \n' % percent)
		sys.stderr.flush()
	else:
		maxpoints = 2000
		sys.stderr.write('Assuming DEFAULT maximum trackpoints to retain at %i\n'%maxpoints)	
		sys.stderr.flush()
	
	sys.stderr.write(' \n')
	sys.stderr.flush()

	tree = etree.parse(inputfilename)
	root = tree.getroot()	

	process_file_segments (tree, root, inputfilename, maxturns, maxpoints, percent, clean)



if __name__ == "__main__":
	sys.exit(main())
