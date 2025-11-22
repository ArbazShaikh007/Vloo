import jwt,json,threading
import os
import secrets, boto3,requests
import random
import string
from datetime import datetime, timedelta
from flask import request, jsonify
from flask_restful import Resource
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from base.database.db import db
from dotenv import load_dotenv
from pathlib import Path
from sqlalchemy import func
from base.apis.v1.admin.models import SubZone,SlotDisableTime,ContactUs,Extras,Cms,Banners,Services,Zone,CarBrands,CarModels,AssignProviderService,Faqs,Store
from base.apis.v1.user.models import ProviderRequest,Notification,UserPayments,UserServiceReviewImages,UserServiceReview,ServiceCompletedData,token_required,User,UserAddress,ProviderSlots,SavedUserCars,ServiceRequested
from base.common.utils import find_assign_zone_for_latlng,find_zone_for_latlng,get_hourly_slots,delete_photos,push_notification,upload_photos_local,upload_photos,user_send_reset_email,delete_photos_local
from base.common.path import COMMON_URL
from sqlalchemy import desc, asc
import pytz
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from collections import defaultdict
from base.common.helpers import get_localized_service_name,get_notification_message
from base.common.path import generate_presigned_url
from base.common.helpers import get_normal_message
from sqlalchemy import cast, Time

# env_path = Path('/var/www/html/backend/base/.env')
# load_dotenv(dotenv_path=env_path)

load_dotenv()

NEOLEAP_HOSTED_URL = os.getenv("NEOLEAP_HOSTED_URL")
NEOLEAP_TRANPORTAL_ID = os.getenv("NEOLEAP_TRANPORTAL_ID")
NEOLEAP_TRANPORTAL_PASSWORD = os.getenv("NEOLEAP_TRANPORTAL_PASSWORD")
NEOLEAP_TERMINAL_RESOURCE_KEY = os.getenv("NEOLEAP_TERMINAL_RESOURCE_KEY")
CURRENCY_CODE = os.getenv("CURRENCY_CODE")
CALLBACK_SUCCESS_URL = os.getenv("CALLBACK_SUCCESS_URL")
CALLBACK_FAILED_URL = os.getenv("CALLBACK_FAILED_URL")
NEOLEAP_INQUIRY_ACTION = os.getenv("NEOLEAP_INQUIRY_ACTION", "8")  # some docs use 8 or 10
NEOLEAP_BASE_URL = os.getenv("NEOLEAP_BASE_URL", "https://securepayments.alrajhibank.com.sa/pg/payment/tranportal.htm")
IV = os.getenv("IV")

def encrypt(text):
    cipher = AES.new(NEOLEAP_TERMINAL_RESOURCE_KEY.encode(), AES.MODE_CBC, IV.encode())
    return cipher.encrypt(pad(text.encode(), AES.block_size)).hex().upper()

class ChangeLanguageResource(Resource):
    @token_required
    def post(self,active_user):
        try:
            data = request.get_json()
            token = request.headers["authorization"]

            active_language = data.get('lang') #en,ar,bn
            if not active_language:
                message = get_normal_message("msg_44", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            if not active_language in ["en","ar","bn"]:
                message = get_normal_message("msg_45", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            active_user.active_language = active_language
            db.session.commit()

            message = get_normal_message("msg_46", active_user.active_language)

            return jsonify({'status': 1,'message': message,'data': active_user.as_dict(token)})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrr:', str(e))
            message = get_normal_message("msg_10", active_user.active_language)
            return {'status': 0, 'message': message}, 500

class NotificationListResource(Resource):
    @token_required
    def get(self,active_user):
        try:
            user_tz = pytz.timezone(active_user.timezone)

            lang = active_user.active_language or "en"
            grouped = defaultdict(list)

            get_notification_data = Notification.query.filter(Notification.to_id == active_user.id).order_by(
                Notification.id.desc()).all()

            for n in get_notification_data:
                local_dt = n.created_time.astimezone(user_tz)
                date_key = local_dt.strftime("%Y-%m-%d")

                if lang == "en":
                    title, message = n.title_en, n.message_en
                elif lang == "bn":
                    title, message = n.title_bn, n.message_bn
                else:
                    title, message = n.title_ar, n.message_ar

                grouped[date_key].append({
                    "id": n.id,
                    "title": title,
                    "message": message,
                    "created_time": n.created_time,
                })

                # Convert dict → list of objects
            notification_list = [
                {"date": date, "list": grouped[date]}
                for date in sorted(grouped.keys(), reverse=True)
            ]

            message = get_normal_message("msg_11", active_user.active_language)

            return jsonify({
                "status": 1,
                "message": message,
                "notification_list": notification_list
            })

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrr:', str(e))
            message = get_normal_message("msg_10", active_user.active_language)
            return {'status': 0, 'message': message}, 500

class ServiceReviewListResource(Resource):
    @token_required
    def post(self,active_user):
        try:
            if active_user.role == "Worker":
                message = get_normal_message("msg_16", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            service_id = request.json.get('service_id')
            if not service_id:
                message = get_normal_message("msg_47", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            get_service_data = Services.query.get(service_id)
            if not get_service_data:
                message = get_normal_message("msg_23", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            get_service_review = UserServiceReview.query.filter(UserServiceReview.service_id==get_service_data.id).all()

            review_list = [ i.as_dict() for i in get_service_review ]

            message = get_normal_message("msg_11", active_user.active_language)

            return jsonify({'status': 1,'message': message,'review_list': review_list})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrr:', str(e))
            message = get_normal_message("msg_10", active_user.active_language)
            return {'status': 0, 'message': message}, 500

class ProviderReviewListResource(Resource):
    @token_required
    def get(self,active_user):
        try:
            if active_user.role == "Customer":
                message = get_normal_message("msg_48", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            get_providers_review = UserServiceReview.query.filter(UserServiceReview.provider_id==active_user.id).all()

            review_list = [i.as_dict() for i in get_providers_review]

            message = get_normal_message("msg_11", active_user.active_language)

            return jsonify({'status': 1, 'message': message, 'review_list': review_list,'avarage_rating': active_user.avarage_rating,'review_count': len(get_providers_review)})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrr:', str(e))
            message = get_normal_message("msg_10", active_user.active_language)
            return {'status': 0, 'message': message}, 500

#Done
class UserServiceReviewResource(Resource):
    @token_required
    def post(self,active_user):
        try:
            if active_user.role == "Worker":
                message = get_normal_message("msg_16", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            request_id = request.form.get('request_id')
            rate = request.form.get('rate')
            review = request.form.get('review')
            images = request.files.getlist('images')

            if not rate:
                message = get_normal_message("msg_49", active_user.active_language)
                return jsonify({'status': 0,'message': message})
            if not review:
                message = get_normal_message("msg_50", active_user.active_language)
                return jsonify({'status': 0,'message': message})
            if not request_id:
                message = get_normal_message("msg_19", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            get_request_data = ServiceRequested.query.get(request_id)
            if not get_request_data:
                message = get_normal_message("msg_20", active_user.active_language)
                return jsonify({'status': 0, 'message': message})
            if get_request_data.status != "Completed":
                message = get_normal_message("msg_51", active_user.active_language)
                return jsonify({"status": 0, "messsage": message})

            check_provider_completed = ProviderRequest.query.filter_by(service_request_id=get_request_data.id,status = "Completed").first()
            if not check_provider_completed:
                message = get_normal_message("msg_113", active_user.active_language)
                return jsonify({'status':0,'message': message})

            get_service = Services.query.get(get_request_data.service_id)
            if not get_service:
                message = get_normal_message("msg_23", active_user.active_language)
                return jsonify({'status': 0, 'message': message})

            add_review = UserServiceReview(user_id=active_user.id,provider_id=check_provider_completed.provider_id,service_request_id=get_request_data.id,service_id=get_request_data.service_id,review=review, rate=rate, created_time=datetime.utcnow())
            db.session.add(add_review)
            db.session.commit()

            if len(images)>0:
                for i in images:

                    file_path , picture = upload_photos(i)

                    add_review_image = UserServiceReviewImages(review_id=add_review.id,image_name=picture,image_path=file_path)
                    db.session.add(add_review_image)
                db.session.commit()

            get_provider = User.query.get(check_provider_completed.provider_id)
            if not get_provider:
                message = get_normal_message("msg_52", active_user.active_language)
                return jsonify({'status': 0, 'message': message})

            avg_service = (
                      db.session.query(func.avg(UserServiceReview.rate))
                          .filter_by(service_id=get_request_data.service_id)
                          .scalar()
                  ) or 0.0

            get_service.avarage_rating = f"{avg_service :.1f}"  # keep as string to match your column

            avg_provider = (
                               db.session.query(func.avg(UserServiceReview.rate))
                                   .filter_by(provider_id=get_provider.id)
                                   .scalar()
                           ) or 0.0
            get_provider.avarage_rating = f"{avg_provider:.1f}"

            db.session.commit()

            titles, messages = {}, {}
            for lang in ("en", "ar", "bn"):
                localized_service = get_localized_service_name(get_service, lang)
                data = get_notification_message("new_review", lang, localized_service)
                titles[lang], messages[lang] = data["title"], data["msg"]

            add_notification = Notification(service_request_id =get_request_data.id,title_en=titles["en"], title_ar=titles["ar"], title_bn=titles["bn"],
                                            message_en=messages["en"], message_ar=messages["ar"],
                                            message_bn=messages["bn"], by_id=active_user.id, to_id=get_provider.id,
                                            is_read=False, created_time=datetime.utcnow(),
                                            notification_type='customer review on service')
            db.session.add(add_notification)
            db.session.commit()

            # Send push only in receiver’s active language
            user_lang = get_provider.active_language if get_provider.active_language in ("en", "ar", "bn") else "en"
            push_title = titles[user_lang]
            push_msg = messages[user_lang]

            if get_provider.device_token:
                push_notification(
                    token=get_provider.device_token,
                    title=push_title,
                    body=push_msg
                )

            message = get_normal_message("msg_53", active_user.active_language)
            return jsonify({'status': 1,'message': message})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrr:', str(e))
            message = get_normal_message("msg_10", active_user.active_language)
            return {'status': 0, 'message': message}, 500

# class ProviderCompleteServiceResource(Resource):
#     @token_required
#     def post(self, active_user):
#         try:
#             if active_user.role == "Customer":
#                 return jsonify({'status': 0, 'message': "This functionality only for providers"})
#
#             request_id = request.form.get('request_id')
#
#             before_image_one = request.files.get('before_image_one')
#             before_image_two = request.files.get('before_image_two')
#             after_image_one = request.files.get('after_image_one')
#             after_image_two = request.files.get('after_image_two')
#
#             if not request_id:
#                 return jsonify({'status': 0, 'message': 'Please select request first'})
#
#             if not before_image_one:
#                 return jsonify({'status': 0, 'message': 'Please provide before image one'})
#             if not before_image_two:
#                 return jsonify({'status': 0, 'message': 'Please provide before image two'})
#             if not after_image_one:
#                 return jsonify({'status': 0, 'message': 'Please provide after image one'})
#             if not after_image_two:
#                 return jsonify({'status': 0, 'message': 'Please provide after image one'})
#
#             get_request_data = ServiceRequested.query.get(request_id)
#             if not get_request_data:
#                 return jsonify({'status': 0, 'message': 'Invalid request'})
#             if get_request_data.status != "Accepted":
#                 return jsonify({"status": 0, "messsage": "Provider must be accept your request first"})
#
#             file_path_before_one, picture_before_one = upload_photos_local(before_image_one)
#             file_path_before_two, picture_before_two = upload_photos_local(before_image_two)
#             file_path_after_one, picture_after_one = upload_photos_local(after_image_one)
#             file_path_after_two, picture_after_two = upload_photos_local(after_image_two)
#
#             add_completed = ServiceCompletedData(
#                 before_image_name_1=picture_before_one
#                 , before_image_path_1=file_path_before_one
#                 , before_image_name_2=picture_before_two
#                 , before_image_path_2=file_path_before_two
#                 , after_image_name_1=picture_after_one
#                 , after_image_path_1=file_path_after_one
#                 , after_image_name_2=picture_after_two
#                 , after_image_path_2=file_path_after_two
#                 , created_time=datetime.utcnow()
#                 , provider_id=active_user.id
#                 , user_id=get_request_data.user_id
#                 , service_request_id=get_request_data.id)
#
#             db.session.add(add_completed)
#             get_request_data.is_provider_completed = True
#             db.session.commit()
#
#             return jsonify({'status': 1, 'message': 'Service completed successfully'})
#
#         except Exception as e:
#             print('errorrrrrrrrrrrrrrrrr:', str(e))
#             return {'status': 0, 'message': 'Something went wrong'}, 500

# Done
class ProviderCompleteServiceResource(Resource):
    @token_required
    def post(self,active_user):
        try:
            if active_user.role == "Customer":
                message = get_normal_message("msg_48", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            request_id = request.form.get('request_id')

            after_image_one = request.files.get('after_image_one')
            after_image_two = request.files.get('after_image_two')

            if not request_id:
                message = get_normal_message("msg_19", active_user.active_language)
                return jsonify({'status': 0,'message': message})
            if not after_image_one:
                message = get_normal_message("msg_54", active_user.active_language)
                return jsonify({'status': 0,'message': message})
            if not after_image_two:
                message = get_normal_message("msg_55", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            get_request_data = ServiceRequested.query.get(request_id)
            if not get_request_data:
                message = get_normal_message("msg_20", active_user.active_language)
                return jsonify({'status': 0,'message': message})
            if get_request_data.status != "Accepted":
                message = get_normal_message("msg_56", active_user.active_language)
                return jsonify({"status": 0, "messsage": message})

            check_provider_accepted = ProviderRequest.query.filter_by(service_request_id=get_request_data.id,status = "Accepted").first()
            if not check_provider_accepted:
                message = get_normal_message("msg_114", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            get_service_completed_data = ServiceCompletedData.query.filter_by(
                service_request_id=get_request_data.id).first()

            if not get_service_completed_data:
                message = get_normal_message("msg_57", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            file_path_after_one, picture_after_one = upload_photos(after_image_one)
            file_path_after_two, picture_after_two = upload_photos(after_image_two)

            get_service_completed_data.after_image_name_1=picture_after_one
            get_service_completed_data.after_image_path_1=file_path_after_one
            get_service_completed_data.after_image_name_2=picture_after_two
            get_service_completed_data.after_image_path_2=file_path_after_two

            check_provider_accepted.is_provider_completed = True
            get_request_data.is_provider_completed = True
            db.session.commit()

            message = get_normal_message("msg_58", active_user.active_language)

            return jsonify({'status': 1,'message': message})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrr:', str(e))
            message = get_normal_message("msg_10", active_user.active_language)
            return {'status': 0, 'message': message}, 500

#Done
class UserCompleteServiceResource(Resource):
    @token_required
    def post(self,active_user):
        try:
            if active_user.role == "Worker":
                message = get_normal_message("msg_16", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            request_id = request.form.get('request_id')
            description = request.form.get('description')
            status = request.form.get('status') #Complete or Issue
            service_complete_id = request.form.get('service_complete_id')

            if not service_complete_id:
                message = get_normal_message("msg_59", active_user.active_language)
                return jsonify({'status': 0,'message': message})
            if not request_id:
                message = get_normal_message("msg_19", active_user.active_language)
                return jsonify({'status': 0,'message': message})
            if not description:
                message = get_normal_message("msg_60", active_user.active_language)
                return jsonify({'status': 0,'message': message})
            if not status:
                message = get_normal_message("msg_61", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            if int(status) == 1:

                get_request_data = ServiceRequested.query.get(request_id)
                if not get_request_data:
                    message = get_normal_message("msg_20", active_user.active_language)
                    return jsonify({'status': 0,'message': message})
                if get_request_data.status != "Accepted":
                    message = get_normal_message("msg_56", active_user.active_language)
                    return jsonify({"status": 0, "messsage": message})

                check_provider_accepted = ProviderRequest.query.filter_by(service_request_id=get_request_data.id,
                                                                          status="Accepted").first()
                if not check_provider_accepted:
                    message = get_normal_message("msg_114", active_user.active_language)
                    return jsonify({'status': 0, 'message': message})

                get_completed_data = ServiceCompletedData.query.get(service_complete_id)
                if not get_completed_data:
                    message = get_normal_message("msg_20", active_user.active_language)
                    return jsonify({"status": 0, "messsage": message})

                get_payment_data = UserPayments.query.filter_by(service_request_id=get_request_data.id,
                                                                intend_status='Success').first()
                if not get_payment_data:
                    message = get_normal_message("msg_62", active_user.active_language)
                    return jsonify({'status': 0, 'message': message})

                plain = [{
                    "amt": str(get_payment_data.total_amount),
                    "action": "5",  # Capture
                    "password": NEOLEAP_TRANPORTAL_PASSWORD,
                    "id": NEOLEAP_TRANPORTAL_ID,
                    "currencyCode": CURRENCY_CODE,
                    "trackId": f"CAP-{int(datetime.utcnow().timestamp())}",
                    # "udf5": "PaymentID",
                    "transId": get_payment_data.transaction_id
                }]

                trandata = encrypt(json.dumps(plain))
                payload = [{
                    "id": NEOLEAP_TRANPORTAL_ID,
                    "trandata": trandata,
                    "errorURL": CALLBACK_FAILED_URL,
                    "responseURL": CALLBACK_SUCCESS_URL
                }]

                r = requests.post(NEOLEAP_BASE_URL, json=payload, timeout=60)
                data = r.json()[0]

                if data.get("status") == "1":

                    get_completed_data.description=description
                    get_completed_data.status=status
                    get_completed_data.user_id = active_user.id

                    check_provider_accepted.status = "Completed"
                    get_request_data.status = "Completed"
                    get_request_data.is_completed = True
                    get_request_data.service_completed_time = datetime.utcnow()

                    get_payment_data.intend_status = 'Completed'

                    db.session.commit()

                    reciver_user = User.query.get(check_provider_accepted.provider_id)
                    if not reciver_user:
                        message = get_normal_message("msg_52", active_user.active_language)
                        return jsonify({'status': 0, 'message': message})

                    get_service_data = Services.query.get(get_request_data.service_id)
                    if not get_service_data:
                        message = get_normal_message("msg_23", active_user.active_language)
                        return jsonify({'status': 0, 'message': message})

                    titles, messages = {}, {}
                    for lang in ("en", "ar", "bn"):
                        localized_service = get_localized_service_name(get_service_data, lang)
                        data = get_notification_message("service_completed", lang, localized_service)
                        titles[lang], messages[lang] = data["title"], data["msg"]

                    add_notification = Notification(service_request_id =get_request_data.id,title_en=titles["en"], title_ar=titles["ar"], title_bn=titles["bn"],
                                                    message_en=messages["en"], message_ar=messages["ar"],
                                                    message_bn=messages["bn"], by_id=active_user.id,
                                                    to_id=reciver_user.id,
                                                    is_read=False, created_time=datetime.utcnow(),
                                                    notification_type='customer review on service')
                    db.session.add(add_notification)
                    db.session.commit()

                    # Send push only in receiver’s active language
                    user_lang = reciver_user.active_language if reciver_user.active_language in (
                    "en", "ar", "bn") else "en"
                    push_title = titles[user_lang]
                    push_msg = messages[user_lang]

                    if reciver_user.device_token:
                        push_notification(
                            token=reciver_user.device_token,
                            title=push_title,
                            body=push_msg
                        )

                    message = get_normal_message("msg_58", active_user.active_language)

                    return jsonify({'status': 1,'message': message})

                else:
                    message = get_normal_message("msg_63", active_user.active_language)
                    return jsonify({'status': 0,'message': message})

            elif int(status) == 2:
                message = get_normal_message("msg_64", active_user.active_language)
                return jsonify({'status': 1,'message': message})

            else:
                message = get_normal_message("msg_65", active_user.active_language)
                return jsonify({'status': 0,'message': message})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrr:', str(e))
            message = get_normal_message("msg_10", active_user.active_language)
            return {'status': 0, 'message': message}, 500

class ProviderOnlineOfflineResource(Resource):
    @token_required
    def get(self,active_user):
        try:
            if active_user.role == "Customer":
                message = get_normal_message("msg_48", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            if active_user.is_online == True:
                active_user.is_online = False
                db.session.commit()

                message = get_normal_message("msg_66", active_user.active_language)
                return jsonify({'status': 1,'message': message,'is_online': active_user.is_online})
            if active_user.is_online == False:
                active_user.is_online = True
                db.session.commit()
                message = get_normal_message("msg_67", active_user.active_language)
                return jsonify({'status': 1, 'message': message,'is_online': active_user.is_online})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrr:', str(e))
            message = get_normal_message("msg_10", active_user.active_language)
            return {'status': 0, 'message': message}, 500

class UserConatactUsChatResource(Resource):
    @token_required
    def get(self,active_user):
        try:
            check_chat = ContactUs.query.filter(ContactUs.user_id == active_user.id).all()

            chat_list = [ i.as_dict_chat() for i in check_chat ]

            message = get_normal_message("msg_11", active_user.active_language)

            return jsonify({'status': 1,'message': message, 'chat_list': chat_list})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrr:', str(e))
            message = get_normal_message("msg_10", active_user.active_language)
            return {'status': 0, 'message': message}, 500

def generate_random_string2(length=7):
    characters = string.ascii_letters + string.digits  # A-Z, a-z, 0-9
    return ''.join(random.choices(characters, k=length))

class UserConatactUsResource(Resource):
    @token_required
    def post(self,active_user):
        try:
            data = request.get_json()

            name = data.get('name')
            email = data.get('email')
            description = data.get('description')

            if not name:
                message = get_normal_message("msg_68", active_user.active_language)
                return jsonify({'status': 0,'message': message})
            if not email:
                message = get_normal_message("msg_69", active_user.active_language)
                return jsonify({'status': 0,'message': message})
            if not description:
                message = get_normal_message("msg_60", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            random_request_id = '#'+generate_random_string2()

            add_contact_us = ContactUs(user_type=active_user.role,request_id=random_request_id,user_id = active_user.id,name=name,email=email,description=description,created_time = datetime.utcnow())
            db.session.add(add_contact_us)
            db.session.commit()

            message = get_normal_message("msg_70", active_user.active_language)

            return jsonify({'status': 1,'message': message})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrr:', str(e))
            message = get_normal_message("msg_10", active_user.active_language)
            return {'status': 0, 'message': message}, 500

class GetUserServiceListResource(Resource):
    @token_required
    def get(self,active_user):
        try:
            service_data = Services.query.filter(Services.is_deleted == False).all()

            services_list = [i.as_dict(active_user.active_language) for i in service_data]
            message = get_normal_message("msg_11", active_user.active_language)
            return jsonify({'status': 1,'message': message,'services_list': services_list})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrr:', str(e))
            message = get_normal_message("msg_10", active_user.active_language)
            return {'status': 0, 'message': message}, 500

class GetUserExtrasResource(Resource):
    @token_required
    def get(self,active_user):
        try:
            get_extras_data = Extras.query.filter(Extras.is_deleted == False).all()

            extras_list = [ i.as_dict(active_user.active_language) for i in get_extras_data ]

            message = get_normal_message("msg_11", active_user.active_language)

            return jsonify({'status':1,'message': message,'extras_list': extras_list})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrr:', str(e))
            message = get_normal_message("msg_10", active_user.active_language)
            return {'status': 0, 'message': message}, 500

class GetUserFaqsResource(Resource):
    @token_required
    def get(self,active_user):
        try:
            get_faqs = Faqs.query.all()

            faq_list = [ i.as_dict(active_user.active_language) for i in get_faqs ]

            if get_faqs:

                message = get_normal_message("msg_11", active_user.active_language)

                return jsonify({'status': 1,'message': message,'faq_list': faq_list})
            else:
                message = get_normal_message("msg_71", active_user.active_language)
                return jsonify({'status': 1, 'message': message})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrr:', str(e))
            message = get_normal_message("msg_10", active_user.active_language)
            return {'status': 0, 'message': message}, 500

class GetUserPrivacyPoliciesResource(Resource):
    @token_required
    def get(self,active_user):
        try:
            get_privacy = Cms.query.get(2)
            if get_privacy:
                message = get_normal_message("msg_11", active_user.active_language)
                return jsonify({'status': 1,'message': message,'data': get_privacy.as_dict(active_user.active_language)})
            else:
                message = get_normal_message("msg_72", active_user.active_language)
                return jsonify({'status': 1, 'message': message})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrr:', str(e))
            message = get_normal_message("msg_10", active_user.active_language)
            return {'status': 0, 'message': message}, 500

# before
# class UserBookingRequestResource(Resource):
#     @token_required
#     def post(self,active_user):
#         try:
#             if active_user.role == "Worker":
#                 message = get_normal_message("msg_16", active_user.active_language)
#                 return jsonify({'status': 0,'message': message})
#
#             data = request.get_json()
#
#             service_date = data.get('service_date')
#             # service_price = data.get('service_price')
#             slot_start_time = data.get('slot_start_time')
#             slot_end_time = data.get('slot_end_time')
#             service_id = data.get('service_id')
#             address_id = data.get('address_id')
#             car_id = data.get('car_id')
#             extras_id = data.get('extras_id')
#             payment_id = data.get('payment_id')
#
#             if not car_id:
#                 message = get_normal_message("msg_32", active_user.active_language)
#                 return jsonify({'status': 0,'message': message})
#             if not service_date:
#                 message = get_normal_message("msg_33", active_user.active_language)
#                 return jsonify({'status': 0,'message': message})
#             if not slot_start_time:
#                 message = get_normal_message("msg_34", active_user.active_language)
#                 return jsonify({'status': 0,'message': message})
#             if not slot_end_time:
#                 message = get_normal_message("msg_35", active_user.active_language)
#                 return jsonify({'status': 0,'message': message})
#             if not service_id:
#                 message = get_normal_message("msg_36", active_user.active_language)
#                 return jsonify({'status': 0,'message': message})
#             if not address_id:
#                 message = get_normal_message("msg_37", active_user.active_language)
#                 return jsonify({'status': 0,'message': message})
#
#             # payment_id is actully track id
#             get_payment_details = UserPayments.query.filter_by(user_id = active_user.id,track_id=payment_id,intend_status='Success').first()
#             if not get_payment_details:
#                 message = get_normal_message("msg_73", active_user.active_language)
#                 return jsonify({'status': 0,'message': message})
#
#             get_service_data = Services.query.get(service_id)
#             if not get_service_data:
#                 message = get_normal_message("msg_38", active_user.active_language)
#                 return jsonify({'status': 0, 'message': message})
#
#             get_address_data = UserAddress.query.filter_by(id=address_id,user_id = active_user.id).first()
#             if not get_address_data:
#                 message = get_normal_message("msg_39", active_user.active_language)
#                 return jsonify({'status': 0, 'message': message})
#
#             get_assign_provider_data = AssignProviderService.query.filter_by(place_id=get_address_data.place_id,
#                                                                             service_id=service_id).all()
#
#             if not len(get_assign_provider_data) > 0:
#                 message = get_normal_message("msg_74", active_user.active_language)
#                 return jsonify({'status': 0, 'message': message})
#
#             get_car_data = SavedUserCars.query.get(car_id)
#             if not get_car_data:
#                 message = get_normal_message("msg_40", active_user.active_language)
#                 return jsonify({'status': 0, 'message': message})
#
#             if extras_id:
#                 split_data = extras_id.split(',')
#                 if len(split_data)>0:
#                     for i in split_data:
#                         check_extras = Extras.query.get(i)
#                         if not check_extras:
#                             message = get_normal_message("msg_75", active_user.active_language)
#                             return jsonify({'status': 0,'message': message})
#
#
#             # Convert string to datetime object
#             date_obj = datetime.strptime(service_date, "%Y-%m-%d")
#
#             # Get full weekday name (e.g., "Monday")
#             day_name = date_obj.strftime("%A")
#             print('day_nameeeeeeeeeeeeeeeeeeeeeeeeeeee', day_name)
#
#             check_available_providers = []
#
#             for i in get_assign_provider_data:
#                 get_available_providers = ServiceRequested.query.filter(ServiceRequested.place_id==get_address_data.place_id,
#                                                                         ServiceRequested.service_day==day_name,
#                                                                         ServiceRequested.service_date==service_date,
#                                                                         ServiceRequested.slot_start_time==slot_start_time,
#                                                                         ServiceRequested.slot_end_time==slot_end_time,
#                                                                         ServiceRequested.provider_id == i.user_id,
#                                                                         ServiceRequested.status == 'Accepted'
#                                                                         # ServiceRequested.service_id == service_id,
#                                                                         # ServiceRequested.address_id == address_id
#                                                                         ).first()
#
#                 check_already_request = ServiceRequested.query.filter_by(car_id=car_id, provider_id=i.user_id,
#                                                                          user_id=active_user.id,
#                                                                          address_id=address_id, service_id=service_id,
#                                                                          place_id=get_address_data.place_id,
#                                                                          service_day=day_name,
#                                                                          slot_end_time=slot_end_time,
#                                                                          service_date=service_date,
#                                                                          slot_start_time=slot_start_time).first()
#
#                 if check_already_request:
#                     message = get_normal_message("msg_41", active_user.active_language)
#                     return jsonify({'status': 0, 'message': message})
#
#                 if not get_available_providers:
#
#                     add_request = ServiceRequested(payment_id=get_payment_details.payment_id,track_id=payment_id,extras_id=extras_id,car_id=car_id,provider_id =i.user_id,user_id = active_user.id,address_id=address_id,service_id=service_id,place_id=get_address_data.place_id,service_day=day_name,slot_end_time=slot_end_time,service_date=service_date,slot_start_time=slot_start_time,created_time=datetime.utcnow())
#                     db.session.add(add_request)
#                     db.session.commit()
#
#                     # ----------------------------------------------------------------------------
#
#                     reciver_user = User.query.get(i.user_id)
#                     if not reciver_user:
#                         message = get_normal_message("msg_52", active_user.active_language)
#                         return jsonify({'status': 0, 'message': message})
#
#                     titles, messages = {}, {}
#                     for lang in ("en", "ar", "bn"):
#                         localized_service = get_localized_service_name(get_service_data, lang)
#                         data = get_notification_message("requested", lang, localized_service)
#                         titles[lang], messages[lang] = data["title"], data["msg"]
#
#                     add_notification = Notification(service_request_id=add_request.id, title_en=titles["en"],
#                                                     title_ar=titles["ar"], title_bn=titles["bn"],
#                                                     message_en=messages["en"], message_ar=messages["ar"],
#                                                     message_bn=messages["bn"], by_id=active_user.id,
#                                                     to_id=reciver_user.id,
#                                                     is_read=False, created_time=datetime.utcnow(),
#                                                     notification_type='new service request')
#                     db.session.add(add_notification)
#                     db.session.commit()
#
#                     # Send push only in receiver’s active language
#                     user_lang = reciver_user.active_language if reciver_user.active_language in (
#                         "en", "ar", "bn") else "en"
#                     push_title = titles[user_lang]
#                     push_msg = messages[user_lang]
#
#                     if reciver_user.device_token:
#                         push_notification(
#                             token=reciver_user.device_token,
#                             title=push_title,
#                             body=push_msg
#                         )
#
#                 # ---------------------------------------------------------------------
#
#                     check_available_providers.append(i.user_id)
#
#             if len(check_available_providers)>0:
#                 # db.session.commit()
#
#                 service_dict = get_service_data.as_dict(active_user.active_language)
#
#                 request_dict = {
#                     'order_id': get_payment_details.payment_id,
#                     'service_day': day_name,
#                     'service_date': service_date,
#                     'is_completed': False,
#                     'service_start_time': slot_start_time,
#                     'service_end_time': slot_end_time,
#                     'status': "Pending",
#                     'service_name': service_dict['service_name'],
#                     'service_description': service_dict['service_description'],
#                     'service_price': get_service_data.service_price,
#                     'service_image': generate_presigned_url(get_service_data.image_name) if get_service_data.image_name is not None else '',
#                     'car_number_plate': get_car_data.number_plate,
#                     'car_colour_code': get_car_data.colour_code,
#                     'car_year': get_car_data.year,
#                     'car_brand': get_car_data.saved_brand.name,
#                     'car_model': get_car_data.saved_model.model,
#                     'user_address': get_address_data.address,
#                     'place_type': get_address_data.place_type,
#                     'place_id': get_address_data.place_id,
#                     'address_lat': get_address_data.lat,
#                     'address_long': get_address_data.long,
#                     'house_no': get_address_data.house_no,
#                     'city': get_address_data.city,
#                     'state': get_address_data.state
#
#                 }
#                 message = get_normal_message("msg_76", active_user.active_language)
#                 return jsonify({'status': 1,'message': message,'request_data': request_dict})
#             else:
#                 message = get_normal_message("msg_77", active_user.active_language)
#                 return jsonify({'status': 0, 'message': message})
#
#         except Exception as e:
#             print('errorrrrrrrrrrrrrrrrr:', str(e))
#             message = get_normal_message("msg_10", active_user.active_language)
#             return {'status': 0, 'message': message}, 500

class UserBookingRequestResource(Resource):
    @token_required
    def post(self,active_user):
        try:
            if active_user.role == "Worker":
                message = get_normal_message("msg_16", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            data = request.get_json()

            service_date = data.get('service_date')
            slot_start_time = data.get('slot_start_time')
            slot_end_time = data.get('slot_end_time')
            service_id = data.get('service_id')
            address_id = data.get('address_id')
            car_id = data.get('car_id')
            extras_id = data.get('extras_id')
            payment_id = data.get('payment_id')

            print('dataaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',data)

            if not car_id:
                message = get_normal_message("msg_32", active_user.active_language)
                return jsonify({'status': 0,'message': message})
            if not service_date:
                message = get_normal_message("msg_33", active_user.active_language)
                return jsonify({'status': 0,'message': message})
            if not slot_start_time:
                message = get_normal_message("msg_34", active_user.active_language)
                return jsonify({'status': 0,'message': message})
            if not slot_end_time:
                message = get_normal_message("msg_35", active_user.active_language)
                return jsonify({'status': 0,'message': message})
            if not service_id:
                message = get_normal_message("msg_36", active_user.active_language)
                return jsonify({'status': 0,'message': message})
            if not address_id:
                message = get_normal_message("msg_37", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            # payment_id is actully track id
            get_payment_details = UserPayments.query.filter_by(user_id = active_user.id,track_id=payment_id,intend_status='Success').first()
            if not get_payment_details:
                message = get_normal_message("msg_73", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            get_service_data = Services.query.get(service_id)
            if not get_service_data:
                message = get_normal_message("msg_38", active_user.active_language)
                return jsonify({'status': 0, 'message': message})

            get_address_data = UserAddress.query.filter_by(id=address_id,user_id = active_user.id).first()
            if not get_address_data:
                message = get_normal_message("msg_39", active_user.active_language)
                return jsonify({'status': 0, 'message': message})

            get_assign_provider_data = AssignProviderService.query.filter_by(service_id=service_id).all()

            if not len(get_assign_provider_data) > 0:
                message = get_normal_message("msg_74", active_user.active_language)
                return jsonify({'status': 0, 'message': message})

            matched_zone_assign_data = []

            for i in get_assign_provider_data:
                # if is_zone_found:
                #     break  # stop checking once we already found a match

                matched_zone = find_assign_zone_for_latlng(i.subzone_polygon_geojson, get_address_data.lat,
                                                           get_address_data.long, accept_border=True)
                # if matched_zone:
                #     is_zone_found = True

                if matched_zone:
                    print('matched_zoneee', matched_zone)
                    matched_zone_assign_data.append(i)

            # if is_zone_found == False:

            if not len(matched_zone_assign_data) > 0:
                message = get_normal_message("msg_104", active_user.active_language)
                return jsonify({'status': 0, 'message': message})




            get_car_data = SavedUserCars.query.get(car_id)
            if not get_car_data:
                message = get_normal_message("msg_40", active_user.active_language)
                return jsonify({'status': 0, 'message': message})

            if extras_id:
                split_data = extras_id.split(',')
                if len(split_data)>0:
                    for i in split_data:
                        check_extras = Extras.query.get(i)
                        if not check_extras:
                            message = get_normal_message("msg_75", active_user.active_language)
                            return jsonify({'status': 0,'message': message})

            # Convert string to datetime object
            date_obj = datetime.strptime(service_date, "%Y-%m-%d")

            # Get full weekday name (e.g., "Monday")
            day_name = date_obj.strftime("%A")
            print('day_nameeeeeeeeeeeeeeeeeeeeeeeeeeee', day_name)

            available_providers_id = []

            check_already_request = ServiceRequested.query.filter_by(car_id=car_id,
                                                                     user_id=active_user.id,
                                                                     address_id=address_id, service_id=service_id,
                                                                     # place_id=get_address_data.place_id,
                                                                     service_day=day_name,
                                                                     slot_end_time=slot_end_time,
                                                                     service_date=service_date,
                                                                     slot_start_time=slot_start_time).first()

            if check_already_request:
                message = get_normal_message("msg_41", active_user.active_language)
                return jsonify({'status': 0, 'message': message})

            check_available_request = ServiceRequested.query.filter(
                # ServiceRequested.place_id == get_address_data.place_id,
                ServiceRequested.service_day == day_name,
                ServiceRequested.service_date == service_date,
                ServiceRequested.slot_start_time == slot_start_time,
                ServiceRequested.slot_end_time == slot_end_time
                ).first()

            for i in matched_zone_assign_data:

                excluded = ["Pending", "Cancelled","Late"]

                if check_available_request:

                    check_requested_providers = ProviderRequest.query.filter(ProviderRequest.service_request_id==check_available_request.id,ProviderRequest.provider_id == i.user_id).first()

                    if check_requested_providers:

                        if check_requested_providers.status in excluded:
                            available_providers_id.append(i.user_id)

                else:
                    available_providers_id.append(i.user_id)

            add_request = ServiceRequested(payment_id=get_payment_details.payment_id, track_id=payment_id,
                                           extras_id=extras_id, car_id=car_id,
                                           user_id=active_user.id, address_id=address_id, service_id=service_id,
                                           place_id=get_address_data.place_id, service_day=day_name,
                                           slot_end_time=slot_end_time, service_date=service_date,
                                           slot_start_time=slot_start_time, created_time=datetime.utcnow())
            db.session.add(add_request)
            db.session.commit()

            if len(available_providers_id)>0:

                for i in available_providers_id:

                    reciver_user = User.query.get(i)
                    if not reciver_user:
                        message = get_normal_message("msg_52", active_user.active_language)
                        return jsonify({'status': 0, 'message': message})

                    add_request_provider = ProviderRequest(provider_id=i,user_id=active_user.id,service_request_id=add_request.id)
                    db.session.add(add_request_provider)
                    db.session.commit()

                    # ----------------------------------------------------------------------------

                    titles, messages = {}, {}
                    for lang in ("en", "ar", "bn"):
                        localized_service = get_localized_service_name(get_service_data, lang)
                        data = get_notification_message("requested", lang, localized_service)
                        titles[lang], messages[lang] = data["title"], data["msg"]

                    add_notification = Notification(service_request_id=add_request.id, title_en=titles["en"],
                                                    title_ar=titles["ar"], title_bn=titles["bn"],
                                                    message_en=messages["en"], message_ar=messages["ar"],
                                                    message_bn=messages["bn"], by_id=active_user.id,
                                                    to_id=reciver_user.id,
                                                    is_read=False, created_time=datetime.utcnow(),
                                                    notification_type='new service request')
                    db.session.add(add_notification)
                    db.session.commit()

                    # Send push only in receiver’s active language
                    user_lang = reciver_user.active_language if reciver_user.active_language in (
                        "en", "ar", "bn") else "en"
                    push_title = titles[user_lang]
                    push_msg = messages[user_lang]

                    if reciver_user.device_token:
                        push_notification(
                            token=reciver_user.device_token,
                            title=push_title,
                            body=push_msg
                        )

                service_dict = get_service_data.as_dict(active_user.active_language)

                request_dict = {
                    'order_id': get_payment_details.payment_id,
                    'service_day': day_name,
                    'service_date': service_date,
                    'is_completed': False,
                    'service_start_time': slot_start_time,
                    'service_end_time': slot_end_time,
                    'status': "Pending",
                    'service_name': service_dict['service_name'],
                    'service_description': service_dict['service_description'],
                    'service_price': get_service_data.service_price,
                    'service_image': generate_presigned_url(
                    get_service_data.image_name) if get_service_data.image_name is not None else '',
                    'car_number_plate': get_car_data.number_plate,
                    'car_colour_code': get_car_data.colour_code,
                    'car_year': get_car_data.year,
                    'car_brand': get_car_data.saved_brand.name,
                    'car_model': get_car_data.saved_model.model,
                    'user_address': get_address_data.address,
                    'place_type': get_address_data.place_type,
                    'place_id': get_address_data.place_id,
                    'address_lat': get_address_data.lat,
                    'address_long': get_address_data.long,
                    'house_no': get_address_data.house_no,
                    'city': get_address_data.city,
                    'state': get_address_data.state

                }
                message = get_normal_message("msg_76", active_user.active_language)
                if active_user.device_token != None:
                    notification = push_notification(token=active_user.device_token, title=None, body=None,
                                                     data=request_dict)

                return jsonify({'status': 1, 'message': message, 'request_data': request_dict})
            else:
                message = get_normal_message("msg_77", active_user.active_language)
                return jsonify({'status': 0, 'message': message})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrr:', str(e))
            message = get_normal_message("msg_10", active_user.active_language)
            return {'status': 0, 'message': message}, 500

class SendStaticNotificationResource(Resource):
    def get(self):
        request_dict = {
            'order_id': "600202526094264046",
            'service_day': "Thursday",
            'service_date': "2025-09-18",
            'is_completed': "False",
            'service_start_time': "13:00",
            'service_end_time': "14:00",
            'status': "Pending",
            'service_name': "Basic Wash",
            'service_description': "Exterior wash with soap, rinse, and air dry. Perfect for a quick clean to remove dirt and grime.",
            'service_price': "20",
            'service_image': "https://s3.me-central-1.amazonaws.com/vloobucket/706738c6ec3dedd6c0c9.webp?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAUMYCIQSVLVGYFGG7%2F20250918%2Fme-central-1%2Fs3%2Faws4_request&X-Amz-Date=20250918T140534Z&X-Amz-Expires=28800&X-Amz-SignedHeaders=host&X-Amz-Signature=e59bc63ba142fd4453b857625d389cec669c971f75f4bbd53e6f767bd6271983",
            'car_number_plate': "GJ 01XS 4096",
            'car_colour_code': "#000000",
            'car_year': "2010",
            'car_brand': "Acura",
            'car_model': "RL",
            'user_address': "XGVV+5GC, Vishala, Ahmedabad, Gujarat 380007, India",
            'place_type': "Home",
            'place_id': "ChIJqevXWxSFXjkRPHer9Pnnh3Q",
            'address_lat': "22.992945599204848",
            'address_long': "72.5437730178237",
            'house_no': "fg",
            'city': "Ahmedabad",
            'state': "Gujarat"
        }

        # request_dict = {
        #     'order_id': "",
        #     'service_day': "",
        #     'service_date': "",
        #     'is_completed': "",
        #     'service_start_time': "",
        #     'service_end_time': "",
        #     'status': "",
        #     'service_name': "",
        #     'service_description': "",
        #     'service_price': "",
        #     'service_image': "",
        #     'car_number_plate': "",
        #     'car_colour_code': "",
        #     'car_year': "",
        #     'car_brand': "",
        #     'car_model': "",
        #     'user_address': "",
        #     'place_type': "",
        #     'place_id': "",
        #     'address_lat': "",
        #     'address_long': "",
        #     'house_no': "",
        #     'city': "",
        #     'state': ""
        # }

        notification = push_notification(token="f1GOXAzmt0hogod-hS5juQ:APA91bG48WZ7nmUvARBdHdK88H-QlAvq8Z-VuwYaqR5P8lfGUqhL2Ul3BkD9QJYw4nnA-uPSOUPVBxwwPDChxt1l3r2avBjx5SDf4M0OAUTGNYqAiECWVY8", title=None, body=None,
                                         data=request_dict)

        return jsonify({'status': 1})

class GetUserSlotsResource(Resource):
    @token_required
    def post(self,active_user):
        try:
            # from frontent when select address that time need to validate place id is same with service id and address id only than they can go forward for getting slots
            # Show all slots with avalaible or not------ also before booking slot validate 2hr before time only
            # if start time of slots pass away so show disable

            if active_user.role == "Worker":
                message = get_normal_message("msg_16", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            data = request.get_json()

            service_id = data.get('service_id')
            address_id = data.get('address_id')
            # car_id = data.get('car_id')
            # slot_id = data.get('slot_id')
            slot_date = data.get('slot_date')

            if not service_id:
                message = get_normal_message("msg_36", active_user.active_language)
                return jsonify({'status': 0,'message': message})
            if not address_id:
                message = get_normal_message("msg_37", active_user.active_language)
                return jsonify({'status': 0,'message': message})
            if not slot_date:
                message = get_normal_message("msg_78", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            get_service_data = Services.query.get(service_id)
            if not get_service_data:
                message = get_normal_message("msg_38", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            get_address_data = UserAddress.query.get(address_id)
            if not get_address_data:
                message = get_normal_message("msg_39", active_user.active_language)
                return jsonify({'status': 0, 'message': message})

            get_asign_provider_data = AssignProviderService.query.filter_by(service_id=service_id).all()

            if not len(get_asign_provider_data)>0:
                message = get_normal_message("msg_79", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            # is_zone_found = False

            matched_zone_assign_data = []

            for i in get_asign_provider_data:
                # if is_zone_found:
                #     break  # stop checking once we already found a match

                matched_zone = find_assign_zone_for_latlng(i.subzone_polygon_geojson, get_address_data.lat, get_address_data.long, accept_border=True)
                # if matched_zone:
                #     is_zone_found = True

                if matched_zone:
                    print('matched_zoneee',matched_zone)
                    matched_zone_assign_data.append(i)

            # if is_zone_found == False:

            if not len(matched_zone_assign_data)>0:
                message = get_normal_message("msg_104", active_user.active_language)
                return jsonify({'status': 0, 'message': message})

            # Convert string to datetime object
            date_obj = datetime.strptime(slot_date, "%Y-%m-%d")

            # Get full weekday name (e.g., "Monday")
            day_name = date_obj.strftime("%A")
            print('day_nameeeeeeeeeeeeeeeeeeeeeeeeeeee',day_name)

            # user_timezone = active_user.timezone

            # get_slots_data = ProviderSlots.query.filter(ProviderSlots.user_id==active_user.id,ProviderSlots.is_selected == True,ProviderSlots.day == day_name).all()

            store_data = Store.query.filter(Store.day == day_name).first()
            print('store_dataaaaaaaaaaaaaaaaaaaaaaaa',store_data)

            if not store_data:
                message = get_normal_message("msg_80", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            slot_list = get_hourly_slots(day_name)

            print('slot_listttttttttttttttt',slot_list)

            if len(slot_list)>0:
                for i in slot_list:
                    check_selected_list = []

                    for k in matched_zone_assign_data:

                        # ProviderSlots.day all day same time slot is selected true false
                        check_selected = ProviderSlots.query.filter(ProviderSlots.is_selected == True,
                                                                    ProviderSlots.day == day_name,
                                                                    ProviderSlots.start_time == i['start_time'],
                                                                    ProviderSlots.end_time == i['end_time'],
                                                                    ProviderSlots.user_id == k.user_id
                                                                    ).all()

                        print('check_selected',check_selected)
                        check_selected_list.extend(check_selected)


                    available_providers_counts = 0

                    if len(check_selected_list) > 0:
                        for j in check_selected_list:

                            request_status = ["Accepted","Completed"]

                            get_not_available_providers = (
                                    db.session.query(ServiceRequested.id)
                                    .join(ProviderRequest, ProviderRequest.service_request_id == ServiceRequested.id)
                            .filter(
                                # ServiceRequested.place_id == get_address_data.place_id,
                                ServiceRequested.service_day == day_name,
                                ServiceRequested.service_date == slot_date,
                                ServiceRequested.slot_start_time == i['start_time'],
                                ServiceRequested.slot_end_time == i['end_time'],
                                ProviderRequest.provider_id == j.user_id,
                                ProviderRequest.status.in_(request_status),

                                        ).first()
                            )

                            if not get_not_available_providers:
                                available_providers_counts += 1

                    print('available_providers_counts', available_providers_counts)

                    if available_providers_counts > 0:
                        i['status'] = "Available"
                    else:
                        i['status'] = "Not Available"
            get_slot_disable_before_data = SlotDisableTime.query.first()

            slot_disable_before = 1

            if get_slot_disable_before_data:
                slot_disable_before = get_slot_disable_before_data.slot_disable_before

            message = get_normal_message("msg_11", active_user.active_language)
            return jsonify({'status': 1,'message': message,'slot_list': slot_list,'slot_disable_before': slot_disable_before})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrr:', str(e))
            message = get_normal_message("msg_10", active_user.active_language)
            return {'status': 0, 'message': message}, 500

class UserAddCarsResource(Resource):
    @token_required
    def post(self, active_user):
        try:
            if active_user.role == "Worker":
                message = get_normal_message("msg_16", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            data = request.get_json()

            car_brand = data.get('car_brand')
            car_model = data.get('car_model')
            year = data.get('year')
            number_plate = data.get('number_plate')
            colour_code = data.get('colour_code')

            if not car_brand:
                message = get_normal_message("msg_81", active_user.active_language)
                return jsonify({'status': 0,'message': message})
            if not car_model:
                message = get_normal_message("msg_82", active_user.active_language)
                return jsonify({'status': 0,'message': message})
            if not year:
                message = get_normal_message("msg_83", active_user.active_language)
                return jsonify({'status': 0,'message': message})
            if not number_plate:
                message = get_normal_message("msg_84", active_user.active_language)
                return jsonify({'status': 0,'message': message})
            if not colour_code:
                message = get_normal_message("msg_85", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            get_brand = CarBrands.query.get(car_brand)
            if not get_brand:
                message = get_normal_message("msg_86", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            get_model = CarModels.query.filter_by(id=car_model,car_brand_id=get_brand.id).first()
            if not get_model:
                message = get_normal_message("msg_87", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            saved_car_data = SavedUserCars(colour_code=colour_code,year=year,number_plate=number_plate,created_time = datetime.utcnow(),user_id = active_user.id,car_brand_id=get_brand.id,car_model_id=get_model.id)
            db.session.add(saved_car_data)
            db.session.commit()

            car_data = {

                'id': saved_car_data.id,
                'car_brand': get_brand.name,
                'car_model': get_model.model,
                'colour_code': colour_code,
                'number_plate': number_plate,
                'year': year

            }
            message = get_normal_message("msg_88", active_user.active_language)
            return jsonify({'status': 1,'message': message,'car_data': car_data })

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            message = get_normal_message("msg_10", active_user.active_language)
            return {'status': 0, 'message': message}, 400

    @token_required
    def get(self, active_user):
        try:
            if active_user.role == "Worker":
                message = get_normal_message("msg_16", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            get_car_data = SavedUserCars.query.filter(SavedUserCars.user_id == active_user.id,SavedUserCars.is_deleted == False).all()

            car_list = []

            if len(get_car_data)>0:
                for i in get_car_data:
                    car_dict = {

                        'id': i.id,
                        'car_brand': i.saved_brand.name,
                        'car_model': i.saved_model.model,
                        'colour_code': i.colour_code,
                        'number_plate': i.number_plate,
                        'year': i.year
                    }

                    car_list.append(car_dict)
            message = get_normal_message("msg_11", active_user.active_language)
            return jsonify({'status':1,'message': message,'car_list': car_list})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            message = get_normal_message("msg_10", active_user.active_language)
            return {'status': 0, 'message': message}, 400

    @token_required
    def delete(self, active_user):
        try:
            if active_user.role == "Worker":
                message = get_normal_message("msg_16", active_user.active_language)
                return jsonify({'status': 0, 'message': message})

            data = request.get_json()

            car_id = data.get('car_id')

            if not car_id:
                message = get_normal_message("msg_32", active_user.active_language)
                return jsonify({'status':0,'message': message})

            get_car_data = SavedUserCars.query.get(car_id)
            if not get_car_data:
                message = get_normal_message("msg_40", active_user.active_language)
                return jsonify({'status':1,'message': message})

            get_car_data.is_deleted = True
            db.session.commit()
            message = get_normal_message("msg_89", active_user.active_language)
            return jsonify({'status':1,'message': message})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            message = get_normal_message("msg_10", active_user.active_language)
            return {'status': 0, 'message': message}, 400

class UserMetadataResource(Resource):
    @token_required
    def get(self, active_user):
        try:
            get_brands_data = (
                CarBrands.query
                    .filter(CarBrands.is_deleted == False)
                    .order_by(desc(CarBrands.is_popular), asc(CarBrands.name))
                    .all()
            )

            # get_brands_data = CarBrands.query.filter(CarBrands.is_deleted == False).order_by(CarBrands.name.asc()).all()

            car_list = [ i.as_dict_merge() for i in get_brands_data ]

            get_faqs = Faqs.query.all()

            faq_list = [i.as_dict(active_user.active_language) for i in get_faqs]

            get_privacy = Cms.query.get(2)

            privacy_dict = {}
            if get_privacy:
                privacy_dict = get_privacy.as_dict(active_user.active_language)

            get_about_us = Cms.query.get(3)

            about_us_dict = {}
            if get_about_us:
                about_us_dict = get_about_us.as_dict(active_user.active_language)
            message = get_normal_message("msg_11", active_user.active_language)
            return jsonify({'status': 1,'message': message,'car_list': car_list,'faq_list': faq_list,'privacy_data': privacy_dict,'about_us_data': about_us_dict})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            message = get_normal_message("msg_10", active_user.active_language)
            return {'status': 0, 'message': message}, 400

class UserCarsBrandListingResource(Resource):
    @token_required
    def get(self, active_user):
        try:
            get_brands_data = CarBrands.query.filter(CarBrands.is_deleted==False).order_by(CarBrands.name.asc()).all()

            car_brand_list = [ i.as_dict() for i in get_brands_data ]
            message = get_normal_message("msg_11", active_user.active_language)
            return jsonify(
                {'status': 1, 'message': message, 'car_brand_list': car_brand_list})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            message = get_normal_message("msg_10", active_user.active_language)
            return {'status': 0, 'message': message}, 400

class UserCarsModelListingResource(Resource):
    @token_required
    def post(self, active_user):
        try:
            data = request.get_json()

            brand_id = data.get('brand_id')
            if not brand_id:
                message = get_normal_message("msg_81", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            get_models_data = CarModels.query.filter(CarModels.is_deleted == False,CarModels.car_brand_id==brand_id).order_by(CarModels.model.asc()).all()

            car_models_list = [ i.as_dict() for i in get_models_data ]
            message = get_normal_message("msg_11", active_user.active_language)
            return jsonify(
                {'status': 1, 'message': message, 'car_models_list': car_models_list})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            message = get_normal_message("msg_10", active_user.active_language)
            return {'status': 0, 'message': message}, 400

class GetProviderSlotsResource(Resource):
    @token_required
    def get(self,active_user):
        try:
            # ["Available","Not Available","Pending"]

            if active_user.role == "Customer":
                message = get_normal_message("msg_48", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            get_store_data = Store.query.all()

            if len(get_store_data) > 0:
                for i in get_store_data:
                    slot_list = get_hourly_slots(i.day)
                    if len(slot_list) > 0:
                        for j in slot_list:
                            get_slot_data = ProviderSlots.query.filter(ProviderSlots.user_id == active_user.id,
                                                                       ProviderSlots.day == i.day,
                                                                       ProviderSlots.start_time == j['start_time'],
                                                                       ProviderSlots.end_time == j['end_time']).first()
                            if not get_slot_data:
                                add_new_slots = ProviderSlots(user_id=active_user.id, day=i.day,
                                                              start_time=j['start_time'], end_time=j['end_time'])
                                db.session.add(add_new_slots)

                        db.session.commit()

            # get_slots_data = ProviderSlots.query.filter_by(user_id = active_user.id).all()

            get_slots_data = (
                ProviderSlots.query
                    .filter_by(user_id=active_user.id)
                    .order_by(cast(ProviderSlots.start_time, Time).asc())
                    .all()
            )

            Monday = []
            Tuesday = []
            Wednesday = []
            Thursday = []
            Friday = []
            Saterday = []
            Sunday = []

            if len(get_slots_data)>0:
                for i in get_slots_data:
                    if i.day == "Monday":
                        Monday.append(i.as_dict())
                    elif i.day == "Tuesday":
                        Tuesday.append(i.as_dict())
                    elif i.day == "Wednesday":
                        Wednesday.append(i.as_dict())
                    elif i.day == "Thursday":
                        Thursday.append(i.as_dict())
                    elif i.day == "Friday":
                        Friday.append(i.as_dict())
                    elif i.day == "Saturday":
                        Saterday.append(i.as_dict())
                    elif i.day == "Sunday":
                        Sunday.append(i.as_dict())
                    else:
                        message = get_normal_message("msg_90", active_user.active_language)
                        return jsonify({'status': 0,'message': message})

            slot_data = [
            {

                'day': "Monday",
                'slot_list': Monday
            },{

                'day': "Tuesday",
                'slot_list': Tuesday
            },{

                'day': "Wednesday",
                'slot_list': Wednesday
            },{

                'day': "Thursday",
                'slot_list': Thursday
            },{

                'day': "Friday",
                'slot_list': Friday
            },{

                'day': "Saterday",
                'slot_list': Saterday
            },{

                'day': "Sunday",
                'slot_list': Sunday
            }

            ]
            message = get_normal_message("msg_11", active_user.active_language)
            return jsonify({'status': 1,'message': message,'slot_data': slot_data})


        except Exception as e:
            print('errorrrrrrrrrrrrrrrrr:', str(e))
            message = get_normal_message("msg_10", active_user.active_language)
            return {'status': 0, 'message': message}, 400

    @token_required
    def put(self, active_user):
        try:
            if active_user.role == "Customer":
                message = get_normal_message("msg_48", active_user.active_language)
                return jsonify({'status': 0, 'message': message})

            data = request.get_json()
            if not data:
                message = get_normal_message("msg_91", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            get_slots_data = data.get('slot_data')

            if not get_slots_data:
                message = get_normal_message("msg_92", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            for i in get_slots_data:
                slot_list = i['slot_list']
                if not slot_list:
                    message = get_normal_message("msg_93", active_user.active_language)
                    return jsonify({'status': 0,'message': message})

                for j in slot_list:
                    print('jjjjjj',j)

                    slot_id = j['id']
                    is_selected = j['is_selected']
                    print('is_selected',is_selected)

                    if not slot_id:
                        message = get_normal_message("msg_94", active_user.active_language)
                        return jsonify({'status': 0,'message': message})
                    if is_selected is None or is_selected == "":
                        message = get_normal_message("msg_95", active_user.active_language)
                        return jsonify({'status': 0,'message': message})

                    get_slot = ProviderSlots.query.filter_by(id = slot_id,user_id = active_user.id).first()
                    if not get_slot:
                        message = get_normal_message("msg_96", active_user.active_language)
                        return jsonify({'status': 0,'message': message})

                    get_slot.is_selected = is_selected

            db.session.commit()
            message = get_normal_message("msg_97", active_user.active_language)
            return jsonify({'status': 1,'message': message,'slot_data': get_slots_data})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrr:', str(e))
            message = get_normal_message("msg_10", active_user.active_language)
            return {'status': 0, 'message': message}, 500

class CustomerAddressResource(Resource):
    @token_required
    def post(self,active_user):
        try:
            if active_user.role == "Worker":
                message = get_normal_message("msg_16", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            data = request.get_json()

            place_type = data.get('place_type')
            lat = data.get('lat')
            long = data.get('long')
            place_id = data.get('place_id')
            house_no = data.get('house_no')
            address = data.get('address')
            city = data.get('city')
            state = data.get('state')

            print('data',data)

            if not house_no:
                message = get_normal_message("msg_98", active_user.active_language)
                return jsonify({'status':0,'message': message})
            if not address:
                message = get_normal_message("msg_99", active_user.active_language)
                return jsonify({'status':0,'message': message})
            if not place_type:
                message = get_normal_message("msg_100", active_user.active_language)
                return jsonify({'status':0,'message': message})
            if not lat:
                message = get_normal_message("msg_101", active_user.active_language)
                return jsonify({'status':0,'message': message})
            if not long:
                message = get_normal_message("msg_102", active_user.active_language)
                return jsonify({'status':0,'message': message})
            if not place_id or place_id == '':
                message = get_normal_message("msg_103", active_user.active_language)
                return jsonify({'status':0,'message': message})

            # get_zone_details = Zone.query.filter_by(place_id = place_id).first()
            # print('get_zone_details',get_zone_details)
            # if not get_zone_details:

            zones = SubZone.query.filter_by(is_deleted = False).all()
            matched_zone = find_zone_for_latlng(zones, lat, long, accept_border=True)

            if not matched_zone:
                message = get_normal_message("msg_104", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            check_exists = UserAddress.query.filter_by(user_id = active_user.id).first()

            is_active = True if bool(check_exists) == False else False

            add_address = UserAddress(house_no=house_no,city = city,state=state,place_type=place_type,lat=lat,long=long,place_id=place_id,address=address,created_time=datetime.utcnow(),is_active=is_active,user_id = active_user.id)
            db.session.add(add_address)
            db.session.commit()

            message = get_normal_message("msg_105", active_user.active_language)

            return jsonify({'status': 1,'message': message})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrr:', str(e))
            message = get_normal_message("msg_10", active_user.active_language)
            return {'status': 0, 'message': message}, 500

    @token_required
    def put(self, active_user):
        try:
            if active_user.role == "Worker":
                message = get_normal_message("msg_16", active_user.active_language)
                return jsonify({'status': 0, 'message': message})

            data = request.get_json()

            place_type = data.get('place_type')
            lat = data.get('lat')
            long = data.get('long')
            place_id = data.get('place_id')
            house_no = data.get('house_no')
            address = data.get('address')
            city = data.get('city')
            state = data.get('state')
            address_id = data.get('address_id')

            print('data', data)

            if not address_id:
                message = get_normal_message("msg_106", active_user.active_language)
                return jsonify({'status': 0, 'message': message})
            if not house_no:
                message = get_normal_message("msg_98", active_user.active_language)
                return jsonify({'status':0,'message': message})
            if not address:
                message = get_normal_message("msg_99", active_user.active_language)
                return jsonify({'status':0,'message': message})
            if not place_type:
                message = get_normal_message("msg_100", active_user.active_language)
                return jsonify({'status':0,'message': message})
            if not lat:
                message = get_normal_message("msg_101", active_user.active_language)
                return jsonify({'status':0,'message': message})
            if not long:
                message = get_normal_message("msg_102", active_user.active_language)
                return jsonify({'status':0,'message': message})
            if not place_id or place_id == '':
                message = get_normal_message("msg_103", active_user.active_language)
                return jsonify({'status':0,'message': message})

            # get_zone_details = Zone.query.filter_by(place_id=place_id).first()
            # print('get_zone_details', get_zone_details)
            # if not get_zone_details:
            #     message = get_normal_message("msg_104", active_user.active_language)
            #     return jsonify({'status': 0, 'message': message})

            zones = SubZone.query.all()
            matched_zone = find_zone_for_latlng(zones, lat, long, accept_border=True)

            if not matched_zone:
                message = get_normal_message("msg_104", active_user.active_language)
                return jsonify({'status': 0, 'message': message})

            check_exists = UserAddress.query.filter_by(user_id=active_user.id,id=address_id).first()

            if not check_exists:
                message = get_normal_message("msg_107", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            check_exists.house_no = house_no
            check_exists.city = city
            check_exists.state = state
            check_exists.place_type = place_type
            check_exists.lat = lat
            check_exists.long = long
            check_exists.place_id = place_id
            check_exists.address = address

            db.session.commit()

            message = get_normal_message("msg_108", active_user.active_language)
            return jsonify({'status': 1, 'message': message})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrr:', str(e))
            message = get_normal_message("msg_10", active_user.active_language)
            return {'status': 0, 'message': message}, 500

    @token_required
    def delete(self, active_user):
        try:
            if active_user.role == "Worker":
                message = get_normal_message("msg_16", active_user.active_language)
                return jsonify({'status': 0, 'message': message})

            data = request.get_json()

            address_id = data.get('address_id')

            if not address_id:
                message = get_normal_message("msg_109", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            get_address = UserAddress.query.filter_by(user_id = active_user.id,id = address_id).first()
            if not get_address:
                message = get_normal_message("msg_107", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            else:
                db.session.delete(get_address)
                db.session.commit()
                message = get_normal_message("msg_110", active_user.active_language)
                return jsonify({'status':1,'message': message})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrr:', str(e))
            message = get_normal_message("msg_10", active_user.active_language)
            return {'status': 0, 'message': message}, 500

    @token_required
    def get(self, active_user):
        try:
            if active_user.role == "Worker":
                message = get_normal_message("msg_16", active_user.active_language)
                return jsonify({'status': 0, 'message': message})

            get_address_data = UserAddress.query.filter_by(user_id = active_user.id).all()

            address_list = [ i.as_dict() for i in get_address_data ]
            message = get_normal_message("msg_11", active_user.active_language)
            return jsonify({'status': 1,'message': message,'address_list': address_list})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrr:', str(e))
            message = get_normal_message("msg_10", active_user.active_language)
            return {'status': 0, 'message': message}, 500

class HomepageResource(Resource):
    @token_required
    def get(self,active_user):
        try:
            if active_user.role == "Worker":
                message = get_normal_message("msg_16", active_user.active_language)
                return jsonify({'status': 0, 'message': message})

            get_banners_data = Banners.query.filter(Banners.is_active == True).all()

            banner_list = [ i.as_dict() for i in get_banners_data ]

            notification_count = 0

            service_data = Services.query.filter(Services.is_deleted == False).all()

            services_list = [ i.as_dict(active_user.active_language) for i in service_data ]

            # request_status = [ "Pending","Accepted" ]
            #
            # get_request_data = ServiceRequested.query.filter(
            #         ServiceRequested.user_id == active_user.id,ServiceRequested.is_completed == False,
            #         ServiceRequested.status.in_(request_status)
            #     ).order_by(desc(ServiceRequested.id)).all()

            request_status = ["Pending", "Accepted"]

            get_request_data = (
                ServiceRequested.query.filter(
                    ServiceRequested.user_id == active_user.id,
                    ServiceRequested.is_completed == False,
                    ServiceRequested.status.in_(request_status),
                )
                    .order_by(ServiceRequested.id.desc())
                    .all()
            )

            request_list = []

            if len(get_request_data)>0:
                for i in get_request_data:

                    get_accepted_provider = ProviderRequest.query.filter_by(service_request_id = i.id,status = "Accepted").first()
                    get_pending_provider = ProviderRequest.query.filter_by(service_request_id=i.id,
                                                                            status="Pending").first()

                    if not get_accepted_provider and not get_pending_provider:
                        message = get_normal_message("msg_112", active_user.active_language)
                        return jsonify({'status': 0,'message': message})

                    provider_id = None

                    if get_accepted_provider:
                        provider_id = get_accepted_provider.provider_id
                    if get_pending_provider:
                        provider_id = get_pending_provider.provider_id

                    user_data = User.query.get(provider_id)

                    get_service_data = Services.query.get(i.service_id)
                    get_car_data = SavedUserCars.query.get(i.car_id)
                    get_address_data = UserAddress.query.get(i.address_id)
                    get_service_completed_data = ServiceCompletedData.query.filter_by(service_request_id = i.id).first()

                    if get_service_completed_data:
                        completed_data = {
                            'id': get_service_completed_data.id,
                            'before_image_one': generate_presigned_url(get_service_completed_data.before_image_name_1) if get_service_completed_data.before_image_name_1 is not None else '',
                            'before_image_two': generate_presigned_url(get_service_completed_data.before_image_name_2) if get_service_completed_data.before_image_name_2 is not None else '',
                            'after_image_one': generate_presigned_url(get_service_completed_data.after_image_name_1) if get_service_completed_data.after_image_name_1 is not None else '',
                            'after_image_two': generate_presigned_url(get_service_completed_data.after_image_name_2) if get_service_completed_data.after_image_name_2 is not None else ''
                        }

                    else:
                        completed_data = {}

                    status_replace = i.status

                    is_service_accepted = False

                    if i.status == "Accepted":
                        status_replace = "In Progress"
                        is_service_accepted = True

                    service_stage = {

                        'is_service_start': i.is_service_start,
                        'start_service_time': i.start_service_time if i.start_service_time is not None else '',
                        'is_service_accepted': is_service_accepted,
                        'service_accepted_time': i.accepted_time if i.accepted_time is not None else '',
                        'is_service_completed': i.is_completed,
                        'service_completed_time': i.service_completed_time if i.service_completed_time is not None else ''

                    }

                    user_dict = {

                        'id': user_data.id,
                        'name': user_data.name if user_data.name is not None else '',
                        'image': generate_presigned_url(
                            user_data.image_name) if user_data.image_name is not None else '',
                        'countryCode': user_data.country_code if user_data.country_code is not None else '',
                        'mobile': user_data.mobile_number if user_data.mobile_number is not None else ''
                    }

                    service_dict = get_service_data.as_dict(active_user.active_language)

                    request_dict = {

                            'id': i.id,
                            'order_id': i.payment_id if i.payment_id is not None else 'N/A',
                            'service_day': i.service_day,
                            'service_date': i.service_date,
                            'is_completed': i.is_completed,
                            'service_start_time': i.slot_start_time,
                            'service_end_time': i.slot_end_time,
                            'status': status_replace,
                            'service_name': service_dict['service_name'],
                            'service_description': service_dict['service_description'],
                            'service_price': get_service_data.service_price,
                            'service_image': generate_presigned_url(get_service_data.image_name) if get_service_data.image_name is not None else '',
                            'car_number_plate': get_car_data.number_plate,
                            'car_colour_code': get_car_data.colour_code,
                            'car_year': get_car_data.year,
                            'car_brand': get_car_data.saved_brand.name,
                            'car_model': get_car_data.saved_model.model,
                            'user_address': get_address_data.address,
                            'place_type': get_address_data.place_type,
                            'place_id': get_address_data.place_id,
                            'address_lat': get_address_data.lat,
                            'address_long': get_address_data.long,
                            'house_no': get_address_data.house_no,
                            'city': get_address_data.city,
                            'state': get_address_data.state,
                            'is_provider_completed': i.is_provider_completed,
                            'is_user_completed': i.is_completed,
                            'completed_data': completed_data,
                            'user_data': user_dict,
                            'service_stage': service_stage,
                            'review_data': {}

                        }
                    request_list.append(request_dict)

            message = get_normal_message("msg_11", active_user.active_language)

            return jsonify({'status': 1, 'message': message,'banner_list': banner_list,'services_list': services_list, 'notification_count': notification_count})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrr:', str(e))
            message = get_normal_message("msg_10", active_user.active_language)
            return {'status': 0, 'message': message}, 500

# class ProviderHomepageResource(Resource):
#     @token_required
#     def post(self,active_user):
#         try:
#             if active_user.role == "Customer":
#                 message = get_normal_message("msg_18", active_user.active_language)
#                 return jsonify({'status': 0,'message': message})
#
#             data = request.get_json()
#
#             # page = int(data.get('page', 1))
#             tab = data.get('tab', 0)
#             # per_page = 10
#
#             notification_count = 0
#
#             if tab == 0:
#
#                 request_status = ["Pending", "Accepted"]
#
#                 get_request_data = ServiceRequested.query.filter(
#                     ServiceRequested.provider_id == active_user.id, ServiceRequested.is_completed == False,
#                     ServiceRequested.status.in_(request_status)
#                 ).order_by(desc(ServiceRequested.id)).all()
#
#                 # has_next = get_request_data.has_next
#                 # total_pages = get_request_data.pages
#                 #
#                 # pagination_info = {
#                 #     "current_page": page,
#                 #     "has_next": has_next,
#                 #     "per_page": per_page,
#                 #     "total_pages": total_pages,
#                 # }
#
#                 request_list = []
#
#                 if len(get_request_data) > 0:
#                     for i in get_request_data:
#                         user_data = User.query.get(i.user_id)
#                         get_service_data = Services.query.get(i.service_id)
#                         get_car_data = SavedUserCars.query.get(i.car_id)
#                         get_address_data = UserAddress.query.get(i.address_id)
#                         get_service_completed_data = ServiceCompletedData.query.filter_by(
#                             service_request_id=i.id).first()
#
#                         if get_service_completed_data:
#                             completed_data = {
#                                 'id': get_service_completed_data.id,
#                                 'before_image_one': generate_presigned_url(get_service_completed_data.before_image_name_1) if get_service_completed_data.before_image_name_1 is not None else '',
#                                 'before_image_two': generate_presigned_url(get_service_completed_data.before_image_name_2) if get_service_completed_data.before_image_name_2 is not None else '',
#                                 'after_image_one': generate_presigned_url(get_service_completed_data.after_image_name_1) if get_service_completed_data.after_image_name_1 is not None else '',
#                                 'after_image_two': generate_presigned_url(get_service_completed_data.after_image_name_2) if get_service_completed_data.after_image_name_2 is not None else ''
#                             }
#
#                         else:
#                             completed_data = {}
#
#                         get_extras = []
#
#                         if i.extras_id and i.extras_id != "":
#                             split_data = i.extras_id.split(',')
#                             if len(split_data) > 0:
#                                 for j in split_data:
#                                     get_extras_data = Extras.query.get(j)
#                                     get_extras.append(get_extras_data.as_dict(active_user.active_language))
#
#                         status_replace = i.status
#
#                         is_service_accepted = False
#
#                         if i.status == "Accepted":
#                             status_replace = "In Progress"
#                             is_service_accepted = True
#
#                         service_stage = {
#
#                             'is_service_start': i.is_service_start,
#                             'start_service_time': i.start_service_time if i.start_service_time is not None else '',
#                             'is_service_accepted': is_service_accepted,
#                             'service_accepted_time': i.accepted_time if i.accepted_time is not None else '',
#                             'is_service_completed': i.is_completed,
#                             'service_completed_time': i.service_completed_time if i.service_completed_time is not None else ''
#
#                         }
#
#                         user_dict = {
#
#                             'id': user_data.id,
#                             'name': user_data.name if user_data.name is not None else '',
#                             'image': generate_presigned_url(user_data.image_name) if user_data.image_name is not None else '',
#                             'countryCode': user_data.country_code if user_data.country_code is not None else '',
#                             'mobile': user_data.mobile_number if user_data.mobile_number is not None else '',
#                         }
#
#                         service_dict = get_service_data.as_dict(active_user.active_language)
#
#                         request_dict = {
#
#                             'id': i.id,
#                             # 'username': user_data.name if user_data.name is not None else '',
#                             # 'user_image': COMMON_URL + user_data.image_path + user_data.image_name if user_data.image_name is not None else '',
#                             'order_id': i.payment_id if i.payment_id is not None else 'N/A',
#                             'service_day': i.service_day,
#                             'service_date': i.service_date,
#                             'is_completed': i.is_completed,
#                             'service_start_time': i.slot_start_time,
#                             'service_end_time': i.slot_end_time,
#                             'status': status_replace,
#                             'service_name': service_dict['service_name'],
#                             'service_description': service_dict['service_description'],
#                             'service_price': get_service_data.service_price,
#                             'service_image': generate_presigned_url(get_service_data.image_name) if get_service_data.image_name is not None else '',
#                             'car_number_plate': get_car_data.number_plate,
#                             'car_colour_code': get_car_data.colour_code,
#                             'car_year': get_car_data.year,
#                             'car_brand': get_car_data.saved_brand.name,
#                             'car_model': get_car_data.saved_model.model,
#                             'user_address': get_address_data.address,
#                             'place_type': get_address_data.place_type,
#                             'place_id': get_address_data.place_id,
#                             'address_lat': get_address_data.lat,
#                             'address_long': get_address_data.long,
#                             'house_no': get_address_data.house_no,
#                             'city': get_address_data.city,
#                             'state': get_address_data.state,
#                             'accepted_time': i.accepted_time if i.accepted_time is not None else '',
#                             'extras_list': get_extras,
#                             'is_review': False,
#                             'is_provider_completed': i.is_provider_completed,
#                             'is_user_completed': i.is_completed,
#                             'user_data': user_dict,
#                             'service_stage': service_stage,
#                             'completed_data': completed_data,
#                             'review_data': {}
#
#                         }
#                         request_list.append(request_dict)
#
#                 message = get_normal_message("msg_11", active_user.active_language)
#
#                 return jsonify({'status': 1, 'message': message, 'request_list': request_list,
#                      'notification_count': notification_count,'is_online': active_user.is_online})
#
#             elif tab == 1:
#
#                 request_status = ["Pending", "Accepted","Late"]
#
#                 # Completed
#
#                 get_request_data = ServiceRequested.query.filter(
#                     ServiceRequested.provider_id == active_user.id,
#                     ~ServiceRequested.status.in_(request_status)
#                 ).order_by(desc(ServiceRequested.id)).all()
#
#                 # has_next = get_request_data.has_next
#                 # total_pages = get_request_data.pages
#                 #
#                 # pagination_info = {
#                 #     "current_page": page,
#                 #     "has_next": has_next,
#                 #     "per_page": per_page,
#                 #     "total_pages": total_pages,
#                 # }
#
#                 request_list = []
#
#                 if len(get_request_data) > 0:
#                     for i in get_request_data:
#                         user_data = User.query.get(i.user_id)
#                         get_service_data = Services.query.get(i.service_id)
#                         get_car_data = SavedUserCars.query.get(i.car_id)
#                         get_address_data = UserAddress.query.get(i.address_id)
#                         get_service_completed_data = ServiceCompletedData.query.filter_by(
#                             service_request_id=i.id).first()
#
#                         if get_service_completed_data:
#                             completed_data = {
#                                 'id': get_service_completed_data.id,
#                                 'before_image_one': generate_presigned_url(get_service_completed_data.before_image_name_1) if get_service_completed_data.before_image_name_1 is not None else '',
#                                 'before_image_two': generate_presigned_url(get_service_completed_data.before_image_name_2) if get_service_completed_data.before_image_name_2 is not None else '',
#                                 'after_image_one': generate_presigned_url(get_service_completed_data.after_image_name_1) if get_service_completed_data.after_image_name_1 is not None else '',
#                                 'after_image_two': generate_presigned_url(get_service_completed_data.after_image_name_2) if get_service_completed_data.after_image_name_2 is not None else ''
#                             }
#
#                         else:
#                             completed_data = {}
#
#                         get_extras = []
#
#                         if i.extras_id and i.extras_id != "":
#                             split_data = i.extras_id.split(',')
#                             if len(split_data) > 0:
#                                 for j in split_data:
#                                     get_extras_data = Extras.query.get(j)
#                                     get_extras.append(get_extras_data.as_dict(active_user.active_language))
#
#                         status_replace = i.status
#
#                         is_service_accepted = False
#
#                         review_data = {}
#
#                         if i.status == "Completed":
#                             is_service_accepted = True
#
#                             get_providers_review = UserServiceReview.query.filter(
#                                 UserServiceReview.service_request_id == i.id).first()
#
#                             if get_providers_review:
#                                 review_data = get_providers_review.as_dict()
#
#                         service_stage = {
#
#                             'is_service_start': i.is_service_start,
#                             'start_service_time': i.start_service_time if i.start_service_time is not None else '',
#                             'is_service_accepted': is_service_accepted,
#                             'service_accepted_time': i.accepted_time if i.accepted_time is not None else '',
#                             'is_service_completed': i.is_completed,
#                             'service_completed_time': i.service_completed_time if i.service_completed_time is not None else ''
#
#                         }
#
#                         user_dict = {
#
#                             'id': user_data.id,
#                             'name': user_data.name if user_data.name is not None else '',
#                             'image': generate_presigned_url(user_data.image_name) if user_data.image_name is not None else '',
#                         }
#                         service_dict = get_service_data.as_dict(active_user.active_language)
#
#                         request_dict = {
#
#                             'id': i.id,
#                             # 'username': user_data.name if user_data.name is not None else '',
#                             # 'user_image': COMMON_URL + user_data.image_path + user_data.image_name if user_data.image_name is not None else '',
#                             'order_id': i.payment_id if i.payment_id is not None else 'N/A',
#                             'service_day': i.service_day,
#                             'service_date': i.service_date,
#                             'is_completed': i.is_completed,
#                             'service_start_time': i.slot_start_time,
#                             'service_end_time': i.slot_end_time,
#                             'status': status_replace,
#                             'service_name': service_dict['service_name'],
#                             'service_description': service_dict['service_description'],
#                             'service_price': get_service_data.service_price,
#                             'service_image': generate_presigned_url(get_service_data.image_name) if get_service_data.image_name is not None else '',
#                             'car_number_plate': get_car_data.number_plate,
#                             'car_colour_code': get_car_data.colour_code,
#                             'car_year': get_car_data.year,
#                             'car_brand': get_car_data.saved_brand.name,
#                             'car_model': get_car_data.saved_model.model,
#                             'user_address': get_address_data.address,
#                             'place_type': get_address_data.place_type,
#                             'place_id': get_address_data.place_id,
#                             'address_lat': get_address_data.lat,
#                             'address_long': get_address_data.long,
#                             'house_no': get_address_data.house_no,
#                             'city': get_address_data.city,
#                             'state': get_address_data.state,
#                             'accepted_time': i.accepted_time if i.accepted_time is not None else '',
#                             'extras_list': get_extras,
#                             'is_review': False,
#                             'is_provider_completed': i.is_provider_completed,
#                             'is_user_completed': i.is_completed,
#                             'user_data': user_dict,
#                             'service_stage': service_stage,
#                             'completed_data': completed_data,
#                             'review_data': review_data
#
#                         }
#                         request_list.append(request_dict)
#                 message = get_normal_message("msg_11", active_user.active_language)
#                 return jsonify({'status': 1, 'message': message, 'request_list': request_list,
#                      'notification_count': notification_count,'is_online': active_user.is_online})
#
#             else:
#                 message = get_normal_message("msg_17", active_user.active_language)
#                 return jsonify({'status': 0, 'message': message})
#
#         except Exception as e:
#             print('errorrrrrrrrrrrrrrrrr:', str(e))
#             message = get_normal_message("msg_10", active_user.active_language)
#             return {'status': 0, 'message': message}, 500

class ProviderHomepageResource(Resource):
    @token_required
    def post(self,active_user):
        try:
            if active_user.role == "Customer":
                message = get_normal_message("msg_18", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            data = request.get_json()

            # page = int(data.get('page', 1))
            tab = data.get('tab', 0)
            # per_page = 10

            notification_count = 0

            if tab == 0:

                request_status = ["Pending", "Accepted"]

                get_request_data = (
                    db.session.query(ServiceRequested)
                        .join(ProviderRequest, ProviderRequest.service_request_id == ServiceRequested.id)
                        .filter(
                        ProviderRequest.provider_id == active_user.id,
                        ServiceRequested.is_completed == False,
                        ProviderRequest.status.in_(request_status),
                    )
                        .order_by(desc(ServiceRequested.id))
                        .all()
                )

                request_list = []

                if len(get_request_data) > 0:
                    for i in get_request_data:
                        user_data = User.query.get(i.user_id)
                        get_service_data = Services.query.get(i.service_id)
                        get_car_data = SavedUserCars.query.get(i.car_id)
                        get_address_data = UserAddress.query.get(i.address_id)
                        get_service_completed_data = ServiceCompletedData.query.filter_by(
                            service_request_id=i.id).first()
                        get_provider_request_data = ProviderRequest.query.filter_by(provider_id=active_user.id,
                                                                                    user_id=i.user_id,
                                                                                    service_request_id=i.id).first()

                        if get_service_completed_data:
                            completed_data = {
                                'id': get_service_completed_data.id,
                                'before_image_one': generate_presigned_url(get_service_completed_data.before_image_name_1) if get_service_completed_data.before_image_name_1 is not None else '',
                                'before_image_two': generate_presigned_url(get_service_completed_data.before_image_name_2) if get_service_completed_data.before_image_name_2 is not None else '',
                                'after_image_one': generate_presigned_url(get_service_completed_data.after_image_name_1) if get_service_completed_data.after_image_name_1 is not None else '',
                                'after_image_two': generate_presigned_url(get_service_completed_data.after_image_name_2) if get_service_completed_data.after_image_name_2 is not None else ''
                            }

                        else:
                            completed_data = {}

                        get_extras = []

                        if i.extras_id and i.extras_id != "":
                            split_data = i.extras_id.split(',')
                            if len(split_data) > 0:
                                for j in split_data:
                                    get_extras_data = Extras.query.get(j)
                                    get_extras.append(get_extras_data.as_dict(active_user.active_language))

                        status_replace = get_provider_request_data.status

                        is_service_accepted = False

                        if get_provider_request_data.status == "Accepted":
                            status_replace = "In Progress"
                            is_service_accepted = True

                        service_stage = {

                            'is_service_start': i.is_service_start,
                            'start_service_time': i.start_service_time if i.start_service_time is not None else '',
                            'is_service_accepted': is_service_accepted,
                            'service_accepted_time': i.accepted_time if i.accepted_time is not None else '',
                            'is_service_completed': i.is_completed,
                            'service_completed_time': i.service_completed_time if i.service_completed_time is not None else ''

                        }

                        user_dict = {

                            'id': user_data.id,
                            'name': user_data.name if user_data.name is not None else '',
                            'image': generate_presigned_url(user_data.image_name) if user_data.image_name is not None else '',
                            'countryCode': user_data.country_code if user_data.country_code is not None else '',
                            'mobile': user_data.mobile_number if user_data.mobile_number is not None else '',
                        }

                        service_dict = get_service_data.as_dict(active_user.active_language)

                        request_dict = {

                            'id': i.id,
                            # 'username': user_data.name if user_data.name is not None else '',
                            # 'user_image': COMMON_URL + user_data.image_path + user_data.image_name if user_data.image_name is not None else '',
                            'order_id': i.payment_id if i.payment_id is not None else 'N/A',
                            'service_day': i.service_day,
                            'service_date': i.service_date,
                            'is_completed': i.is_completed,
                            'service_start_time': i.slot_start_time,
                            'service_end_time': i.slot_end_time,
                            'status': status_replace,
                            'service_name': service_dict['service_name'],
                            'service_description': service_dict['service_description'],
                            'service_price': get_service_data.service_price,
                            'service_image': generate_presigned_url(get_service_data.image_name) if get_service_data.image_name is not None else '',
                            'car_number_plate': get_car_data.number_plate,
                            'car_colour_code': get_car_data.colour_code,
                            'car_year': get_car_data.year,
                            'car_brand': get_car_data.saved_brand.name,
                            'car_model': get_car_data.saved_model.model,
                            'user_address': get_address_data.address,
                            'place_type': get_address_data.place_type,
                            'place_id': get_address_data.place_id,
                            'address_lat': get_address_data.lat,
                            'address_long': get_address_data.long,
                            'house_no': get_address_data.house_no,
                            'city': get_address_data.city,
                            'state': get_address_data.state,
                            'accepted_time': i.accepted_time if i.accepted_time is not None else '',
                            'extras_list': get_extras,
                            'is_review': False,
                            'is_provider_completed': i.is_provider_completed,
                            'is_user_completed': i.is_completed,
                            'user_data': user_dict,
                            'service_stage': service_stage,
                            'completed_data': completed_data,
                            'review_data': {}

                        }
                        request_list.append(request_dict)

                message = get_normal_message("msg_11", active_user.active_language)

                return jsonify({'status': 1, 'message': message, 'request_list': request_list,
                     'notification_count': notification_count,'is_online': active_user.is_online})

            elif tab == 1:

                request_status = ["Pending", "Accepted","Late"]

                # Completed

                get_request_data = (
                    db.session.query(ServiceRequested)
                        .join(ProviderRequest, ProviderRequest.service_request_id == ServiceRequested.id)
                        .filter(
                        ProviderRequest.provider_id == active_user.id,
                        ProviderRequest.status.notin_(request_status)
                    )
                        .order_by(desc(ServiceRequested.id))
                        .all()
                )

                # has_next = get_request_data.has_next
                # total_pages = get_request_data.pages
                #
                # pagination_info = {
                #     "current_page": page,
                #     "has_next": has_next,
                #     "per_page": per_page,
                #     "total_pages": total_pages,
                # }

                request_list = []

                if len(get_request_data) > 0:
                    for i in get_request_data:
                        user_data = User.query.get(i.user_id)
                        get_service_data = Services.query.get(i.service_id)
                        get_car_data = SavedUserCars.query.get(i.car_id)
                        get_address_data = UserAddress.query.get(i.address_id)
                        get_service_completed_data = ServiceCompletedData.query.filter_by(
                            service_request_id=i.id).first()
                        get_provider_request_data = ProviderRequest.query.filter_by(provider_id=active_user.id,
                                                                                    user_id=i.user_id,
                                                                                    service_request_id=i.id).first()

                        if get_service_completed_data:
                            completed_data = {
                                'id': get_service_completed_data.id,
                                'before_image_one': generate_presigned_url(get_service_completed_data.before_image_name_1) if get_service_completed_data.before_image_name_1 is not None else '',
                                'before_image_two': generate_presigned_url(get_service_completed_data.before_image_name_2) if get_service_completed_data.before_image_name_2 is not None else '',
                                'after_image_one': generate_presigned_url(get_service_completed_data.after_image_name_1) if get_service_completed_data.after_image_name_1 is not None else '',
                                'after_image_two': generate_presigned_url(get_service_completed_data.after_image_name_2) if get_service_completed_data.after_image_name_2 is not None else ''
                            }

                        else:
                            completed_data = {}

                        get_extras = []

                        if i.extras_id and i.extras_id != "":
                            split_data = i.extras_id.split(',')
                            if len(split_data) > 0:
                                for j in split_data:
                                    get_extras_data = Extras.query.get(j)
                                    get_extras.append(get_extras_data.as_dict(active_user.active_language))

                        status_replace = get_provider_request_data.status

                        is_service_accepted = False

                        review_data = {}

                        if get_provider_request_data.status == "Completed":
                            is_service_accepted = True

                            get_providers_review = UserServiceReview.query.filter(
                                UserServiceReview.service_request_id == i.id).first()

                            if get_providers_review:
                                review_data = get_providers_review.as_dict()

                        service_stage = {

                            'is_service_start': i.is_service_start,
                            'start_service_time': i.start_service_time if i.start_service_time is not None else '',
                            'is_service_accepted': is_service_accepted,
                            'service_accepted_time': i.accepted_time if i.accepted_time is not None else '',
                            'is_service_completed': i.is_completed,
                            'service_completed_time': i.service_completed_time if i.service_completed_time is not None else ''

                        }

                        user_dict = {

                            'id': user_data.id,
                            'name': user_data.name if user_data.name is not None else '',
                            'image': generate_presigned_url(user_data.image_name) if user_data.image_name is not None else '',
                        }
                        service_dict = get_service_data.as_dict(active_user.active_language)

                        request_dict = {

                            'id': i.id,
                            # 'username': user_data.name if user_data.name is not None else '',
                            # 'user_image': COMMON_URL + user_data.image_path + user_data.image_name if user_data.image_name is not None else '',
                            'order_id': i.payment_id if i.payment_id is not None else 'N/A',
                            'service_day': i.service_day,
                            'service_date': i.service_date,
                            'is_completed': i.is_completed,
                            'service_start_time': i.slot_start_time,
                            'service_end_time': i.slot_end_time,
                            'status': status_replace,
                            'service_name': service_dict['service_name'],
                            'service_description': service_dict['service_description'],
                            'service_price': get_service_data.service_price,
                            'service_image': generate_presigned_url(get_service_data.image_name) if get_service_data.image_name is not None else '',
                            'car_number_plate': get_car_data.number_plate,
                            'car_colour_code': get_car_data.colour_code,
                            'car_year': get_car_data.year,
                            'car_brand': get_car_data.saved_brand.name,
                            'car_model': get_car_data.saved_model.model,
                            'user_address': get_address_data.address,
                            'place_type': get_address_data.place_type,
                            'place_id': get_address_data.place_id,
                            'address_lat': get_address_data.lat,
                            'address_long': get_address_data.long,
                            'house_no': get_address_data.house_no,
                            'city': get_address_data.city,
                            'state': get_address_data.state,
                            'accepted_time': i.accepted_time if i.accepted_time is not None else '',
                            'extras_list': get_extras,
                            'is_review': False,
                            'is_provider_completed': i.is_provider_completed,
                            'is_user_completed': i.is_completed,
                            'user_data': user_dict,
                            'service_stage': service_stage,
                            'completed_data': completed_data,
                            'review_data': review_data

                        }
                        request_list.append(request_dict)
                message = get_normal_message("msg_11", active_user.active_language)
                return jsonify({'status': 1, 'message': message, 'request_list': request_list,
                     'notification_count': notification_count,'is_online': active_user.is_online})

            else:
                message = get_normal_message("msg_17", active_user.active_language)
                return jsonify({'status': 0, 'message': message})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrr:', str(e))
            message = get_normal_message("msg_10", active_user.active_language)
            return {'status': 0, 'message': message}, 500