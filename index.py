import os, logging, wsgiref.handlers, datetime, random, math, string, urllib, csv, json

from google.appengine.ext import webapp, db
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template 
from gaesessions import get_current_session
from google.appengine.api import urlfetch




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
	courseNumbers = 			db.ListProperty(int) # to allow for multiple courses

class Course(db.Model):
	term = 				db.StringProperty()
	year = 				db.StringProperty()
	courseNumber = 		db.IntegerProperty()
	instructor = 		db.StringProperty()
	instructorEmail =	db.StringProperty()
	roster = 			db.ListProperty(str) 
	courseName =		db.StringProperty()
	moduleList = 		db.ListProperty(str) # list of modules in this course. For now this is inactive, we just assume they'll use all three.


class StudentCourse(db.Model): # student/course combination, when a student adds a course this object is created.
	# student linked
	usernum = 			db.IntegerProperty()

	# course linked
	courseNumbers = 		db.IntegerProperty()

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
#https://developers.google.com/appengine/docs/python/datastore/modelclass#Model_get_or_insert
class NumOfUsers(db.Model):
	counter = db.IntegerProperty(default=0)


#Increments NumOfUsers ensuring strong consistency in the datastore
@db.transactional
def create_or_increment_NumOfUsers():
	obj = NumOfUsers.get_by_key_name('NumOfUsers', read_policy=db.STRONG_CONSISTENCY)
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
#http://stackoverflow.com/questions/16004135/python-gae-assert-typedata-is-stringtype-write-argument-must-be-string
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

def killSession(self):
	# kill all the session stuff that would identify them (username, password, etc)
	sessionlist = ['Logged_In', 'email', 'firstName', 'usernum', 'username', 'Module1', 'Module2', 'Module3', 'Logged_In', 'M1_Progress', 'M2_Progress', 'M3_Progress']

	for i in sessionlist:
		if i in self.session:
			self.session.__delitem__(i)



###############################################################################
###############################################################################
################################## Handlers! ##################################
###############################################################################
###############################################################################

###############################################################################
########################### Student Page Handlers #############################
###############################################################################

class SignupHandler(webapp.RequestHandler):
	def get(self):
		doRender(self, 'signup.htm')

	def post(self):
		self.session = get_current_session()
			
		firstName = self.request.get('firstName')
		lastName = self.request.get('lastName')
		email = self.request.get('email')
		role = self.request.get('roleSelect')
		password = self.request.get('password1')

		# courseNumbers = self.request.get('courseNumbers')
		

		logging.info('ROLE '+role)
		if role == 'Student':
	

			# Check whether user already exists
			que = db.Query(Student)
			que = que.filter('email =', email)
			results = que.fetch(limit=1)

			# If the user already exists in the datastore
			if (len(results) > 0) & (str(firstName) != 'test'):
				doRender(self,
					'signupfail.htm',
					{'error': 'This account already exists. Please contact your instructor if you need to reset your password.'})
				return


			# firstName = 		db.StringProperty()
			# lastName = 			db.StringProperty()
			# email = 			db.StringProperty()
			# password =			db.StringProperty()
			# usernum = 			db.IntegerProperty()
			# courses = 			db.ListProperty(int) # to allow for multiple courses

			# Create User object in the datastore
			usernum = create_or_increment_NumOfUsers()
			newuser = Student(usernum=usernum, 
				firstName=firstName,
				lastName=lastName,
				email = email,
				password=password,
				# modules are at the course level? So here we should have an empty array of course numbers.
				# Module1="Incomplete", 
				# Module2="Incomplete",
				# Module3="Incomplete"
				courses = []);
			
			userkey = newuser.put()
			
			newuser.put();

			# store these variables in the session, log user in
			self.session = get_current_session() 
			self.session['usernum']    	= usernum
			self.session['firstName']	= firstName
			self.session['courseNumbers'] 	= []
			self.session['email']		= email
			# self.session['Module1']   = 'Incomplete'
			# self.session['Module2']  	= 'Incomplete'
			# self.session['Module3']  	= 'Incomplete'
			self.session['Logged_In']	= True
			# self.session['M1_Progress'] = 0
			# self.session['M2_Progress'] = 0
			# self.session['M3_Progress'] = 0

			doRender(self, 'courseMenu.htm',
				{'firstName':self.session['firstName'],
				'courseNumbers': self.session['courseNumbers']})
		else:
			# create new instructor
			# Check whether user already exists
			que = db.Query(Instructor)
			que = que.filter('email =', email)
			results = que.fetch(limit=1)

			# If the user already exists in the datastore
			if (len(results) > 0) & (firstName != 'Cory'):
				doRender(self,
					'signupfail.htm',
					{'error': 'This account already exists. Please contact administrator if you need to reset your password.'})
				return


class LoginHandler(webapp.RequestHandler):
	def get(self):
		self.session = get_current_session()
		
		self.session['M1_Progress'] = 0
		self.session['M2_Progress'] = 0
		self.session['M3_Progress'] = 0

		

		# logging.info(Logged_In)
		# If they're logged in, take them to the main menu
		if 'Logged_In' in self.session:
			if self.session['Logged_In'] == True:
				courses = self.session['courseNumbers']
				doRender(self, 'courseMenu.htm',
					{'firstName':self.session['firstName'],
					'courseNumbers': courses})

			else:
				doRender(self, 'login.htm')
		# If they aren't, take them to the login page
		else:
			self.session['Logged_In'] = False
			doRender(self, 'login.htm')

	def post(self):
		return
		# self.session = get_current_session()
		
		# # if guest
		# if self.request.get('userType') == 'guest':
		# 	usernum = create_or_increment_NumOfUsers()
		# 	username = str('Guest'+str(usernum))

		# 	logging.info('USERNAME: '+username)

		# 	firstName = 'Guest'
		# 	lastName = 'Guest'
		# 	instructor = 'Guest'

		# 	self.session = get_current_session() 
		# 	self.session['usernum']    	= usernum
		# 	self.session['username']   	= username
		# 	self.session['firstName']	= firstName
		# 	# self.session['password']    = password1
		# 	self.session['Module1']   	= 'Incomplete'
		# 	self.session['Module2']  	= 'Incomplete'
		# 	self.session['Module3']  	= 'Incomplete'
		# 	self.session['Logged_In']	= True
		# 	self.session['M1_Progress'] = 0
		# 	self.session['M2_Progress'] = 0
		# 	self.session['M3_Progress'] = 0

		# 	newuser = Student(usernum=usernum, 
		# 		username=username,
		# 		firstName=firstName,
		# 		lastName=self.request.get('lastName'),
		# 		# note: this is the manual input for term. Doesn't make sense at this point to have them do this themselves since it's all for Spring 2016
		# 		term='Spring 2016',
				
		# 		instructor=instructor,
		# 		# password=password1,
		# 		Module1="Incomplete",
		# 		Module2="Incomplete",
		# 		Module3="Incomplete");

		# 	userkey = newuser.put()
			
		# 	newuser.put();

		# 	doRender(self, 'courseMenu.htm',
		# 		{'firstName':self.session['firstName'],
		# 		'Module1':self.session['Module1'],
		# 		'Module2':self.session['Module2'],
		# 		'Module3':self.session['Module3']})



		# 	return

		# if self.request.get('userType') == 'student':
		# 	email = self.request.get('email')
		# 	# password = self.request.get('password')
			
		# 	# Check whether user already exists
		# 	que = db.Query(Student)
		# 	que = que.filter('email =', email)
		# 	results = que.fetch(limit=1)

		# 	# If user does not exist
		# 	if len(results) == 0:
		# 		doRender(self,
		# 			'loginfailed.htm',
		# 			{'error': 'This username does not exist'})
		# 		return

		# 	# Check if password matches password entry in datastore
		# 	# que = que.filter('password =', password)
		# 	# results = que.fetch(limit=1)

		# 	# # If password mismatch
		# 	# if len(results) == 0:
		# 	# 	doRender(self,
		# 	# 		'loginfailed.htm',
		# 	# 		{'error': 'Incorrect password'})
		# 	# 	return


		# 	# i is a list object (basically a row of data) in the datastore. This loop saves each relevant piece of info from our query into the session.
		# 	for i in results:
		# 		# self.session['username'] = i.username
		# 		# self.session['password'] = i.password
		# 		self.session['firstName'] = i.firstName
		# 		self.session['usernum'] = i.usernum
		# 		self.session['courseNumbers'] = i.courses
		# 		# self.session['Module1'] = i.Module1
		# 		# self.session['Module2'] = i.Module2
		# 		# self.session['Module3'] = i.Module3
			
		# 	# get course names
		# 	test = self.session['courseNumbers']

		# 	courseNames = []
		# 	for i in test:
		# 		que = db.Query(Course).filter("courseNumbers=", i)
		# 		results = que.fetch(limit = 1)

		# 		for j in results:
		# 			courseNames.append(j.courseName)

		# 	# self.session['M1_Progress'] = 0
		# 	# self.session['M2_Progress'] = 0
		# 	# self.session['M3_Progress'] = 0
		# 	self.session['Logged_In'] = True


		# 	json_list = json.dumps(courseNames)

		# 	doRender(self,'courseMenu.htm',
		# 		{'firstName':self.session['firstName'],
		# 		'courseNumbers':str(self.session['courseNumbers']),
		# 		'courseNames':json_list})

		# 	return

		# # STILL NEED TO CHANGE THIS ONE
		# if self.request.get('userType') == 'instructor':
		# 	email = self.request.get('email')
		# 	# password = self.request.get('password')
			
		# 	# Check whether user already exists
		# 	que = db.Query(Instructor)
		# 	que = que.filter('email =', email)
		# 	results = que.fetch(limit=1)

		# 	# If user does not exist
		# 	if len(results) == 0:
		# 		doRender(self,
		# 			'loginfailed.htm',
		# 			{'error': 'This username does not exist'})
		# 		return

		# 	# Check if password matches password entry in datastore
		# 	# que = que.filter('password =', password)
		# 	# results = que.fetch(limit=1)

		# 	# # If password mismatch
		# 	# if len(results) == 0:
		# 	# 	doRender(self,
		# 	# 		'loginfailed.htm',
		# 	# 		{'error': 'Incorrect password'})
		# 	# 	return


		# 	# i is a list object (basically a row of data) in the datastore. This loop saves each relevant piece of info from our query into the session.
		# 	for i in results:
		# 		# self.session['username'] = i.username
		# 		# self.session['password'] = i.password
		# 		self.session['firstName'] = i.firstName
		# 		self.session['usernum'] = i.usernum
		# 		self.session['courseNumbers'] = i.courses
		# 		# self.session['Module1'] = i.Module1
		# 		# self.session['Module2'] = i.Module2
		# 		# self.session['Module3'] = i.Module3
			
		# 	# get course names
		# 	test = self.session['courseNumbers']

		# 	courseNames = []
		# 	for i in test:
		# 		que = db.Query(Course).filter("courseNumbers=", i)
		# 		results = que.fetch(limit = 1)

		# 		for j in results:
		# 			courseNames.append(str(j.courseName))

		# 	# self.session['M1_Progress'] = 0
		# 	# self.session['M2_Progress'] = 0
		# 	# self.session['M3_Progress'] = 0
		# 	self.session['Logged_In'] = True


			
		# 	json_list = json.dumps(courseNames)

		# 	doRender(self,'courseMenuInstructor.htm',
		# 		{'firstName':self.session['firstName'],
		# 		'courseNumbers':str(self.session['courseNumbers']),
		# 		'courseNames':str(json_list)})

		# 	return

class EnrollCourseHandler(webapp.RequestHandler):
	def post(self):
		self.session = get_current_session()

		courseInput = self.request.get('courseInput')
		logging.info('COURSE NUMBER '+str(courseInput))
		# query database for this course

		que = db.Query(Course).filter('courseNumbers =', courseInput)
		results = que.fetch(limit=1)


		# If course does not exist
		if len(results) == 0:
			if int(courseInput) != 1:
				doRender(self,
					'loginfailed.htm',
					{'error': 'This course does not exist'})
			
			
		# get student object
		que = db.Query(Student)
		que = que.filter('usernum =', self.session['usernum'])
		student = que.fetch(limit = 1)

		# append course to student course property
		for i in student:
			test = i.courses
			if courseInput not in test:
				test.append(courseInput)
			logging.info('COURSE NUMBER (datastore): '+str(test))
			i.courses = test

			firstName = i.firstName
			lastName = i.lastName

			self.session['courseNumbers'] = i.courses
			# term = i.term
			# instructor = i.instructor

			i.put()

		# get existing list of course names and numbers (for next page)
		# numbers are "test" above
		courseNames = []
		for i in test:
			que = db.Query(Course).filter("courseNumbers=", i)
			results = que.fetch(limit = 1)

			for j in results:
				courseNames.append(j.courseName)

		logging.info('TEST VAR: '+str(test))

		# get course object
		que = db.Query(Course)
		que = que.filter('courseNumbers =', courseInput)
		course = que.fetch(limit = 1)

		studentName = str(lastName)+', '+str(firstName)

		logging.info("STUDENT NAME: "+str(studentName))

		# testing, b/c there isn't yet a course object in the datastore
		if courseInput == 1:
			term = 'Fall 2017'
			instructor = 'Rottman, Ben'
			courseName = 'Research Methods'

		else:
			for i in course:
				term = i.term
				instructor = i.instructor
				i.roster.append(studentName)
				courseName = i.courseName

				i.put()

		# test.append(courseInput)

		courseNumbers = test
		self.session['courseNumbers'] = courseNumbers
		courseNames.append(courseName)

		self.session['courseNumbers'] = [v for v in self.session['courseNumbers']]

		# create object for student/course combination
		newEnroll = StudentCourse(usernum=self.session['usernum'], 
			courseNumbers = courseInput,
			# note: this is the manual input for term. Doesn't make sense at this point to have them do this themselves since it's all for Spring 2016
			term=term,
			instructor=instructor);

		newEnroll.put();


		json_list = json.dumps(courseNames)

		doRender(self,
			'courseMenu.htm',
			{'courseNumbers': courseNumbers,
			'courseNames':json_list,
			'firstName': self.session['firstName']})
		

class MainMenuHandler(webapp.RequestHandler):
	def get(self):
		self.session = get_current_session()


		courseNumbers = int(self.request.get('courseNumbersInput'))

		logging.info('COURSE NUMBER: '+str(courseNumbers))


		doRender(self, "menu.htm",
			{'firstName': self.session['firstName'],
			'courseNumbers': self.session['courseNumbers'],
			'courseNumbers': courseNumbers})

###############################################################################
########################### Module Page Handlers ##############################
###############################################################################

class CarryoverEffectsHandler(webapp.RequestHandler):

	def get(self):
		self.session = get_current_session()
		if self.session['M1_Progress'] == 0:
			doRender(self, "CarryoverEffectsIntro.htm",
				{'progress':self.session['M1_Progress']})

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

			# Query the datastore
			que = db.Query(User)

			# find the current user
			que = que.filter('username =', self.session['username'])
			results = que.fetch(limit=1)

			# change the datastore result for module 1
			for i in results:
				i.COEAnswer1 = self.session['COEAnswer1']
				i.COEAnswer2 = self.session['COEAnswer2']
				i.COEAnswer3 = COEAnswer3
				i.COEAnswer4 = COEAnswer4
				i.COEAnswer5 = COEAnswer5
				i.Module1 = self.session['Module1']
				i.put()

			logging.info('Datastore updated')

			self.session['M1_Progress'] = 0
			doRender(self, "FinishCarryoverEffects.htm")
		else:
			logging.info("something is wrong")



class PracticeFatigueEffectsHandler(webapp.RequestHandler):

	def get(self):
		self.session = get_current_session()
		if self.session['M3_Progress'] == 0:
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
			PFEAnswer3 = int(self.request.get('Question1'))
			# PFEAnswer4 = int(self.request.get('Question2'))
			PFEAnswer5 = int(self.request.get('Question3'))

			# Record that user completed the module
			self.session['Module3'] = 'Complete'

			# Query the datastore
			que = db.Query(User)

			# find the current user
			que = que.filter('username =', self.session['username'])
			results = que.fetch(limit=1)

			# change the datastore result for module 1
			for i in results:
				i.PFEAnswer1 = self.session['PFEAnswer1']
				i.PFEAnswer2 = self.session['PFEAnswer2']
				# i.COEAnswer3 = self.session['COEAnswer3']
				i.PFEAnswer3 = PFEAnswer3
				i.PFEAnswer4 = PFEAnswer5
				# i.PFEAnswer5 = PFEAnswer5
				i.Module3 = self.session['Module3']
				i.put()

			logging.info('Datastore updated')

			self.session['M3_Progress'] = 0
			doRender(self, "FinishPracticeFatigueEffects.htm")
		else:
			logging.info("something is wrong")


class WithinSubjectHandler(webapp.RequestHandler):
	def get(self):
		self.session = get_current_session()
		if self.session['M2_Progress'] == 0:
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
				self.session['numberOfGuesses'] = int(self.request.get('guessesinput'))

				pValues1 = [[0,0,0,0]] * 50
				sigTally1 = [[0,0,0,0]] * 50
				
				f = open('pValues1.csv', 'rU')
				mycsv = csv.reader(f)
				mycsv = list(mycsv)   

				for x in range(0,50):
					pValues1[x] = [float(mycsv[x][0]), float(mycsv[x][1]), float(mycsv[x][2]), float(mycsv[x][3])]
					sigTally1[x] = [int(mycsv[x][4]), int(mycsv[x][5]), int(mycsv[x][6]), int(mycsv[x][7])]

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
					pValues1[x] = [float(mycsv[x][0]), float(mycsv[x][1]), float(mycsv[x][2]), float(mycsv[x][3])]
					sigTally1[x] = [int(mycsv[x][4]), int(mycsv[x][5]), int(mycsv[x][6]), int(mycsv[x][7])]

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
			self.session['numberOfSimulations'] = int(self.request.get('numbersims'))
			
			pValues2 = [[0,0]] * 50
			sigTally2 = [[0,0]] * 50
			correlations = [[0,0]] * 50

			f = open('pValues2.csv', 'rU')
			mycsv = csv.reader(f)
			mycsv = list(mycsv)

			for x in range(0,50):
				pValues2[x] = [float(mycsv[x][2]), float(mycsv[x][3])]
				sigTally2[x] = [int(mycsv[x][4]), int(mycsv[x][5])]
				correlations[x] = [float(mycsv[x][0]), float(mycsv[x][1])]


			doRender(self, "WithinSubjectSim2.htm",
				{'progress':self.session['M2_Progress'],
				'pValues2':pValues2,
				'sigTally2':sigTally2,
				'correlations':correlations})

		elif M2_Progress == 3:
			# Record things from sim 2
			self.session['numberOfSimulations2'] = int(self.request.get('numbersims2'))

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
			que = db.Query(User)

			# find the current user
			que = que.filter('username =', self.session['username'])
			results = que.fetch(limit=1)

			# change the datastore result for module 2
			for i in results:
				i.WSAnswer1 = self.session['WSAnswer1']
				i.WSAnswer2 = self.session['WSAnswer2']
				i.WSAnswer3 = self.session['WSAnswer3']
				i.numberOfGuesses = self.session['numberOfGuesses']
				i.numberOfSimulations = self.session['numberOfSimulations']
				i.numberOfSimulations2 = self.session['numberOfSimulations2']
				i.QuizResults = self.session['QuizResults']
				i.Module2 = self.session['Module2']
				i.put()

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


	# In this handler, add all the progress/back-end stuff, so that the first page rendered is the overall experiment description
	# It should then cycle through the pages to the other parts with graphs and stuff

		
###############################################################################
######################### Data Display Page Handler ###########################
###############################################################################

class DataHandler(webapp.RequestHandler):
	def get(self):

		doRender(self, 'datalogin.htm')


	def post(self):
		password=self.request.get('password')

		if password == "Bensei": # just for now


			que=db.Query(User)
			que.order("usernum")
			users=que.fetch(limit=10000)

			doRender(
				self, 
				'data.htm',
				{'users':users})
		else:
			doRender(self, 'dataloginfail.htm')
 


###############################################################################
###################### Instructor Sign Up Page Handler ########################
###############################################################################

class InstructorSignupHandler(webapp.RequestHandler):
	
	def post(self):
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
		if (len(results) > 0) & (firstName != 'Cory'):
			doRender(self,
				'signupfail.htm',
				{'error': 'This account already exists. Please contact administrator if you need to reset your password.'})
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
			'courseNumbers': self.session['courseNumbers'],
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
		

		# this is the ugliest solution, but it works
		a = ''
		for i in self.session['courseNames']:
			a+=i+','

		b = ''
		for i in self.session['courseNumbers']:
			b+=str(i)+','

		doRender(self, 'courseMenuInstructor.htm',
			{'firstName':self.session['firstName'],
			'courseNumbers': b,
			'courseNames': a})


class CreateCourseHandler(webapp.RequestHandler):
	def get(self):
		self.session = get_current_session()

		# get instructor's current courses, send to page to make sure they don't create one they already have
		q = db.Query(Course).filter('instructorEmail =', self.session['email'])
		results = q.fetch(limit=100)

		logging.info('There are '+ str(len(results)) + ' classes for ' + self.session['email'])

		names = []
		terms = []
		years = []

		for i in results: # This should keep them in order
			logging.info('Course Name: '+str(i.courseName) + ', '+str(i.term) + ' ' + str(i.year))
			names.append(i.courseName)
			terms.append(i.term)
			years.append(i.year)
	
		names = map(str, names) # this is how you get around "u" in front of strings
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
		que = db.Query(Course).filter('instructorEmail =', self.session['email'])
		que.filter('term =', term).filter('year =', year).filter('courseName =', courseName)
		r = que.fetch(limit=1)

		if len(r) > 0: # if it's already in the datastore
			logging.info('Course name: '+courseName)
			logging.info('The course is already in the datastore')

			# get the most current list of courses to send to the front end
			que = db.Query(Course).filter('instructorEmail =', self.session['email'])
			results = que.fetch(limit=100)

			names = []
			numbers = []

			for i in results: # This should keep them in order
				names.append(i.courseName)
				numbers.append(i.courseNumbers)

			# save to session (this just makes sure the session is up to date on the datastore)
			self.session['courseNames'] = names
			self.session['courseNumbers'] = numbers

			# this is the ugliest solution, but it works
			# course names
			a = ''
			for i in names:
				a+=i+','

			logging.info(a)

			# course numbers
			b = ''
			for i in numbers:
				b+=str(i)+','

			doRender(self, 'courseMenuInstructor.htm',
				{'firstName':self.session['firstName'],
				'courseNumbers': b,
				'courseNames': a})

		else:
			# if it's not already in the datastore, we need to:

			# 1. Get list of existing course names and numbers
			# 2. Append the session arrays for names and numbers so we can render the next page
			# 3. Write the new course to the datastore under the instructor and course models

			
			# 1. Get list of existing courses (names and numbers)
			q = db.Query(Course).filter('courseNumber IN', self.session['courseNumbers'])
			results = q.fetch(limit = 100) # arbitrary, don't expect to ever hit it

			names = []
			numbers = []
			for i in results: # This should keep them in order
				names.append(i.courseName)
				numbers.append(i.courseNumber)

			
			# 2a. append the newest course name/number

			# create course number			
			results = [1,2,3]

			while len(results) > 0: # prevents duplicate course numbers in the datastore
				# logging.info('LENGTH OF RESULTS: '+str(len(results)))
				courseNumber = random.randint(10000000,99999999)

				que = db.Query(Course).filter('courseNumber =', courseNumber)
				results = que.fetch(limit=1)

			names.append(courseName) # from above self.request.get() function
			numbers.append(courseNumber)

			self.session['courseNames'] = names
			self.session['courseNumbers'] = numbers

			# 2b. Prep these arrays to go to the front end.
			# because of problems with arrays of strings in django, I'm converting each to one long string

			# this is the ugliest solution, but it works
			a = ''
			for i in self.session['courseNames']:
				a+=i+','

			b = ''
			for i in self.session['courseNumbers']:
				b+=str(i)+','

			
			# 3a. Modify the instructor object add course to instructor object
			que = db.Query(Instructor)
			que = que.filter('email =', self.session['email'])
			obj = que.get()
			
			obj.courseNumbers.append(courseNumber)
			obj.courseNames.append(courseName)

			obj.put()


			# 3b. Add new course object
			# add course to the datastore
			instructor = ', '.join([self.session['lastName'], self.session['firstName']])
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
				'courseNumbers': b,
				'courseNames': a})


class CourseDataHandler(webapp.RequestHandler):
	def get(self):
		self.session = get_current_session()
		
		# This handler should query the datastore to get data from the selected class
		# for now set term to Spring 2018
		year = '2018'
		term = 'Spring'

		courseName = self.request.get('courseSelect')

		logging.info('Course Name: '+courseName)

		q = db.Query(Course).filter('instructorEmail =', self.session['email'])
		q.filter('courseName =', courseName).filter('year =', year).filter('term =', term)
		results = q.fetch(limit=1)
		


class LogoutHandler(webapp.RequestHandler):
	
	def get(self):	
		self.session = get_current_session()
		self.session['Logged_In'] = False	
		
		# kill all the session stuff that would identify them (username, password, etc)
		killSession(self)

		# Send them back to the login page
		doRender(self, 'login.htm')


		
###############################################################################
############################### MainAppLoop ###################################
###############################################################################

application = webapp.WSGIApplication([
	('/data', DataHandler),
	('/EnrollCourse', EnrollCourseHandler),
	('/CreateCourse', CreateCourseHandler),
	('/logout', LogoutHandler),
	('/login', LoginHandler),
	('/signup', SignupHandler),
	('/CarryoverEffects', CarryoverEffectsHandler),
	('/WithinSubject', WithinSubjectHandler),
	('/PracticeFatigueEffects', PracticeFatigueEffectsHandler),
	('/LineGraphTest', LineGraphTestHandler),
	('/CarryoverEffects', CarryoverEffectsHandler),
	('/MainMenu', MainMenuHandler),
	('/InstructorLogin', InstructorLoginHandler),
	('/CourseData', CourseDataHandler),
	('/InstructorSignup', InstructorSignupHandler),
	('/.*',  LoginHandler)],  #default page
	debug=True)

def main():
		run_wsgi_app(application)

if __name__ == '__main__':
	main()

