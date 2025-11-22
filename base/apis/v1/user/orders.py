from datetime import datetime
from flask import request, jsonify
from flask_restful import Resource
from base.database.db import db
from dotenv import load_dotenv
from pathlib import Path
from base.apis.v1.admin.models import Extras, Services
from base.apis.v1.user.models import ProviderRequest,UserServiceReview,ServiceCompletedData,Notification,UserPayments,token_required, User, UserAddress,SavedUserCars, ServiceRequested
from base.common.utils import push_notification
from base.common.path import COMMON_URL
from sqlalchemy import desc
from base.common.utils import upload_photos_local,upload_photos
from base.common.helpers import get_localized_service_name,get_notification_message
from base.common.path import generate_presigned_url
from base.common.helpers import get_normal_message
from base.apis.v1.user.payments import process_refund

class MyEarningResource(Resource):
    @token_required
    def get(self, active_user):
        try:

            get_payments_data = UserPayments.query.filter_by(
                    provider_id=active_user.id,
                    intend_status='Completed'
                ).order_by(UserPayments.created_time.desc(), UserPayments.id.desc()).all()

            earning_list = []
            amounts = []

            if len(get_payments_data)>0:
                for i in get_payments_data:
                    try:
                        amt = float(i.total_amount)
                    except Exception:
                        amt = 0.0
                    amounts.append(amt)

                    get_service_details = ServiceRequested.query.get(i.service_request_id)
                    if not get_service_details:
                        message = get_normal_message("msg_14", active_user.active_language)
                        return jsonify({'status': 0,'message':message})

                    get_service = Services.query.get(get_service_details.service_id)
                    if not get_service:
                        message = get_normal_message("msg_15", active_user.active_language)
                        return jsonify({'status': 0,'message':message})

                    # show_text = f"Earn {i.total_amount}SAR for the {get_service.service_name} service."

                    service_dict = get_service.as_dict(active_user.active_language)

                    payment_dict = {
                        'id': i.id,
                        # 'show_text': show_text,
                        'amount': i.total_amount,
                        'service_name': service_dict['service_name'],
                        'created_time': i.created_time
                    }

                    earning_list.append(payment_dict)

            total_earning = sum(amounts)


            # total = (
            #     db.session.query(
            #         func.coalesce(func.sum(cast(UserPayments.total_amount, Float)), 0.0)
            #     )
            #     .filter(
            #         UserPayments.provider_id == active_user.id,
            #         UserPayments.intend_status == 'Completed'
            #     )
            #     .scalar()
            # )
            #
            # return jsonify({
            #     'status': 1,
            #     'message': 'Success',
            #     'total_earning': f"{total:.1f}"  # e.g., "10.0"
            # })

            message = get_normal_message("msg_11", active_user.active_language)

            return jsonify({'status': 1,'message': message,'total_earning': total_earning,'earning_list': earning_list})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrr:', str(e))
            message = get_normal_message("msg_10", active_user.active_language)
            return {'status': 0, 'message': message}, 500

# class UserOrderListResource(Resource):
#     @token_required
#     def post(self, active_user):
#         try:
#             if active_user.role == "Worker":
#                 message = get_normal_message("msg_16", active_user.active_language)
#                 return jsonify({'status': 0,'message': message})
#
#             data = request.get_json()
#
#             # page = int(data.get('page', 1))
#             tab = data.get('tab',0)
#             # per_page = 10
#
#             if tab == 0:
#
#                 # request_status = ["Pending", "Accepted"]
#                 #
#                 # get_request_data = ServiceRequested.query.filter(
#                 #     ServiceRequested.user_id == active_user.id, ServiceRequested.is_completed == False,
#                 #     ServiceRequested.status.in_(request_status)
#                 # ).order_by(desc(ServiceRequested.id)).all()
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
#                 request_status = ["Pending", "Accepted"]
#
#                 all_rows = (
#                     ServiceRequested.query.filter(
#                         ServiceRequested.user_id == active_user.id,
#                         ServiceRequested.is_completed == False,
#                         ServiceRequested.status.in_(request_status),
#                     )
#                         .order_by(ServiceRequested.id.desc())
#                         .all()
#                 )
#
#                 # collapse duplicates based on all fields you listed
#                 unique = {}
#                 for r in all_rows:
#                     key = (
#                         r.user_id,
#                         r.service_date,
#                         r.slot_start_time,
#                         r.slot_end_time,
#                         r.service_id,
#                         r.car_id,
#                         r.address_id,
#                         r.place_id
#                     )
#
#                     if key not in unique:
#                         unique[key] = r
#                     else:
#                         # if one is Accepted → prefer that
#                         if unique[key].status != "Accepted" and r.status == "Accepted":
#                             unique[key] = r
#
#                 get_request_data = list(unique.values())
#
#                 request_list = []
#
#                 if len(get_request_data)>0:
#                     for i in get_request_data:
#                         user_data = User.query.get(i.provider_id)
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
#
#                         get_extras = []
#
#                         if i.extras_id and i.extras_id != "":
#                             split_data = i.extras_id.split(',')
#                             if len(split_data)>0:
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
#                             'mobile': user_data.mobile_number if user_data.mobile_number is not None else ''
#                         }
#
#                         service_dict = get_service_data.as_dict(active_user.active_language)
#
#                         request_dict = {
#
#                             'id': i.id,
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
#                             'completed_data': completed_data,
#                             'user_data': user_dict,
#                             'service_stage': service_stage,
#                             'review_data': {}
#
#                         }
#                         request_list.append(request_dict)
#
#                 message = get_normal_message("msg_11", active_user.active_language)
#
#                 return jsonify({'status': 1,'message': message,'request_list': request_list})
#
#             elif tab == 1:
#
#                 request_status = ["Pending", "Accepted","Late"]
#
#                 # Completed
#
#                 get_request_data = ServiceRequested.query.filter(
#                     ServiceRequested.user_id == active_user.id,
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
#                 if len(get_request_data)>0:
#                     for i in get_request_data:
#                         user_data = User.query.get(i.provider_id)
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
#                             if len(split_data)>0:
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
#                             'countryCode': user_data.country_code if user_data.country_code is not None else '',
#                             'mobile': user_data.mobile_number if user_data.mobile_number is not None else ''
#                         }
#
#                         service_dict = get_service_data.as_dict(active_user.active_language)
#
#                         request_dict = {
#
#                             'id': i.id,
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
#                             'completed_data': completed_data,
#                             'user_data': user_dict,
#                             'service_stage': service_stage,
#                             'review_data': review_data
#
#                         }
#                         request_list.append(request_dict)
#                 message = get_normal_message("msg_11", active_user.active_language)
#
#                 return jsonify({'status': 1,'message': message,'request_list': request_list})
#
#             else:
#                 message = get_normal_message("msg_17", active_user.active_language)
#                 return jsonify({'status': 0,'message': message})
#
#         except Exception as e:
#             print('errorrrrrrrrrrrrrrrrr:', str(e))
#             message = get_normal_message("msg_10", active_user.active_language)
#             return {'status': 0, 'message': message}, 500

class UserOrderListResource(Resource):
    @token_required
    def post(self, active_user):
        try:
            if active_user.role == "Worker":
                message = get_normal_message("msg_16", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            data = request.get_json()

            # page = int(data.get('page', 1))
            tab = data.get('tab',0)
            # per_page = 10

            if tab == 0:

                # has_next = get_request_data.has_next
                # total_pages = get_request_data.pages
                #
                # pagination_info = {
                #     "current_page": page,
                #     "has_next": has_next,
                #     "per_page": per_page,
                #     "total_pages": total_pages,
                # }

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

                        get_accepted_provider = ProviderRequest.query.filter_by(service_request_id=i.id,
                                                                                status="Accepted").first()
                        get_pending_provider = ProviderRequest.query.filter_by(service_request_id=i.id,
                                                                               status="Pending").first()

                        if not get_accepted_provider and not get_pending_provider:
                            message = get_normal_message("msg_112", active_user.active_language)
                            return jsonify({'status': 0, 'message': message})

                        provider_id = None

                        if get_accepted_provider:
                            provider_id = get_accepted_provider.provider_id
                        if get_pending_provider:
                            provider_id = get_pending_provider.provider_id

                        user_data = User.query.get(provider_id)
                        get_service_data = Services.query.get(i.service_id)
                        get_car_data = SavedUserCars.query.get(i.car_id)
                        get_address_data = UserAddress.query.get(i.address_id)
                        get_service_completed_data = ServiceCompletedData.query.filter_by(
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
                            if len(split_data)>0:
                                for j in split_data:
                                    get_extras_data = Extras.query.get(j)
                                    get_extras.append(get_extras_data.as_dict(active_user.active_language))

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
                            'image': generate_presigned_url(user_data.image_name) if user_data.image_name is not None else '',
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
                            'accepted_time': i.accepted_time if i.accepted_time is not None else '',
                            'extras_list': get_extras,
                            'is_review': False,
                            'is_provider_completed': i.is_provider_completed,
                            'is_user_completed': i.is_completed,
                            'completed_data': completed_data,
                            'user_data': user_dict,
                            'service_stage': service_stage,
                            'review_data': {}

                        }
                        request_list.append(request_dict)

                message = get_normal_message("msg_11", active_user.active_language)

                return jsonify({'status': 1,'message': message,'request_list': request_list})

            elif tab == 1:

                request_status = ["Pending", "Accepted","Late"]

                # Completed

                get_request_data = ServiceRequested.query.filter(
                    ServiceRequested.user_id == active_user.id,
                    ~ServiceRequested.status.in_(request_status)
                ).order_by(desc(ServiceRequested.id)).all()

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

                if len(get_request_data)>0:
                    for i in get_request_data:

                        get_cancelled_provider = ProviderRequest.query.filter_by(service_request_id=i.id,
                                                                                status="Cancelled").first()
                        get_completed_provider = ProviderRequest.query.filter_by(service_request_id=i.id,
                                                                               status="Completed").first()

                        if not get_cancelled_provider and not get_completed_provider:
                            message = get_normal_message("msg_112", active_user.active_language)
                            return jsonify({'status': 0, 'message': message})

                        provider_id = None

                        if get_cancelled_provider:
                            provider_id = get_cancelled_provider.provider_id
                        if get_completed_provider:
                            provider_id = get_completed_provider.provider_id

                        user_data = User.query.get(provider_id)
                        get_service_data = Services.query.get(i.service_id)
                        get_car_data = SavedUserCars.query.get(i.car_id)
                        get_address_data = UserAddress.query.get(i.address_id)
                        get_service_completed_data = ServiceCompletedData.query.filter_by(
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
                            if len(split_data)>0:
                                for j in split_data:
                                    get_extras_data = Extras.query.get(j)
                                    get_extras.append(get_extras_data.as_dict(active_user.active_language))

                        status_replace = i.status

                        is_service_accepted = False

                        review_data = {}

                        if i.status == "Completed":
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
                            'accepted_time': i.accepted_time if i.accepted_time is not None else '',
                            'extras_list': get_extras,
                            'is_review': False,
                            'is_provider_completed': i.is_provider_completed,
                            'is_user_completed': i.is_completed,
                            'completed_data': completed_data,
                            'user_data': user_dict,
                            'service_stage': service_stage,
                            'review_data': review_data

                        }
                        request_list.append(request_dict)
                message = get_normal_message("msg_11", active_user.active_language)

                return jsonify({'status': 1,'message': message,'request_list': request_list})

            else:
                message = get_normal_message("msg_17", active_user.active_language)
                return jsonify({'status': 0,'message': message})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrr:', str(e))
            message = get_normal_message("msg_10", active_user.active_language)
            return {'status': 0, 'message': message}, 500

class RequestAcceptRejectResource(Resource):
    @token_required
    def post(self, active_user):
        try:
            if active_user.role == "Customer":
                message = get_normal_message("msg_18", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            data = request.get_json()

            request_id = data.get('request_id')
            request_status = data.get('request_status')

            if not request_id:
                message = get_normal_message("msg_19", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            get_requested_data = ServiceRequested.query.get(request_id)
            if not get_requested_data:
                message = get_normal_message("msg_20", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            if request_status == 1:
                check_late_status = ProviderRequest.query.filter_by(provider_id=active_user.id,service_request_id = get_requested_data.id,status="Late").first()

                if check_late_status:
                    message = get_normal_message("msg_21", active_user.active_language)
                    return jsonify({'status': 0,'message': message})

                excluded = ["Pending", "Cancelled","Late"]

                check_another_request_accepted_for_same_slot = (
                    db.session.query(ServiceRequested.id)
                        .join(ProviderRequest, ProviderRequest.service_request_id == ServiceRequested.id)
                        .filter(
                        ServiceRequested.service_date == get_requested_data.service_date,
                        ServiceRequested.slot_start_time == get_requested_data.slot_start_time,
                        ServiceRequested.slot_end_time == get_requested_data.slot_end_time,
                        # ServiceRequested.is_completed.is_(False),
                        ServiceRequested.id != get_requested_data.id,  # avoid matching the same request
                        ProviderRequest.provider_id == active_user.id,  # check this provider
                        ~ProviderRequest.status.in_(excluded),  # exclude (Pending/Cancelled/Late) on PR
                    )
                        .first()
                )

                # check_another_request_accepted_for_same_slot = ServiceRequested.query.filter(
                #     ServiceRequested.service_date == get_requested_data.service_date,
                #     ServiceRequested.slot_start_time == get_requested_data.slot_start_time,
                #     ServiceRequested.slot_end_time == get_requested_data.slot_end_time,
                #     ServiceRequested.provider_id == active_user.id,
                #     ~ServiceRequested.status.in_(excluded)
                #     ).first()

                if check_another_request_accepted_for_same_slot:
                    message = get_normal_message("msg_111", active_user.active_language)
                    return jsonify({'status': 0,'message': message})

                get_particular_requested_provider = ProviderRequest.query.filter_by(provider_id=active_user.id,service_request_id=get_requested_data.id).first()

                get_requested_data.status = "Accepted"
                get_particular_requested_provider.status = "Accepted"
                get_requested_data.accepted_time = datetime.utcnow()

                get_payment_details = UserPayments.query.filter(UserPayments.payment_id == get_requested_data.payment_id).first()
                if not get_payment_details:
                    message = get_normal_message("msg_22", active_user.active_language)
                    return jsonify({'status': 0,'message': message})

                get_payment_details.provider_id = active_user.id
                get_payment_details.service_request_id = get_requested_data.id

                # check_another_providers = ServiceRequested.query.filter(
                #     ServiceRequested.user_id == get_requested_data.user_id,
                #     ServiceRequested.service_date == get_requested_data.service_date,
                #     ServiceRequested.slot_start_time == get_requested_data.slot_start_time,
                #     ServiceRequested.slot_end_time == get_requested_data.slot_end_time,
                #     ServiceRequested.service_id == get_requested_data.service_id,
                #     ServiceRequested.car_id == get_requested_data.car_id,
                #     ServiceRequested.address_id == get_requested_data.address_id,
                #     ServiceRequested.place_id == get_requested_data.place_id,
                #     ServiceRequested.provider_id != active_user.id
                #
                # ).all()

                check_another_providers = ProviderRequest.query.filter(
                    ProviderRequest.service_request_id == get_requested_data.id,
                    ProviderRequest.provider_id != active_user.id,
                    ProviderRequest.user_id == get_requested_data.user_id,
                    ProviderRequest.status == "Pending"
                ).all()

                if len(check_another_providers)>0:
                    for i in check_another_providers:
                        i.status = "Late"

                db.session.commit()

                get_service_data = Services.query.get(get_requested_data.service_id)
                if not get_service_data:
                    message = get_normal_message("msg_23", active_user.active_language)
                    return jsonify({'status': 0,'message': message})

                reciver_user = User.query.get(get_requested_data.user_id)
                if not reciver_user:
                    message = get_normal_message("msg_24", active_user.active_language)
                    return jsonify({'status': 0,'message': message})

                # title_en = "Your request has been accepted"
                # title_ar = "تم قبول طلبك"
                # title_bn = "আপনার অনুরোধ গ্রহণ করা হয়েছে"
                #
                # msg_en = f"Your request has been accepted for {get_service_data.service_name}"
                # msg_ar = f"تم قبول طلبك لـ {get_service_data.service_name}"
                # msg_bn = f"আপনার অনুরোধ {get_service_data.service_name} এর জন্য গ্রহণ করা হয়েছে"
                #
                # if reciver_user.active_language == 'en':
                #     title = title_en
                #     msg = msg_en
                # elif reciver_user.active_language == 'ar':
                #     title = title_ar
                #     msg = msg_ar
                # else:
                #     title = title_bn
                #     msg = msg_bn


                titles, messages = {}, {}
                for lang in ("en", "ar", "bn"):
                    localized_service = get_localized_service_name(get_service_data, lang)
                    data = get_notification_message("accepted", lang, localized_service)
                    titles[lang], messages[lang] = data["title"], data["msg"]

                add_notification = Notification(service_request_id =get_requested_data.id,title_en=titles["en"],title_ar=titles["ar"],title_bn=titles["bn"], message_en=messages["en"], message_ar=messages["ar"], message_bn=messages["bn"], by_id=active_user.id, to_id=reciver_user.id,
                                                   is_read=False, created_time=datetime.utcnow(),
                                                notification_type='provider accepts request')
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

                message = get_normal_message("msg_25", active_user.active_language)
                return jsonify({'status': 1,'message': message})

            elif request_status == 2:
                check_late_status = ProviderRequest.query.filter_by(provider_id=active_user.id,
                                                                    service_request_id=get_requested_data.id,
                                                                    status="Late").first()

                if check_late_status:
                    message = get_normal_message("msg_26", active_user.active_language)
                    return jsonify({'status': 0,
                                    'message': message})

                check_all_cancelled = ProviderRequest.query.filter(ProviderRequest!="Cancelled",ProviderRequest.service_request_id==get_requested_data.id,ProviderRequest.provider_id!=active_user.id).first()
                provider_request = ProviderRequest.query.filter_by(service_request_id=get_requested_data.id,
                                                                   provider_id=active_user.id).first()

                get_payment_details = UserPayments.query.filter_by(service_request_id=get_requested_data.id,provider_id= active_user.id).first()
                if not get_payment_details:
                    message = get_normal_message("msg_22", active_user.active_language)
                    return jsonify({'status': 0,
                                    'message': message})

                ok, message = process_refund(get_payment_details.total_amount,get_payment_details.transaction_id)

                if ok:

                    if check_all_cancelled:
                        provider_request.status = "Cancelled"

                    else:
                        provider_request.status = "Cancelled"
                        get_requested_data.status = "Cancelled"
                        get_requested_data.cencelled_by = "Worker"
                        get_requested_data.cencelled_time = datetime.utcnow()

                    db.session.commit()

                    if not check_all_cancelled:

                        get_service_data = Services.query.get(get_requested_data.service_id)
                        if not get_service_data:
                            message = get_normal_message("msg_23", active_user.active_language)
                            return jsonify({'status': 0, 'message': message})

                        reciver_user = User.query.get(get_requested_data.user_id)
                        if not reciver_user:
                            message = get_normal_message("msg_24", active_user.active_language)
                            return jsonify({'status': 0, 'message': message})

                        titles, messages = {}, {}
                        for lang in ("en", "ar", "bn"):
                            localized_service = get_localized_service_name(get_service_data, lang)
                            data = get_notification_message("cancelled", lang, localized_service)
                            titles[lang], messages[lang] = data["title"], data["msg"]

                        add_notification = Notification(service_request_id=get_requested_data.id, title_en=titles["en"],
                                                        title_ar=titles["ar"], title_bn=titles["bn"],
                                                        message_en=messages["en"], message_ar=messages["ar"],
                                                        message_bn=messages["bn"], by_id=active_user.id,
                                                        to_id=reciver_user.id,
                                                        is_read=False, created_time=datetime.utcnow(),
                                                        notification_type='provider cancelled request')
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

                    message = get_normal_message("msg_27", active_user.active_language)
                    return jsonify({'status': 1, 'message': message})

                else:
                    return {
                    "status": 0,
                    "message": "Refund Failed"
                }

            else:
                message = get_normal_message("msg_17", active_user.active_language)
                return jsonify({'status': 0,'message': message})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrr:', str(e))
            message = get_normal_message("msg_10", active_user.active_language)
            return {'status': 0, 'message': message}, 500

class StartServiceResource(Resource):
    @token_required
    def post(self, active_user):
        try:
            if active_user.role == "Customer":
                message = get_normal_message("msg_18", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            before_image_one = request.files.get('before_image_one')
            before_image_two = request.files.get('before_image_two')
            request_id = request.form.get('request_id')

            if not before_image_one:
                message = get_normal_message("msg_28", active_user.active_language)
                return jsonify({'status': 0,'message': message})
            if not before_image_two:
                message = get_normal_message("msg_29", active_user.active_language)
                return jsonify({'status': 0,'message': message})
            if not request_id:
                message = get_normal_message("msg_19", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            # get_request = ServiceRequested.query.filter_by(provider_id=active_user.id,id=request_id).first()

            get_request = (
                db.session.query(ServiceRequested)
                    .join(ProviderRequest, ProviderRequest.service_request_id == ServiceRequested.id)
                    .filter(
                    ServiceRequested.id == request_id,
                    ProviderRequest.provider_id == active_user.id,
                    ProviderRequest.status=="Accepted"
                )
                    .first()
            )

            if not get_request:
                message = get_normal_message("msg_20", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            if not get_request.status == 'Accepted':
                message = get_normal_message("msg_30", active_user.active_language)
                return jsonify({'status': 0,'message': message})

            get_request.start_service_time = datetime.utcnow()
            get_request.is_service_start = True

            file_path_before_one, picture_before_one = upload_photos(before_image_one)
            file_path_before_two, picture_before_two = upload_photos(before_image_two)

            add_completed = ServiceCompletedData(before_image_name_1=picture_before_one
                                                 , before_image_path_1=file_path_before_one
                                                 , before_image_name_2=picture_before_two
                                                 , before_image_path_2=file_path_before_two

                                                 , created_time=datetime.utcnow()
                                                 , provider_id=active_user.id
                                                 , user_id=get_request.user_id
                                                 , service_request_id=get_request.id)

            db.session.add(add_completed)

            db.session.commit()

            message = get_normal_message("msg_31", active_user.active_language)

            return jsonify({'status': 1,'message': message})

        except Exception as e:
            print('errorrrrrrrrrrrrrrrrr:', str(e))
            message = get_normal_message("msg_10", active_user.active_language)
            return {'status': 0, 'message': message}, 500