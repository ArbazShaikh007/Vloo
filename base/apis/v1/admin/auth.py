from flask import request, make_response, render_template, jsonify, url_for, redirect
from flask_restful import Resource
from base.common.utils import admin_login_required
from datetime import datetime, timedelta
import os
import jwt
import secrets
import random
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from base.apis.v1.admin.models import Admin
from base.database.db import db
from base.common.utils import user_send_reset_email,upload_photos_local,upload_photos,send_otp
from dotenv import load_dotenv
from pathlib import Path

# env_path = Path('/var/www/html/backend/base/.env')
# load_dotenv(dotenv_path=env_path)

load_dotenv()

# UPLOAD_FOLDER = "base/static/admin_photos/"

class AdminRegisterResource(Resource):
    def post(self):
        data = request.get_json()

        firstname = data.get("firstname")
        lastname = data.get("lastname")
        email = data.get("email")
        password = data.get("password")

        if not firstname:
            return jsonify({'status': 0,'message': 'Please provide firstname'})
        if not lastname:
            return jsonify({'status': 0,'message': 'Please provide lastname'})
        if not email:
            return jsonify({'status': 0,'message': 'Please provide email'})
        if not password:
            return jsonify({'status': 0,'message': 'Please provide password'})

        hashed_password = generate_password_hash(password)

        admin = Admin.query.filter_by(email=email).first()

        if admin:
            return jsonify({'status':0,'message': "Email already exists. Please try another one."})

        admin = Admin(
            firstname=firstname,
            lastname=lastname,
            email=email,
            password=hashed_password,
            created_at=datetime.utcnow()
        )

        db.session.add(admin)
        db.session.commit()

        token = jwt.encode(
            {"id": admin.id, "exp": datetime.utcnow() + timedelta(days=365)},
            os.getenv("ADMIN_SECRET_KEY"),
        )

        return jsonify({'status': 1,'message': "Register successfully.", 'data':admin.as_dict(token)})

class AdminLoginResource(Resource):
    def post(self):
        data = request.get_json()

        email = data.get("email")
        password = data.get("password")

        admin = Admin.query.filter_by(email=email).first()

        if admin and check_password_hash(admin.password, password):
            token = jwt.encode(
                {"id": admin.id, "exp": datetime.utcnow() + timedelta(days=365)},
                os.getenv("ADMIN_SECRET_KEY")
            )

            return jsonify({'status': 1,'message': "Login successfully.", 'data':admin.as_dict(token)})
        else:
            return jsonify({'status': 0,'message': "Invalid email or password."})

class GetAdminResource(Resource):
    @admin_login_required
    def get(self, active_user):
        token = request.headers.get("authorization")
        return jsonify({'status':1,'message':"Success",'data': active_user.as_dict(token)})

class AdminChangePasswordResource(Resource):
    @admin_login_required
    def put(self, active_user):

        data = request.get_json()

        current_password = data.get("current_password")
        new_password = data.get("new_password")

        if check_password_hash(active_user.password, current_password):
            active_user.password = generate_password_hash(new_password)
            db.session.commit()

            return jsonify({'status': 1,'message': "Password changed successfully."})
        else:
            return jsonify({'status': 0,'message': "Invalid current password."})

class AdminEditProfileResource(Resource):
    @admin_login_required
    def put(self, active_user):
        try:
            token = request.headers.get("authorization")

            data = request.form

            firstname = data.get("firstname")
            lastname = data.get("lastname")
            profile_pic = request.files.get("profile_pic")

            print('profile_pic',profile_pic)

            active_user.firstname = firstname
            active_user.lastname = lastname

            if profile_pic:

                file_path, picture = upload_photos(profile_pic)

                active_user.image_name = picture
                active_user.image_path = file_path
            print('runninggggggggggggggggggg')
            db.session.commit()

            return jsonify({'status':1,'message': "Profile updated successfully.", 'data':active_user.as_dict(token)})
        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

class AdminForgetPassword(Resource):
    def post(self):
        try:
            email = request.json.get('email')
            if not email:
                return jsonify({'status': 0, 'message': 'Please enter your email'})

            admin_data = Admin.query.filter_by(email=email).first()
            if not admin_data:
                return jsonify({'status': 0, 'message': 'Wrong email address you entered try again'})
            else:
                otp = random.randint(100000, 999999)
                admin_data.otp = otp
                db.session.commit()

                send_otp(admin_data, otp)

                return jsonify({'status': 1, "message": "Reset password link sucessfully sent to your email"})

        except Exception as e:
            return {'status': 0, 'message': 'Something went wrong', 'error': str(e)}, 400

class VerifyOTPResource(Resource):
    def post(self):
        email = request.json.get('email')
        otp = request.json.get('otp')

        if not email:
            return jsonify({'status':0,'message': 'Email is required'})
        if not otp:
            return jsonify({'status':0,'message': 'Please enter otp'})

        get_admin = Admin.query.filter_by(otp=otp,email=email).first()
        if not get_admin:
            return jsonify({'status':0,'message': 'Invalid data'})

        token = jwt.encode(
            {"id": get_admin.id, "exp": datetime.utcnow() + timedelta(days=365)},
            os.getenv("ADMIN_SECRET_KEY")
        )

        return jsonify({'status':1,'message':"Success",'data': get_admin.as_dict(token)})

class UpdatePasswordResource(Resource):
    @admin_login_required
    def post(self, active_user):
        token = request.headers["authorization"]
        new_password = request.json.get('new_password')

        if not new_password:
            return jsonify({'status':0,'message': 'Please enter password'})

        active_user.password = generate_password_hash(new_password)
        db.session.commit()

        return jsonify({'status':1,'message':"Password updated successfully",'data': active_user.as_dict(token)})
