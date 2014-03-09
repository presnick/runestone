db.define_table('assignments',
	Field('course',db.courses),
	Field('name', 'string'),
	Field('points', 'integer'),
	Field('grade_type', 'string', default="additive", requires=IS_IN_SET(['additive','checkmark'])),
	Field('threshold', 'integer', default=1),
	format='%(name)s',
	migrate='runestone_assignments.table'
	)

def assignment_get_problems(assignment, user=None):
	if user:
		q = db(db.problems.acid == db.scores.acid)
		q = q(db.problems.assignment == assignment.id)
		q = q(db.scores.auth_user == user.id)
		scores = q.select(
			db.scores.ALL,
			orderby=db.scores.acid,
			)
		return scores
	problems = db(db.problems.assignment == assignment.id).select(
		db.problems.ALL,
		orderby=db.problems.acid
		)
	return problems
db.assignments.problems = Field.Method(lambda row, user=None: assignment_get_problems(row.assignments, user))
def assignment_set_grade(assignment, user):
	# delete the old grades; we're regrading
	db(db.grades.assignment == assignment.id)(db.grades.auth_user == user.id).delete()
	
	points = 0.0
	for prob in assignment.problems(user):
		if not prob.score:
			continue
		points = points + prob.score

	if assignment.grade_type == 'checkmark':
		#threshold grade
		if points >= assignment.threshold:
			points = assignment.points
		else:
			points = 0
	else:
		# they got the points they earned
		pass

	db.grades.insert(
		auth_user = user.id,
		assignment = assignment.id,
		score = points,
		)
	return points
db.assignments.grade = Field.Method(lambda row, user: assignment_set_grade(row.assignments, user))
def assignment_get_grades(assignment, section_id=None, problem=None):
	""" Return a list of users with grades for assignment (or problem) """
	if problem:
		return problems_get_scores(problem, section_id)
	if section_id:
		section_users = db((db.sections.id==db.section_users.section) & (db.auth_user.id==db.section_users.auth_user))
		users = section_users(db.auth_user.course_id == assignment.course)
		users = users(db.sections.id == section_id)
	else:
		users = db(db.auth_user.course_id == assignment.course)
	users = users.select(
		db.auth_user.ALL,
		orderby = db.auth_user.last_name,
		)
	if problem:
		grades = db(db.scores.acid == problem).select(db.scores.ALL)
	else:
		grades = db(db.grades.assignment == assignment.id).select(db.grades.ALL)
	for u in users:
		u.score = None
		u.comment = ""
		for g in grades:
			if g.auth_user.id == u.id:
				u.score = g.score
	return users
def problems_get_scores(problem, section_id=None):
	rows = db(db.scores.auth_user == db.auth_user.id)
	if section_id:
		rows = rows((db.sections.id==db.section_users.section) & (db.auth_user.id==db.section_users.auth_user))
		rows = rows(db.sections.id == section_id)
	rows = rows(db.scores.acid == problem)
	rows = rows.select(
		db.auth_user.ALL,
		db.scores.ALL,
		orderby = db.auth_user.last_name,
		)
	users = []
	for row in rows:
		user = row.auth_user
		user.score = row.scores.score
		user.comment = row.scores.comment
		users.append(user)
	return users
db.assignments.grades_get = Field.Method(lambda row, section=None, problem=None: assignment_get_grades(row.assignments, section, problem))

db.define_table('problems',
	Field('assignment',db.assignments),
	Field('acid','string'),
	migrate='runestones_problems.table',
	)

db.define_table('scores',
	Field('acid','string'),
	Field('auth_user',db.auth_user),
	Field('score','double'),
	Field('comment','string'),
	Field('released','boolean'),
	migrate='runestone_scores.table',
	)

db.define_table('grades',
	Field('auth_user', db.auth_user),
	Field('assignment', db.assignments),
	Field('score', 'double'),
	Field('released','boolean'),
	migrate='runestone_grades.table',
	)

db.define_table('deadlines',
	Field('assignment', db.assignments, requires=IS_IN_DB(db,'assignments.id',db.assignments._format)),
	Field('section', db.sections, requires=IS_EMPTY_OR(IS_IN_DB(db,'sections.id','%(name)s'))),
	Field('deadline','datetime'),
	migrate='runestone_deadlines.table',
	)