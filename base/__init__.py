import os,io
from flask import Flask
from flask_cors import CORS
# from flask_marshmallow import Marshmallow
from base.database.db import initialize_db
from base.routes import api
from dotenv import load_dotenv
from base.common.path import COMMON_URL
from base.apis.v1.user.models import User
from base.apis.v1.admin.models import Admin
from pathlib import Path

# env_path = Path('/var/www/html/backend/base/.env')
# load_dotenv(dotenv_path=env_path)

load_dotenv()

# marshmallow = Marshmallow()
app = Flask(__name__)


def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    # app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config["PROPAGATE_EXCEPTIONS"] = True

    db = initialize_db(app)

    cors = CORS(app)

    api.init_app(app)

    return app