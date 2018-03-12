import os, logging, wsgiref.handlers, datetime, random, math, string, urllib
import csv, json

from google.appengine.ext import webapp, db
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template
from gaesessions import get_current_session
from google.appengine.api import urlfetch


# TEST from kevin
# TEST from cory

###############################################################################
###############################################################################
######################## Data Classes for Database ############################
###############################################################################
###############################################################################

class Instructor(db.Model):
	firstName = 		db.StringProperty()
	lastName = 			db.StringProperty()
	email = 			db.StringProperty()
	password = 			db.StringProperty()
	usernum = 			db.IntegerProperty()
	courseNames =		db.ListProperty(str)
	courseNumbers = 	db.ListProperty(int) # to allow for multiple courses


class Student(db.Model):
	firstName = 		db.StringProperty()
	lastName = 			db.StringProperty()
	email = 			db.StringProperty()
	password =			db.StringProperty()
	usernum = 			db.IntegerProperty()
	courseNumbers = 	db.ListProperty(int) # to allow for multiple courses
	courseNames = 		db.ListProperty(str)

class Course(db.Model):
	term = 				db.StringProperty()
	year = 				db.StringProperty()
	courseNumber = 		db.IntegerProperty()
	instructor = 		db.StringProperty()
	instructorEmail =	db.StringProperty()
	roster = 			db.ListProperty(str)
	courseName =		db.StringProperty()
	moduleList = 		db.ListProperty(str) # list of modules in this course.

	# For now this is inactive, we just assume they'll use all three.
	# Consider removing the select boxes in course creation (for now).


class StudentCourse(db.Model):
# student/course combination, created when a student adds a course
	# student linked
	usernum = 			db.IntegerProperty()
	term = 				db.StringProperty()
	year = 				db.IntegerProperty()
	firstName = 		db.StringProperty()
	lastName = 			db.StringProperty()

	# course linked
	courseNumber = 		db.IntegerProperty()
	courseName = 		db.StringProperty()

	# module properties...
	Module1 =			db.StringProperty()
	Module2 = 			db.StringProperty()
	Module3 = 			db.StringProperty()
	WSAnswer1 = 		db.StringProperty()
	WSAnswer2 = 		db.StringProperty()
	WSAnswer3 = 		db.StringProperty()
	COEAnswer1 =		db.StringProperty()
	COEAnswer2 =		db.StringProperty()
	COEAnswer3 =		db.IntegerProperty()
	COEAnswer4 =		db.IntegerProperty()
	COEAnswer5 =		db.IntegerProperty()
	PFEAnswer1 =		db.StringProperty()
	PFEAnswer2 =		db.StringProperty()
	PFEAnswer3 =		db.IntegerProperty()
	PFEAnswer4 =		db.IntegerProperty()
	# PFEAnswer5 =		db.IntegerProperty()

	numberOfGuesses = 	db.IntegerProperty()
	numberOfSimulations = db.IntegerProperty()
	numberOfSimulations2 = db.IntegerProperty()
	QuizResults = 		db.ListProperty(str)


#This stores the current number of participants who have ever taken the study.
#see https://developers.google.com/appengine/docs/python/datastore/transactions
#could also use get_or_insert
#https://developers.google.com/appengine/docs/python/datastore/modelclass#Model_
#get_or_insert
class NumOfUsers(db.Model):
	counter = db.IntegerProperty(default=0)


#Increments NumOfUsers ensuring strong consistency in the datastore
@db.transactional
def create_or_increment_NumOfUsers():
	obj = NumOfUsers.get_by_key_name('NumOfUsers',
		read_policy=db.STRONG_CONSISTENCY)
	if not obj:
		obj = NumOfUsers(key_name='NumOfUsers')
	obj.counter += 1
	x=obj.counter
	obj.put()
	return(x)



###############################################################################
###############################################################################
########################### From Book Don't Touch #############################
###############################################################################
###############################################################################
# One line had to be updated for Python 2.7
#http://stackoverflow.com/questions/16004135/python-gae-assert-typedata-is-strin
#gtype-write-argument-must-be-string
# A helper to do the rendering and to add the necessary
# variables for the _base.htm template
def doRender(handler, tname = 'index.htm', values = { }):
	temp = os.path.join(
			os.path.dirname(__file__),
			'templates/' + tname)
	if not os.path.isfile(temp):
		return False
	# Make a copy of the dictionary and add the path and session
	newval = dict(values)
	newval['path'] = handler.request.path
#   handler.session = Session()
#   if 'username' in handler.session:
#      newval['username'] = handler.session['username']

	outstr = template.render(temp, newval)
	handler.response.out.write(unicode(outstr))  #### Updated for Python 2.7
	return True

################################################################################
################################################################################
################ Function to read data to show participants ####################
################################################################################
################################################################################

def readData(module,stimuli):
	if module=='test':
		f = open('test.csv', 'rU')

	data = csv.reader(f)
	data = list(data)

	condition = [0]*len(data)
	x = [0]*len(data)
	y = [0]*len(data)
	coord = [0,0]*len(data)

	for i in range(0,len(data)):
		condition[i] = int(data[i][0])
		x[i] = float(data[i][1])
		y[i] = float(data[i][2])

	return condition, x, y


################################################################################
################################################################################
############## Function to log participants out of the system ##################
################################################################################
################################################################################

# called in several places, so I made a standalone function
def killSession(self):
	# kill all the session stuff (username, password, etc)
	sessionlist = ['Logged_In', 'email', 'firstName', 'usernum', 'username',
	'Module1', 'Module2', 'Module3', 'Logged_In', 'M1_Progress', 'M2_Progress',
	'M3_Progress']

	for i in sessionlist:
		if i in self.session:
			self.session.__delitem__(i)


###############################################################################
###############################################################################
################################## Handlers! ##################################
###############################################################################
###############################################################################

###############################################################################
######################## Student/Instructor Handlers ##########################
###############################################################################

# this should be renamed "splash handler," since it's just the splash page
class LoginHandler(webapp.RequestHandler):
	def get(self):
		self.session = get_current_session()

		doRender(self, 'login.htm')


class LogoutHandler(webapp.RequestHandler):

	def get(self):
		self.session = get_current_session()
		self.session['Logged_In'] = False

		# kill all the session stuff (username, password, etc)
		killSession(self)

		# Send them back to the login page
		doRender(self, 'login.htm')

###############################################################################
########################### Student Page Handlers #############################
###############################################################################

class StudentLoginHandler(webapp.RequestHandler):
	def get(self):
		logging.info('render student login page')
		doRender(self, 'StudentLogin.htm',
			{'errorNumber':0})

	def post(self):
		self.session = get_current_session()

		# 1. make sure user exists
		email = str(self.request.get('loginEmail'))
		password = str(self.request.get('loginPassword'))

		que = db.Query(Student)
		que = que.filter('email =', email)
		results = que.fetch(limit=1)

		# If the user does not already exist in the datastore, send back
		if len(results) == 0:
			killSession(self)
			doRender(self, 'StudentLogin.htm',
				{'errorNumber':1})
			return

		# user exists if we made it this far


		# 2. make sure password is correct
		for i in results:
			p = i.password

		# if incorrect, send them back with error message
		if password != p:
			killSession(self)
			doRender(self, 'StudentLogin.htm',
				{'errorNumber':2})
			return

		# email/password combo is correct if we made it this far

		# 3. Store session variables
		for j in results: # even though there's only 1
			self.session['usernum']    		= j.usernum
			self.session['firstName']		= j.firstName
			self.session['lastName']		= j.lastName
			self.session['email']			= j.email
			self.session['courseNumbers']	= j.courseNumbers
			self.session['courseNames']		= j.courseNames
			self.session['Logged_In']		= True


		# 4. get instructor last names for courses
		instructors = []
		for i in self.session['courseNumbers']:
			instructors.append(db.Query(Course).filter('courseNumber =', i)
			.get().instructor)

		instructors = map(str, instructors)
		logging.info('Instructors: '+str(instructors))

		instructorLastNames = []
		for i in instructors:
			instructorLastNames.append(i.split(',')[0])

		instructorLastNames = map(str, instructorLastNames)
		self.session['courseNames'] = map(str, self.session['courseNames'])

		logging.info('Instructor last names: '+str(instructorLastNames))

		# convert arrays into strings for easier Django
		a = ''
		for i in self.session['courseNames']:
			a+=i+','

		t = ''
		for i in instructorLastNames:
			t+=i+','

		# 5. render courseMenuStudent.htm with those courses

		doRender(self, 'courseMenuStudent.htm',
			{'firstName':self.session['firstName'],
			'courseNames': a,
			'instructorNames':t})


class StudentSignupHandler(webapp.RequestHandler):
	def post(self):
		self.session = get_current_session()

		firstName = self.request.get('firstName')
		lastName = self.request.get('lastName')
		email = self.request.get('createEmail')
		password = self.request.get('password1')
		courseNumbers = []
		courseNames = []


		# create new student
		# Check whether user already exists
		que = db.Query(Student)
		que = que.filter('email =', email)
		results = que.fetch(limit=1)

		# If the user already exists in the datastore
		if len(results) > 0:
			doRender(self,
				'signupfail.htm',
				{'error': 'This account already exists. Please contact \
				administrator if you need to reset your password.'})
			return


		# Create User object in the datastore
		usernum = create_or_increment_NumOfUsers()
		newuser = Student(usernum=usernum,
			firstName=firstName,
			lastName=lastName,
			email = email,
			courseNumbers = courseNumbers,
			courseNames = courseNames,
			password=password);

		userkey = newuser.put()

		newuser.put()


		# store these variables in the session, log user in
		self.session = get_current_session()
		self.session['usernum']    	= usernum
		self.session['firstName']	= firstName
		self.session['lastName']	= lastName
		self.session['email']		= email
		self.session['Logged_In']	= True
		self.session['courseNumbers'] = courseNumbers
		self.session['courseNames'] = courseNames

		doRender(self, 'courseMenuStudent.htm',
			{'firstName':self.session['firstName'],
			'courseNames': self.session['courseNames']})


class StudentCourseMenuHandler(webapp.RequestHandler):
	def get(self):
		self.session = get_current_session()

		# detect if they came from the course selector or the end of a modules
		whichPath = self.request.get('path')

		if whichPath == 'courseSelect':

			# parse the input for the course name and instructor
			formInput = self.request.get('courseSelect').split(' -- ')

			courseName = formInput[0]
			instructorLastName = formInput[1]

			# query the user db for the course number
			# we might need a way to remove courses. Maybe not for this version,
			# but def in the future.
			courseNumber = db.Query(StudentCourse).filter(
				'courseName =', courseName).get().courseNumber

			self.session['activeCourse'] = courseNumber

			# query the StudentCourse db for student's progress
			active = db.Query(StudentCourse).filter(
				'usernum =', self.session['usernum']).filter(
				'courseNumber =', courseNumber).get()

			# update the session with relevant variables for StudentCourse

			self.session['Module1'] = active.Module1
			self.session['Module2'] = active.Module2
			self.session['Module3'] = active.Module3
			self.session['WSAnswer1'] = active.WSAnswer1
			self.session['WSAnswer2'] = active.WSAnswer2
			self.session['WSAnswer3'] = active.WSAnswer3
			self.session['COEAnswer1'] = active.COEAnswer1
			self.session['COEAnswer2'] = active.COEAnswer2
			self.session['COEAnswer3'] = active.COEAnswer3
			self.session['COEAnswer4'] = active.COEAnswer4
			self.session['COEAnswer5'] = active.COEAnswer5
			self.session['PFEAnswer1'] = active.PFEAnswer1
			self.session['PFEAnswer2'] = active.PFEAnswer2
			self.session['PFEAnswer3'] = active.PFEAnswer3
			self.session['PFEAnswer4'] = active.PFEAnswer4
			# PFEAnswer5 =		db.IntegerProperty()

			self.session['numberOfGuesses'] = active.numberOfGuesses
			self.session['numberOfSimulations'] = active.numberOfSimulations
			self.session['numberOfSimulations2'] = active.numberOfSimulations2
			self.session['QuizResults'] = active.QuizResults

			doRender(self, 'menu.htm',
				{'firstName':self.session['firstName'],
				'courseNumber': courseNumber,
				'courseName': courseName,
				'Module1': self.session['Module1'],
				'Module2': self.session['Module2'],
				'Module3': self.session['Module3'],})
		else:
			courseName = db.Query(Course).filter('courseNumber =', self.session['activeCourse']).get().courseName

			doRender(self, 'menu.htm',
				{'firstName':self.session['firstName'],
				'courseNumber': self.session['activeCourse'],
				'courseName': courseName,
				'Module1': self.session['Module1'],
				'Module2': self.session['Module2'],
				'Module3': self.session['Module3'],})

class EnrollCourseHandler(webapp.RequestHandler):
	def get(self):
		self.session = get_current_session()

		# much simpler for students than instructors:
		# students get a code from their instructors (in the future maybe a
		# customized link?), which is the course number they enter, that's it.

		doRender(self, "courseEnroll.htm",
			{'firstName':self.session['firstName'],
			'errorNumber':0})



	def post(self):


		self.session = get_current_session()
		thisCourseNumber = int(self.request.get('courseNumberInput'))

		# things this function needs to do:

		# 1. Confirm that course exists, and that student isn't registered
		# query database
		q = db.Query(Course).filter('courseNumber =', thisCourseNumber)
		c = q.fetch(limit=1)

		# 1 is the dummy course number for testing
		if thisCourseNumber != 1:
			if(len(c) == 0):
				# if course does not exist
				doRender(self, 'courseEnroll.htm',
					{'firstName':self.session['firstName'],
					'errorNumber': 1})
				return

			thisCourse = q.get()
			thisCourseName = thisCourse.courseName # for step 3

			term = thisCourse.term
			year = thisCourse.year

			# if you're here the course exists
			logging.info('COURSE EXISTS')


			# 2. Get list of courses the student currently has, create local array
			q = db.Query(Student).filter('email =', self.session['email'])
			student = q.get()

			newCourseNameArray = student.courseNames
			newCourseNumberArray = student.courseNumbers

			newCourseNameArray = map(str, newCourseNameArray)
			logging.info('OLD courses: '+str(newCourseNameArray))

			# 3. Append new course name to old ones (if they're not in the course)
			if thisCourseNumber not in newCourseNumberArray:

				newCourseNameArray.append(thisCourseName)
				newCourseNumberArray.append(thisCourseNumber)

			# 4. Save the local array into the datastore and session
			newCourseNameArray = map(str, newCourseNameArray)
			logging.info('NEW courses: '+str(newCourseNameArray))
			student.courseNames = newCourseNameArray
			student.courseNumbers = newCourseNumberArray
			student.put()

			self.session['courseNames'] = newCourseNameArray
			self.session['courseNumbers'] = newCourseNumberArray


			# 5. Create a StudentCourse instance for this student/course combination
			logging.info('new StudentCourse going into the datastore')

			currentSC = db.Query(StudentCourse).filter(
				'courseNumber =', thisCourseNumber).filter(
				'usernum =', self.session['usernum']).fetch(limit=1)

			if len(currentSC) == 0: # if this object doesn't exist

				newSC = StudentCourse(
					usernum = self.session['usernum'],
					courseNumber = thisCourseNumber,
					courseName = thisCourseName,

					term = term,
					year = int(year),
					firstName = self.session['firstName'],
					lastName = self.session['lastName'],

					# student/course combination, created when a student adds a course
					# student linked

					# module properties...
					Module1 =			'Incomplete',
					Module2 = 			'Incomplete',
					Module3 = 			'Incomplete',
					WSAnswer1 = 		'',
					WSAnswer2 = 		'',
					WSAnswer3 = 		'',
					COEAnswer1 =		'',
					COEAnswer2 =		'',
					COEAnswer3 =		0,
					COEAnswer4 =		0,
					COEAnswer5 =		0,
					PFEAnswer1 =		'',
					PFEAnswer2 =		'',
					PFEAnswer3 =		0,
					PFEAnswer4 =		0,
					# PFEAnswer5 =		0,

					numberOfGuesses = 	0,
					numberOfSimulations = 0,
					numberOfSimulations2 = 0,
					QuizResults = 		[])

				newSC.put()

			# 6. Feed the local course array into the page with instructor name
			instructors = []
			for i in newCourseNumberArray:
				instructors.append(db.Query(Course).filter('courseNumber =', i)
				.get().instructor) # started doing this to fit the 80 char limit


			instructors = map(str, instructors)
			logging.info('Instructors: '+str(instructors))
			# details about the course:

			instructorLastNames = []
			for i in instructors:
				instructorLastNames.append(i.split(',')[0])

			instructorLastNames = map(str, instructorLastNames)

			logging.info('Instructor last names: '+str(instructorLastNames))


			# this is the ugliest solution, but it works
			a = ''
			for i in newCourseNameArray:
				a+=i+','

			t = ''
			for i in instructorLastNames:
				t+=i+','


			doRender(self, 'courseMenuStudent.htm',
				{'firstName':self.session['firstName'],
				'courseNames': a,
				'instructorNames':t})

		else: # if courseNumber == 1 (testing)
			logging.info('testing with courseNumber 1')


			# thisCourse = q.get()
			thisCourseName = 'Dummy Course'


			# 2. Get list of courses the student currently has, create local array
			q = db.Query(Student).filter('email =', self.session['email'])
			student = q.get()

			newCourseNameArray = student.courseNames
			newCourseNumberArray = student.courseNumbers

			newCourseNameArray = map(str, newCourseNameArray)
			logging.info('OLD courses: '+str(newCourseNameArray))

			# 3. Append new course name to old ones
			# (if they're not in the course)
			# This works out nicely for testing, because if they're registered
			# nothing happens!
			if thisCourseNumber not in newCourseNumberArray:

				newCourseNameArray.append(thisCourseName)
				newCourseNumberArray.append(thisCourseNumber)

			# 4. Save the local array into the datastore and session
			newCourseNameArray = map(str, newCourseNameArray)
			logging.info('NEW courses: '+str(newCourseNameArray))
			student.courseNames = newCourseNameArray
			student.courseNumbers = newCourseNumberArray
			student.put()

			self.session['courseNames'] = newCourseNameArray
			self.session['courseNumbers'] = newCourseNumberArray


			# 5. Create a StudentCourse instance for this student/course combination
			logging.info('new StudentCourse going into the datastore')

			currentSC = db.Query(StudentCourse).filter(
				'courseNumber =', thisCourseNumber).filter(
				'usernum =', self.session['usernum']).fetch(limit=1)

			if len(currentSC) == 0: # if this object doesn't exist

				newSC = StudentCourse(
					usernum = self.session['usernum'],
					courseNumber = thisCourseNumber,
					courseName = thisCourseName)

				newSC.put()

			# newCourse = Course(
			# 	term = term,
			# 	year = year,
			# 	courseNumber = courseNumber,
			# 	instructor = instructor,
			# 	instructorEmail = email,
			# 	roster = roster,
			# 	courseName = courseName,
			# 	moduleList = moduleList)
            #
			# newCourse.put()


			logging.info('It\'s in.')
			# new StudentCourse object in the datastore


			# 6. Feed the local course array into the page with instructor name
			instructors = []
			for i in newCourseNumberArray:
				if i != 1:
					instructors.append(db.Query(Course).filter(
					'courseNumber =', i).get().instructor)
				else:
					instructors.append('Dummy, Instructor')


			instructors = map(str, instructors)
			logging.info('Instructors: '+str(instructors))
			# details about the course:

			instructorLastNames = []
			for i in instructors:
				instructorLastNames.append(i.split(',')[0])

			instructorLastNames = map(str, instructorLastNames)

			logging.info('Instructor last names: '+str(instructorLastNames))


			# this is the ugliest solution, but it works
			a = ''
			for i in newCourseNameArray:
				a+=i+','

			t = ''
			for i in instructorLastNames:
				t+=i+','


			doRender(self, 'courseMenuStudent.htm',
				{'firstName':self.session['firstName'],
				'courseNames': a,
				'instructorNames':t})


###############################################################################
########################### Module Page Handlers ##############################
###############################################################################

class CarryoverEffectsHandler(webapp.RequestHandler):

	def get(self):
		self.session = get_current_session()

		self.session['M1_Progress'] = 0

		doRender(self, "CarryoverEffectsIntro.htm",
			{'progress':self.session['M1_Progress']})

		# KEVIN: this was the previous code for this; there wasn't an
		# alternative for if the progress var didn't equal 0, and it was
		# throwing an error if it wasn't in the session. With the redesign
		# we have to just set it to zero. I think if it's calling the get
		# handler it will never be more than zero, but let me know if I'm
		# missing something.

		# previous code:
		# if self.session['M1_Progress'] == 0:
		# 	doRender(self, "CarryoverEffectsIntro.htm",
		# 		{'progress':self.session['M1_Progress']})

	def post(self):
		logging.info("checkpoint 1")
		self.session = get_current_session()

		M1_Progress = int(self.request.get('progressinput'))
		self.session['M1_Progress'] = M1_Progress
		logging.info("Progress: "+str(M1_Progress))

		if M1_Progress == 1:
			self.session['COEAnswer1'] = self.request.get('Q1')

			doRender(self, "CarryoverEffects1.htm",
				{'progress':self.session['M1_Progress']})

		elif M1_Progress == 2:
			self.session['COEAnswer2'] = self.request.get('Q2')

			doRender(self, "CarryoverEffects2.htm",
				{'progress':self.session['M1_Progress']})

		elif M1_Progress == 3:
			# self.session['COEAnswer3'] = self.request.get('Q3')

			doRender(self, "CarryoverEffects3.htm",
				{'progress':self.session['M1_Progress']})

		elif M1_Progress == 4:
			doRender(self, "CarryoverEffectsQuiz.htm",
				{'progress':self.session['M1_Progress']})

		elif M1_Progress == 5:
			COEAnswer3 = int(self.request.get('Question1'))
			COEAnswer4 = int(self.request.get('Question2'))
			COEAnswer5 = int(self.request.get('Question3'))

			# Record that user completed the module
			self.session['Module1'] = 'Complete'

			# old db code, keeping because I haven't tested new code yet
			# # Query the datastore
			# que = db.Query(User)
            #
			# # find the current user
			# que = que.filter('username =', self.session['username'])
			# results = que.fetch(limit=1)
            #
			# # change the datastore result for module 1
			# for i in results:
			# 	i.COEAnswer1 = self.session['COEAnswer1']
			# 	i.COEAnswer2 = self.session['COEAnswer2']
			# 	i.COEAnswer3 = COEAnswer3
			# 	i.COEAnswer4 = COEAnswer4
			# 	i.COEAnswer5 = COEAnswer5
			# 	i.Module1 = self.session['Module1']
			# 	i.put()

			# new db code
			course = db.Query(StudentCourse).filter(
				'usernum =', self.session['usernum']).filter(
				'courseNumber =', self.session['activeCourse']).get()

			# change the datastore result for this module
			course.COEAnswer1 = self.session['COEAnswer1']
			course.COEAnswer2 = self.session['COEAnswer2']
			course.COEAnswer3 = self.session['COEAnswer3']
			course.COEAnswer4 = self.session['COEAnswer4']
			course.COEAnswer5 = self.session['COEAnswer5']
			course.Module1 = self.session['Module1']
			course.put()
			# end new db code


			logging.info('Datastore updated')

			self.session['M1_Progress'] = 0
			doRender(self, "FinishCarryoverEffects.htm")
		else:
			logging.info("something is wrong")



class PracticeFatigueEffectsHandler(webapp.RequestHandler):

	def get(self):
		self.session = get_current_session()

		# KEVIN: see note from carryover effects, same applies here.
		# please delete these notes to indicate that you're okay with these
		# changes.

		self.session['M3_Progress'] = 0

		doRender(self, "PracticeFatigueEffectsIntro.htm",
			{'progress':self.session['M3_Progress']})

	def post(self):
		logging.info("checkpoint 1")
		self.session = get_current_session()

		M1_Progress = int(self.request.get('progressinput'))
		self.session['M3_Progress'] = M1_Progress
		logging.info("Progress: "+str(M1_Progress))

		if M1_Progress == 1:
			self.session['PFEAnswer1'] = self.request.get('Q1')

			doRender(self, "PracticeFatigueEffects1.htm",
				{'progress':self.session['M3_Progress']})

		elif M1_Progress == 2:
			self.session['PFEAnswer2'] = self.request.get('Q2')

			doRender(self, "PracticeFatigueEffects2.htm",
				{'progress':self.session['M3_Progress']})

		elif M1_Progress == 3:
			doRender(self, "PracticeFatigueEffectsQuiz.htm",
				{'progress':self.session['M3_Progress']})

		elif M1_Progress == 4:
		# 	doRender(self, "CarryoverEffectsQuiz.htm",
		# 		{'progress':self.session['M1_Progress']})

		# elif M1_Progress == 5:
			self.session['PFEAnswer3'] = int(self.request.get('Question1'))
			# PFEAnswer4 = int(self.request.get('Question2'))
			self.session['PFEAnswer5'] = int(self.request.get('Question3'))

			# Record that user completed the module
			self.session['Module3'] = 'Complete'

			# old db code, keeping because I haven't tested new code yet
			# # Query the datastore
			# que = db.Query(User)
            #
			# # find the current user
			# que = que.filter('username =', self.session['username'])
			# results = que.fetch(limit=1)
            #
			# # change the datastore result for module 1
			# for i in results:
			# 	i.PFEAnswer1 = self.session['PFEAnswer1']
			# 	i.PFEAnswer2 = self.session['PFEAnswer2']
			# 	# i.COEAnswer3 = self.session['COEAnswer3']
			# 	i.PFEAnswer3 = PFEAnswer3
			# 	i.PFEAnswer4 = PFEAnswer5
			# 	# i.PFEAnswer5 = PFEAnswer5
			# 	i.Module3 = self.session['Module3']
			# 	i.put()
            #
			# logging.info('Datastore updated')

			# new db code
			course = db.Query(StudentCourse).filter(
				'usernum =', self.session['usernum']).filter(
				'courseNumber =', self.session['activeCourse']).get()

			# change the datastore result for this module
			course.PFEAnswer1 = self.session['PFEAnswer1']
			course.PFEAnswer2 = self.session['PFEAnswer2']
			course.PFEAnswer3 = self.session['PFEAnswer3']
			# course.PFEAnswer4 = self.session['PFEAnswer4']
			course.PFEAnswer5 = self.session['PFEAnswer5']
			course.Module3 = self.session['Module3']
			course.put()
			# end new db code

			self.session['M3_Progress'] = 0
			doRender(self, "FinishPracticeFatigueEffects.htm")
		else:
			logging.info("something is wrong")


class WithinSubjectHandler(webapp.RequestHandler):
	def get(self):
		self.session = get_current_session()
		logging.info('TEST')
		courseObj = db.Query(StudentCourse).filter(
			'courseNumber =', self.session['activeCourse']).filter(
			'usernum =', self.session['usernum']).get()

		logging.info('MODULE 2: '+str(self.session['Module2']))

		self.session['M2_Progress'] = 0
		# progress variables are session-level, not db-level
		# if they logout and log back in, they'll have to start over

		doRender(self, "WithinSubjectIntro.htm",
			{'progress':self.session['M2_Progress'],
			'introProgress':0})


	def post(self):
		logging.info("checkpoint 1")
		self.session = get_current_session()
		direction = self.request.get('directioninput')

		M2_Progress = int(self.request.get('progressinput'))
		self.session['M2_Progress'] = M2_Progress
		logging.info("Progress: "+str(M2_Progress))

		if M2_Progress == 0:
			doRender(self, "WithinSubjectIntro.htm",
				{'progress':self.session['M2_Progress'],
				'introProgress':3})

		elif M2_Progress == 1:
			if direction == 'forward':

				# Record things from intro (answers to questions)
				self.session['WSAnswer1'] = self.request.get('Q1')
				self.session['WSAnswer2'] = self.request.get('Q2')
				self.session['numberOfGuesses'] = int(
					self.request.get('guessesinput'))

				pValues1 = [[0,0,0,0]] * 50
				sigTally1 = [[0,0,0,0]] * 50

				f = open('pValues1.csv', 'rU')
				mycsv = csv.reader(f)
				mycsv = list(mycsv)

				for x in range(0,50):
					pValues1[x] = [
						float(mycsv[x][0]),
						float(mycsv[x][1]),
						float(mycsv[x][2]),
						float(mycsv[x][3])]

					sigTally1[x] = [
						int(mycsv[x][4]),
						int(mycsv[x][5]),
						int(mycsv[x][6]),
						int(mycsv[x][7])]

				self.session['pValues1'] = pValues1
				self.session['sigTally1'] = sigTally1

				doRender(self, "WithinSubjectSim1.htm",
					{'progress':self.session['M2_Progress'],
					'pValues1':pValues1,
					'sigTally1':sigTally1,
					'sim1Progress':0})
			else:
				# Record things from intro (answers to questions)

				pValues1 = [[0,0,0,0]] * 50
				sigTally1 = [[0,0,0,0]] * 50

				f = open('pValues1.csv', 'rU')
				mycsv = csv.reader(f)
				mycsv = list(mycsv)

				for x in range(0,50):
					pValues1[x] = [
						float(mycsv[x][0]),
						float(mycsv[x][1]),
						float(mycsv[x][2]),
						float(mycsv[x][3])]

					sigTally1[x] = [
						int(mycsv[x][4]),
						int(mycsv[x][5]),
						int(mycsv[x][6]),
						int(mycsv[x][7])]

				self.session['pValues1'] = pValues1
				self.session['sigTally1'] = sigTally1

				doRender(self, "WithinSubjectSim1.htm",
					{'progress':self.session['M2_Progress'],
					'pValues1':pValues1,
					'sigTally1':sigTally1,
					'sim1Progress':3})

		elif M2_Progress == 2:
			# Record things from sim 1
			self.session['WSAnswer3'] = self.request.get('Q3')
			self.session['numberOfSimulations'] = int(
				self.request.get('numbersims'))

			pValues2 = [[0,0]] * 50
			sigTally2 = [[0,0]] * 50
			correlations = [[0,0]] * 50

			f = open('pValues2.csv', 'rU')
			mycsv = csv.reader(f)
			mycsv = list(mycsv)

			for x in range(0,50):
				pValues2[x] = [
					float(mycsv[x][2]),
					float(mycsv[x][3])]

				sigTally2[x] = [
					int(mycsv[x][4]),
					int(mycsv[x][5])]

				correlations[x] = [
					float(mycsv[x][0]),
					float(mycsv[x][1])]


			doRender(self, "WithinSubjectSim2.htm",
				{'progress':self.session['M2_Progress'],
				'pValues2':pValues2,
				'sigTally2':sigTally2,
				'correlations':correlations})

		elif M2_Progress == 3:
			# Record things from sim 2
			self.session['numberOfSimulations2'] = int(
				self.request.get('numbersims2'))

			doRender(self, "WithinSubjectQuiz.htm",
				{'progress':self.session['M2_Progress']})

		elif M2_Progress == 4:
			# Record results of final quiz
			QuizResults = self.request.get('AnswerInput')
			QuizResults = map(str,QuizResults.split(","))

			self.session['QuizResults'] = QuizResults

			# Record that user completed the module
			self.session['Module2'] = 'Complete'

			# Query the datastore
			course = db.Query(StudentCourse).filter(
				'usernum =', self.session['usernum']).filter(
				'courseNumber =', self.session['activeCourse']).get()

			# change the datastore result for module 2

			course.WSAnswer1 = self.session['WSAnswer1']
			course.WSAnswer2 = self.session['WSAnswer2']
			course.WSAnswer3 = self.session['WSAnswer3']
			course.numberOfGuesses = self.session['numberOfGuesses']
			course.numberOfSimulations = self.session['numberOfSimulations']
			course.numberOfSimulations2 = self.session['numberOfSimulations2']
			course.QuizResults = self.session['QuizResults']
			course.Module2 = self.session['Module2']
			course.put()

			logging.info('Datastore updated')

			self.session['M2_Progress'] = 0
			doRender(self, "FinishWithinSubjects.htm")

		elif M2_Progress < 0:
			M2_Progress += 1
			doRender(self, 'menu.htm',
				{'firstName':self.session['firstName'],
				'Module1':self.session['Module1'],
				'Module2':self.session['Module2']})

		else:
			logging.info("something is wrong")


class LineGraphTestHandler(webapp.RequestHandler):
	def get(self):
		# condition, x, y = readData('test',1)
		doRender(self, 'linegraph2.htm')
			# {'condition' : condition,
			# 'x' : x,
			# 'y' : y})

	# ASK KEVIN: do we still need this?

	# In this handler, add all the progress/back-end stuff, so that the first
	# page rendered is the overall experiment description.
	# It should then cycle through the pages to the parts with graphs and stuff.


###############################################################################
######################### Data Display Page Handler ###########################
###############################################################################

# this is going to go away since I have the one with CourseData.htm
# class DataHandler(webapp.RequestHandler):
# 	def get(self):
#
# 		doRender(self, 'datalogin.htm')
#
#
# 	def post(self):
# 		password=self.request.get('password')
#
# 		if password == "Bensei": # just for now
#
#
# 			que=db.Query(User)
# 			que.order("usernum")
# 			users=que.fetch(limit=10000)
#
# 			doRender(
# 				self,
# 				'data.htm',
# 				{'users':users})
# 		else:
# 			doRender(self, 'dataloginfail.htm')



###############################################################################
###################### Instructor Sign Up Page Handler ########################
###############################################################################

class InstructorSignupHandler(webapp.RequestHandler):

	def post(self):
		# modify this so you can't create an account if your email is listed!

		self.session = get_current_session()

		firstName = self.request.get('firstName')
		lastName = self.request.get('lastName')
		email = self.request.get('createEmail')
		password = self.request.get('password1')
		courseNumbers = []
		courseNames = []


		# create new instructor
		# Check whether user already exists
		que = db.Query(Instructor)
		que = que.filter('email =', email)
		results = que.fetch(limit=1)

		# If the user already exists in the datastore
		if len(results) > 0:
			doRender(self,
				'signupfail.htm',
				{'error': 'This account already exists. Please contact \
				administrator if you need to reset your password.'})
			return


		# Create User object in the datastore
		usernum = create_or_increment_NumOfUsers()
		newuser = Instructor(usernum=usernum,
			firstName=firstName,
			lastName=lastName,
			email = email,
			courseNumbers = courseNumbers,
			courseNames = courseNames,
			password=password);

		userkey = newuser.put()

		newuser.put()


		# store these variables in the session, log user in
		self.session = get_current_session()
		self.session['usernum']    	= usernum
		self.session['firstName']	= firstName
		self.session['lastName']	= lastName
		self.session['email']		= email
		self.session['Logged_In']	= True
		self.session['courseNumbers'] = courseNumbers
		self.session['courseNames'] = courseNames

		doRender(self, 'courseMenuInstructor.htm',
			{'firstName':self.session['firstName'],
			'courseNames': self.session['courseNames']})

###############################################################################
######################## Instructors Logging In and Out #######################
###############################################################################

class InstructorLoginHandler(webapp.RequestHandler):
	def get(self):
		logging.info('TEST TEST TEST')
		doRender(self, 'InstructorLogin.htm',
			{'errorNumber':0})

	def post(self):
		self.session = get_current_session()

		email = str(self.request.get('loginEmail'))
		password = str(self.request.get('loginPassword'))

		logging.info('EMAIL: '+email)



		# Check whether user already exists
		que = db.Query(Instructor)
		que = que.filter('email =', email)
		results = que.fetch(limit=1)

		# If the user does not already exist in the datastore
		if len(results) == 0:
			killSession(self)
			doRender(self, 'InstructorLogin.htm',
				{'errorNumber':1})
			return

		# user exists if we made it this far

		# check password
		for i in results:
			p = i.password

		if password != p:
			killSession(self)
			doRender(self, 'InstructorLogin.htm',
				{'errorNumber':2})
			return

		# email/password combo is correct if we made it this far
		# store these variables in the session, log user in
		for j in results: # even though there's only 1
			self.session['usernum']    		= j.usernum
			self.session['firstName']		= j.firstName
			self.session['lastName']		= j.lastName
			self.session['email']			= j.email
			self.session['courseNumbers']	= j.courseNumbers
			self.session['courseNames']		= j.courseNames
			self.session['Logged_In']		= True


		# for each course number, run a query, get the term

		terms = []
		years = []
		for i in self.session['courseNumbers']:
			q = db.Query(Course).filter('courseNumber =', i)
			r = q.get()

			terms.append(r.term)
			years.append(r.year)

		# this is the ugliest solution, but it works
		a = ''
		for i in self.session['courseNames']:
			a+=i+','

		t = ''
		for i in terms:
			t+=i+','

		y = ''
		for i in years:
			y+=i+','

		doRender(self, 'courseMenuInstructor.htm',
			{'firstName':self.session['firstName'],
			'courseNames': a,
			'terms':t,
			'years':y})


class CreateCourseHandler(webapp.RequestHandler):
	def get(self):
		self.session = get_current_session()

		# get instructor's current courses, send to page to make sure they don't
		# create one they already have.
		q = db.Query(Course).filter('instructorEmail =', self.session['email'])
		results = q.fetch(limit=100)

		logging.info('There are '+ str(len(results)) + ' classes for ' +
			self.session['email'])

		names = []
		terms = []
		years = []

		for i in results: # This should keep them in order
			logging.info('Course Name: '+str(i.courseName) + ', '+str(i.term) +
				' ' + str(i.year))
			names.append(i.courseName)
			terms.append(i.term)
			years.append(i.year)

		names = map(str, names) # trying to get around "u" in front of strings
		terms = map(str, terms)
		years = map(str, years)

		a = ''
		for i in names:
			a+=i+','
		nameString = a

		a = ''
		for i in terms:
			a+=i+','
		termString = a

		a = ''
		for i in years:
			a+=i+','
		yearString = a

		doRender(self, 'createCourse.htm',
			{'firstName':self.session['firstName'],
			'courseNames':nameString,
			'terms': termString,
			'years': yearString})

	def post(self):
		self.session = get_current_session()

		logging.info('TEST')
		# details about the course:
		termWithYear = self.request.get('termInput')
		term = termWithYear.split(' ')[0]
		year = termWithYear.split(' ')[1]
		courseName = self.request.get('courseNameInput')

		# prevent adding duplicate on refresh:
		que = db.Query(Course).filter(
			'instructorEmail =', self.session['email'])
		que.filter('term =', term).filter('year =', year).filter(
			'courseName =', courseName)
		r = que.fetch(limit=1)

		if len(r) > 0: # if it's already in the datastore
			logging.info('Course name: '+courseName)
			logging.info('The course is already in the datastore')

			# get the most current list of courses to send to the front end
			que = db.Query(Course).filter(
				'instructorEmail =', self.session['email'])
			results = que.fetch(limit=100)

			names = []
			numbers = []
			terms = []
			years = []

			for i in results: # This should keep them in order
				names.append(i.courseName)
				numbers.append(i.courseNumber)
				terms.append(i.term)
				years.append(i.year)

			# save to session (bring session up to date with datastore)
			self.session['courseNames'] = names
			self.session['courseNumbers'] = numbers

			# this is the ugliest solution, but it works
			a = ''
			for i in self.session['courseNames']:
				a+=i+','

			t = ''
			for i in terms:
				t+=i+','

			y = ''
			for i in years:
				y+=i+','

			doRender(self, 'courseMenuInstructor.htm',
				{'firstName':self.session['firstName'],
				'courseNames': a,
				'terms':t,
				'years':y})

		else:
			# if it's not already in the datastore, we need to:

			# 1. Get list of existing course names and numbers
			# 2. Append session arrays so we can render the next page
			# 3. Write course to the datastore (instructor and course models)


			# 1. Get list of existing courses (names, terms, and numbers)
			self.session['courseNumbers'] = db.Query(Instructor).filter(
				'email =', self.session['email']).get().courseNumbers

			q = db.Query(Course).filter(
				'courseNumber IN', self.session['courseNumbers'])
			results = q.fetch(limit = 100) # arbitrary, don't expect to hit it

			names = []
			numbers = []
			terms = []
			years = []
			for i in results: # This should keep them in order
				names.append(i.courseName)
				numbers.append(i.courseNumber)
				terms.append(i.term)
				years.append(i.year)

			# 2a. append the newest course name/number

			# create course number
			results = [1,2,3]

			while len(results) > 0: # prevent duplicate numbers in the datastore
				courseNumber = random.randint(10000000,99999999)

				que = db.Query(Course).filter('courseNumber =', courseNumber)
				results = que.fetch(limit=1)

			names.append(courseName) # from above self.request.get() function
			numbers.append(courseNumber)
			terms.append(term) # from above self.request.get() function
			years.append(year) # from above self.request.get() function

			self.session['courseNames'] = names
			self.session['courseNumbers'] = numbers


			# 2b. Prep these arrays to go to the front end.
			# because of problems with arrays of strings in django,
			# I'm converting each to one long string

			# for each course number, run a query, get the term

			# this is the ugliest solution, but it works
			a = ''
			for i in self.session['courseNames']:
				a+=i+','

			t = ''
			for i in terms:
				t+=i+','

			y = ''
			for i in years:
				y+=i+','

			# 3a. Add course to instructor object
			que = db.Query(Instructor)
			que = que.filter('email =', self.session['email'])
			obj = que.get()

			obj.courseNumbers.append(courseNumber)
			obj.courseNames.append(courseName)

			obj.put()


			# 3b. Add new course object
			# add course to the datastore
			instructor = ', '.join(
				[self.session['lastName'],
				self.session['firstName']])

			email = self.session['email']
			roster = ['']

			# specific modules for this course
			moduleList = []

			WSC = self.request.get('WSC')
			CEC = self.request.get('CEC')
			PFEC = self.request.get('PFEC')

			if WSC == '1':
				moduleList.append("WithinSubject")
			if CEC == '1':
				moduleList.append("CarryoverEffects")
			if PFEC == '1':
				moduleList.append("PracticeFatigueEffects")

			logging.info('Name: ' + courseName)
			logging.info('modules: ' + ', '.join(moduleList))


			newCourse = Course(
				term = term,
				year = year,
				courseNumber = courseNumber,
				instructor = instructor,
				instructorEmail = email,
				roster = roster,
				courseName = courseName,
				moduleList = moduleList)

			newCourse.put()


			logging.info('line 1300ish')
			doRender(self, 'courseMenuInstructor.htm',
				{'firstName':self.session['firstName'],
				'courseNames': a,
				'terms':t,
				'years':y})


class CourseDataHandler(webapp.RequestHandler):
	def get(self):
		self.session = get_current_session()

		# This handler should query the datastore to get data from the class

		# querying STUDENT data, limiting it to the course we care about
		courseInfo = self.request.get('courseSelect').split(' -- ')

		# split it up:
		courseName = courseInfo[0]
		termYear = courseInfo[1].split(' ')
		term = termYear[0]
		year = termYear[1]

		logging.info('Course Name: '+courseName)

		q = db.Query(Course).filter('instructorEmail =', self.session['email'])
		q.filter('courseName =', courseName).filter(
			'year =', year).filter('term =', term)

		results = q.fetch(limit=1)

		for i in results:
			courseNumber = i.courseNumber

		# Each time a student registers for a class, new StudentCourse instance.
		# Modify it as they complete the course.
		q = db.Query(StudentCourse).filter('courseNumber =', courseNumber)
		data = q.fetch(limit=1000) # arbitrarily high, probably never get

		doRender(self, 'CourseData.htm',
			{'users':data,
			'courseName': courseName,
			'term': term,
			'year':year,
			'courseNumber':courseNumber})








###############################################################################
############################### MainAppLoop ###################################
###############################################################################

application = webapp.WSGIApplication([
	# old pages (might not need)
	# ('/data', DataHandler),
	# ('/signup', SignupHandler),
	# ('/MainMenu', MainMenuHandler),

	# module pages
	('/CarryoverEffects', CarryoverEffectsHandler),
	('/WithinSubject', WithinSubjectHandler),
	('/PracticeFatigueEffects', PracticeFatigueEffectsHandler),
	('/LineGraphTest', LineGraphTestHandler),

	# student pages
	('/StudentSignup', StudentSignupHandler),
	('/StudentLogin', StudentLoginHandler),
	('/StudentCourseMenu', StudentCourseMenuHandler),
	('/EnrollCourse', EnrollCourseHandler),


	# instructor pages
	('/InstructorSignup', InstructorSignupHandler),
	('/InstructorLogin', InstructorLoginHandler),
	('/CourseData', CourseDataHandler),
	('/CreateCourse', CreateCourseHandler),


	# combined pages
	('/login', LoginHandler),
	('/logout', LogoutHandler),

	('/.*',  LoginHandler)],  #default page
	debug=True)

def main():
		run_wsgi_app(application)

if __name__ == '__main__':
	main()
