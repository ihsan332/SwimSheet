from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
import os
load_dotenv()


class Base(DeclarativeBase):
  pass

db = SQLAlchemy(model_class=Base)



def create_app():
    app = Flask(__name__)
    # TODO: dotenv to hide app.config info
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("SQLALCHEMY_DATABASE_URI")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = os.environ.get("SQLALCHEMY_TRACK_MODIFICATIONS")
    app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
    db.init_app(app)

    with app.app_context():
        from . import models
        db.create_all()
    return app

from . import create_app, db, Base
