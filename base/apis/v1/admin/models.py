from base.database.db import db
from datetime import datetime,timedelta
from base.common.path import COMMON_URL
from itsdangerous import URLSafeTimedSerializer as Serializer
import os
from dotenv import load_dotenv
from base.common.path import generate_presigned_url
from pathlib import Path
import json

# env_path = Path('/var/www/html/backend/base/.env')
# load_dotenv(dotenv_path=env_path)

load_dotenv()

FMT = "%H:%M"   # 24h like '05:00'

def get_hourly_slots_seperate(day_name: str):
    store = Store.query.filter(Store.day == day_name).first()
    if not store or not store.open_time or not store.close_time:
        return []

    print('storeeeeeeeeeeeeeeeeeeee',store)

    start = datetime.strptime(store.open_time, FMT)
    end   = datetime.strptime(store.close_time, FMT)

    # If your data can cross midnight (e.g., 22:00 -> 02:00), uncomment:
    # if end <= start:
    #     end += timedelta(days=1)

    slots = []
    cur = start
    while cur + timedelta(hours=1) <= end:
        nxt = cur + timedelta(hours=1)
        slots.append({
            "start_time": cur.strftime(FMT),
            "end_time":   nxt.strftime(FMT),
        })
        cur = nxt
    return slots

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(150), nullable=True)
    lastname = db.Column(db.String(150), nullable=True)
    email = db.Column(db.String(150), nullable=True)
    otp = db.Column(db.String(6),nullable=True)
    image_name = db.Column(db.String(150), nullable=True)
    image_path = db.Column(db.String(150), nullable=True)
    password = db.Column(db.String(150), nullable=True)
    admin_timezone = db.Column(db.String(150), nullable=True)
    created_at = db.Column(db.Date)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow())
    is_subadmin = db.Column(db.Boolean(), default=False)
    is_block = db.Column(db.Boolean(), default=False)

    country_code = db.Column(db.String(5))
    mobile_number = db.Column(db.String(20))

    def as_dict(self,token):

        return {
            'id': self.id,
            'firstname': self.firstname,
            'lastname': self.lastname,
            'email': self.email,
            'profile_pic': self.image_path if self.image_name is not None else '',
            'created_at': str(self.created_at),
            'token': token,
            'is_subadmin': self.is_subadmin
        }

    def as_dict_admin(self):

        return {

            'id': self.id,
            'name': self.firstname+' '+self.lastname if self.firstname is not None else '',
            'countryCode': self.country_code if self.country_code is not None else '',
            'mobile': self.mobile_number if self.mobile_number is not None else '',
            'email': self.email if self.email is not None else '',
            'image': generate_presigned_url(self.image_name) if self.image_name is not None else '',
        }

    def get_admin_token(self, expiress_sec=1800):
        serial = Serializer(os.getenv("ADMIN_SECRET_KEY"))
        return serial.dumps({'user_id': self.id})

    @staticmethod
    def verify_admin_token(token):
        serial = Serializer(os.getenv("ADMIN_SECRET_KEY"))
        try:
            user_id = serial.loads(token)['user_id']
        except:
            return None
        return Admin.query.get(user_id)

class Banners(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_name = db.Column(db.String(150), nullable=True)
    image_path = db.Column(db.String(150), nullable=True)
    is_active = db.Column(db.Boolean(), default=True)
    created_time = db.Column(db.DateTime)

    def as_dict_admin(self):

        return {

            'id': self.id,
            'banner_image': generate_presigned_url(self.image_name) if self.image_name is not None else '',
            'is_active': self.is_active
        }

    def as_dict(self):

        return {

            'id': self.id,
            'banner_image': self.image_path
        }

class BrodCastMessages(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message_en = db.Column(db.Text)
    message_ar = db.Column(db.Text)
    message_bn = db.Column(db.Text)
    created_time = db.Column(db.DateTime)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin.id', ondelete='CASCADE', onupdate='CASCADE'))

class Services(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    service_name = db.Column(db.String(150))
    service_name_ar = db.Column(db.String(150))
    service_name_bn = db.Column(db.String(150))
    service_description = db.Column(db.Text)
    service_description_ar = db.Column(db.Text)
    service_description_bn = db.Column(db.Text)
    service_price = db.Column(db.Integer)
    image_name = db.Column(db.String(150), nullable=True)
    image_path = db.Column(db.String(150), nullable=True)
    avarage_rating = db.Column(db.String(150), default='0')
    created_time = db.Column(db.DateTime)
    is_deleted = db.Column(db.Boolean(), default=False)
    assign_service = db.relationship('AssignProviderService', backref='assign_service')

    def as_dict(self,active_language="en"):
        get_store_data = Store.query.all()

        store_availibility = [ i.as_dict_seperate() for i in get_store_data ]

        # store_availibility = [
        #     {
        #
        #         'day': "Monday",
        #         'open_time': '10:00 AM',
        #         'close_time': '10:00 PM'
        #     },{
        #
        #         'day': "Tuesday",
        #         'open_time': '10:30:00 AM',
        #         'close_time': '07:30 PM'
        #     },{
        #
        #         'day': "Wednesday",
        #         'open_time': '11:00 AM',
        #         'close_time': '11:00 PM'
        #     },{
        #
        #         'day': "Thursday",
        #         'open_time': '10:00 AM',
        #         'close_time': '09:30 PM'
        #     },{
        #
        #         'day': "Friday",
        #         'open_time': '09:30 AM',
        #         'close_time': '09:00 PM'
        #     },{
        #
        #         'day': "Saterday",
        #         'open_time': '12:00 PM',
        #         'close_time': '10:00 PM'
        #     },{
        #
        #         'day': "Sunday",
        #         'open_time': '11:00 AM',
        #         'close_time': '08:00 PM'
        #     }
        #
        #     ]

        service_name = self.service_name
        service_description = self.service_description

        if active_language == 'ar':
            service_name = self.service_name_ar
            service_description = self.service_description_ar
        if active_language == 'bn':
            service_name = self.service_name_bn
            service_description = self.service_description_bn

        return {

            'id': self.id,
            'service_name': service_name,
            'service_description': service_description,
            'service_price': self.service_price,
            'service_image': generate_presigned_url(self.image_name) if self.image_name is not None else '',
            'store_avaibility': store_availibility

        }

    def as_dict_admin(self):

        return {

            'id': self.id,
            'service_name': self.service_name,
            'service_description': self.service_description,
            'service_name_ar': self.service_name_ar,
            'service_description_ar': self.service_description_ar,
            'service_name_bn': self.service_name_bn,
            'service_description_bn': self.service_description_bn,
            'service_price': self.service_price,
            'service_image': generate_presigned_url(self.image_name) if self.image_name is not None else ''

        }

class Zone(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    zone_name = db.Column(db.String(350))
    zone_area = db.Column(db.String(350))
    zone_city = db.Column(db.String(350))
    address = db.Column(db.String(350))
    place_id = db.Column(db.String(150))
    lat = db.Column(db.String(150))
    long = db.Column(db.String(150))

    polygon_path = db.Column(db.Text)  # keep your original array of {lat,lng}
    polygon_geojson = db.Column(db.Text, nullable=False)  # ✅ full polygon

    created_time = db.Column(db.DateTime)
    is_deleted = db.Column(db.Boolean(), default=False)
    subadmin_id = db.Column(db.Integer, db.ForeignKey('admin.id', ondelete='CASCADE', onupdate='CASCADE'))
    assign_zone = db.relationship('AssignProviderService', backref='assign_zone')

    def _safe_json_loads(self, value, default):
        if not value:
            return default
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            # you can also log here
            return default

    def as_dict(self):
        get_sub_zone = SubZone.query.filter_by(zone_id = self.id).all()

        sub_zone_list = [ i.as_dict() for i in get_sub_zone ]

        return {

            'id': self.id,
            'zone_name': self.zone_name,
            'zone_city': self.zone_city,
            'zone_area': self.zone_area,
            'address': self.address,
            'lat': self.lat,
            'long': self.long,
            # if polygon is missing, return [] instead of ''
            'polygon_path': self._safe_json_loads(self.polygon_path, []),
            # if geojson is missing, return {} instead of ''
            'polygon_geojson': self._safe_json_loads(self.polygon_geojson, {}),
            'sub_zone_list': sub_zone_list
        }

class SubZone(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    zone_name = db.Column(db.String(350))
    zone_area = db.Column(db.String(350))
    zone_city = db.Column(db.String(350))
    address = db.Column(db.String(350))
    place_id = db.Column(db.String(150))
    lat = db.Column(db.String(150))
    long = db.Column(db.String(150))

    polygon_path = db.Column(db.Text)  # keep your original array of {lat,lng}
    polygon_geojson = db.Column(db.Text, nullable=False)  # ✅ full polygon

    created_time = db.Column(db.DateTime)
    is_deleted = db.Column(db.Boolean(), default=False)
    zone_id = db.Column(db.Integer, db.ForeignKey('zone.id', ondelete='CASCADE', onupdate='CASCADE'))
    subadmin_id = db.Column(db.Integer, db.ForeignKey('admin.id', ondelete='CASCADE', onupdate='CASCADE'))

    def _safe_json_loads(self, value, default):
        if not value:
            return default
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            # you can also log here
            return default

    def as_dict(self):
        return {

            'id': self.id,
            'zone_name': self.zone_name,
            'zone_city': self.zone_city,
            'zone_area': self.zone_area,
            'address': self.address,
            'lat': self.lat,
            'long': self.long,
            # if polygon is missing, return [] instead of ''
            'polygon_path': self._safe_json_loads(self.polygon_path, []),
            # if geojson is missing, return {} instead of ''
            'polygon_geojson': self._safe_json_loads(self.polygon_geojson, {})
        }

class Cars(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    make = db.Column(db.String(150))
    type = db.Column(db.String(150))
    year = db.Column(db.String(150))
    color = db.Column(db.String(150))
    options = db.Column(db.String(150))
    engine_size = db.Column(db.String(150))
    fuel_type = db.Column(db.String(150))
    gear_type = db.Column(db.String(150))
    mileage = db.Column(db.String(150))
    region = db.Column(db.String(150))
    created_time = db.Column(db.DateTime)

class CarBrands(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    created_time = db.Column(db.DateTime)
    is_deleted = db.Column(db.Boolean(), default=False)
    is_popular = db.Column(db.Boolean(), default=False)
    car_models = db.relationship('CarModels', backref='car_models')
    saved_brand = db.relationship('SavedUserCars', backref='saved_brand')

    def as_dict_merge(self):
        if self.car_models:
            car_models = [ i.as_dict() for i in self.car_models ]
        else:
            car_models = []

        return {

            'id': self.id,
            'name': self.name,
            'car_models': car_models,
            'is_popular': self.is_popular

        }

    def as_dict(self):
        return {

            'id': self.id,
            'name': self.name,
            'is_popular': self.is_popular
        }

class CarModels(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    model = db.Column(db.String(150))
    year = db.Column(db.String(150))
    region = db.Column(db.String(150))
    created_time = db.Column(db.DateTime)
    is_deleted = db.Column(db.Boolean(), default=False)
    saved_model = db.relationship('SavedUserCars', backref='saved_model')
    car_brand_id = db.Column(db.Integer, db.ForeignKey('car_brands.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)

    def as_dict(self):
        return {
            'id': self.id,
            'model': self.model,
            'year': self.year,
            'brand_name': self.car_models.name
        }

class Store(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    day = db.Column(db.String(50))
    open_time = db.Column(db.String(50))
    close_time = db.Column(db.String(50))
    open_time_format = db.Column(db.Time)
    close_time_format = db.Column(db.Time)
    created_time = db.Column(db.DateTime)

    def as_dict(self):
        return {
            'id': self.id,
            'day': self.day,
            'open_time': self.open_time,
            'close_time': self.close_time
        }

    def as_dict_seperate(self):
        return {
            'day': self.day,
            'open_time': self.open_time,
            'close_time': self.close_time
        }

class AssignProviderService(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    place_id = db.Column(db.String(150))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    zone_id = db.Column(db.Integer, db.ForeignKey('zone.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    sub_zone_id = db.Column(db.Integer, db.ForeignKey('sub_zone.id', ondelete='CASCADE', onupdate='CASCADE'))
    created_time = db.Column(db.DateTime)

    zone_polygon_geojson = db.Column(db.Text)
    subzone_polygon_geojson = db.Column(db.Text)

class Cms(db.Model):
    id = db.Column(db.Integer, primary_key=True,
                       autoincrement=True, nullable=False)
    title = db.Column(db.String(100), nullable=False)

    content = db.Column(db.Text, nullable=False)
    title_ar = db.Column(db.String(100), nullable=False)

    content_ar = db.Column(db.Text, nullable=False)
    title_bn = db.Column(db.String(100), nullable=False)

    content_bn = db.Column(db.Text, nullable=False)

    def as_dict(self,active_language="en"):
        content = self.content
        if active_language == "ar":
            content = self.content_ar
        if active_language == "bn":
            content = self.content_bn

        return {
                'content': content
                    }

    def as_dict_admin(self):

        return {
                'content': self.content,
            'content_ar': self.content_ar,
            'content_bn': self.content_bn
                    }

class Faqs(db.Model):
    id = db.Column('id', db.Integer, primary_key=True,
                   autoincrement=True, nullable=False)
    question = db.Column(db.Text,
                         nullable=False)
    answer = db.Column(db.Text,
                         nullable=False)
    question_ar = db.Column(db.Text,
                         nullable=False)
    answer_ar = db.Column(db.Text,
                       nullable=False)
    question_bn = db.Column(db.Text,
                         nullable=False)
    answer_bn = db.Column(db.Text,
                       nullable=False)

    def as_dict(self,active_language="en"):
        question = self.question
        answer = self.answer

        if active_language == "ar":
            question = self.question_ar
            answer = self.answer_ar

        if active_language == "bn":
            question = self.question_bn
            answer = self.answer_bn

        return {'id': self.id,
                'question': question,
                'answer': answer
                }

    def as_dict_admin(self):

        return {'id': self.id,
                'question': self.question,
                'answer': self.answer,
                'question_ar': self.question_ar,
                'answer_ar': self.answer_ar,
                'question_bn': self.question_bn,
                'answer_bn': self.answer_bn
                }

class Extras(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    name_ar = db.Column(db.String(150))
    name_bn = db.Column(db.String(150))
    price = db.Column(db.String(150))
    image_name = db.Column(db.String(150))
    image_path = db.Column(db.String(150))
    is_deleted = db.Column(db.Boolean(), default=False)

    def as_dict(self,active_language="en"):

        name = self.name

        if active_language == "ar":
            name = self.name_ar
        if active_language == "bn":
            name = self.name_bn

        return {

            'id': self.id,
            'name': name,
            'image': generate_presigned_url(self.image_name) if self.image_name is not None else '',
            'price': int(self.price)
        }

    def as_dict_admin(self):
        return {

            'id': self.id,
            'name': self.name,
            'name_ar': self.name_ar,
            'name_bn': self.name_bn,
            'image': generate_presigned_url(self.image_name) if self.image_name is not None else '',
            'price': int(self.price)
        }

class ContactUs(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    request_id = db.Column(db.String(50))
    email = db.Column(db.String(150))
    description = db.Column(db.Text)
    reply = db.Column(db.Text)
    created_time = db.Column(db.DateTime)
    is_reply = db.Column(db.Boolean(), default=False)
    reply_id = db.Column(db.Integer)
    user_type = db.Column(db.String(150))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'))
    admin_id = db.Column(db.Integer, db.ForeignKey('admin.id', ondelete='CASCADE', onupdate='CASCADE'))

    def as_dict(self):
        return {

            'id': self.id,
            'name': self.name,
            'email': self.email,
            'description': self.description,
            'created_time': self.created_time,
            'username': self.my_contact_us.name if self.my_contact_us.name is not None else '',
            'user_image': generate_presigned_url(self.my_contact_us.image_name) if self.my_contact_us.image_name is not None else '',
            'role': self.my_contact_us.role,
            'is_reply': self.is_reply
        }

    def as_dict_chat(self):
        message_by = 'User'
        name = self.name
        username = self.my_contact_us.name if self.my_contact_us.name is not None else ''
        user_image = generate_presigned_url(self.my_contact_us.image_name) if self.my_contact_us.image_name is not None else ''
        request_id = self.request_id

        description = self.description
        if self.admin_id:
            description = self.reply
            message_by = 'Admin'
            name = 'Admin'
            user_image = ''
            username = 'Admin'
            request_id = ''

        return {

            'id': self.id,
            'name': name,
            'email': self.email if self.email is not None else '',
            'description': description,
            'created_time': self.created_time,
            'username': username,
            'user_image': user_image,
            'message_by': message_by,
            'request_id': request_id
        }

class SlotDisableTime(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slot_disable_before = db.Column(db.Integer)