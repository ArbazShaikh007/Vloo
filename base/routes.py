from flask_restful import Api

from base.apis.v1.admin.auth import UpdatePasswordResource,VerifyOTPResource,AdminRegisterResource,GetAdminResource,AdminLoginResource,AdminEditProfileResource,AdminForgetPassword,AdminChangePasswordResource
from base.apis.v1.admin.view import UserListNoPaginationResource,SubAdminZoneListingResource,AddMainProviderResource,MainProviderListResource,SubZoneListingResource,SubZoneResource,PopularBrandResource,BrodCastMessagesResource,ProviderMonthlyReportResource,DisableBeforeTimeResource,AdminAcceptServiceRequestsResource,PendingServiceRequestsResource,AdminReplyContactUsResource,AdminContactUsListingResource,AdminPrivacyResource,AdminAboutUsResource,StaticFileUploadResource,AdminFaqResource,AssignProviderListResource,AdminMetadataResource,AdminExtrasListingResource,CarBrandsResource,CarModelsResource,AdminExtrasResource,CarsBrandListingNoPaginationResource,ProviderListResource,UserListResource,ServicesListResource,StoreResource,CarsModelListingResource,CarsBrandListingResource,ZoneListingResource,AssignProviderResource,ZoneResource,ServicesResource,GetProviderResource,CarsResource,BannerResource,BannerListResource,BannerStatusResource,DashboardResource,AddProviderResource

from base.apis.v1.user.auth import UserLoginResource,GetUserResource,UpdateUserResource
from base.apis.v1.user.view import SendStaticNotificationResource,ChangeLanguageResource,NotificationListResource,UserConatactUsChatResource,ProviderCompleteServiceResource,ProviderReviewListResource,ServiceReviewListResource,UserServiceReviewResource,UserCompleteServiceResource,ProviderOnlineOfflineResource,ProviderHomepageResource,UserConatactUsResource,GetUserServiceListResource,GetUserExtrasResource,UserBookingRequestResource,GetUserSlotsResource,GetUserFaqsResource,GetUserPrivacyPoliciesResource,UserAddCarsResource,UserMetadataResource,GetProviderSlotsResource,HomepageResource,CustomerAddressResource,UserCarsBrandListingResource,UserCarsModelListingResource
from base.apis.v1.user.orders import StartServiceResource,MyEarningResource,UserOrderListResource,RequestAcceptRejectResource
from base.apis.v1.user.payments import CapturePaymentResource,MakePaymentHoldResource,PaymentSuccessUrl,PaymentFailedUrl,GetPaymentDetailsUrl

api = Api()
api.add_resource(SendStaticNotificationResource, "/send_static_notification")
admin_base = '/admin/'

api.add_resource(StaticFileUploadResource, "/static_upload_s3")

#Admin Auth
api.add_resource(AdminRegisterResource, admin_base+"register")
api.add_resource(AdminLoginResource, admin_base+"login")
api.add_resource(GetAdminResource, admin_base+"get_profile")
api.add_resource(AdminChangePasswordResource, admin_base+"change_password")
api.add_resource(AdminEditProfileResource, admin_base+"update_profile")
api.add_resource(AdminForgetPassword,admin_base+"forget_password")
api.add_resource(VerifyOTPResource,admin_base+"verify_otp")
api.add_resource(UpdatePasswordResource,admin_base+"update_password")

admin_view = '/admin_view/'

# Admin view

api.add_resource(PopularBrandResource, admin_view+"popular_car_brand")
api.add_resource(BrodCastMessagesResource, admin_view+"broadcast_message")
api.add_resource(ProviderMonthlyReportResource, admin_view+"provider_monthly_report")
api.add_resource(DisableBeforeTimeResource, admin_view+"update_disable_time")
api.add_resource(AdminAcceptServiceRequestsResource, admin_view+"admin_accept_service_request")
api.add_resource(PendingServiceRequestsResource, admin_view+"pending_request_list")
api.add_resource(AdminReplyContactUsResource, admin_view+"contact_us_reply")
api.add_resource(AdminContactUsListingResource, admin_view+"admin_contact_us_list")
api.add_resource(AdminAboutUsResource, admin_view+"update_about_us")
api.add_resource(AdminPrivacyResource, admin_view+"update_privacy")
api.add_resource(AdminFaqResource, admin_view+"add_faqs")

api.add_resource(AdminMetadataResource, admin_view+"admin_metadata")
api.add_resource(AdminExtrasListingResource, admin_view+"extras_listing")

api.add_resource(CarBrandsResource, admin_view+"add_car_brand")
api.add_resource(CarModelsResource, admin_view+"add_car_model")

api.add_resource(DashboardResource, admin_view+"dashboard")

api.add_resource(AddMainProviderResource, admin_view+"add_main_provider")

api.add_resource(AddProviderResource, admin_view+"add_provider")
api.add_resource(GetProviderResource, admin_view+"get_provider")

api.add_resource(CarsResource, admin_view+"add_car")
api.add_resource(CarsBrandListingResource, admin_view+"car_brand_list")
api.add_resource(CarsBrandListingNoPaginationResource, admin_view+"car_brand_list_no_pagination")
api.add_resource(CarsModelListingResource, admin_view+"car_models_list")

api.add_resource(BannerResource, admin_view+"add_banner")
api.add_resource(BannerListResource, admin_view+"banner_list")
api.add_resource(BannerStatusResource, admin_view+"banner_status_change")

api.add_resource(ServicesResource, admin_view+"add_service")

api.add_resource(ZoneResource, admin_view+"add_zone")
api.add_resource(ZoneListingResource, admin_view+"zone_list")
api.add_resource(SubAdminZoneListingResource, admin_view+"subadmin_zone_list")

api.add_resource(SubZoneResource, admin_view+"add_sub_zone")
api.add_resource(SubZoneListingResource, admin_view+"sub_zone_list")

api.add_resource(AssignProviderListResource, admin_view+"assigned_provider_list")
api.add_resource(AssignProviderResource, admin_view+"assign_service")

api.add_resource(StoreResource, admin_view+"update_store_data")
api.add_resource(ServicesListResource, admin_view+"service_list")

api.add_resource(UserListResource, admin_view+"user_list")
api.add_resource(UserListNoPaginationResource, admin_view+"user_no_pagination_list")

api.add_resource(MainProviderListResource, admin_view+"main_provider_list")
api.add_resource(ProviderListResource, admin_view+"provider_list")

api.add_resource(AdminExtrasResource, admin_view+"add_extras")


user_base = '/user/'

api.add_resource(UserLoginResource,user_base+ "login" )
api.add_resource(GetUserResource,user_base+ "get_user" )
api.add_resource(UpdateUserResource,user_base+ "update_user" )

user_base = '/user_view/'

api.add_resource(ChangeLanguageResource,user_base+ "change_language")

api.add_resource(ProviderCompleteServiceResource,user_base+ "provider_complete_service")
api.add_resource(ProviderReviewListResource,user_base+ "provider_review_list")
api.add_resource(ServiceReviewListResource,user_base+ "service_review_list")
api.add_resource(UserServiceReviewResource,user_base+ "user_service_review")
api.add_resource(UserCompleteServiceResource,user_base+ "user_complete_service")

api.add_resource(ProviderOnlineOfflineResource,user_base+ "change_active_status")
api.add_resource(GetUserFaqsResource,user_base+ "get_faqs")
api.add_resource(GetUserPrivacyPoliciesResource,user_base+ "privacy_policy")

api.add_resource(HomepageResource,user_base+ "homepage")
api.add_resource(ProviderHomepageResource,user_base+ "provider_homepage")

api.add_resource(CustomerAddressResource,user_base+ "add_address")
api.add_resource(GetProviderSlotsResource,user_base+ "get_provider_slots")
api.add_resource(UserCarsBrandListingResource,user_base+ "car_brand_list")
api.add_resource(UserCarsModelListingResource,user_base+ "car_models_list")
api.add_resource(UserAddCarsResource,user_base+ "user_add_car")
api.add_resource(GetUserSlotsResource,user_base+ "available_slots")

api.add_resource(UserBookingRequestResource,user_base+ "user_booking_request")
api.add_resource(RequestAcceptRejectResource,user_base+ "request_action")

api.add_resource(GetUserExtrasResource,user_base+ "user_extras_list")
api.add_resource(GetUserServiceListResource,user_base+ "user_service_list")

api.add_resource(UserMetadataResource,user_base+ "metadata")

api.add_resource(UserConatactUsResource,user_base+ "user_contact_us")
api.add_resource(UserConatactUsChatResource,user_base+ "admin_chat_list")

api.add_resource(UserOrderListResource,user_base+ "user_order_list")

api.add_resource(MakePaymentHoldResource,user_base+ "payment_initiat")
api.add_resource(CapturePaymentResource,user_base+ "payment_complete")
api.add_resource(GetPaymentDetailsUrl,user_base+ "payment_details")
api.add_resource(PaymentSuccessUrl,"/payment_success")
api.add_resource(PaymentFailedUrl,"/payment_failed")

api.add_resource(MyEarningResource,user_base+ "my_earnings")
api.add_resource(NotificationListResource,user_base+ "notification_list")

api.add_resource(StartServiceResource,user_base+ "provider_start_service")
