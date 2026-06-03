from LTGenerator import db, Base
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from flask_login import UserMixin

# Instructor model
class Instructor(Base, UserMixin):
    __tablename__ = "instructors"
    iid = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    is_approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    def __repr__(self):
        return f"<Instructor {self.name}>"
    def get_id(self):
        return str(self.iid)

# Student model
class Student(Base):
    __tablename__ = "students"
    sid = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    sessionid = db.Column(db.BigInteger, db.ForeignKey("sessions.sessionid"), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    Session = db.relationship("Session", backref="students")
    studentresults = db.relationship(
        "studentresults",
        back_populates="Student",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    def __repr__(self):
        return f"<Student {self.name}>"

# Session model
class Session(Base):
    __tablename__ = "sessions"
    sessionid = db.Column(db.BigInteger, primary_key=True)
    iid = db.Column(db.Integer, db.ForeignKey("instructors.iid"), nullable=False)
    time = db.Column(db.String(50), nullable=False)
    session = db.Column(db.String(20), nullable=False)
    Instructor = db.relationship("Instructor", backref="sessions")
    weekdays = db.Column(db.String(20), nullable=False)
    pool = db.Column(db.String(50), nullable=False)
    evaluated = db.Column(db.Integer)
    enrolled = db.Column(db.Integer, nullable=False)
    completed = db.Column(db.Integer, nullable=False)
    incomplete = db.Column(db.Integer, nullable=False)
    levelid = db.Column(db.Integer, db.ForeignKey("levels.levelid"), nullable=False)
    Level = db.relationship("Level", backref="sessions")
    def __repr__(self):
        return f"<Session {self.sessionid}>"

# Level model
class Level(Base):
    __tablename__ = "levels"
    levelid = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    template = db.Column(db.String(200), nullable=False)
    def __repr__(self):
        return f"<Level {self.name}>"

# Skills model
class Skills(Base):
    __tablename__ = "skills"
    skillid = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    levelid = db.Column(db.Integer, db.ForeignKey("levels.levelid"), nullable=False)
    Level = db.relationship("Level", backref="skills")
    def __repr__(self):
        return f"<Skill {self.name}>"

# Levelskills model
class levelskills(Base):
    __tablename__ = "levelskills"
    levelid = db.Column(db.Integer, db.ForeignKey("levels.levelid"), nullable=False, primary_key=True)
    skillid = db.Column(db.Integer, db.ForeignKey("skills.skillid"), nullable=False, primary_key=True)
    columnid = db.Column(db.Integer, nullable=False)
    Level = db.relationship("Level", backref="levelskills")
    Skills = db.relationship("Skills", backref="levelskills")

# Studentresults model
class studentresults(Base):
    __tablename__ = "studentresults"
    sid = db.Column(
        db.Integer,
        db.ForeignKey("students.sid", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
    )
    skillid = db.Column(db.Integer, db.ForeignKey("skills.skillid"), nullable=False, primary_key=True)
    result = db.Column(db.String(1), nullable=False)
    Student = db.relationship("Student", back_populates="studentresults")
    Skills = db.relationship("Skills", backref="studentresults")