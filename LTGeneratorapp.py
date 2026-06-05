import importlib.util
import logging
import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
_PKG_NAME = "LTGenerator"


def _ensure_ltgenerator_package():
    """Make repo-root files importable as the LTGenerator package on Render."""
    if _PKG_NAME in sys.modules and hasattr(sys.modules[_PKG_NAME], "create_app"):
        return

    if os.path.basename(_ROOT) == _PKG_NAME:
        _parent = os.path.dirname(_ROOT)
        if _parent not in sys.path:
            sys.path.insert(0, _parent)
        return

    init_path = os.path.join(_ROOT, "__init__.py")
    spec = importlib.util.spec_from_file_location(
        _PKG_NAME,
        init_path,
        submodule_search_locations=[_ROOT],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[_PKG_NAME] = module
    spec.loader.exec_module(module)


_ensure_ltgenerator_package()

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from LTGenerator import create_app, db, Base
from flask import render_template, request, redirect, url_for, send_file, flash, jsonify
from LTGenerator.models import Instructor, Level, Session, Student, studentresults
from LTGenerator.print import print_general_fields, resolve_sheet_pdf_path
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

logging.basicConfig(level=logging.INFO)


def configure_database_from_env():
    """Map Render DATABASE_URL to SQLAlchemy before app initialization."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        return
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    os.environ["SQLALCHEMY_DATABASE_URI"] = database_url


configure_database_from_env()

# Initialize the Flask application and login manager
app = create_app()
is_debug = os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes")
app.config["TEMPLATES_AUTO_RELOAD"] = is_debug
app.config["DEBUG"] = is_debug
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User loader callback for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Instructor, user_id)


def studentrowsforsession(session_id, limit=8):
    trimmed = func.trim(Student.name)
    last_char = func.lower(func.right(trimmed, 1))
    rows = db.session.scalars(
        select(Student)
        .where(Student.sessionid == session_id)
        .order_by(last_char, Student.sid)
    ).all()
    rows = sorted(
        rows,
        key=lambda s: (s.name.strip()[-1].lower() if s.name.strip() else '', s.sid),
    )[:limit]
    return rows + [None] * (limit - len(rows))


# Main route
@app.route('/', methods=['GET', 'POST'])
def welcome():
    return render_template('welcome.html')  

# Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        iname = request.form.get('name')
        iemail = request.form.get('email')
        ipassword = request.form.get('password')
        iconfirm_password = request.form.get('confirm_password')
        if ipassword != iconfirm_password:
            error = "Passwords do not match. Please try again."
            return render_template('register.html', error=error)
        else:
                new_instructor = Instructor(
                    name=iname, 
                    email=iemail, 
                    password=ipassword)
                db.session.add(new_instructor)
                db.session.commit()
                return redirect(url_for('login'))
    return render_template('register.html')  

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        iemail = request.form.get('email')
        ipassword = request.form.get('password')
        instructor = db.session.scalar(db.select(Instructor).filter_by(email=iemail))
        if instructor and instructor.password == ipassword:
            if not instructor.is_approved:
                error = "Your account is pending approval. Please wait for an administrator to approve your account."
                return render_template('login.html', error=error)
            login_user(instructor)
            return render_template('dashboard.html')
        else:
            error = "Invalid email or password. Please try again."
            return render_template('login.html', error=error)
    return render_template('login.html')  

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('dashboard'))

# Dashboard route
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# New session route
@app.route('/newsession', methods=['GET', 'POST'])
@login_required
def newsession():
    levels = db.session.scalars(
        db.select(Level).order_by(Level.levelid.desc())
    ).all()

    if request.method == 'POST':
        level = int(request.form.get('level'))
        time = request.form.get('time')
        session_code = request.form.get('session_id')
        weekdays = request.form.get('weekdays')
        pool = request.form.get('pool')
        enrolled = int(request.form.get('enrolled'))

        evaluated_val = request.form.get('evaluated', '').strip()
        evaluated = int(evaluated_val) if evaluated_val else None

        completed_val = request.form.get('completed', '').strip()
        completed = int(completed_val) if completed_val else 0

        incomplete_val = request.form.get('incomplete', '').strip()
        incomplete = int(incomplete_val) if incomplete_val else 0

        new_session = Session(
            iid=current_user.iid,
            time=time,
            session=session_code,
            weekdays=weekdays,
            pool=pool,
            levelid=level,
            enrolled=enrolled,
            evaluated=evaluated,
            completed=completed,
            incomplete=incomplete
        )
        db.session.add(new_session)
        db.session.commit()
        return redirect(url_for('newsession'))

    return render_template('newsession.html', levels=levels)

# Select session route
@app.route('/selectsession')
@login_required
def selectsession():
    sessions = db.session.scalars(db.select(Session).filter_by(iid=current_user.iid)).all()
    levels = db.session.scalars(db.select(Level)).all()
    return render_template('selectsession.html', sessions=sessions, levels=levels)


def deletestudentrecord(student):
    db.session.delete(student)
    db.session.flush()


def saveeditsessionform(sess, session_id, skills):
    sess.session  = request.form.get('session_code') or sess.session
    sess.weekdays = request.form.get('weekdays') or sess.weekdays
    sess.time     = request.form.get('time') or sess.time
    sess.pool     = request.form.get('pool') or sess.pool
    for attr, key in [('enrolled', 'enrolled'), ('evaluated', 'evaluated'),
                      ('completed', 'completed'), ('incomplete', 'incomplete')]:
        val = request.form.get(key, '').strip()
        if val.isdigit():
            setattr(sess, attr, int(val))

    for i in range(1, 9):
        name    = request.form.get(f'student{i}', '').strip()
        status  = request.form.get(f'student{i}_result', '').strip() or 'enrolled'
        sid_raw = request.form.get(f'student{i}_sid', '').strip()

        student = None
        if sid_raw.isdigit():
            candidate = db.session.get(Student, int(sid_raw))
            if candidate and candidate.sessionid == session_id:
                student = candidate

        if not name:
            if student is not None:
                deletestudentrecord(student)
            continue

        if student is None:
            student = Student(name=name, sessionid=session_id, status=status)
            db.session.add(student)
            db.session.flush()
        else:
            student.name   = name
            student.status = status

        for skill in skills:
            checked    = request.form.get(f'student{i}_skill{skill.skillid}') is not None
            result_val = 'C' if checked else 'I'
            stmt = pg_insert(studentresults).values(
                sid=student.sid, skillid=skill.skillid, result=result_val
            ).on_conflict_do_update(
                index_elements=['sid', 'skillid'],
                set_={'result': result_val}
            )
            db.session.execute(stmt)

    db.session.commit()
    db.session.expire_all()


def editsessioncontext(sess):
    clevel = sess.Level
    skills = clevel.skills
    students = studentrowsforsession(sess.sessionid)
    results_map = {
        idx: ({r.skillid: r.result for r in s.studentresults} if s else {})
        for idx, s in enumerate(students)
    }
    return dict(
        swim_session=sess,
        clevel=clevel,
        skills=skills,
        skillcount=len(skills) + 18,
        students=students,
        results_map=results_map,
    )


# Edit session route
@app.route('/editsession/<int:session_id>', methods=['GET', 'POST'])
@login_required
def editsession(session_id):
    sess = db.session.get(Session, session_id)
    if sess is None:
        flash('Session not found.', 'error')
        return redirect(url_for('selectsession'))

    if request.method == 'POST':
        skills = sess.Level.skills
        saveeditsessionform(sess, session_id, skills)
        return redirect(url_for('editsession', session_id=session_id))

    ctx = editsessioncontext(sess)
    response = app.make_response(render_template('editsession.html', **ctx))
    response.headers['Cache-Control'] = 'no-store'
    return response


@app.route('/editsession/<int:session_id>/student/<int:sid>/delete', methods=['POST'])
@login_required
def editsessiondeletestudent(session_id, sid):
    sess = db.session.get(Session, session_id)
    if sess is None:
        return jsonify({'error': 'Session not found.'}), 404

    student = db.session.get(Student, sid)
    if student is None or student.sessionid != session_id:
        return jsonify({'error': 'Student not found.'}), 404

    deletestudentrecord(student)
    db.session.commit()
    return jsonify({'ok': True})


@app.route('/editsession/<int:session_id>/print', methods=['POST'])
@login_required
def editsessionprint(session_id):
    sess = db.session.get(Session, session_id)
    if sess is None:
        return jsonify({'error': 'Session not found.'}), 404

    ctx = editsessioncontext(sess)
    clevel = ctx['clevel']

    try:
        saveeditsessionform(sess, session_id, ctx['skills'])
        pdf_path = resolve_sheet_pdf_path(app.root_path, clevel)
        db.session.refresh(sess)
        form_rows = [
            {
                'name': request.form.get(f'student{i}', '').strip(),
                'sid': request.form.get(f'student{i}_sid', '').strip(),
            }
            for i in range(1, 9)
        ]
        buf = print_general_fields(pdf_path, sess, form_rows=form_rows)
        safe_level = clevel.name.replace(' ', '_')
        filename   = f"{sess.session}_{safe_level}.pdf"
        return send_file(
            buf,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename,
        )
    except Exception as exc:
        app.logger.exception('Print failed for session %s', session_id)
        return jsonify({'error': str(exc)}), 500

if __name__ == "__main__":
    app.run(debug=True)
