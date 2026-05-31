from sqlalchemy import case
from LTGenerator import create_app, db, Base
from flask import render_template, request, redirect, url_for
from LTGenerator.models import Instructor, Level, Session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from print import print_general_fields

# Initialize the Flask application and login manager
app = create_app()
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User loader callback for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Instructor, user_id)

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
    if request.method == 'POST':
        time = request.form.get('time')
        session = request.form.get('session_id')
        weekdays = request.form.get('weekdays')
        pool = request.form.get('pool')
        enrolled = request.form.get('enrolled')
        evaluated = request.form.get('evaluated')  
        completed = request.form.get('completed')
        incomplete = request.form.get('incomplete')
        new_session = Session(
            iid=current_user.iid,
            time=time,
            session=session,
            weekdays=weekdays,
            pool=pool,
            levelid=4,
            enrolled=enrolled,
            evaluated=evaluated,
            completed=completed,
            incomplete=incomplete
        )
        db.session.add(new_session)
        db.session.commit()
        return redirect(url_for('newsession'))
    return render_template('newsession.html')

# Select session route
@app.route('/selectsession')
@login_required
def selectsession():
    sessions = db.session.scalars(db.select(Session).filter_by(iid=current_user.iid)).all()
    levels = db.session.scalars(db.select(Level)).all()
    return render_template('selectsession.html', sessions=sessions, levels=levels)

# Edit session route    
# TODO: Make sessionid lookup check database
@app.route('/editsession/<int:session_id>', methods=['GET', 'POST'])
@login_required
def editsession(session_id):
    session = db.session.get(Session, session_id)
    match session.levelid:
        case 4:
            clevel = session.Level
            # page = clevel.template
            skillcount = len(clevel.skills) + 18
        case _:
            pass

    if request.method == 'POST':

        # TODO: print_general_fields(page, 'sheets/output.pdf')
        return redirect(url_for('selectsession'))       

    return render_template('editsession.html', session=session, clevel=clevel, skillcount=skillcount)

if __name__ == "__main__":
    app.run(debug=True)
