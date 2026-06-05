from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
import os
load_dotenv(encoding='utf-8-sig')

def _resolve_database_uri():
    """Use Render DATABASE_URL in production, local SQLALCHEMY_DATABASE_URI as fallback."""
    uri = os.environ.get("DATABASE_URL") or os.environ.get("SQLALCHEMY_DATABASE_URI")
    if not uri:
        uri = "postgresql://localhost/ltgenerator_postgres_database"
    if uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)
    return uri

# Base class for all models
class Base(DeclarativeBase):
  pass

db = SQLAlchemy(model_class=Base)

_PKG_DIR = os.path.dirname(os.path.abspath(__file__))

# Ensure studentresults.sid FK uses ON DELETE CASCADE on PostgreSQL
def _ensure_studentresults_cascade():
    from sqlalchemy import text

    if db.engine.url.get_backend_name() != 'postgresql':
        return

    row = db.session.execute(text("""
        SELECT c.conname, c.confdeltype
        FROM pg_constraint c
        JOIN pg_class t ON c.conrelid = t.oid
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(c.conkey)
        WHERE t.relname = 'studentresults'
          AND c.contype = 'f'
          AND a.attname = 'sid'
        LIMIT 1
    """)).first()

    if row and row.confdeltype == 'c':
        return

    if row:
        db.session.execute(text(f'ALTER TABLE studentresults DROP CONSTRAINT "{row.conname}"'))

    db.session.execute(text(
        'ALTER TABLE studentresults ADD CONSTRAINT studentresults_sid_fkey '
        'FOREIGN KEY (sid) REFERENCES students(sid) ON DELETE CASCADE'
    ))
    db.session.commit()

# Create the Flask application
def create_app():
    app = Flask(
        __name__,
        static_folder=os.path.join(_PKG_DIR, "static"),
        template_folder=os.path.join(_PKG_DIR, "templates"),
    )
    # Set the SQLAlchemy database URI and other configuration options
    app.config["SQLALCHEMY_DATABASE_URI"] = _resolve_database_uri()
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = os.environ.get("SQLALCHEMY_TRACK_MODIFICATIONS")
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 280,
    }
    app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
    db.init_app(app)

    with app.app_context():
        from . import models
        db.create_all()
        _ensure_studentresults_cascade()
    return app
