import firebase_admin,jwt
from firebase_admin import credentials, messaging
import secrets, boto3
from werkzeug.utils import secure_filename
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import url_for,jsonify,request
from base.apis.v1.admin.models import Admin
from functools import wraps
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime, timedelta
from base.apis.v1.admin.models import Store
from shapely.geometry import shape, Point
import json
# env_path = Path('/var/www/html/backend/base/.env')
# load_dotenv(dotenv_path=env_path)

load_dotenv()

REGION_NAME = os.getenv("REGION_NAME")
ACCESS_KEY = os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")

s3_client = boto3.client('s3', aws_access_key_id=ACCESS_KEY,
                         aws_secret_access_key=SECRET_KEY ,region_name=REGION_NAME,endpoint_url=f"https://s3.{REGION_NAME}.amazonaws.com")

USER_FOLDER = 'base/static/user_photos/'

def find_zone_for_latlng(zones, lat, lng, accept_border=True):
    """Return the first zone whose polygon contains the point."""
    pt = Point(float(lng), float(lat))  # Shapely: x=lng, y=lat

    for z in zones:
        try:
            if not z.polygon_geojson:
                continue

            # ✅ Convert DB text → JSON object
            gj = json.loads(z.polygon_geojson)

            poly = shape(gj)

            # ✅ Check inside or on boundary
            if poly.contains(pt) or (accept_border and poly.touches(pt)):
                return z

        except Exception as e:
            print("Polygon decode/shape error:", e)
            continue

    return None

def find_assign_zone_for_latlng(polygon_geojson, lat, lng, accept_border=True):
    """Return the first zone whose polygon contains the point."""
    pt = Point(float(lng), float(lat))  # Shapely: x=lng, y=lat

    try:
        if not polygon_geojson:
            return None

        # ✅ Convert DB text → JSON object
        gj = json.loads(polygon_geojson)

        poly = shape(gj)

        # ✅ Check inside or on boundary
        if poly.contains(pt) or (accept_border and poly.touches(pt)):
            return polygon_geojson

    except Exception as e:
        print("Polygon decode/shape error:", e)

    return None

FMT = "%H:%M"   # 24h like '05:00'

def get_hourly_slots(day_name: str):
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

cred = credentials.Certificate('base/vloo_key.json')
firebase_admin.initialize_app(cred)

def push_notification(token=None, title=None, body=None,data=None):
    try:
        sound = "default"

        data_payload = data if data is not None else {}

        print('data_payload',data_payload)

        if title is None:
            sound = None

        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,

            ),

            android=messaging.AndroidConfig(
                notification=messaging.AndroidNotification(
                    sound=sound
                ),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound=sound
                    )
                )
            ),

            token=token,
            data=data_payload

        )

        # Send the message
        response = messaging.send(message)
        #message.data['type'] = notification_type

        # Log the response
        print(f'Successfully sent message: {response}')

    except Exception as e:
        print('Error sending message:', e)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in {
        "jpg",
        "jpeg",
        "png",
        "gif",
        "bmp",
        "tiff",
        "tif",
        "webp",
        "svg",
        "psd",
        "raw",
        "crw",
        "cr2",
        "cr3",
        "nef",
        "arw",
        "orf",
        "raf",
        "dng",
        "pef",
        "srf",
        "sr2",
        "rw2",
    }


def upload_photos(file):
    try:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            extension = os.path.splitext(filename)[1]
            extension2 = os.path.splitext(filename)[1][1:].lower()
            content_type = f'image/{extension2}'
            x = secrets.token_hex(10)
            picture = x + extension
            file.seek(0)
            s3_client.upload_fileobj(file, S3_BUCKET, picture,
                                     ExtraArgs={'ContentType': content_type})
            file_path = f"https://{S3_BUCKET}.s3.{REGION_NAME}.amazonaws.com/{picture}"

            return file_path, picture

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'message': 'Something went wrong'}, 500

def upload_photos_local(file):
    try:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            extension = os.path.splitext(filename)[1]

            x = secrets.token_hex(10)
            picture = x + extension

            image_path = os.path.join(USER_FOLDER)
            file.save(os.path.join(image_path, picture))
            file_path = image_path.replace("base", "")

            return file_path, picture

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'message': 'Something went wrong'}, 500

def delete_photos_local(file):
    try:
        os.remove(os.path.join(USER_FOLDER, file))
    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'message': 'Something went wrong'}, 500

def delete_photos(file):
    try:
        s3_client.delete_object(Bucket=S3_BUCKET, Key=file)
    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'message': 'Something went wrong'}, 500

def user_send_reset_email(user,type):
    token = ''
    url = '#'

    if type == 'user':
        token = user.get_user_token()
        url = url_for('reset_password', token=token, _external=True)
    elif type == 'admin':
        token = user.get_admin_token()
        url = url_for('admin_reset_password', token=token, _external=True)
    else:
        return {'status': 0,'message': 'Invalid type'}

    print('Composing Email.......')

    SERVER = 'smtp.gmail.com'  # smtp server
    PORT = 587  # mail port number
    FROM = 'fearsfight211@gmail.com'  # sender Mail
    TO = user.email  # receiver mail
    PASS = 'mdltifkjmclajper'
    MAIL_FROM_NAME = "Beacon Clubb"

    msg = MIMEMultipart()
    content = '''
<!DOCTYPE html>
<html>

<head>
    <title>Password Reset</title>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="X-UA-Compatible" content="IE=edge" />
    <style type="text/css">
        body, table, td, a {
            -webkit-text-size-adjust: 100%;
            -ms-text-size-adjust: 100%;
        }
        table, td {
            mso-table-lspace: 0pt;
            mso-table-rspace: 0pt;
        }
        img {
            -ms-interpolation-mode: bicubic;
            border: 0;
            height: auto;
            line-height: 100%;
            outline: none;
            text-decoration: none;
        }
        table {
            border-collapse: collapse !important;
        }
        body {
            margin: 0 !important;
            padding: 0 !important;
            width: 100% !important;
            background-color: #f4f4f4;
        }
        a[x-apple-data-detectors] {
            color: inherit !important;
            text-decoration: none !important;
            font-size: inherit !important;
            font-family: inherit !important;
            font-weight: inherit !important;
            line-height: inherit !important;
        }

        .reset-button {
            font-size: 18px;
            font-family: Helvetica, Arial, sans-serif;
            color: #fff !important;
            text-decoration: none;
            padding: 12px 22px;
            border-radius: 5px;
            display: inline-block;
            background: linear-gradient(94.86deg, #FFCF03 1.22%, #FD343D 94.76%);
        }

        @media only screen and (max-width: 768px) {
            .container {
                padding: 20px;
            }
            .logo {
                width: 50%;
                margin: 0 auto;
                display: block;
            }
            .reset-button {
                width: 100% !important;
                font-size: 1rem !important;
                padding: 14px !important;
                box-sizing: border-box;
                display: block;
                text-align: center;
            }
        }
    </style>
</head>

<body>
    <table border="0" cellpadding="0" cellspacing="0" width="100%">
        <tr>
            <td style="background:#FD343D" align="center">
                <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 560px;">
                    <tr>
                        <td align="center" valign="top" style="padding: 30px 10px;"></td>
                    </tr>
                </table>
            </td>
        </tr>
        <tr>
            <td align="center" style="background:#FD343D">
                <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 560px;">
                    <tr>
                        <td bgcolor="#ffffff" align="center" style="padding: 25px 20px; border-radius: 4px 4px 0 0;">
                            <img src="http://3.19.145.138/static/user_photos/app_logo.png" width="150px" height="150px" class="logo"/>
                            <h1 style="font-size: 28px; font-weight: 300; margin: 10px 0; color: #111;">Trouble signing in?</h1>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
        <tr>
            <td bgcolor="#f4f4f4" align="center">
                <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 560px;">
                    <tr>
                        <td bgcolor="#ffffff" align="left" style="padding: 15px 25px; color: #666; font-size: 16px; line-height: 24px;">
                            <p>Resetting your password is easy. Just press the button below and follow the instructions. We'll have you up and running in no time.</p>
                        </td>
                    </tr>
                    <tr>
                        <td bgcolor="#ffffff" align="center" style="padding: 20px 25px;">
                            <a href="''' + url + '''" class="reset-button">Reset Password</a>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>

</html>


 '''

    msg['Subject'] = 'Reset Password - Beacon Clubb'
    msg['From'] = f'{MAIL_FROM_NAME} <{FROM}>'
    msg['To'] = TO

    msg.attach(MIMEText(content, 'html'))

    print('Initiating server ...')

    server = smtplib.SMTP(SERVER, PORT)
    server.set_debuglevel(1)
    server.ehlo()
    server.starttls()
    server.login(FROM, PASS)
    server.sendmail(FROM, TO, msg.as_string())
    print('Email Sent...')
    server.quit()

def admin_login_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        token = None

        if "authorization" in request.headers:
            token = request.headers["authorization"]
            print('token',token)

        if not token:
            return {"status": 0, "message": "a valid token is missing"}
        try:
            data = jwt.decode(token, os.getenv("ADMIN_SECRET_KEY"), algorithms=["HS256"])
            active_user = Admin.query.filter_by(id=data["id"]).first()
        except jwt.ExpiredSignatureError:
            return {"status": 0, "message": "Token has expired"},401
        except jwt.InvalidTokenError:
            return {"status": 0, "message": "Invalid token"},401
        except Exception as e:
            return {"status": 0, "message": f"An error occurred: {str(e)}"}

        kwargs['active_user'] = active_user

        return f( *args, **kwargs)

    return decorator

# def send_admin_reset_email(admin):
#     token = admin.get_admin_token()
#
#     print('Composing Email.......')
#
#     SERVER = 'mail.app.fight-fears.com'
#     PORT = 465  # SSL port for SMTP
#     FROM = 'no-reply@app.fight-fears.com'
#     TO = admin.email
#     PASS = 'FightFears.App.@@2024'
#
#     msg = MIMEMultipart()
#     content = '''
# <!DOCTYPE html>
# <html>
#
# <head>
#     <title>Reset Password</title>
#     <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
#     <meta name="viewport" content="width=device-width, initial-scale=1">
#     <meta http-equiv="X-UA-Compatible" content="IE=edge" />
#     <style type="text/css">
#         @media screen {
#             @font-face {
#                 font-family: 'Lato';
#                 font-style: normal;
#                 font-weight: 400;
#                 src: local('Lato Regular'), local('Lato-Regular'), url(https://fonts.gstatic.com/s/lato/v11/qIIYRU-oROkIk8vfvxw6QvesZW2xOQ-xsNqO47m55DA.woff) format('woff');
#             }
#
#             @font-face {
#                 font-family: 'Lato';
#                 font-style: normal;
#                 font-weight: 700;
#                 src: local('Lato Bold'), local('Lato-Bold'), url(https://fonts.gstatic.com/s/lato/v11/qdgUG4U09HnJwhYI-uK18wLUuEpTyoUstqEm5AMlJo4.woff) format('woff');
#             }
#
#             @font-face {
#                 font-family: 'Lato';
#                 font-style: italic;
#                 font-weight: 400;
#                 src: local('Lato Italic'), local('Lato-Italic'), url(https://fonts.gstatic.com/s/lato/v11/RYyZNoeFgb0l7W3Vu1aSWOvvDin1pK8aKteLpeZ5c0A.woff) format('woff');
#             }
#
#             @font-face {
#                 font-family: 'Lato';
#                 font-style: italic;
#                 font-weight: 700;
#                 src: local('Lato Bold Italic'), local('Lato-BoldItalic'), url(https://fonts.gstatic.com/s/lato/v11/HkF_qI1x_noxlxhrhMQYELO3LdcAZYWl9Si6vvxL-qU.woff) format('woff');
#             }
#         }
#
#         /* CLIENT-SPECIFIC STYLES */
#         body,
#         table,
#         td,
#         a {
#             -webkit-text-size-adjust: 100%;
#             -ms-text-size-adjust: 100%;
#         }
#
#         table,
#         td {
#             mso-table-lspace: 0pt;
#             mso-table-rspace: 0pt;
#         }
#
#         img {
#             -ms-interpolation-mode: bicubic;
#         }
#
#         /* RESET STYLES */
#         img {
#             border: 0;
#             height: auto;
#             line-height: 100%;
#             outline: none;
#             text-decoration: none;
#         }
#
#         table {
#             border-collapse: collapse !important;
#         }
#
#         body {
#             height: 100% !important;
#             margin: 0 !important;
#             padding: 0 !important;
#             width: 100% !important;
#             background-color: black;
#         }
#
#         a[x-apple-data-detectors] {
#             color: inherit !important;
#             text-decoration: none !important;
#             font-size: inherit !important;
#             font-family: inherit !important;
#             font-weight: inherit !important;
#             line-height: inherit !important;
#         }
#
#         /* Responsive Styles */
#         @media screen and (max-width: 600px) {
#             h1 {
#                 font-size: 32px !important;
#                 line-height: 32px !important;
#             }
#         }
#
#         /* Custom Styles */
#         h1,
#         p {
#             color: #ffffff;
#             font-family: 'Lato', Helvetica, Arial, sans-serif;
#         }
#
#         h1 {
#             font-size: 28px;
#             font-weight: 300;
#             margin: 25px 0 0;
#         }
#
#         p {
#             font-size: 18px;
#             font-weight: 400;
#             line-height: 25px;
#             margin: 0;
#         }
#
#         .email-container {
#             background-color: black;
#             border-radius: 10px;
#             box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.15);
#             max-width: 600px;
#             margin: 0 auto;
#             padding: 50px 30px;
#             margin-top: 75px;
#         }
#
#         .header {
#             background-color: black;
#             padding: 20px;
#             border-radius: 4px 4px 0 0;
#             text-align: center;
#         }
#
#         .button {
#             display: inline-block;
#             padding: 15px 25px;
#             font-size: 20px;
#             color: white !important;
#             background-color: #646d77;
#             text-decoration: none;
#             border-radius: 6px;
#             font-family: 'Lato', Helvetica, Arial, sans-serif;
#             font-weight: bold;
#             box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.1);
#         }
#
#         .footer {
#             padding: 20px 0;
#             text-align: center;
#             font-size: 14px;
#             color: #aaaaaa;
#         }
#     </style>
# </head>
#
# <body>
#     <table border="0" cellpadding="0" cellspacing="0" width="100%">
#         <!-- HIDDEN PREHEADER TEXT -->
#         <div style="display: none; font-size: 1px; color: #fefefe; line-height: 1px; font-family: 'Lato', Helvetica, Arial, sans-serif; max-height: 0px; max-width: 0px; opacity: 0; overflow: hidden;">
#             We're thrilled to have you here! Get ready to dive into your new account.
#         </div>
#         <!-- LOGO -->
#         <tr>
#             <td align="center">
#                 <div class="email-container">
#                     <div class="header">
#                         <img src="https://first-face.s3.amazonaws.com/89e884021a321b83698b.png" width="240" height="150" style=" border: 0; margin-inline: auto " alt="Logo">
#
#                     </div>
#                     <h1>Trouble signing in?</h1>
#                     <div style="padding: 20px 30px;">
#                         <p>Resetting your password is easy. Just press the button below and follow the instructions. We'll have you up and running in no time.</p>
#                     </div>
#                     <div style="text-align: center; padding: 20px 0;">
#                         <a href="''' + url_for('admin_reset_password', token=token, _external=True) + '''" class="button">Reset Password</a>
#                     </div>
#                 </div>
#             </td>
#         </tr>
#         <tr>
#             <td align="center">
#                 <div class="footer">
#                     © 2024 FirstFace. All rights reserved.
#                 </div>
#             </td>
#         </tr>
#     </table>
# </body>
#
# </html>
#
#
#
#  '''
#
#     msg['Subject'] = 'Reset Password - First Face'
#     msg['From'] = FROM
#     msg['To'] = TO
#
#     msg.attach(MIMEText(content, 'html'))
#
#     print('Initiating server ...')
#
#     try:
#         server = smtplib.SMTP_SSL(SERVER, PORT)
#         server.set_debuglevel(1)
#         server.login(FROM, PASS)
#         server.sendmail(FROM, TO, msg.as_string())
#         print('Email Sent...')
#     except smtplib.SMTPServerDisconnected as e:
#         print(f"Server disconnected unexpectedly: {e}")
#
#     # server = smtplib.SMTP(SERVER, PORT)
#     # server.set_debuglevel(1)
#     # server.ehlo()
#     # server.starttls()
#     # server.login(FROM, PASS)
#     # server.sendmail(FROM, TO, msg.as_string())
#     print('Email Sent...')
#     server.quit()

def send_otp(user, otp):
    otp_value = str(otp)

    print('Composing Email.......')

    SERVER = 'smtp.gmail.com'  # smtp server
    PORT = 587  # mail port number
    FROM = 'fearsfight211@gmail.com'  # sender Mail
    TO = user.email  # receiver mail
    PASS = 'mdltifkjmclajper'
    MAIL_FROM_NAME = "Vloo"

    msg = MIMEMultipart()
    content = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify Your Sign-Up</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f26d6114;
            margin: 0;
            padding: 0;
        }
        .container {
            max-width: 400px;
            margin: 40px auto;
            background: #5bd0d712;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            text-align: center;
        }
        .header {
            background-color: #5BD0D7;
            padding: 30px;
            border-top-left-radius: 10px;
            border-top-right-radius: 10px;
            display: flex;
            justify-content: center;
            align-items: center;
            
        }
        .logo {
    background: white;
    border-radius: 50%;
    padding: 10px;
    width: 80px;
    height: 80px;
    margin: auto;  /* Ensures centering */
}
        .title {
            font-size: 22px;
            font-weight: bold;
            color: #333333;
            margin: 20px 0 10px;
        }
        .message {
            font-size: 16px;
            color: #666666;
            margin-bottom: 20px;
        }
        .otp-box {
            background: #E5E7EB;
            padding: 15px;
            font-size: 24px;
            font-weight: bold;
            letter-spacing: 3px;
            border-radius: 5px;
            display: inline-block;
            color: #333333;
            margin-bottom: 20px;
        }
        .footer {
            font-size: 14px;
            color: #999999;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <img src="https://frienddate-app.s3.amazonaws.com/conprofile.png" alt="Logo" class="logo">
        </div>
        <div class="title">Verify Your Sign-Up</div>
        <div class="message">
            Enter the OTP below to verify your email and complete the sign-up process.
        </div>
        <div class="otp-box">'''+ otp_value +'''</div>
        <div class="footer">©2025 Vloo. All rights reserved.</div>
    </div>
</body>
</html>

 '''

    msg['Subject'] = 'OTP Verification - Vloo'
    msg['From'] = f'{MAIL_FROM_NAME} <{FROM}>'
    msg['To'] = TO

    msg.attach(MIMEText(content, 'html'))

    print('Initiating server ...')

    server = smtplib.SMTP(SERVER, PORT)
    server.set_debuglevel(1)
    server.ehlo()
    server.starttls()
    server.login(FROM, PASS)
    server.sendmail(FROM, TO, msg.as_string().encode('utf-8'))
    print('Email Sent...')
    server.quit()

def send_provider_cred(user,password,user_type):
    try:
        print('Composing Email.......')

        SERVER = 'smtp.gmail.com'  # smtp server
        PORT = 587  # mail port number
        FROM = 'fearsfight211@gmail.com'  # sender Mail
        TO = user.email  # receiver mail
        PASS = 'mdltifkjmclajper'
        MAIL_FROM_NAME = "Vloo"

        msg = MIMEMultipart()

        if user_type == 'Admin':
            name = user.firstname
        else:
            name = user.name

        image_url = "http://192.168.1.15:3031/static/images/app_logo.png"

        mobile_number = user.country_code + user.mobile_number

        content = '''
    <!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Your Login Credentials</title>
</head>
<body style="margin: 0; padding: 0; background-color: #81D8D0; font-family: 'Segoe UI', sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#f4f4f4">
    <tr>
      <td align="center" style="padding: 40px 20px;">
        <table width="600" cellpadding="0" cellspacing="0" border="0" style="background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">

          <!-- Header -->
          <tr>
            <td style="background:#004d61;" align="center">
              <table border="0" cellpadding="0" cellspacing="0" width="100%">
                <tr>
                  <td bgcolor="#004d61" align="center" style="padding: 20px;">
                    <img src='''+ image_url +''' height="auto" width="35%" style="display: block; border: 0;" />
                    <h1 style="font-size: 28px; font-weight: 400; margin: 16px 0 0; color: #ffffff;">
                      Welcome to Our Platform!
                    </h1>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding: 15px 15px; text-align: center;">
              <p style="font-size: 18px; color: #333333; margin-bottom: 24px;">
                Hi ''' + name + ''',
              </p>
              <p style="font-size: 16px; color: #555555; line-height: 1.6; margin-bottom: 20px;">
                Here are your login credentials. Use these to sign in to your account:
              </p>

              <table style="margin: 0 auto 30px; font-size: 16px; color: #444;">
                <tr>
                  <td style="padding: 8px 12px; font-weight: bold;">Mobile Number:</td>
                  <td style="padding: 8px 12px;">''' + mobile_number + '''</td>
                </tr>
                <tr>
                  <td style="padding: 8px 12px; font-weight: bold;">Password:</td>
                  <td style="padding: 8px 12px;">''' + password + '''</td>
                </tr>
              </table>

              <p style="font-size: 14px; color: #888888;">
                For security, please change your password after logging in.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding: 15px; background-color: #fafafa; text-align: center; color: #999999; font-size: 12px;">
              Need help? Contact our support team anytime.
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>



     '''

        msg['Subject'] = 'Account Credentials'
        # msg['From'] = FROM
        msg['From'] = f'{MAIL_FROM_NAME} <{FROM}>'
        msg['To'] = TO

        msg.attach(MIMEText(content, 'html'))

        print('Initiating server ...')

        server = smtplib.SMTP(SERVER, PORT)
        server.set_debuglevel(1)
        server.ehlo()
        server.starttls()
        server.login(FROM, PASS)
        server.sendmail(FROM, TO, msg.as_string())
        print('Email Sent...')
        server.quit()

    except Exception as e:
        print('errorrrrrrrrrrrrrrrrr:', str(e))
        return {'status': 0, 'message': 'Something went wrong'}, 500