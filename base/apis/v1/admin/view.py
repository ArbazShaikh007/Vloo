from flask import request, make_response, render_template, jsonify, url_for, redirect
from flask_restful import Resource
from base.common.utils import admin_login_required
from datetime import datetime, timedelta
import os
import jwt
import secrets,csv
import random
import string
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from base.apis.v1.admin.models import SubZone,BrodCastMessages,SlotDisableTime,ContactUs,Cms,Faqs,Extras,Store,Admin,Banners,Services,Cars,Zone,AssignProviderService,CarBrands,CarModels
from base.database.db import db
from base.common.utils import push_notification,user_send_reset_email,delete_photos_local,upload_photos_local,delete_photos,send_provider_cred,upload_photos,delete_photos
from dotenv import load_dotenv
from base.apis.v1.user.models import Notification,UserPayments,User,ProviderSlots,ServiceRequested,ProviderRequest,UserAddress,SavedUserCars
from pathlib import Path
from base.apis.v1.user.view import get_hourly_slots
from sqlalchemy.orm import contains_eager
from base.common.path import generate_presigned_url
import math
from base.common.helpers import get_normal_message,get_localized_service_name,get_notification_message
import pytz
from sqlalchemy import cast, Date, extract

from shapely.geometry import shape, Polygon
from shapely.validation import explain_validity
import json
from sqlalchemy import func

# env_path = Path('/var/www/html/backend/base/.env')
# load_dotenv(dotenv_path=env_path)

load_dotenv()

# UPLOAD_FOLDER = "base/static/admin_photos/"

class StaticFileUploadResource(Resource):
    def post(self):
        try:
            file = request.files.get('file')

            file_path, picture = upload_photos(file)

            check = generate_presigned_url(picture)

            return jsonify({'status': 1,'image_name': picture,'image_path': file_path,'check':check})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

# from sqlalchemy import func, and_
# from sqlalchemy.sql import exists
# from sqlalchemy.orm import aliased
# import math
#
# page = int(data.get('page', 1))
# per_page = 10
#
# base_q = (
#     ServiceRequested.query
#     .filter(ServiceRequested.status == "Pending")
#     .order_by(ServiceRequested.id.desc())
# )
#
# request_list = []
# excluded = ["Pending", "Cancelled", "Late"]
#
# # ---- exact total_pages using EXISTS that matches your provider filtering ----
# SR2 = aliased(ServiceRequested)
# PR1 = aliased(ProviderRequest)
# PR2 = aliased(ProviderRequest)
#
# eligibility_exists = exists().where(and_(
#     PR1.service_request_id == ServiceRequested.id,
#     PR1.status == "Pending",
#     ~exists().where(and_(
#         PR2.service_request_id == SR2.id,
#         SR2.service_date == ServiceRequested.service_date,
#         SR2.slot_start_time == ServiceRequested.slot_start_time,
#         SR2.slot_end_time == ServiceRequested.slot_end_time,
#         SR2.id != ServiceRequested.id,
#         PR2.provider_id == PR1.provider_id,
#         ~PR2.status.in_(excluded),  # i.e., Accepted/Completed/etc.
#     ))
# ))
#
# total_items = db.session.query(func.count(ServiceRequested.id)).filter(
#     ServiceRequested.status == "Pending",
#     eligibility_exists
# ).scalar() or 0
#
# total_pages = math.ceil(total_items / per_page) if per_page else 0
#
# # ---- build current page with your existing over-fetch loop ----
# cursor = (page - 1) * per_page
# filled = 0
#
# while filled < per_page:
#     candidates = base_q.offset(cursor).limit(per_page).all()
#     if not candidates:
#         break
#
#     for i in candidates:
#         get_provider_request = ProviderRequest.query.filter_by(
#             service_request_id=i.id, status="Pending"
#         ).all()
#
#         provider_list = []
#         for j in get_provider_request:
#             conflict = (
#                 db.session.query(ServiceRequested.id)
#                 .join(ProviderRequest, ProviderRequest.service_request_id == ServiceRequested.id)
#                 .filter(
#                     ServiceRequested.service_date == i.service_date,
#                     ServiceRequested.slot_start_time == i.slot_start_time,
#                     ServiceRequested.slot_end_time == i.slot_end_time,
#                     ServiceRequested.id != i.id,
#                     ProviderRequest.provider_id == j.provider_id,
#                     ~ProviderRequest.status.in_(excluded),
#                 )
#                 .first()
#             )
#
#             if not conflict:
#                 get_provider = User.query.get(j.provider_id)
#                 provider_list.append({
#                     'id': get_provider.id,
#                     'name': (get_provider.name or '')
#                 })
#
#         if provider_list:
#             get_service_data = Services.query.get(i.service_id)
#             get_car_data     = SavedUserCars.query.get(i.car_id)
#             get_address_data = UserAddress.query.get(i.address_id)
#             user_data        = User.query.get(i.user_id)
#
#             user_dict = {
#                 'id': user_data.id,
#                 'name': user_data.name or '',
#                 'image': generate_presigned_url(user_data.image_name) if user_data.image_name else '',
#                 'countryCode': user_data.country_code or '',
#                 'mobile': user_data.mobile_number or '',
#             }
#
#             request_dict = {
#                 'id': i.id,
#                 'service_day': i.service_day,
#                 'service_date': i.service_date,
#                 'service_start_time': i.slot_start_time,
#                 'service_end_time': i.slot_end_time,
#                 'service_name': get_service_data.service_name,
#                 'service_description': get_service_data.service_description,
#                 'service_price': get_service_data.service_price,
#                 'service_image': generate_presigned_url(get_service_data.image_name) if get_service_data.image_name else '',
#                 'user_address': get_address_data.address,
#                 'place_type': get_address_data.place_type,
#                 'place_id': get_address_data.place_id,
#                 'address_lat': get_address_data.lat,
#                 'address_long': get_address_data.long,
#                 'house_no': get_address_data.house_no,
#                 'city': get_address_data.city,
#                 'state': get_address_data.state,
#                 'user_data': user_dict,
#                 'car_number_plate': get_car_data.number_plate,
#                 'car_colour_code': get_car_data.colour_code,
#                 'car_year': get_car_data.year,
#                 'car_brand': get_car_data.saved_brand.name,
#                 'car_model': get_car_data.saved_model.model,
#                 'provider_list': provider_list,
#             }
#
#             request_list.append(request_dict)
#             filled += 1
#             if filled == per_page:
#                 break
#
#     cursor += per_page
#
# # has_next derived from exact count
# has_next = page < total_pages
#
# return jsonify({
#     'status': 1,
#     'message': 'Success',
#     'request_list': request_list,
#     'pagination_info': {
#         'current_page': page,
#         'has_next': has_next,
#         'per_page': per_page,
#         'total_pages': total_pages,
#     }
# })

# class ProviderMonthlyReportResource(Resource):
#     @admin_login_required
#     def post(self, active_user):
#         try:
#             data = request.get_json()
#
#             filter_text = data.get('filter_text',"Monthly")
#
#             get_all_providers = User.query.filter(User.role == "Worker").all()
#
#             today = datetime.today()
#
#             if filter_text == "Daily":
#                 # get timezone from active_user
#                 tz = pytz.timezone(active_user.admin_timezone or "Asia/Kolkata")
#
#                 # convert current time to that timezone
#                 today_local = datetime.now(tz)
#
#                 get_all_service_request = (
#                     ServiceRequested.query
#                         .filter(
#                         extract('year', cast(ServiceRequested.service_date, Date)) == today_local.year,
#                         extract('month', cast(ServiceRequested.service_date, Date)) == today_local.month,
#                         extract('day', cast(ServiceRequested.service_date, Date)) == today_local.day
#                     )
#                         .all()
#                 )
#
#
#             elif filter_text == "Monthly":
#                 get_all_service_request = (
#                     ServiceRequested.query
#                         .filter(
#                         extract('year', cast(ServiceRequested.service_date, Date)) == today.year,
#                         extract('month', cast(ServiceRequested.service_date, Date)) == today.month
#                     )
#                         .all()
#                 )
#
#             # elif filter_text == "Yearly":
#
#             else:
#                 get_all_service_request = (
#                     ServiceRequested.query
#                         .filter(
#                         extract('year', cast(ServiceRequested.service_date, Date)) == today.year
#                     )
#                         .all()
#                 )
#
#         except Exception as e:
#             print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
#             return {'status': 0, 'message': 'Something went wrong'}, 400

class AddMainProviderResource(Resource):
    def post(self):
        data = request.get_json()

        name = data.get("name")
        country_code = data.get('country_code')
        mobile_number = data.get('mobile_number')
        timezone = data.get('timezone')
        email = data.get("email")

        if not name:
            return jsonify({'status': 0,'message': 'Please provide name'})
        if not email:
            return jsonify({'status': 0,'message': 'Please provide email'})

        admin = Admin.query.filter_by(email=email).first()

        if admin:
            if admin.is_subadmin == True:
                return jsonify({'status':0,'message': "Email already exists. Please try another one."})
            elif admin.is_subadmin == False:
                return jsonify({'status':0,'message': "Email already exists as a admin. Please try another one."})
            else:
                return jsonify({'status': 0, 'message': "Email already exists. Please try another one."})

        random_password = generate_random_string()

        print('random_password',random_password)

        hashed_password = generate_password_hash(random_password)

        admin = Admin(
            is_subadmin = True,
            admin_timezone=timezone,
            mobile_number=mobile_number,
            country_code=country_code,
            firstname=name,
            lastname='',
            email=email,
            password=hashed_password,
            created_at=datetime.utcnow()
        )

        db.session.add(admin)
        db.session.commit()

        # token = jwt.encode(
        #     {"id": admin.id, "exp": datetime.utcnow() + timedelta(days=365)},
        #     os.getenv("ADMIN_SECRET_KEY"),
        # )

        send_provider_cred(admin, random_password,'Admin')

        return jsonify({'status': 1,
                        'message': 'Provider added successfully, and login credentials have been sent to their email.'})

class PopularBrandResource(Resource):
    @admin_login_required
    def post(self, active_user):
        try:
            brand_id = request.json.get('brand_id')
            if not brand_id:
                return jsonify({'status': 0,'message': 'Please select car brand first.'})

            get_car_barnd = CarBrands.query.get(brand_id)
            if not get_car_barnd:
                return jsonify({'status': 0,'message': 'Invalid car brand.'})

            if get_car_barnd.is_popular == False:
                get_car_barnd.is_popular = True
                db.session.commit()

                return jsonify({'status': 1,'message': "Successfully make car brand popular"})

            else:
                get_car_barnd.is_popular = False
                db.session.commit()

                return jsonify({'status': 1, 'message': "Successfully removed car brand from popular"})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

class BrodCastMessagesResource(Resource):
    @admin_login_required
    def post(self, active_user):
        try:
            data = request.get_json()

            message_en = data.get('message_en')
            message_ar = data.get('message_ar')
            message_bn = data.get('message_bn')

            user_id = data.get('user_id')

            if not message_en:
                return jsonify({'status': 0,'message': 'Message in english is required'})
            if not message_ar:
                return jsonify({'status': 0,'message': 'Message in arabic is required'})
            if not message_bn:
                return jsonify({'status': 0,'message': 'Message in bangladeshi is required'})
            if not user_id:
                return jsonify({'status': 0,'message': 'Please select user'})

            add_new_message = BrodCastMessages(message_en=message_en,message_ar=message_ar,message_bn=message_bn,created_time=datetime.utcnow(),admin_id = active_user.id)
            db.session.add(add_new_message)
            db.session.commit()

            split_users_id = user_id.split(',')

            title_en = 'New broadcast message'
            title_ar = 'رسالة بث جديدة'
            title_bn = 'নতুন সম্প্রচার বার্তা'

            for i in split_users_id:
                user_data = User.query.get(i)
                if not user_data:
                    return jsonify({'status': 0,'message': "User data not found."})

                add_notification = Notification(title_en=title_en,
                                                title_ar=title_ar, title_bn=title_bn,
                                                message_en=message_en, message_ar=message_ar,
                                                message_bn=message_bn, to_id=user_data.id,
                                                is_read=False, created_time=datetime.utcnow(),
                                                notification_type='new broadcast message')
                db.session.add(add_notification)
                db.session.commit()

                if user_data.device_token is not None and user_data.device_token != "":

                    title = title_en
                    message = message_en

                    if user_data.active_language == "ar":
                        title = title_ar
                        message = message_ar

                    if user_data.active_language == "bn":
                        title = title_bn
                        message = message_bn

                    push_notification(
                        token=user_data.device_token,
                        title=title,
                        body=message
                    )

            return jsonify({'status': 1,'message': "Broadcast message successfully send to user"})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

def first_day_n_months_ago(dt: datetime, n: int) -> datetime:
    """Return dt moved back n months and set to the first day of that month at 00:00:00."""
    y, m = dt.year, dt.month - n
    while m <= 0:
        m += 12
        y -= 1
    return dt.replace(year=y, month=m, day=1, hour=0, minute=0, second=0, microsecond=0)

class ProviderMonthlyReportResource(Resource):
    @admin_login_required
    def post(self, active_user):
        try:
            data = request.get_json()

            print("dataaaaaaaa",data)

            filter_text = (data.get('filter_text') or "Monthly").title()
            search_text = (data.get('search_text') or "").strip()
            specific_date = (data.get('specific_date') or "").strip()
            from_date = (data.get('from_date') or "").strip()
            to_date = (data.get('to_date') or "").strip()

            # ---- timezone (default India) ----
            tz = pytz.timezone(active_user.admin_timezone or "Asia/Kolkata")
            now = datetime.now(tz)

            if from_date and to_date:
                try:
                    start = datetime.strptime(from_date, "%Y-%m-%d").date()
                    end = datetime.strptime(to_date, "%Y-%m-%d").date()
                except ValueError:
                    return {
                               "status": 0,
                               "message": "Invalid from_date/to_date. Use YYYY-MM-DD."
                           }, 400

                if end < start:
                    return {
                               "status": 0,
                               "message": "to_date must be greater than or equal to from_date."
                           }, 400

                date_filters = [
                    cast(ServiceRequested.service_date, Date) >= start,
                    cast(ServiceRequested.service_date, Date) <= end,
                ]

            # ---- date filter on ServiceRequested.service_date (stored as 'YYYY-MM-DD') ----
            elif specific_date:
                # Override other filters: exact date match
                try:
                    target_date = datetime.strptime(specific_date, "%Y-%m-%d").date()
                except ValueError:
                    return {"status": 0, "message": "Invalid specific_date. Use YYYY-MM-DD."}, 400

                date_filters = [
                    cast(ServiceRequested.service_date, Date) == target_date
                ]
            else:

                if filter_text == "Daily":
                    date_filters = [
                        extract('year', cast(ServiceRequested.service_date, Date)) == now.year,
                        extract('month', cast(ServiceRequested.service_date, Date)) == now.month,
                        extract('day', cast(ServiceRequested.service_date, Date)) == now.day,
                    ]
                elif filter_text == "Monthly":
                    date_filters = [
                        extract('year', cast(ServiceRequested.service_date, Date)) == now.year,
                        extract('month', cast(ServiceRequested.service_date, Date)) == now.month,
                    ]

                elif filter_text == "3 Months":
                    # Include current month: from the 1st of (now - 2 months) to today
                    start = first_day_n_months_ago(now, 2).date()
                    end = now.date()
                    date_filters = [
                        cast(ServiceRequested.service_date, Date) >= start,
                        cast(ServiceRequested.service_date, Date) <= end,
                    ]

                elif filter_text == "6 Months":
                    # Include current month: from the 1st of (now - 5 months) to today
                    start = first_day_n_months_ago(now, 5).date()
                    end = now.date()
                    date_filters = [
                        cast(ServiceRequested.service_date, Date) >= start,
                        cast(ServiceRequested.service_date, Date) <= end,
                    ]

                else:  # "Yearly"
                    date_filters = [
                        extract('year', cast(ServiceRequested.service_date, Date)) == now.year,
                    ]

            provider_query = User.query.filter(User.role == "Worker",User.subadmin_id == active_user.id)
            if search_text:
                provider_query = provider_query.filter(User.name.ilike(f"{search_text}%"),User.subadmin_id == active_user.id)

            providers = provider_query.all()
            provider_ids = [p.id for p in providers]

            rows = (
                db.session.query(ProviderRequest, ServiceRequested)
                    .join(ServiceRequested, ProviderRequest.service_request_id == ServiceRequested.id)
                    .filter(ProviderRequest.provider_id.in_(provider_ids), *date_filters)
                    .all()
            )

            def _norm(s: str) -> str:
                return (s or "").strip().lower()

            report = {
                p.id: {
                    "provider_id": p.id,
                    "provider_name": getattr(p, "name", None),
                    "provider_email": p.email if p.email is not None else '',
                    "provider_mobile_number": p.mobile_number if p.mobile_number is not None else '',
                    "avarage_rating": p.avarage_rating if p.avarage_rating is not None else '0.0',
                    "total": 0,
                    "pending": 0,
                    "accepted": 0,
                    "completed": 0,
                    "cancelled": 0,
                    "late": 0,
                } for p in providers
            }

            for pr, sr in rows:
                pid = pr.provider_id
                r = report[pid]
                r["total"] += 1

                status = _norm(pr.status)

                # treat Completed if status == completed OR is_provider_completed == True
                completed_flag = pr.is_provider_completed or status == "completed"

                # Completed -> increments Completed
                if completed_flag:
                    r["completed"] += 1

                # Accepted -> if status == accepted OR completed_flag
                # (counts at most once per row)

                # if status == "accepted" or completed_flag:
                if status == "accepted":
                    r["accepted"] += 1

                # Pending -> only when status == pending and not completed/cancelled
                if status == "pending" and not completed_flag:
                    r["pending"] += 1

                # Cancelled -> strictly from PR status
                if status == "cancelled":
                    r["cancelled"] += 1

                # Late -> strictly from PR status
                if status == "late":
                    r["late"] += 1

            service_status_summary = {
                "total_count": 0,
                "accepted_count": 0,
                "pending_count": 0,
                "cancelled_count": 0,
                "completed_count": 0,
            }
            seen_sr_ids = set()

            for _, sr in rows:
                if sr.id in seen_sr_ids:
                    continue
                seen_sr_ids.add(sr.id)

                s = _norm(sr.status)
                if sr.is_completed or s == "completed":
                    service_status_summary["completed_count"] += 1
                elif s == "accepted":
                    service_status_summary["accepted_count"] += 1
                elif s == "cancelled":
                    service_status_summary["cancelled_count"] += 1
                elif s == "pending":
                    service_status_summary["pending_count"] += 1

            return jsonify(
                {"status": 1, "message": "Success", "data": list(report.values()), "provider_counts": len(providers),
                 "summary": service_status_summary})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

class DisableBeforeTimeResource(Resource):
    @admin_login_required
    def post(self, active_user):
        try:
            data = request.get_json()
            hr = data.get('hr')

            get_disable_time = SlotDisableTime.query.get(1)
            if not get_disable_time:
                return jsonify({'status': 0,'message': "Default disable time is not set yet"})

            get_disable_time.slot_disable_before = int(hr)
            db.session.commit()

            return jsonify({'status': 1,'message': "Successfully updated disabled hr before slot time"})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

    @admin_login_required
    def get(self, active_user):
        try:
            get_disable_time = SlotDisableTime.query.get(1)
            if not get_disable_time:
                return jsonify({'status': 0, 'message': "Default disable time is not set yet"})

            return jsonify({'status': 1,'message': 'Success','hr': get_disable_time.slot_disable_before})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

class AdminAcceptServiceRequestsResource(Resource):
    @admin_login_required
    def post(self, active_user):
        try:
            data = request.get_json()

            request_id = data.get('request_id')
            provider_id = data.get('provider_id')

            if not request_id:
                return jsonify({'status': 0,'message': "Please select request first."})
            if not provider_id:
                return jsonify({'status': 0,'message': "Please select worker first."})

            get_provider = User.query.get(provider_id)
            if not get_provider:
                return jsonify({'status': 0,'message': "Invalid worker."})

            get_requested_data = (
                db.session.query(ServiceRequested)
                    .join(ProviderRequest, ProviderRequest.service_request_id == ServiceRequested.id)
                    .filter(
                    ServiceRequested.id == request_id,
                    ServiceRequested.status == "Pending",
                    ProviderRequest.provider_id == get_provider.id,
                    ProviderRequest.status == "Pending",
                )
                    .first()
            )

            if not get_requested_data:
                return jsonify({'status': 0,'message': 'One of worker made action with this request. Please reload your page'})

            # check_late_status = ProviderRequest.query.filter_by(provider_id=get_provider.id,
            #                                                     service_request_id=get_requested_data.id,
            #                                                     status="Late").first()
            #
            # if check_late_status:
            #     message = get_normal_message("msg_21", active_user.active_language)
            #     return jsonify({'status': 0, 'message': message})

            excluded = ["Pending", "Cancelled", "Late"]

            check_another_request_accepted_for_same_slot = (
                db.session.query(ServiceRequested.id)
                    .join(ProviderRequest, ProviderRequest.service_request_id == ServiceRequested.id)
                    .filter(
                    ServiceRequested.service_date == get_requested_data.service_date,
                    ServiceRequested.slot_start_time == get_requested_data.slot_start_time,
                    ServiceRequested.slot_end_time == get_requested_data.slot_end_time,
                    ServiceRequested.id != get_requested_data.id,  # avoid matching the same request
                    ProviderRequest.provider_id == get_provider.id,  # check this provider
                    ~ProviderRequest.status.in_(excluded),  # exclude (Pending/Cancelled/Late) on PR
                )
                    .first()
            )

            if check_another_request_accepted_for_same_slot:
                return jsonify({'status': 0, 'message': "Provider already accepted another request for the same date and time slot."})

            get_particular_requested_provider = ProviderRequest.query.filter_by(provider_id=get_provider.id,
                                                                                service_request_id=get_requested_data.id).first()

            get_requested_data.status = "Accepted"
            get_particular_requested_provider.status = "Accepted"
            get_requested_data.accepted_time = datetime.utcnow()

            get_payment_details = UserPayments.query.filter(
                UserPayments.payment_id == get_requested_data.payment_id).first()
            if not get_payment_details:
                message = get_normal_message("msg_22", "en")
                return jsonify({'status': 0, 'message': message})

            get_payment_details.provider_id = get_provider.id
            get_payment_details.service_request_id = get_requested_data.id

            check_another_providers = ProviderRequest.query.filter(
                ProviderRequest.service_request_id == get_requested_data.id,
                ProviderRequest.provider_id != get_provider.id,
                ProviderRequest.user_id == get_requested_data.user_id,
                ProviderRequest.status == "Pending"
            ).all()

            if len(check_another_providers) > 0:
                for i in check_another_providers:
                    i.status = "Late"

            db.session.commit()

            get_service_data = Services.query.get(get_requested_data.service_id)
            if not get_service_data:
                message = get_normal_message("msg_23", "en")
                return jsonify({'status': 0, 'message': message})

            reciver_user = User.query.get(get_requested_data.user_id)
            if not reciver_user:
                message = get_normal_message("msg_24", "en")
                return jsonify({'status': 0, 'message': message})

            titles, messages = {}, {}
            for lang in ("en", "ar", "bn"):
                localized_service = get_localized_service_name(get_service_data, lang)
                data = get_notification_message("accepted", lang, localized_service)
                titles[lang], messages[lang] = data["title"], data["msg"]

            add_notification = Notification(service_request_id=get_requested_data.id, title_en=titles["en"],
                                            title_ar=titles["ar"], title_bn=titles["bn"], message_en=messages["en"],
                                            message_ar=messages["ar"], message_bn=messages["bn"], by_id=get_provider.id,
                                            to_id=reciver_user.id,
                                            is_read=False, created_time=datetime.utcnow(),
                                            notification_type='provider accepts request (Admin)')
            db.session.add(add_notification)
            db.session.commit()

            # Send push only in receiver’s active language
            user_lang = reciver_user.active_language if reciver_user.active_language in ("en", "ar", "bn") else "en"
            push_title = titles[user_lang]
            push_msg = messages[user_lang]

            if reciver_user.device_token:
                push_notification(
                    token=reciver_user.device_token,
                    title=push_title,
                    body=push_msg
                )

            message = get_normal_message("msg_25", "en")
            return jsonify({'status': 1, 'message': message})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

class PendingServiceRequestsResource(Resource):
    @admin_login_required
    def post(self, active_user):
        try:
            data = request.get_json()

            page = int(data.get('page', 1))
            per_page = 10

            get_pending_request = ServiceRequested.query.filter(ServiceRequested.status == "Pending").order_by(
                ServiceRequested.id.desc()).all()

            request_list = []

            if len(get_pending_request)>0:
                for i in get_pending_request:

                    get_provider_request = ProviderRequest.query.filter_by(service_request_id=i.id,status = "Pending").all()

                    provider_list = []

                    if len(get_provider_request)>0:
                        for j in get_provider_request:

                            excluded = ["Pending", "Cancelled", "Late"]

                            check_another_request_accepted_for_same_slot = (
                                    db.session.query(ServiceRequested.id)
                            .join(ProviderRequest, ProviderRequest.service_request_id == ServiceRequested.id)
                            .filter(
                            ServiceRequested.service_date == i.service_date,
                            ServiceRequested.slot_start_time == i.slot_start_time,
                            ServiceRequested.slot_end_time == i.slot_end_time,
                            ServiceRequested.id != i.id,  # avoid matching the same request
                            ProviderRequest.provider_id == j.provider_id,  # check this provider
                            ~ProviderRequest.status.in_(excluded),  # exclude (Pending/Cancelled/Late) on PR
                                    )
                                        .first()
                                )

                            if not check_another_request_accepted_for_same_slot:
                                get_provider = User.query.get(j.provider_id)

                                provider_dict = {
                                    'id': get_provider.id,
                                    'name': get_provider.name if get_provider.name is not None else ''
                                }

                                provider_list.append(provider_dict)

                    get_service_data = Services.query.get(i.service_id)
                    get_car_data = SavedUserCars.query.get(i.car_id)
                    get_address_data = UserAddress.query.get(i.address_id)
                    user_data = User.query.get(i.user_id)

                    user_dict = {

                        'id': user_data.id,
                        'name': user_data.name if user_data.name is not None else '',
                        'image': generate_presigned_url(
                            user_data.image_name) if user_data.image_name is not None else '',
                        'countryCode': user_data.country_code if user_data.country_code is not None else '',
                        'mobile': user_data.mobile_number if user_data.mobile_number is not None else ''
                    }

                    request_dict = {

                        'id': i.id,
                        'service_day': i.service_day,
                        'service_date': i.service_date,
                        'service_start_time': i.slot_start_time,
                        'service_end_time': i.slot_end_time,
                        'service_name': get_service_data.service_name,
                        'service_description': get_service_data.service_description,
                        'service_price': get_service_data.service_price,
                        'service_image': generate_presigned_url(
                            get_service_data.image_name) if get_service_data.image_name is not None else '',
                        'user_address': get_address_data.address,
                        'place_type': get_address_data.place_type,
                        'place_id': get_address_data.place_id,
                        'address_lat': get_address_data.lat,
                        'address_long': get_address_data.long,
                        'house_no': get_address_data.house_no,
                        'city': get_address_data.city,
                        'state': get_address_data.state,
                        'user_data': user_dict,
                        'car_number_plate': get_car_data.number_plate,
                        'car_colour_code': get_car_data.colour_code,
                        'car_year': get_car_data.year,
                        'car_brand': get_car_data.saved_brand.name,
                        'car_model': get_car_data.saved_model.model,
                        'provider_list': provider_list
                    }

                    request_list.append(request_dict)

            page = max(1, int(page))
            per_page = max(1, int(per_page))

            total_items = len(request_list)
            total_pages = math.ceil(total_items / per_page) if per_page else 0

            start = (page - 1) * per_page
            end = start + per_page
            paginated_list = request_list[start:end]

            pagination_info = {
                "current_page": page,
                "has_next": page < total_pages,
                "per_page": per_page,
                "total_pages": total_pages,
            }

            return jsonify({'status': 1,'message': 'Success','request_list': paginated_list,"pagination_info":pagination_info})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

class AdminReplyContactUsResource(Resource):
    @admin_login_required
    def post(self, active_user):
        try:
            data = request.get_json()

            contact_us_id = data.get('id')
            reply = data.get('reply')

            if not contact_us_id:
                return jsonify({'status': 0,'message': 'Please select message first'})
            if not reply:
                return jsonify({'status': 0,'message': 'Please provide message'})

            get_contact_us_data = ContactUs.query.get(contact_us_id)
            if not get_contact_us_data:
                return jsonify({'status': 0,'message': 'Invalid data'})

            add_reply = ContactUs(user_type = get_contact_us_data.my_contact_us.role,request_id=get_contact_us_data.request_id,user_id = get_contact_us_data.user_id,created_time= datetime.utcnow(),reply = reply,admin_id= active_user.id,reply_id = get_contact_us_data.id)
            db.session.add(add_reply)

            get_contact_us_data.is_reply = True
            get_contact_us_data.reply = reply

            db.session.commit()

            return jsonify({'status': 1,'message': 'Reply sent successfully'})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

class AdminContactUsListingResource(Resource):
    @admin_login_required
    def post(self, active_user):
        try:
            data = request.get_json()

            page = int(data.get('page', 1))
            search_text = data.get('search_text')
            user_type = data.get('user_type')
            per_page = 10

            if not user_type:
                return jsonify({'status':0,'message': 'Please select user type'})
            if not user_type in ["Worker","Customer"]:
                return jsonify({'status': 0, 'message': 'Invalid user type'})

            if search_text:
                get_contact_us = ContactUs.query.filter(ContactUs.name.ilike(f"{search_text}%",ContactUs.admin_id == None,ContactUs.user_type == user_type)
                                              ).order_by(
                    ContactUs.id.desc()).paginate(page=page, per_page=per_page,
                                             error_out=False)

            else:
                get_contact_us = ContactUs.query.filter(ContactUs.admin_id == None,ContactUs.user_type == user_type).order_by(
                    ContactUs.id.desc()).paginate(page=page, per_page=per_page,
                                                  error_out=False)

            has_next = get_contact_us.has_next
            total_pages = get_contact_us.pages

            pagination_info = {
                "current_page": page,
                "has_next": has_next,
                "per_page": per_page,
                "total_pages": total_pages,
            }

            contact_us_list = [ i.as_dict() for i in get_contact_us.items ]

            return jsonify({'status': 1,'message': 'Success','contact_us_list': contact_us_list,'pagination_info': pagination_info })

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

class AdminPrivacyResource(Resource):
    @admin_login_required
    def post(self, active_user):
        try:
            content = request.json.get('content')
            content_ar = request.json.get('content_ar')
            content_bn = request.json.get('content_bn')

            if not content:
                return jsonify({'status': 0,'message': 'Please provide content in english'})
            if not content_ar:
                return jsonify({'status': 0,'message': 'Please provide content in arabic'})
            if not content_bn:
                return jsonify({'status': 0,'message': 'Please provide content in bangladeshi'})

            get_privacy = Cms.query.get(2)
            if not get_privacy:
                return jsonify({'status': 0,'message': 'privacy data is empty'})

            get_privacy.content = content
            get_privacy.content_ar = content_ar
            get_privacy.content_bn = content_bn
            db.session.commit()

            return jsonify({'status': 1,'message': 'Privacy policy is updated'})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

    @admin_login_required
    def get(self, active_user):
        try:
            get_privacy = Cms.query.get(2)
            if not get_privacy:
                return jsonify({'status': 0, 'message': 'privacy data is empty'})

            return jsonify({'status': 1,'message': 'Success','data': get_privacy.as_dict_admin() })

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

class AdminAboutUsResource(Resource):
    @admin_login_required
    def post(self, active_user):
        try:
            content = request.json.get('content')
            content_ar = request.json.get('content_ar')
            content_bn = request.json.get('content_bn')

            if not content:
                return jsonify({'status': 0, 'message': 'Please provide content in english'})
            if not content_ar:
                return jsonify({'status': 0, 'message': 'Please provide content in arabic'})
            if not content_bn:
                return jsonify({'status': 0, 'message': 'Please provide content in bangladeshi'})

            get_about_us = Cms.query.get(3)
            if not get_about_us:
                return jsonify({'status': 0, 'message': 'about us data is empty'})

            get_about_us.content = content
            get_about_us.content_ar = content_ar
            get_about_us.content_bn = content_bn
            db.session.commit()

            return jsonify({'status': 1, 'message': 'About us is updated'})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

    @admin_login_required
    def get(self, active_user):
        try:
            get_about_us = Cms.query.get(3)
            if not get_about_us:
                return jsonify({'status': 0, 'message': 'About us data is empty'})

            return jsonify({'status': 1, 'message': 'Success', 'data': get_about_us.as_dict_admin()})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

class AdminFaqResource(Resource):
    @admin_login_required
    def post(self, active_user):
        try:
            data = request.get_json()

            question = data.get('question')
            answer = data.get('answer')
            question_ar = data.get('question_ar')
            answer_ar = data.get('answer_ar')
            question_bn = data.get('question_bn')
            answer_bn = data.get('answer_bn')

            if not question:
                return jsonify({'status': 0,'message': 'Please provide question in english'})
            if not answer:
                return jsonify({'status': 0,'message': 'Please provide answer in english'})
            if not question_ar:
                return jsonify({'status': 0,'message': 'Please provide question in arabic'})
            if not answer_ar:
                return jsonify({'status': 0,'message': 'Please provide answer in arabic'})
            if not question_bn:
                return jsonify({'status': 0,'message': 'Please provide question in bangladeshi'})
            if not answer_bn:
                return jsonify({'status': 0,'message': 'Please provide answer in bangladeshi'})

            add_faq = Faqs(answer_bn=answer_bn,question_bn=question_bn,answer_ar=answer_ar,question_ar=question_ar,question=question,answer=answer)
            db.session.add(add_faq)
            db.session.commit()

            return jsonify({'status': 1, 'message': 'Successfully new faq added'})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

    @admin_login_required
    def put(self, active_user):
        try:
            data = request.get_json()

            question = data.get('question')
            answer = data.get('answer')
            question_ar = data.get('question_ar')
            answer_ar = data.get('answer_ar')
            question_bn = data.get('question_bn')
            answer_bn = data.get('answer_bn')
            faq_id = data.get('faq_id')

            if not faq_id:
                return jsonify({'status': 0, 'message': 'Please select faq'})
            if not question:
                return jsonify({'status': 0,'message': 'Please provide question in english'})
            if not answer:
                return jsonify({'status': 0,'message': 'Please provide answer in english'})
            if not question_ar:
                return jsonify({'status': 0,'message': 'Please provide question in arabic'})
            if not answer_ar:
                return jsonify({'status': 0,'message': 'Please provide answer in arabic'})
            if not question_bn:
                return jsonify({'status': 0,'message': 'Please provide question in bangladeshi'})
            if not answer_bn:
                return jsonify({'status': 0,'message': 'Please provide answer in bangladeshi'})

            get_faq = Faqs.query.get(faq_id)
            if not get_faq:
                return jsonify({'status': 0, 'message': 'Invalid faq'})

            get_faq.question=question
            get_faq.answer=answer
            get_faq.question_ar = question_ar
            get_faq.answer_ar = answer_ar
            get_faq.question_bn = question_bn
            get_faq.answer_bn = answer_bn

            db.session.commit()

            return jsonify({'status': 1, 'message': 'Successfully faq updated'})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

    @admin_login_required
    def delete(self, active_user):
        try:
            data = request.get_json()

            faq_id = data.get('faq_id')

            if not faq_id:
                return jsonify({'status': 0, 'message': 'Please select faq'})

            get_faq = Faqs.query.get(faq_id)
            if not get_faq:
                return jsonify({'status': 0, 'message': 'Invalid faq'})

            db.session.delete(get_faq)
            db.session.commit()

            return jsonify({'status': 1, 'message': 'Successfully faq deleted'})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

    @admin_login_required
    def get(self, active_user):
        try:
            get_faqs = Faqs.query.all()

            faq_list = [ i.as_dict_admin() for i in get_faqs ]

            return jsonify({'status': 1,'message': 'Success','faq_list': faq_list})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

class AdminMetadataResource(Resource):
    @admin_login_required
    def get(self, active_user):
        try:
            get_services = Services.query.filter_by(is_deleted=False).all()

            service_list = [ i.as_dict_admin() for i in get_services ]

            if active_user.is_subadmin == True:
                get_zones = Zone.query.filter_by(is_deleted=False,subadmin_id=active_user.id).all()

            else:
                get_zones = Zone.query.filter_by(is_deleted=False).all()

            zone_list = [ i.as_dict() for i in get_zones ]

            if active_user.is_subadmin == True:
                get_provider = User.query.filter(User.subadmin_id == active_user.id,User.is_deleted == False, User.is_block == False,
                                                  User.role == "Worker").order_by(User.id.desc()).all()

                provider_list = [ i.as_dict_admin() for i in get_provider ]

            else:
                get_provider = Admin.query.filter_by(is_subadmin = True,is_block = False).all()

                provider_list = [i.as_dict_admin() for i in get_provider]

            return jsonify({'status': 1,'message': 'Success','service_list': service_list,'zone_list': zone_list,'provider_list': provider_list})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

class AdminExtrasListingResource(Resource):
    @admin_login_required
    def post(self, active_user):
        try:
            data = request.get_json()

            page = int(data.get('page', 1))
            search_text = data.get('search_text')
            per_page = 10

            if search_text:
                get_extras = Extras.query.filter(Extras.name.ilike(f"{search_text}%"), Extras.is_deleted == False
                                              ).order_by(
                    Extras.name.asc()).paginate(page=page, per_page=per_page,
                                             error_out=False)
            else:
                get_extras = Extras.query.filter(Extras.is_deleted == False,
                                                 ).order_by(
                    Extras.name.asc()).paginate(page=page, per_page=per_page,
                                                error_out=False)

            has_next = get_extras.has_next
            total_pages = get_extras.pages

            pagination_info = {
                "current_page": page,
                "has_next": has_next,
                "per_page": per_page,
                "total_pages": total_pages,
            }

            extras_list = [ i.as_dict_admin() for i in get_extras.items ]

            return jsonify({'status': 1,'message': 'Success','extras_list': extras_list,'pagination_info': pagination_info})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

class AdminExtrasResource(Resource):
    @admin_login_required
    def post(self, active_user):
        try:
            name = request.form.get('name')
            name_ar = request.form.get('name_ar')
            name_bn = request.form.get('name_bn')
            price = request.form.get('price')
            image = request.files.get('image')

            if not name:
                return jsonify({'status': 0,'message': 'Name in english is required'})
            if not name_ar:
                return jsonify({'status': 0,'message': 'Name in arabic is required'})
            if not name_bn:
                return jsonify({'status': 0,'message': 'Name in bangladeshi is required'})
            if not price:
                return jsonify({'status': 0,'message': 'Price is required'})
            if not image:
                return jsonify({'status': 0,'message': 'Image is required'})

            image_name = None
            image_path = None

            if image:
                file_path, picture = upload_photos(image)
                image_name = picture
                image_path = file_path

            add_extras = Extras(name_bn=name_bn,name_ar=name_ar,name=name,price=price,image_name = image_name,image_path = image_path)
            db.session.add(add_extras)
            db.session.commit()

            return jsonify({'status': 1,'message': 'Successfully added'})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

    @admin_login_required
    def put(self, active_user):
        try:
            name = request.form.get('name')
            name_ar = request.form.get('name_ar')
            name_bn = request.form.get('name_bn')
            price = request.form.get('price')
            image = request.files.get('image')
            extra_id = request.form.get('extra_id')

            if not extra_id:
                return jsonify({'status': 0, 'message': 'Please select item first'})
            if not name:
                return jsonify({'status': 0, 'message': 'Name is required'})
            if not name_ar:
                return jsonify({'status': 0,'message': 'Name in arabic is required'})
            if not name_bn:
                return jsonify({'status': 0,'message': 'Name in bangladeshi is required'})
            if not price:
                return jsonify({'status': 0, 'message': 'Price is required'})

            get_extras = Extras.query.get(extra_id)
            if not get_extras:
                return jsonify({'status': 0, 'message': 'Invalid item'})

            image_name = get_extras.image_name
            image_path = get_extras.image_path

            if image:
                delete_photos(image_name)
                file_path, picture = upload_photos(image)
                image_name = picture
                image_path = file_path

            get_extras.image_name = image_name
            get_extras.image_path = image_path
            get_extras.name = name
            get_extras.name_ar = name_ar
            get_extras.name_bn = name_bn
            get_extras.price = price

            db.session.commit()

            return jsonify({'status': 1, 'message': 'Successfully item updated'})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

    @admin_login_required
    def delete(self, active_user):
        try:
            extra_id = request.json.get('extra_id')

            if not extra_id:
                return jsonify({'status': 0, 'message': 'Please select item first'})

            get_extras = Extras.query.get(extra_id)
            if not get_extras:
                return jsonify({'status': 0, 'message': 'Invalid item'})

            get_extras.is_deleted = True
            db.session.commit()

            return jsonify({'status': 1,'message': 'Successfully item deleted'})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

class StoreResource(Resource):
    @admin_login_required
    def get(self, active_user):
        try:
            get_store_data = Store.query.all()

            store_data = [ i.as_dict() for i in get_store_data ]

            return jsonify({'status': 1,'message': 'Success','store_data': store_data})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

    @admin_login_required
    def put(self, active_user):
        try:
            data = request.get_json()

            day_id = data.get('id')
            open_time = data.get('open_time')
            close_time = data.get('close_time')

            if not day_id:
                return jsonify({'status': 0,'message': 'Please select day first'})

            get_data = Store.query.get(day_id)
            if not get_data:
                return jsonify({'status': 0,'message': 'Invalid data'})

            get_data.open_time = open_time
            get_data.close_time = close_time

            db.session.commit()

            return jsonify({'status': 1,'message': 'Time updated successfully'})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

class AssignProviderListResource(Resource):
    @admin_login_required
    def post(self, active_user):
        try:
            data = request.get_json()

            page = int(data.get('page', 1))
            per_page = 10

            if active_user.is_subadmin == True:

                get_assigned_data = AssignProviderService.query.order_by(AssignProviderService.id.desc()).paginate(page=page,
                                                                                                         per_page=per_page,
                                                                                                         error_out=False)
                assigend_list = []
                if get_assigned_data.items:
                    for i in get_assigned_data.items:
                        get_subzone = SubZone.query.get(i.sub_zone_id)

                        assigend_dict = {
                            'user_id': i.user_id,
                            'name': i.assign_provider.name,
                            'service_id': i.service_id,
                            'service_name': i.assign_service.service_name,
                            'zone_id': i.zone_id,
                            'zone_name': i.assign_zone.zone_name,
                            'subzone_name': get_subzone.zone_name
                        }
                        assigend_list.append(assigend_dict)

                has_next = get_assigned_data.has_next
                total_pages = get_assigned_data.pages

                pagination_info = {
                    "current_page": page,
                    "has_next": has_next,
                    "per_page": per_page,
                    "total_pages": total_pages
                }

                return jsonify({'status': 1,'messsage': 'Success','assigend_list': assigend_list,'pagination_info': pagination_info})

            else:

                get_assigned_data = Zone.query.filter(Zone.subadmin_id != None,Zone.is_deleted==False).order_by(Zone.id.desc()).paginate(
                    page=page,
                    per_page=per_page,
                    error_out=False)

                assigend_list = []

                if get_assigned_data.items:
                    for i in get_assigned_data.items:

                        get_subadmin_data = Admin.query.get(i.subadmin_id)

                        assigend_dict = {
                            'user_id': get_subadmin_data.id,
                            'name': get_subadmin_data.firstname + get_subadmin_data.lastname if get_subadmin_data.lastname is not None else get_subadmin_data.firstname,
                            'service_id': '',
                            'service_name': '',
                            'zone_id': i.id,
                            'zone_name': i.zone_name,
                            'subzone_name': ""
                        }
                        assigend_list.append(assigend_dict)

                has_next = get_assigned_data.has_next
                total_pages = get_assigned_data.pages

                pagination_info = {
                    "current_page": page,
                    "has_next": has_next,
                    "per_page": per_page,
                    "total_pages": total_pages
                }

                return jsonify({'status': 1, 'messsage': 'Success', 'assigend_list': assigend_list,
                                'pagination_info': pagination_info})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

# class AssignProviderResource(Resource):
#     @admin_login_required
#     def post(self, active_user):
#         try:
#             data = request.get_json()
#
#             print('dataaaaaaaaaaaaaaaaaaaaaaa',data)
#
#             provider_id = data.get('provider_id')
#             service_id = data.get('service_id')
#             zone_id = data.get('zone_id')
#             sub_zone_id = data.get('sub_zone_id')
#
#             if not provider_id:
#                 return jsonify({'status': 0,'message': 'Please select provider first.'})
#             if not zone_id:
#                 return jsonify({'status': 0,'message': 'Please select zone first.'})
#
#             get_zone = Zone.query.get(zone_id)
#             if not get_zone:
#                 return jsonify({'status': 0, 'message': 'Invalid zone.'})
#
#             if active_user.is_subadmin == True:
#                 if not service_id:
#                     return jsonify({'status': 0, 'message': 'Please select service first.'})
#                 if not sub_zone_id:
#                     return jsonify({'status': 0, 'message': 'Please select subzone.'})
#
#                 get_sub_zone = SubZone.query.get(sub_zone_id)
#                 if not get_sub_zone:
#                     return jsonify({'status': 0, 'message': 'Invalid sub zone.'})
#
#                 get_provider = User.query.filter_by(id=provider_id,role = "Worker").first()
#                 if not get_provider:
#                     return jsonify({'status': 0,'message': 'Invalid worker.'})
#
#                 get_service = Services.query.get(service_id)
#                 if not get_service:
#                     return jsonify({'status': 0, 'message': 'Invalid service.'})
#
#                 check_already_assign = AssignProviderService.query.filter_by(sub_zone_id=sub_zone_id,user_id = provider_id,service_id=service_id,zone_id=zone_id).first()
#                 if check_already_assign:
#                     return jsonify({'status': 0,'message': 'You cannot assign same worker for same subzone with same service which is already assigned'})
#
#                 get_store_data = Store.query.all()
#
#                 if len(get_store_data)>0:
#                     for i in get_store_data:
#                         slot_list = get_hourly_slots(i.day)
#                         if len(slot_list)>0:
#                             for j in slot_list:
#                                 get_slot_data = ProviderSlots.query.filter(ProviderSlots.user_id == provider_id,ProviderSlots.day == i.day,ProviderSlots.start_time== j['start_time'],ProviderSlots.end_time== j['end_time']).first()
#                                 if not get_slot_data:
#                                     add_new_slots = ProviderSlots(user_id = provider_id,day = i.day,start_time = j['start_time'],end_time= j['end_time'])
#                                     db.session.add(add_new_slots)
#
#                             db.session.commit()
#
#                 add_data = AssignProviderService(subzone_polygon_geojson=get_sub_zone.polygon_geojson,zone_polygon_geojson=get_zone.polygon_geojson,sub_zone_id=sub_zone_id,place_id = get_zone.place_id,user_id = provider_id,service_id=service_id,zone_id=zone_id,created_time=datetime.utcnow())
#                 db.session.add(add_data)
#                 db.session.commit()
#
#                 return jsonify({'status': 1,'message': 'Service assign successfully'})
#
#             else:
#                 get_provider = Admin.query.filter_by(id=provider_id, is_subadmin=True).first()
#                 if not get_provider:
#                     return jsonify({'status': 0, 'message': 'Invalid provider.'})
#
#                 if get_zone.subadmin_id is not None:
#                     if get_zone.subadmin_id == int(provider_id):
#                         return jsonify({'status': 0,'message': 'You already assign this provider to same zone.'})
#
#                     return jsonify({'status': 0,'message': 'You already assign this zone to another provider.'})
#
#                 get_zone.subadmin_id = provider_id
#                 db.session.commit()
#
#                 return jsonify({'status': 1, 'message': 'Zone assign successfully'})
#
#         except Exception as e:
#             print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
#             return {'status': 0, 'message': 'Something went wrong'}, 400

class AssignProviderResource(Resource):
    @admin_login_required
    def post(self, active_user):
        try:
            data = request.get_json()

            print('dataaaaaaaaaaaaaaaaaaaaaaa',data)

            provider_id = data.get('provider_id')
            service_id = data.get('service_id')
            zone_id = data.get('zone_id')
            sub_zone_id = data.get('sub_zone_id')

            if not provider_id:
                return jsonify({'status': 0,'message': 'Please select provider first.'})
            if not zone_id:
                return jsonify({'status': 0,'message': 'Please select zone first.'})

            get_zone = Zone.query.get(zone_id)
            if not get_zone:
                return jsonify({'status': 0, 'message': 'Invalid zone.'})

            if active_user.is_subadmin == True:
                if not service_id:
                    return jsonify({'status': 0, 'message': 'Please select service first.'})
                if not sub_zone_id:
                    return jsonify({'status': 0, 'message': 'Please select subzone.'})

                get_sub_zone = SubZone.query.get(sub_zone_id)
                if not get_sub_zone:
                    return jsonify({'status': 0, 'message': 'Invalid sub zone.'})

                # get_provider = User.query.filter_by(id=provider_id,role = "Worker").first()
                # if not get_provider:
                #     return jsonify({'status': 0,'message': 'Invalid worker.'})

                # get_service = Services.query.get(service_id)
                # if not get_service:
                #     return jsonify({'status': 0, 'message': 'Invalid service.'})

                for i in provider_id:
                    get_provider = User.query.filter_by(id=i,role = "Worker").first()
                    if not get_provider:
                        return jsonify({'status': 0,'message': 'Invalid worker.'})

                    for j in service_id:
                        get_service = Services.query.get(j)
                        if not get_service:
                            return jsonify({'status': 0, 'message': 'Invalid service.'})

                        check_already_assign = AssignProviderService.query.filter_by(sub_zone_id=sub_zone_id,
                                                                             user_id=i, service_id=j,
                                                                             zone_id=zone_id).first()
                        if check_already_assign:
                            return jsonify({'status': 0,
                                    'message': 'You cannot assign same worker for same subzone with same service which is already assigned'})

                        add_data = AssignProviderService(subzone_polygon_geojson=get_sub_zone.polygon_geojson,
                                                         zone_polygon_geojson=get_zone.polygon_geojson,
                                                         sub_zone_id=sub_zone_id, place_id=get_zone.place_id,
                                                         user_id=i, service_id=j, zone_id=zone_id,
                                                         created_time=datetime.utcnow())
                        db.session.add(add_data)
                        db.session.commit()

                # get_store_data = Store.query.all()
                #
                # if len(get_store_data)>0:
                #     for i in get_store_data:
                #         slot_list = get_hourly_slots(i.day)
                #         if len(slot_list)>0:
                #             for j in slot_list:
                #                 get_slot_data = ProviderSlots.query.filter(ProviderSlots.user_id == provider_id,ProviderSlots.day == i.day,ProviderSlots.start_time== j['start_time'],ProviderSlots.end_time== j['end_time']).first()
                #                 if not get_slot_data:
                #                     add_new_slots = ProviderSlots(user_id = provider_id,day = i.day,start_time = j['start_time'],end_time= j['end_time'])
                #                     db.session.add(add_new_slots)
                #
                #             db.session.commit()

                return jsonify({'status': 1,'message': 'Service assign successfully'})

            else:
                get_provider = Admin.query.filter_by(id=provider_id, is_subadmin=True).first()
                if not get_provider:
                    return jsonify({'status': 0, 'message': 'Invalid provider.'})

                if get_zone.subadmin_id is not None:
                    if get_zone.subadmin_id == int(provider_id):
                        return jsonify({'status': 0,'message': 'You already assign this provider to same zone.'})

                    return jsonify({'status': 0,'message': 'You already assign this zone to another provider.'})

                get_zone.subadmin_id = provider_id
                db.session.commit()

                return jsonify({'status': 1, 'message': 'Zone assign successfully'})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

class ZoneListingResource(Resource):
    @admin_login_required
    def post(self, active_user):
        try:
            data = request.get_json()

            page = int(data.get('page', 1))
            per_page = 10

            get_zone_data = Zone.query.filter_by(is_deleted = False).order_by(Zone.id.desc()).paginate(page=page, per_page=per_page,error_out=False)

            has_next= get_zone_data.has_next
            total_pages = get_zone_data.pages

            pagination_info = {
                "current_page": page,
                "has_next": has_next,
                "per_page": per_page,
                "total_pages": total_pages,
            }

            zone_list = [ i.as_dict() for i in get_zone_data.items ]

            return jsonify({'status': 1,'message': 'Success','zone_list': zone_list,'pagination_info': pagination_info})


        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

class SubAdminZoneListingResource(Resource):
    @admin_login_required
    def post(self, active_user):
        try:
            data = request.get_json()

            page = int(data.get('page', 1))
            per_page = 10

            get_zone_data = Zone.query.filter_by(is_deleted = False,subadmin_id = active_user.id).order_by(Zone.id.desc()).paginate(page=page, per_page=per_page,error_out=False)

            has_next= get_zone_data.has_next
            total_pages = get_zone_data.pages

            pagination_info = {
                "current_page": page,
                "has_next": has_next,
                "per_page": per_page,
                "total_pages": total_pages,
            }

            zone_list = [ i.as_dict() for i in get_zone_data.items ]

            return jsonify({'status': 1,'message': 'Success','zone_list': zone_list,'pagination_info': pagination_info})


        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

class SubZoneListingResource(Resource):
    @admin_login_required
    def post(self, active_user):
        try:
            data = request.get_json()

            page = int(data.get('page', 1))
            per_page = 10

            zone_id = data.get('zone_id')

            get_zone_data = SubZone.query.filter_by(is_deleted = False,zone_id=zone_id,subadmin_id = active_user.id).order_by(SubZone.id.desc()).paginate(page=page, per_page=per_page,error_out=False)

            has_next= get_zone_data.has_next
            total_pages = get_zone_data.pages

            pagination_info = {
                "current_page": page,
                "has_next": has_next,
                "per_page": per_page,
                "total_pages": total_pages,
            }

            zone_list = [ i.as_dict() for i in get_zone_data.items ]

            return jsonify({'status': 1,'message': 'Success','zone_list': zone_list,'pagination_info': pagination_info})


        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

class SubZoneResource(Resource):
    @admin_login_required
    def post(self, active_user):
        try:
            data = request.get_json()

            print('dataaaaaaaaa',data)

            zone_name = data.get('subzone_name')
            zone_city = data.get('zone_city')
            zone_area = data.get('zone_area')
            address = data.get('address')
            place_id = data.get('place_id')
            lat = data.get('lat')
            long = data.get('long')

            zone_id = data.get('parent_zone_id')

            polygon_path = data.get('polygon_path')
            polygon_geojson = data.get('polygon_geojson')

            if not zone_id:
                return jsonify({'status': 0,'message': 'Please select zone'})

            if not polygon_geojson:
                return jsonify({'status': 0,'message': 'Polygon not found'})

            if not zone_name:
                return jsonify({'status': 0,'message': 'Please provide zone name'})
            if not zone_area:
                return jsonify({'status': 0,'message': 'Please provide zone area'})
            if not zone_city:
                return jsonify({'status': 0,'message': 'Please provide zone city'})
            if not address:
                return jsonify({'status': 0,'message': 'Please provide address'})
            if not lat:
                return jsonify({'status': 0,'message': 'Please provide latitude'})
            if not long:
                return jsonify({'status': 0,'message': 'Please provide longitude'})

            get_zone_data = Zone.query.get(zone_id)
            if not get_zone_data:
                return jsonify({'status': 0,'message': 'Zone data not found'})

            # Validate geometry with Shapely
            poly = shape(polygon_geojson)  # expects GeoJSON [lng, lat]
            if not isinstance(poly, Polygon):
                return jsonify({"status": 0, "message": "Invalid polygon"}), 400

            if len(list(poly.exterior.coords)) < 4:  # closed ring includes last==first
                return jsonify({"status": 0, "message": "Polygon needs at least 3 points"}), 400

            if not poly.is_valid:
                reason = explain_validity(poly)
                return jsonify({"status": 0, "message": f"Invalid polygon: {reason}"}), 400

            polygon_geojson_json = json.dumps(polygon_geojson)
            polygon_path_json = json.dumps(polygon_path)

            add_zone = SubZone(subadmin_id=active_user.id,zone_id = zone_id,polygon_geojson=polygon_geojson_json,polygon_path=polygon_path_json,zone_area=zone_area,created_time=datetime.utcnow(),zone_name=zone_name,zone_city=zone_city,address=address,place_id=place_id,lat=lat,long=long)
            db.session.add(add_zone)
            db.session.commit()

            return jsonify({'status':1,'message': 'Zone saved successfully'})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

    @admin_login_required
    def delete(self, active_user):
        try:
            data = request.get_json()

            print('dataaaaaaa',data)

            zone_id = data.get('subzone_id')

            if not zone_id:
                return jsonify({'status': 0, 'message': 'Please select zone first'})

            get_zone = SubZone.query.get(zone_id)
            if not get_zone:
                return jsonify({'status': 0, 'message': 'Invalid zone'})

            get_zone.is_deleted = True
            db.session.commit()

            return jsonify({'status': 1, 'message': 'Zone deleted successfully'})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

class ZoneResource(Resource):
    @admin_login_required
    def post(self, active_user):
        try:
            data = request.get_json()

            print('dataaaaaaaaa',data)

            zone_name = data.get('zone_name')
            zone_city = data.get('zone_city')
            zone_area = data.get('zone_area')
            address = data.get('address')
            place_id = data.get('place_id')
            lat = data.get('lat')
            long = data.get('long')

            polygon_path = data.get('polygon_path')
            polygon_geojson = data.get('polygon_geojson')

            if not polygon_geojson:
                return jsonify({'status': 0,'message': 'Polygon not found'})

            if not zone_name:
                return jsonify({'status': 0,'message': 'Please provide zone name'})
            if not zone_area:
                return jsonify({'status': 0,'message': 'Please provide zone area'})
            if not zone_city:
                return jsonify({'status': 0,'message': 'Please provide zone city'})
            if not address:
                return jsonify({'status': 0,'message': 'Please provide address'})
            if not lat:
                return jsonify({'status': 0,'message': 'Please provide latitude'})
            if not long:
                return jsonify({'status': 0,'message': 'Please provide longitude'})

            # Validate geometry with Shapely
            poly = shape(polygon_geojson)  # expects GeoJSON [lng, lat]
            if not isinstance(poly, Polygon):
                return jsonify({"status": 0, "message": "Invalid polygon"}), 400

            if len(list(poly.exterior.coords)) < 4:  # closed ring includes last==first
                return jsonify({"status": 0, "message": "Polygon needs at least 3 points"}), 400

            if not poly.is_valid:
                reason = explain_validity(poly)
                return jsonify({"status": 0, "message": f"Invalid polygon: {reason}"}), 400

            polygon_geojson_json = json.dumps(polygon_geojson)
            polygon_path_json = json.dumps(polygon_path)

            add_zone = Zone(polygon_geojson=polygon_geojson_json,polygon_path=polygon_path_json,zone_area=zone_area,created_time=datetime.utcnow(),zone_name=zone_name,zone_city=zone_city,address=address,place_id=place_id,lat=lat,long=long)
            db.session.add(add_zone)
            db.session.commit()

            return jsonify({'status':1,'message': 'Zone saved successfully'})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

    @admin_login_required
    def delete(self, active_user):
        try:
            zone_id = request.json.get('zone_id')
            if not zone_id:
                return jsonify({'status': 0,'message': 'Please select zone first'})

            get_zone = Zone.query.get(zone_id)
            if not get_zone:
                return jsonify({'status': 0,'message': 'Invalid zone'})

            get_subzones = SubZone.query.filter_by(zone_id = get_zone.id,is_deleted=False).all()
            if len(get_subzones)>0:
                for i in get_subzones:
                    i.is_deleted = True
                db.session.commit()

            get_zone.is_deleted = True
            db.session.commit()

            return jsonify({'status': 1,'message': 'Zone deleted successfully'})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

class ServicesResource(Resource):
    @admin_login_required
    def post(self, active_user):
        try:
            data = request.form

            service_name = data.get('service_name')
            service_description = data.get('service_description')
            service_name_ar = data.get('service_name_ar')
            service_description_ar = data.get('service_description_ar')
            service_name_bn = data.get('service_name_bn')
            service_description_bn = data.get('service_description_bn')
            service_price = data.get('service_price')
            service_image = request.files.get('service_image')

            if not service_name:
                return jsonify({'status': 0,'message': 'Service name in english is required'})
            if not service_description:
                return jsonify({'status': 0,'message': 'Service description in english is required'})

            if not service_name_ar:
                return jsonify({'status': 0,'message': 'Service name in arabic is required'})
            if not service_description_ar:
                return jsonify({'status': 0,'message': 'Service description in arabic is required'})

            if not service_name_bn:
                return jsonify({'status': 0,'message': 'Service name in bangladeshi is required'})
            if not service_description_bn:
                return jsonify({'status': 0,'message': 'Service description in bangladeshi is required'})

            if not service_price:
                return jsonify({'status': 0,'message': 'Service price is required'})
            if not service_image:
                return jsonify({'status': 0,'message': 'Service image is required'})

            image_name = None
            image_path = None

            if service_image:
                file_path , picture = upload_photos(service_image)
                image_name = picture
                image_path = file_path

            add_service = Services(service_description_bn=service_description_bn,service_name_bn=service_name_bn,service_description_ar=service_description_ar,service_name_ar=service_name_ar,service_name=service_name,service_description=service_description,service_price=service_price,
                                   image_name=image_name,image_path=image_path,created_time= datetime.utcnow())

            db.session.add(add_service)
            db.session.commit()

            return jsonify({'status': 1,'message': 'Service added successfully'})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

    @admin_login_required
    def put(self, active_user):
        try:
            data = request.form

            service_id = data.get('service_id')
            service_name = data.get('service_name')
            service_description = data.get('service_description')

            service_name_ar = data.get('service_name_ar')
            service_description_ar = data.get('service_description_ar')
            service_name_bn = data.get('service_name_bn')
            service_description_bn = data.get('service_description_bn')

            service_price = data.get('service_price')
            service_image = request.files.get('service_image')

            if not service_id:
                return jsonify({'status': 0, 'message': 'Please select service first'})
            if not service_name:
                return jsonify({'status': 0,'message': 'Service name in english is required'})
            if not service_description:
                return jsonify({'status': 0,'message': 'Service description in english is required'})

            if not service_name_ar:
                return jsonify({'status': 0,'message': 'Service name in arabic is required'})
            if not service_description_ar:
                return jsonify({'status': 0,'message': 'Service description in arabic is required'})

            if not service_name_bn:
                return jsonify({'status': 0,'message': 'Service name in bangladeshi is required'})
            if not service_description_bn:
                return jsonify({'status': 0,'message': 'Service description in bangladeshi is required'})
            if not service_price:
                return jsonify({'status': 0, 'message': 'Service price is required'})

            get_service_data = Services.query.get(service_id)
            if not get_service_data:
                return jsonify({'status': 0, 'message': 'Invalid service'})

            image_name = get_service_data.image_name
            image_path = get_service_data.image_path

            if service_image:
                delete_photos(image_name)
                file_path, picture = upload_photos(service_image)
                image_name = picture
                image_path = file_path

            get_service_data.image_name = image_name
            get_service_data.image_path = image_path
            get_service_data.service_name = service_name
            get_service_data.service_description = service_description

            get_service_data.service_name_ar = service_name_ar
            get_service_data.service_description_ar = service_description_ar
            get_service_data.service_name_bn = service_name_bn
            get_service_data.service_description_bn = service_description_bn

            get_service_data.service_price = service_price

            db.session.commit()

            return jsonify({'status': 1, 'message': 'Service updated successfully'})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

    @admin_login_required
    def delete(self, active_user):
        try:
            data = request.get_json()

            service_id = data.get('service_id')
            if not service_id:
                return jsonify({'status': 0, 'message': 'Please select service first'})

            get_service_data = Services.query.get(service_id)
            if not get_service_data:
                return jsonify({'status': 0, 'message': 'Invalid service'})

            get_service_data.is_deleted = True
            db.session.commit()

            return jsonify({'status': 1, 'message': 'Service deleted successfully'})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

class UserListResource(Resource):
    @admin_login_required
    def post(self, active_user):
        try:
            data = request.get_json()

            page = int(data.get('page', 1))
            search_text = data.get('search_text')
            per_page = 10

            if search_text:
                get_users = User.query.filter(User.name.ilike(f"{search_text}%"),User.is_deleted == False,User.is_block == False,User.role == "Customer").order_by(User.id.desc()).paginate(page=page, per_page=per_page,
                                                                                          error_out=False)
            else:
                get_users = User.query.filter(User.is_deleted == False, User.is_block == False,
                                              User.role == "Customer").order_by(User.id.desc()).paginate(page=page,
                                                                                                             per_page=per_page,
                                                                                                             error_out=False)

            has_next = get_users.has_next
            total_pages = get_users.pages

            pagination_info = {
                "current_page": page,
                "has_next": has_next,
                "per_page": per_page,
                "total_pages": total_pages,
            }

            user_list = [ i.as_dict_admin() for i in get_users.items ]

            return jsonify({'status': 1,'message': 'Success','user_list': user_list,'pagination_info': pagination_info})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

class UserListNoPaginationResource(Resource):
    @admin_login_required
    def get(self, active_user):
        try:

            get_users = User.query.filter(User.is_deleted == False, User.is_block == False,
                                              User.role == "Customer").order_by(User.id.desc()).all()

            user_list = [ i.as_dict_admin() for i in get_users ]

            return jsonify({'status': 1,'message': 'Success','user_list': user_list})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

class MainProviderListResource(Resource):
    @admin_login_required
    def post(self, active_user):
        try:
            data = request.get_json()

            print('dataaaaaaaaaaaaaa',data)

            page = int(data.get('page', 1))
            search_text = data.get('search_text')
            per_page = 10

            if search_text:
                print('searchhhh running')
                full_name = func.concat(Admin.firstname, ' ', Admin.lastname)
                get_subadmins = (
                    Admin.query.filter(
                        full_name.ilike(f"%{search_text}%"),
                        Admin.is_subadmin == True,
                        Admin.is_block == False
                    )
                        .order_by(Admin.id.desc())
                        .paginate(page=page, per_page=per_page, error_out=False)
                )
            else:
                print('searchhhh not running')
                get_subadmins = Admin.query.filter(Admin.is_subadmin == True, Admin.is_block == False).order_by(Admin.id.desc()).paginate(page=page,
                                                                                                             per_page=per_page,
                                                                                                             error_out=False)
                print('itemsssssssssssss',get_subadmins.items)

            has_next = get_subadmins.has_next
            total_pages = get_subadmins.pages

            pagination_info = {
                "current_page": page,
                "has_next": has_next,
                "per_page": per_page,
                "total_pages": total_pages,
            }

            user_list = [ i.as_dict_admin() for i in get_subadmins.items ]

            return jsonify({'status': 1,'message': 'Success','user_list': user_list,'pagination_info': pagination_info})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

class ProviderListResource(Resource):
    @admin_login_required
    def post(self, active_user):
        try:
            data = request.get_json()

            page = int(data.get('page', 1))
            search_text = data.get('search_text')
            per_page = 10

            if search_text:
                print('searchhhh running')
                get_users = User.query.filter(User.name.ilike(f"{search_text}%"),User.subadmin_id==active_user.id,User.is_deleted == False,User.is_block == False,User.role == "Worker").order_by(User.id.desc()).paginate(page=page, per_page=per_page,
                                                                                          error_out=False)
            else:
                print('searchhhh notttttttttt running')
                get_users = User.query.filter(User.subadmin_id==active_user.id,User.is_deleted == False, User.is_block == False,
                                              User.role == "Worker").order_by(User.id.desc()).paginate(page=page,
                                                                                                             per_page=per_page,
                                                                                                             error_out=False)

            has_next = get_users.has_next
            total_pages = get_users.pages

            pagination_info = {
                "current_page": page,
                "has_next": has_next,
                "per_page": per_page,
                "total_pages": total_pages,
            }

            user_list = [ i.as_dict_admin() for i in get_users.items ]

            return jsonify({'status': 1,'message': 'Success','user_list': user_list,'pagination_info': pagination_info})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

class ServicesListResource(Resource):
    @admin_login_required
    def post(self, active_user):
        try:
            data = request.get_json()

            page = int(data.get('page', 1))
            search_text = data.get('search_text')
            per_page = 10

            if search_text:
                get_services = Services.query.filter(Services.service_name.ilike(f"{search_text}%"),Services.is_deleted == False).order_by(Services.id.desc()).paginate(page=page, per_page=per_page,
                                                                                      error_out=False)
            else:
                get_services = Services.query.filter(Services.is_deleted == False).order_by(Services.id.desc()).paginate(page=page, per_page=per_page,
                                                                                      error_out=False)

            has_next = get_services.has_next
            total_pages = get_services.pages

            pagination_info = {
                "current_page": page,
                "has_next": has_next,
                "per_page": per_page,
                "total_pages": total_pages,
            }

            service_list = [ i.as_dict_admin() for i in get_services.items ]

            return jsonify({'status': 1,'message': 'Success','service_list': service_list,'pagination_info': pagination_info})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

# class CarsResource(Resource):
#     @admin_login_required
#     def get(self, active_user):
#         try:
#             # "E:\all-vehicles-model.csv"
#             # E:\UsedCarsSA_Clean_EN.csv
#
#             # car = Cars(
#             #     name=row.get('Make'),
#             #     type=row.get('Type'),
#             #     year=row.get('Year'),
#             #     color=row.get('Color'),
#             #     options=row.get('Options'),
#             #     engine_size=row.get('Engine_Size'),
#             #     fuel_type=row.get('Fuel_Type'),
#             #     gear_type=row.get('Gear_Type'),
#             #     mileage=str(row.get('Mileage')),
#             #     region=row.get('Region'),
#             #     created_time=datetime.utcnow()
#             # )
#
#
#             with open(r'E:\all-vehicles-model (2).csv', 'r', encoding='utf-8') as f:
#                 reader = csv.DictReader(f)
#                 for row in reader:
#
#                     get_exists_brand = CarBrands.query.filter_by(name=row.get('Make')).first()
#
#                     if get_exists_brand:
#                         brand_id = get_exists_brand.id
#                     else:
#
#                         car_brands = CarBrands(
#                             name=row.get('Make'),
#                             created_time=datetime.utcnow()
#                         )
#
#                         db.session.add(car_brands)
#                         db.session.commit()
#
#                         brand_id = car_brands.id
#                     get_exists_model = CarModels.query.filter_by(model=row.get('Model'),car_brand_id = brand_id).first()
#
#                     if not get_exists_model:
#                         add_car_models = CarModels(
#
#                             model=row.get('Model'),
#                             year=row.get('Year'),
#                             created_time=datetime.utcnow(),
#                             car_brand_id = brand_id
#
#                         )
#
#                         db.session.add(add_car_models)
#                         db.session.commit()
#
#             return {'status': 1, 'message': 'Cars imported successfully'}, 200
#
#         except Exception as e:
#             print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
#             return {'status': 0, 'message': 'Something went wrong'}, 400

class CarsResource(Resource):
    @admin_login_required
    def get(self, active_user):
        try:
            # "E:\all-vehicles-model.csv"
            # E:\UsedCarsSA_Clean_EN.csv

            # car = Cars(
            #     name=row.get('Make'),
            #     type=row.get('Type'),
            #     year=row.get('Year'),
            #     color=row.get('Color'),
            #     options=row.get('Options'),
            #     engine_size=row.get('Engine_Size'),
            #     fuel_type=row.get('Fuel_Type'),
            #     gear_type=row.get('Gear_Type'),
            #     mileage=str(row.get('Mileage')),
            #     region=row.get('Region'),
            #     created_time=datetime.utcnow()
            # )


            # with open(r'E:\all-vehicles-model (2).csv', 'r', encoding='utf-8') as f:
            #     reader = csv.DictReader(f)
            #     for row in reader:
            #
            #         get_exists_brand = CarBrands.query.filter_by(name=row.get('Make')).first()
            #
            #         if get_exists_brand:
            #             brand_id = get_exists_brand.id
            #         else:
            #
            #             car_brands = CarBrands(
            #                 name=row.get('Make'),
            #                 created_time=datetime.utcnow()
            #             )
            #
            #             db.session.add(car_brands)
            #             db.session.commit()
            #
            #             brand_id = car_brands.id
            #         get_exists_model = CarModels.query.filter_by(model=row.get('Model'),car_brand_id = brand_id).first()
            #
            #         if not get_exists_model:
            #             add_car_models = CarModels(
            #
            #                 model=row.get('Model'),
            #                 year=row.get('Year'),
            #                 created_time=datetime.utcnow(),
            #                 car_brand_id = brand_id
            #
            #             )
            #
            #             db.session.add(add_car_models)
            #             db.session.commit()

            return {'status': 1, 'message': 'Cars imported successfully'}, 200

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

class CarBrandsResource(Resource):
    @admin_login_required
    def post(self, active_user):
        try:
            data = request.get_json()

            name = data.get('name')
            if not name:
                return jsonify({'status': 0,'message': 'Please provide brand name'})

            add_car_brand = CarBrands(name=name,created_time=datetime.utcnow())
            db.session.add(add_car_brand)
            db.session.commit()

            return {'status': 1, 'message': 'Car brand added successfully'}, 200

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

    @admin_login_required
    def put(self, active_user):
        try:
            data = request.get_json()

            name = data.get('name')
            brand_id = data.get('brand_id')
            if not name:
                return jsonify({'status': 0, 'message': 'Please provide brand name'})
            if not brand_id:
                return jsonify({'status': 0, 'message': 'Please select brand first'})

            get_brand = CarBrands.query.get(brand_id)
            if not get_brand:
                return jsonify({'status': 0, 'message': 'Invalid brand'})

            get_brand.name=name
            db.session.commit()

            return {'status': 1, 'message': 'Car brand updated successfully'}, 200

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

    @admin_login_required
    def delete(self, active_user):
        try:
            data = request.get_json()

            brand_id = data.get('brand_id')
            if not brand_id:
                return jsonify({'status': 0, 'message': 'Please select brand first'})

            check_brand = CarBrands.query.get(brand_id)
            if not check_brand:
                return jsonify({'status': 0, 'message': 'Invalid brand'})

            get_car_models = CarModels.query.filter_by(car_brand_id=check_brand.id).all()
            if len(get_car_models)>0:
                for i in get_car_models:
                    i.is_deleted = True
                db.session.commit()

            check_brand.is_deleted = True
            db.session.commit()

            return {'status': 1, 'message': 'Car brand deleted successfully'}, 200

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

class CarModelsResource(Resource):
    @admin_login_required
    def post(self, active_user):
        try:
            data = request.get_json()

            name = data.get('name')
            year = data.get('year')
            brand_id = data.get('brand_id')

            if not name:
                return jsonify({'status': 0,'message': 'Please provide model name'})
            if not year:
                return jsonify({'status': 0,'message': 'Please provide model year'})
            if not brand_id:
                return jsonify({'status': 0,'message': 'Please provide brand'})

            check_brand = CarBrands.query.get(brand_id)
            if not check_brand:
                return jsonify({'status': 0, 'message': 'Invalid brand'})

            add_car_model = CarModels(model=name,created_time=datetime.utcnow(),car_brand_id=brand_id,year=year)
            db.session.add(add_car_model)
            db.session.commit()

            return {'status': 1, 'message': 'Car model added successfully'}, 200

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

    @admin_login_required
    def put(self, active_user):
        try:
            data = request.get_json()

            name = data.get('name')
            year = data.get('year')
            model_id = data.get('model_id')
            # brand_id = data.get('brand_id')

            if not model_id:
                return jsonify({'status': 0, 'message': 'Please select model first'})
            if not name:
                return jsonify({'status': 0, 'message': 'Please provide model name'})
            if not year:
                return jsonify({'status': 0, 'message': 'Please provide model year'})
            # if not brand_id:
            #     return jsonify({'status': 0, 'message': 'Please provide brand'})

            # check_brand = CarBrands.query.get(brand_id)
            # if not check_brand:
            #     return jsonify({'status': 0, 'message': 'Invalid brand'})

            get_model_data = CarModels.query.get(model_id)
            if not get_model_data:
                return jsonify({'status': 0, 'message': 'Invalid model'})

            get_model_data.model=name
            get_model_data.year=year

            db.session.commit()

            return {'status': 1, 'message': 'Car model updated successfully'}, 200

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

    @admin_login_required
    def delete(self, active_user):
        try:
            data = request.get_json()

            model_id = data.get('model_id')
            if not model_id:
                return jsonify({'status': 0, 'message': 'Please select model first'})

            check_model = CarModels.query.get(model_id)
            if not check_model:
                return jsonify({'status': 0, 'message': 'Invalid brand'})

            check_model.is_deleted = True
            db.session.commit()

            return {'status': 1, 'message': 'Car model deleted successfully'}, 200

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

class CarsBrandListingResource(Resource):
    @admin_login_required
    def post(self, active_user):
        try:
            data = request.get_json()

            page = int(data.get('page', 1))
            search_text = data.get('search_text')
            per_page = 10

            if search_text:

                get_brands_data = CarBrands.query.filter(CarBrands.is_deleted == False,CarBrands.name.ilike(f"{search_text}%")).order_by(CarBrands.name.asc()).paginate(page=page, per_page=per_page,
                                                                                error_out=False)
            else:
                get_brands_data = CarBrands.query.filter(CarBrands.is_deleted == False).order_by(CarBrands.name.asc()).paginate(page=page, per_page=per_page,
                                                                                          error_out=False)

            has_next = get_brands_data.has_next
            total_pages = get_brands_data.pages

            pagination_info = {
                "current_page": page,
                "has_next": has_next,
                "per_page": per_page,
                "total_pages": total_pages,
            }

            car_brand_list = [ i.as_dict() for i in get_brands_data.items ]

            return jsonify(
                {'status': 1, 'message': 'Success', 'car_brand_list': car_brand_list, 'pagination_info': pagination_info})


        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

class CarsBrandListingNoPaginationResource(Resource):
    @admin_login_required
    def get(self, active_user):
        try:

            get_brands_data = CarBrands.query.filter(CarBrands.is_deleted == False).order_by(CarBrands.name.asc()).all()

            car_brand_list = [ i.as_dict() for i in get_brands_data ]

            return jsonify(
                {'status': 1, 'message': 'Success', 'car_brand_list': car_brand_list})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400


# class CarsModelListingResource(Resource):
#     @admin_login_required
#     def post(self, active_user):
#         try:
#             data = request.get_json()
#
#             page = int(data.get('page', 1))
#             brand_id = data.get('brand_id')
#             year = data.get('year')
#             search_text = data.get('search_text')
#
#             per_page = 10
#
#             query = CarModels.query.filter(CarModels.is_deleted==False)
#
#             # Filter by brand if provided
#             if brand_id:
#                 check_brand = CarBrands.query.get(brand_id)
#                 if not check_brand:
#                     return jsonify({'status': 0, 'message': 'Invalid brand'})
#                 query = query.filter(CarModels.car_brand_id == brand_id)
#
#             # Filter by year if provided
#             if year:
#                 query = query.filter(CarModels.year == year)
#
#             if search_text:
#                 query = query.filter(CarModels.model.ilike(f"{search_text}%"))
#
#             # Apply ordering and pagination
#             get_models_data = query.order_by(CarModels.model.asc()).paginate(
#                            page=page,
#                           per_page=per_page,
#                           error_out=False
#                        )
#
#             has_next = get_models_data.has_next
#             total_pages = get_models_data.pages
#
#             pagination_info = {
#                 "current_page": page,
#                 "has_next": has_next,
#                 "per_page": per_page,
#                 "total_pages": total_pages,
#             }
#
#             car_models_list = [ i.as_dict() for i in get_models_data.items ]
#
#             return jsonify(
#                 {'status': 1, 'message': 'Success', 'car_models_list': car_models_list, 'pagination_info': pagination_info})
#
#
#         except Exception as e:
#             print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
#             return {'status': 0, 'message': 'Something went wrong'}, 400


class CarsModelListingResource(Resource):
    @admin_login_required
    def post(self, active_user):
        try:
            data = request.get_json() or {}

            page = int(data.get('page', 1))
            per_page = 30

            brand_id = data.get('brand_id')        # optional
            year = data.get('year')                # optional (your model stores as string)
            search_text = (data.get('search_text') or '').strip()  # optional

            # Base query: only non-deleted models, JOIN brand for ordering by brand name
            query = (
                CarModels.query
                .filter(CarModels.is_deleted == False)
                .join(CarBrands, CarBrands.id == CarModels.car_brand_id)
                .options(contains_eager(CarModels.car_models))  # car_models is the backref to brand
            )

            # Filter by brand if provided
            if brand_id:
                check_brand = CarBrands.query.get(brand_id)
                if not check_brand:
                    return jsonify({'status': 0, 'message': 'Invalid brand'})
                query = query.filter(CarModels.car_brand_id == brand_id)

            # Filter by year if provided (stored as string in your model)
            if year:
                query = query.filter(CarModels.year == str(year))

            # Search: prefix match on model; also allow brand-name match for convenience
            if search_text:
                like_pattern = f"{search_text}%"
                query = query.filter(
                    (CarModels.model.ilike(like_pattern)) |
                    (CarBrands.name.ilike(like_pattern))
                )

            # ORDER BY brand name ASC, then model ASC
            query = query.order_by(CarBrands.name.asc(), CarModels.model.asc())

            # Pagination
            get_models_data = query.paginate(page=page, per_page=per_page, error_out=False)

            pagination_info = {
                "current_page": page,
                "has_next": get_models_data.has_next,
                "per_page": per_page,
                "total_pages": get_models_data.pages,
            }

            # Build list using your existing as_dict() (uses self.car_models.name for brand)
            car_models_list = [item.as_dict() for item in get_models_data.items]

            return jsonify({
                'status': 1,
                'message': 'Success',
                'car_models_list': car_models_list,
                'pagination_info': pagination_info
            })

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return jsonify({'status': 0, 'message': 'Something went wrong'}), 400

class DashboardResource(Resource):
    @admin_login_required
    def post(self, active_user):
        try:
            admin_timezone = request.json.get('timezone')
            if not admin_timezone:
                return jsonify({'status': 0,'message': 'Timezone not found'})

            print('admin_timezone',admin_timezone)

            active_user.admin_timezone = admin_timezone
            db.session.commit()

            if active_user.is_subadmin == True:

                user_counts = User.query.filter_by(is_deleted = False,is_block = False,role = 'Customer').count()
                provider_counts = User.query.filter_by(is_deleted=False, is_block=False, role='Worker',subadmin_id = active_user.id).count()
                services_counts = Services.query.filter(Services.is_deleted == False).count()

                return jsonify({'status': 1,'message': 'Success','user_counts': user_counts,'provider_counts': provider_counts,'services_counts': services_counts})

            else:

                user_counts = User.query.filter_by(is_deleted=False, is_block=False, role='Customer').count()
                provider_counts = Admin.query.filter_by(is_block=False,is_subadmin=True).count()
                services_counts = Services.query.filter(Services.is_deleted == False).count()

                return jsonify(
                    {'status': 1, 'message': 'Success', 'user_counts': user_counts, 'provider_counts': provider_counts,
                     'services_counts': services_counts})


        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

class BannerResource(Resource):
    @admin_login_required
    def post(self, active_user):
        try:
            banner_image = request.files.get('banner_image')
            if banner_image:
                file_path, picture = upload_photos(banner_image)

                addd_banner = Banners(image_name = picture, image_path = file_path,created_time = datetime.utcnow())
                db.session.add(addd_banner)
                db.session.commit()

                return jsonify({'status': 1,'message': 'Successfully banned added'})

            else:
                return jsonify({'status': 0,'message': 'Please select banner.'})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

    @admin_login_required
    def put(self, active_user):
        try:
            banner_id = request.form.get('banner_id')
            banner_image = request.files.get('banner_image')

            validate_banner = Banners.query.get(banner_id)

            if not validate_banner:
                return jsonify({'status': 0,'message': 'Invalid banner.'})

            if banner_image:
                delete_photos(validate_banner.image_name)

                file_path, picture = upload_photos(banner_image)

                validate_banner.image_name = picture
                validate_banner.image_path = file_path
                db.session.commit()

                return jsonify({'status': 1, 'message': 'Successfully banned updated'})

            else:
                return jsonify({'status': 0, 'message': 'Please select banner.'})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

    @admin_login_required
    def delete(self, active_user):
        try:
            banner_id = request.json.get('banner_id')

            validate_banner = Banners.query.get(banner_id)

            if not validate_banner:
                return jsonify({'status': 0, 'message': 'Invalid banner.'})

            delete_photos(validate_banner.image_name)

            db.session.delete(validate_banner)
            db.session.commit()

            return jsonify({'status': 1,'message': 'Banner deleted successfully'})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

class BannerListResource(Resource):
    @admin_login_required
    def post(self, active_user):
        try:
            data = request.get_json()

            page = int(data.get('page', 1))
            per_page = 10

            get_banners_data = Banners.query.order_by(Banners.is_active.desc()).paginate(page=page, per_page=per_page,
                                                                                error_out=False)
            banner_list = [ i.as_dict_admin() for i in get_banners_data.items ]

            has_next = get_banners_data.has_next
            total_pages = get_banners_data.pages

            pagination_info = {
                "current_page": page,
                "has_next": has_next,
                "per_page": per_page,
                "total_pages": total_pages,
            }

            return jsonify({'status': 1,'message': 'Success','banner_list': banner_list,'pagination_info': pagination_info})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

class BannerStatusResource(Resource):
    @admin_login_required
    def post(self, active_user):
        try:
            banner_id = request.json.get('banner_id')

            validate_banner = Banners.query.get(banner_id)

            if not validate_banner:
                return jsonify({'status': 0, 'message': 'Invalid banner.'})

            if validate_banner.is_active == True:
                validate_banner.is_active = False
                db.session.commit()

                return jsonify({'status': 1,'message': 'Successfully banner deactivated'})

            else:
                validate_banner.is_active = True
                db.session.commit()

                return jsonify({'status': 1, 'message': 'Successfully banner activated'})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

def generate_random_string(length=10):
    characters = string.ascii_letters + string.digits  # A-Z, a-z, 0-9
    return ''.join(random.choices(characters, k=length))

class AddProviderResource(Resource):
    @admin_login_required
    def post(self, active_user):
        try:
            data = request.get_json()

            name = data.get('name')
            email = data.get('email')
            country_code = data.get('country_code')
            mobile_number = data.get('mobile_number')
            timezone = data.get('timezone')

            if not name:
                return jsonify({'status': 0,'message': 'Name is required.'})
            if not email:
                return jsonify({'status': 0,'message': 'Email is required.'})
            if not country_code:
                return jsonify({'status': 0,'message': 'Country code is required.'})
            if not mobile_number:
                return jsonify({'status': 0,'message': 'Mobile number is required.'})
            if not timezone:
                return jsonify({'status': 0,'message': 'Timezone not found.'})

            validate_user = User.query.filter_by(mobile_number=mobile_number, is_deleted=False, role="Worker").first()

            if validate_user:
                if validate_user.is_block:
                    return jsonify({'status':  0,'message': 'Your account has been blocked by the admin. Please contact the admin to reactivate your account.'})

                return jsonify({'status': 0,'message': 'Provider already exists with same mobile number.'})

            random_password = generate_random_string()

            hashed_password = generate_password_hash(random_password)

            add_provider = User(subadmin_id = active_user.id,name = name,email = email,timezone=timezone,country_code=country_code,mobile_number=mobile_number,
                                created_time=datetime.utcnow(),role = 'Worker',last_login = datetime.utcnow(),password =hashed_password)
            db.session.add(add_provider)
            db.session.commit()

            get_store_data = Store.query.all()

            if len(get_store_data) > 0:
                for i in get_store_data:
                    slot_list = get_hourly_slots(i.day)
                    if len(slot_list) > 0:
                        for j in slot_list:
                            get_slot_data = ProviderSlots.query.filter(ProviderSlots.user_id == add_provider.id,
                                                                       ProviderSlots.day == i.day,
                                                                       ProviderSlots.start_time == j['start_time'],
                                                                       ProviderSlots.end_time == j[
                                                                           'end_time']).first()
                            if not get_slot_data:
                                add_new_slots = ProviderSlots(user_id=add_provider.id, day=i.day,
                                                              start_time=j['start_time'], end_time=j['end_time'])
                                db.session.add(add_new_slots)

                        db.session.commit()


            send_provider_cred(add_provider,random_password,'User')

            return jsonify({'status': 1,'message': 'Provider added successfully, and login credentials have been sent to their email.'})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

    @admin_login_required
    def put(self, active_user):
        try:
            data = request.get_json()

            provider_id = data.get('provider_id')
            name = data.get('name')
            email = data.get('email')

            if not name:
                return jsonify({'status': 0, 'message': 'Name is required.'})
            if not email:
                return jsonify({'status': 0, 'message': 'Email is required.'})

            validate_user = User.query.filter_by(id= provider_id,role="Worker").first()

            if not validate_user:
                return jsonify({'status': 0, 'message': 'Invalid provider.'})

            validate_user.name = name
            validate_user.email = email

            db.session.commit()

            return jsonify({'status': 1,
                            'message': 'Provider profile updated successfully.'})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

    @admin_login_required
    def delete(self, active_user):
        try:
            data = request.get_json()

            provider_id = data.get('provider_id')

            validate_user = User.query.filter_by(id=provider_id, role="Worker").first()

            if not validate_user:
                return jsonify({'status': 0, 'message': 'Invalid provider.'})

            validate_user.is_deleted = True
            db.session.commit()

            return jsonify({'status': 1,'message': 'Provider deleted successfully'})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400

class GetProviderResource(Resource):
    @admin_login_required
    def post(self, active_user):
        try:
            data = request.get_json()

            provider_id = data.get('provider_id')

            validate_user = User.query.filter_by(id=provider_id, role="Worker").first()

            if not validate_user:
                return jsonify({'status': 0, 'message': 'Invalid provider.'})

            return jsonify({'status': 1,
                            'message': 'Success','data': validate_user.as_dict_basic()})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrrrrrrrrrrrrrr:', str(e))
            return {'status': 0, 'message': 'Something went wrong'}, 400