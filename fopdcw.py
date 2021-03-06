from datetime import datetime, timedelta, time
from functools import wraps
from io import BytesIO, StringIO
import json
from os import path 
from sys import exc_info
import threading
from zipfile import ZipFile, ZIP_STORED, ZIP_DEFLATED
from threading import Lock

from flask import flash, Flask, render_template, request, Response, send_file, send_from_directory,\
                  session, make_response
from flask_cors import CORS
from flask_socketio import Namespace, SocketIO, send, emit
import requests
import psycopg2

from DbConnection import DbConnection
from data import get_device_data, get_device_data_json
from django_authenticator import check_password 
from generate_chart import generate_chart
from jose_fop import make_image_request_jwt
from logger import get_top_level_logger
from nacl_fop import decrypt, decrypt_dict_vals, generate_reset_code
from python.boto3_fop import S3Session
from python.image import get_image_file_v2, get_newest_image_uuid, get_s3_file_names
from python.permissions import has_permission, get_user_groups
from python.twilio_fop import send_text
from python.mqtt import mqtt_connect 

from config.config import dbconfig, flask_app_secret_key_b64_cipher, fop_url_for_get_image

##############
# TODO: Build in a Web Socket interface for realtime control of fopd devices.
#       See: https://hacks.mozilla.org/2019/10/firefoxs-new-websocket-inspector/
##############

class FopwFlask(Flask):

    jinja_options = Flask.jinja_options.copy()

    # change the server side Jinja template code markers so that we can use Vue.js on the client.
    # Vue.js uses {{ }} as code markers so we don't want Jinja to interpret them.
    jinja_options.update(dict(
        block_start_string = '(%',
        block_end_string = '%)',
        variable_start_string = '((',
        variable_end_string = '))',
        comment_start_string = '(#',
        comment_end_string = '#)',
))

app = FopwFlask(__name__)

# TODO - Consider generating a new secret key everytime Flask is restarted. Flask
#        stores session data in the client on an enrypted cookie.  If you set a
#        new secret key everytime Flask is restarted then pre-restart sessions
#        become invalid after the restart.
#
app.secret_key = decrypt(flask_app_secret_key_b64_cipher)

# Inject Flask app into the socketio object. 
socketio = SocketIO(app)

# This function has the side effect of injecting the fopdcw log handler into the 
# flask.app logger.
logger = get_top_level_logger()

from logging import getLogger, DEBUG, INFO
from logger import get_the_fopdcw_log_handler

getLogger('flask_cors').level =  INFO
getLogger('flask_cors').addHandler(get_the_fopdcw_log_handler())

#TODO: move this stuff to the configuration file
# this works for development, i.e serving the web client from my laptop: cors = 
#      CORS(app, supports_credentials = True, origins =['http://localhost:8080', 'http://localhost'])
cors = CORS(app, supports_credentials = True, origins =['http:192.168.4.247', 'http://localhost:8080', 'http://localhost', 'http://fop3.urbanspacefarms.com:5000'])

# Decorate URL route functions with this function in order to restrict access
# to logged on users.
def enforce_login(func):

    @wraps(func)

    def wrapper(*args, **kwargs):
        
        if 'user' in session and session['user'] != None:
            return func(*args, **kwargs)		
        else:
            logger.warning('Unauthorized URL access attempt. Route function name: {}'.format(func.__name__))
            r = Response('{"auth_failure": true}')
            #TODO Need to make this a installation variable so that you can turn it off on production.
            r.headers['Access-Control-Allow-Origin'] = '*'
            return r

    return wrapper

#TODO: Create a folder for database objects and put this function in it. Put the folder in the Python folder.
class Person():

    def __init__(self, user_name):

        self.nick_name = None 
        self.guid = None 
        self.django_username = None
        self.text_number = None 

        with DbConnection(decrypt_dict_vals(dbconfig, {'password'})) as cur:

            sql = """select person.nick_name, person.guid, person.django_username,
                     text_number 
                     from person where person.django_username = %s;"""

            cur.execute(sql, (user_name[0:150],))

            if cur.rowcount == 1:

                record = cur.fetchone()
                self.nick_name = record[0]
                self.guid = record[1]
                self.django_username = record[2]
                self.text_number = record[3]

            else:
       
                logger.warn('no unique database record for {}'.format(user_name[0:150]))

    @staticmethod
    def check_that_unique_user_exists(user_name):

         # See if the user name given matches anything in the database.
         with DbConnection(decrypt_dict_vals(dbconfig, {'password'})) as cur:

             sql = """select person.guid from person where person.django_username = %s;"""

             cur.execute(sql, (user_name[0:150],))

             if cur.rowcount == 1:
                 return True 
             else:
                 return False
    
    def send_password_reset_code(self):

        rc = generate_reset_code()

        self.set_new_password_reset_code(rc)

        result = send_text(self.text_number,  'fop reset code: {}'.format(rc))


    def set_new_password_reset_code(self, rc):
        #TODO: update the Person table to contain the password reset code and hte timestamp
        # save the 6 digit number in the db as the reset code with a timeout of say 1 hour 
        
        with DbConnection(decrypt_dict_vals(dbconfig, {'password'})) as cur:

            sql = """update person set password_reset_code = %s, 
                                       password_reset_code_create_time = now(),
                                       password_reset_failed_tries = 0 
                     where guid = %s;"""

            cur.execute(sql, (rc, self.guid))
            #TODO: if the sql command fails then you need to tell the user to try again.
     
  

    def clear_password_reset_code(self):

        #TODO implement a clear of the user name reset code and reset_code_timeout in the Person table
        pass
    
# #########################################################################
# The following four routes:get_reset_code, login, logout, and reset_password should be the only ones that are exposed
# to sessionless connections.
#
@app.route('/api/get_reset_code/<user_name>', methods=['GET'])
def get_reset_code(user_name):

    # TODO: This url can be used by hackers to fish for valid usernames. Is this an issue?

    try:

        if Person.check_that_unique_user_exists(user_name):

            # At this point we know the user name exists in the database - so instantiate a person in Python
            # so that you can send a password reset code.
            person = Person(user_name[0:150])
            person.send_password_reset_code()
            
            raise NameError('un-implemented API call')

            return json.dumps({'r':True, 'logged_in':None})

        else:
            logger.warn('api/get_reset_code:BAD USER INPUTS: no unique database record for {}'.format(user_name[0:150]))
            return json.dumps({'r':False, 'logged_in':None})

    except Exception as err:
        logger.error('api/get_reset_code exception: {}, {}'.format(exc_info()[0], exc_info()[1]))
        return json.dumps({'r':False, 'logged_in':None})

@app.route('/api/register', methods=['POST'])
def register():

    # TODO - Need to finish the registration algorithm
    #- registration_code = request.get_json(force=True)
    #- logger.info('registration code: {}'.format(registration_code))
    logger.info('registration code: {}'.format('foobar'))
    return json.dumps({'jwt_secret':'you wish!', 'mqtt_password':'in your dreams'})
    

@app.route("/api/login", methods=['POST'])
def process_api_login():

    try:

        with DbConnection(decrypt_dict_vals(dbconfig, {'password'})) as cur:
            
            creds = request.get_json(force=True)

            if authenticate(creds['username'][0:150], creds['password'][0:150], cur):
                logger.info('authenticate succesful')
                session['user'] = create_new_session(creds['username'][0:150], cur)
                return json.dumps({'logged_in':True, 'organizations':session['user']['organizations']})
            else:
                logger.warning('authentication failed.')
                session['user'] = None
                return json.dumps({'logged_in':False, 'organizations':[{}]})
                #- return '{"logged_in":false}'
    except Exception as err:
         logger.error('process_api_login exception: {}, {}, {}'.format(exc_info()[0], exc_info()[1], err))
         session['user'] = None
         return json.dumps({'logged_in':False, 'organizations':[{}]})
         #- return '{"logged_in":false}'

#TODO: Think about protecting this with @enforce_login. If there is no session then why bother 
@app.route("/api/logout", methods=['POST'])
def process_logout():
    try:
        logger.info('{}: api/logout'.format(session['user']['nick_name']))
        session.pop('user', None)
        return json.dumps({'r':True, 'logged_in':False})
    except Exception as err:
        logger.error('api/logout exception: {}, {}, {}'.format(exc_info()[0], exc_info()[1], err))
        return json.dumps({'r':False, 'logged_in':None})

@app.route("/api/reset_password", methods=['POST'])
def reset_password():

    try:
        logger.info('api/reset_password')
        return json.dumps({'r':True, 'message':'this function is not implemented'})
    except Exception as err:
        logger.error('api/reset_password exception: {}, {}, {}'.format(exc_info()[0], exc_info()[1], err))
        return json.dumps({'r':False, 'message':'an error occurred'})

# #########################################################################
# Web Socket event handlers go here.
thread = None
thread_lock = Lock()
mqtt_thread = None
mqtt_thread_lock = Lock()

repl_state = {}

def apply(message):
    global repl_state
    logger.info('message received: {}'.format(message))
    if message == 'mqtt':
        # TODO - See https://flask-mqtt.readthedocs.io/en/latest/index.html for an approach that might be better.
        #        As of 10/11/2020 I can't get this current code to succesfully show subscribed messges ont he vue
        #        client.
        # Add code to keep from creating multiple mqtt threads
        mqtt_thread  = socketio.start_background_task(mqtt_connect, socketio, repl_state)
        return 'mqtt connected'
    elif message == 'sub':
        repl_state['mqtt_client'].subscribe('#', 2)
        return 'subscribed to all mqtt topics'
    else:
        return 'unknown commnd'

def start_repl(*args):
    global repl_state
    # Socketio can pass in *args as well as **kwargs
    # logger.info(args[0])
    repl_state['start_time'] = time()
    repl_state['current_time'] = time()
    logger.info('repl state created')
    while True:
        socketio.sleep(10)
        #- logger.info("heartbeat")
        repl_state['current_time'] = time()
        #- socketio.emit('response', 'heartbeat')
        """-
        socketio.emit('response',
                      {'data': 'Server generated event', 'uptime': uptime(repl_state)},
                      namespace='/')
        """

class MyNameSpace(Namespace):

    @enforce_login
    def on_connect(self):
        logger.info('on_connect triggered')
        global thread
        with thread_lock:
            if thread is None:
                logger.info('No thread exist, will create a new one.')
                # See __init__.py in the sockectio project for details of this function
                # One can pass in args if necessary -> thread = socketio.start_background_task(start_repl, 'hooya')
                thread = socketio.start_background_task(start_repl)
            else:
               logger.info('thread already exists, skipping new thread creation.')
        logger.info('SocketIO connected as client {}'.format(request.sid))
        #- emit('response', {'data': 'Connected', 'uptime': 0})
        emit('response', 'connected')

    @enforce_login
    def on_disconnect(self):
        logger.info('SocketIO client {} disconnected'.format(request.sid))

    @enforce_login
    def on_command(self, message):
        logger.info('SocketIO command {} received'.format(message))
        emit('response', apply(message))
        #- emit('response', message)
        #-     {'data': message['data'], 'count': 'foobar'})

socketio.on_namespace(MyNameSpace('/'))

# #########################################################################
# All routes below this line should apply the @enforce_login decorater in
# order to restrict access to logged in users.

@app.route('/api/get_chart_list/<system_uuid>', methods=['GET'])
@enforce_login
def get_chart_list(system_uuid):

    #TODO - verify that the user has the privliges to see charts for the 
    #       grow system identified by <system_uuid>

    #TODO - I bet this could moved to a decorator or hell put it in enforce_login!
    logger.info('{}: api/get_chart_list/{}'.format(session['user']['nick_name'], system_uuid))
  
    try:
        with DbConnection(decrypt_dict_vals(dbconfig, {'password'})) as cur:

            sql = """select chart_config from grow_system inner join grow_system_devices on
                     grow_system.uuid = grow_system_devices.grow_system_uuid inner join 
                     device on device.guid = grow_system_devices.device_uuid where
                     uuid = %s;"""

            cur.execute(sql, (system_uuid,))

            assert(cur.rowcount == 1), 'No or more than one device found. Only one device was expected.'

            return json.dumps(
                {'r':True, 
                    'chart_list':[{'rel_url':'/chart/{}/{}'.format(cl['vue_name'], system_uuid)}
                                  for cl in cur.fetchone()[0]['chart_list']]
                })
    except:
        logger.error('error {}, {}'.format(exc_info()[0], exc_info()[1]))
        return json.dumps({'r':False, 'chart_list':[{}]})


@app.route('/api/get_data_json/<system_uuid>/<start_date>/<end_date>')
@enforce_login
def get_data_json(system_uuid, start_date, end_date):

    #TODO - verify that the user has the privliges to see the contents of the zip file. 
    logger.info('{}: api/get_data_json/{}/{}/{}'.format(session['user']['nick_name'], system_uuid, start_date, end_date))

    try:
        # Get the fopd device UUID 
        with DbConnection(decrypt_dict_vals(dbconfig, {'password'})) as cur:

            sql = """select device_uuid from grow_system as gs inner join
                     grow_system_devices as gsd on gs.uuid = gsd.grow_system_uuid where 
                     gs.uuid = %s"""
     
            cur.execute(sql, (system_uuid,))
            # Get the 1st device id returned from the grow system devices list
            device_uuid = cur.fetchone()[0]

        result = get_device_data_json(device_uuid, start_date, end_date, session['user']['ct_offset'])

        if result:
            return result
        else:
            #TODO: Need a different error message here than the s3_error
            return send_from_directory(path.join(app.root_path, 'static'), 's3_error.jpg', mimetype='image/png')
    except:
        logger.error('in /api/get_data_json route: {}, {}'.format(exc_info()[0], exc_info()[1]))
        return send_from_directory(path.join(app.root_path, 'static'), 's3_error.jpg', mimetype='image/png')


@app.route('/api/get_data_csv/<system_uuid>/<start_date>/<end_date>')
@enforce_login
def get_data_csv(system_uuid, start_date, end_date):
    #TODO - verify that the user has the privliges to see the contents of the zip file. 

    #TODO - I bet this could moved to a decorator or hell put it in enforce_login!
    logger.info('{}: api/get_data_csv/{}/{}/{}'.format(session['user']['nick_name'], system_uuid, start_date, end_date))

    try:

        # Get the fopd device UUID 
        with DbConnection(decrypt_dict_vals(dbconfig, {'password'})) as cur:

            sql = """select device_uuid from grow_system as gs inner join
                     grow_system_devices as gsd on gs.uuid = gsd.grow_system_uuid where 
                     gs.uuid = %s"""
     
            cur.execute(sql, (system_uuid,))
            device_uuid = cur.fetchone()[0]
       
        logger.info('fopd device id {}'.format(device_uuid))

        out_fp = StringIO() 
        flask_out_fp = BytesIO()

        # Fill out_fp with csv formatted lines containing all the devices's observerations
        
        if get_device_data(out_fp, device_uuid, start_date, end_date, session['user']['ct_offset']):
            # Flask wants a byte file so transfer out_fp to flask_out_fp
            flask_out_fp.write(out_fp.getvalue().encode('utf-8')) 
            flask_out_fp.seek(0)
            out_fp.close()

            return send_file(flask_out_fp, mimetype='text/csv', as_attachment=True, attachment_filename='data.csv')
        else:
            #TODO: Need a different error message here than the s3_error
            return send_from_directory(path.join(app.root_path, 'static'), 's3_error.jpg', mimetype='image/png')

    except:
        logger.error('in /api/get_data_csv route: {}, {}'.format(exc_info()[0], exc_info()[1]))
        return send_from_directory(path.join(app.root_path, 'static'), 's3_error.jpg', mimetype='image/png')
        #- return send_from_directory('/static', 's3_error.jpg', mimetype='image/png')


@app.route('/api/get_zip/<system_uuid>/<images_per_day>/<start_date>/<end_date>')
@enforce_login
def get_zip(system_uuid, images_per_day, start_date, end_date):

    #TODO - verify that the user has the privliges to see the contents of the zip file. 

    #TODO - I bet this could moved to a decorator or hell put it in enforce_login!
    logger.info('{}: api/get_zip/{}/{}/{}/{}'.format(session['user']['nick_name'], system_uuid, images_per_day, start_date, end_date))
   
    try:

        # Get the camera id
        with DbConnection(decrypt_dict_vals(dbconfig, {'password'})) as cur:

            sql = """select camera_uuid from grow_system where 
                     uuid = %s"""

            cur.execute(sql, (system_uuid,))
            camera_uuid = cur.fetchone()[0]

        #TODO - Need to make sure the user has the permission to view this camera.
        if not has_permission(session['user']['user_guid'], camera_uuid, 'view'):
            logger.warning('user {} does not have permissions to view camera {}'.format(session['user']['user_guid'],
                camera_uuid))
            return send_from_directory(path.join(app.root_path, 'static'), 's3_error.jpg', mimetype='image/png')

        
        logger.info('org uud: {}, camera uuid: {}'.format(session['user']['organizations'][0]['guid'], camera_uuid))

        s3_file_names = get_s3_file_names(camera_uuid, images_per_day, start_date, end_date) 

        # TODO: Retrun a zip archive containing a file that contains text indicating that there are no files available.
        if len(s3_file_names) == 0:
            logger.warning('no images found')
            return send_from_directory(path.join(app.root_path, 'static'), 's3_error.jpg', mimetype='image/png')

        zip_archive = BytesIO()

        with ZipFile(zip_archive, mode='w', compression=ZIP_DEFLATED, allowZip64=False) as zip_file: 

            # TODO: create a context that opens an S3 session on the back end.
            with S3Session() as s3:
                for s3_file_name in s3_file_names:
                    current_image = s3.get_s3_image(s3_file_name['s3_reference'])
                    if current_image['image_blob'] != None:
                        zip_file.writestr(s3_file_name['utc_timestamp'].strftime('%Y_%m_%d_%H_%M.jpg'), 
                                          current_image['image_blob'])

        zip_archive.seek(0)
        logger.info("length of archive: {}".format(len(zip_archive.getvalue())))
        return send_file(zip_archive, mimetype='application/zip', as_attachment=True, 
                         attachment_filename='image_archive.zip')

    except:
        logger.error('in /api/get_zip route: {}, {}'.format(exc_info()[0], exc_info()[1]))
        return send_from_directory(path.join(app.root_path, 'static'), 's3_error.jpg', mimetype='image/png')
        #- return send_from_directory('/static', 's3_error.jpg', mimetype='image/png')

# TODO - add start and end date to charts so user can chart over more than just one day.
#        see if Flask supports optional parameters
@app.route('/api/chart/<data_type>/<grow_system_guid>')
@enforce_login
def chart(data_type, grow_system_guid):

    #TODO - verify that the user has the privliges to see charts for the 
    #       grow system identified by <grow_system_guid>

    #TODO - I bet this could moved to a decorator or hell put it in enforce_login!
    logger.info('{}: api/chart/{}/{}'.format(session['user']['nick_name'], data_type, grow_system_guid))
  
    try:
        with DbConnection(decrypt_dict_vals(dbconfig, {'password'})) as cur:

            # Use the grow_system_guid to lookup the chart configuration.
            sql = """select device.chart_config, device.guid from grow_system_devices inner join device on
                     grow_system_devices.device_uuid = device.guid
                     where grow_system_devices.grow_system_uuid = %s;"""

            cur.execute(sql, (grow_system_guid,))
            rc = cur.rowcount

            assert(rc == 1), 'No chart configurations are associated with grow system: {}'.format(grow_system_guid)

            r = cur.fetchone()
            result = generate_chart(r[1], data_type, r[0], session['user']['ct_offset'])
            
            if result['bytes'] != None:
                return Response(result['bytes'], mimetype='image/svg+xml')
            else:
                #- return send_from_directory('static', 'graph_error.jpg', mimetype='image/png')
                return send_from_directory('static', 's3_error.jpg', mimetype='image/png')

    except:
        logger.error('error {}, {}'.format(exc_info()[0], exc_info()[1]))
        return send_from_directory('static', 'graph_error.jpg', mimetype='image/png')


@app.route('/api/extend_session', methods=['GET'])
@enforce_login
def extend_session():
    """ Clients are expected to call this endpoint when they want to keep their session alive. """

    if 'user' in session:
        logger.info('{}: api/extend_session'.format(session['user']['nick_name']))
        return json.dumps({'r':True, 'logged_in':True})
    else:
        logger.error('api/extend_session: No user session.')
        return json.dumps({'r':False, 'logged_in':None})


@app.route('/api/image/<system_uuid>', methods=['GET'])
@enforce_login
def image(system_uuid):

    #TODO - verify that the user has the privliges to see the image. 

    #TODO - I bet this could moved to a decorator or hell put it in enforce_login!
    logger.info('{}: api/image/{}'.format(session['user']['nick_name'], system_uuid))

    try:

        # Get the camera id
        with DbConnection(decrypt_dict_vals(dbconfig, {'password'})) as cur:

            sql = """select camera_uuid from grow_system where uuid = %s"""

            cur.execute(sql, (system_uuid,))

            camera_uuid = cur.fetchone()[0]

        if not has_permission(session['user']['user_guid'], camera_uuid, 'view'):
            logger.warning('user_uuid {}: get image permission failure for org {} and camera {}'.format(
               session['user']['user_guid'], session['user']['organizations'][0]['guid'], camera_uuid))
            return send_from_directory(path.join(app.root_path, 'static'), 's3_error.jpg', mimetype='image/png')

        logger.info('org uud: {}, camera uuid: {}'.format(session['user']['organizations'][0]['guid'], camera_uuid))
        result = get_image_file_v2(get_newest_image_uuid(camera_uuid))

        if result['image_blob'] != None:
            return Response(result['image_blob'], mimetype='image/jpg')
        else:
            logger.error('get image failure {}'.format(result['msg']))
            return send_from_directory(path.join(app.root_path, 'static'), 's3_error.jpg', mimetype='image/png')

    except:
        logger.error('in /image.jpg route: {}, {}'.format(exc_info()[0], exc_info()[1]))
        return send_from_directory('/static', 's3_error.jpg', mimetype='image/png')


@app.route('/api/get_crops', methods=['GET'])
@enforce_login
def get_crops():

    logger.info('{}: api/get_crops/'.format(session['user']['nick_name']))

    try:
        with DbConnection(decrypt_dict_vals(dbconfig, {'password'})) as cur:

            sql = """select grow_batch_id, g.start_date, 'germination' as status, v.common_name, v.species from germination as g 
                     inner join grow_batch as gb on g.grow_batch_id = gb.id
                     inner join seed_lot as sl on gb.seed_lot_id = sl.id
                     inner join variety as v on sl.variety_id = v.id
                     union
                     select 100, '20190620' as start_date, 'stage 2' as status, 'basil' as common_name, 'Genovese' as variety;"""

            cur.execute(sql)

            if cur.rowcount > 0:
                crops = [{'batch_id':c[0], 'start_date':c[1].strftime('%x'), 'status':c[2], 'name':c[3], 'variety':c[4]}
                         for c in cur.fetchall()]
              
            else:
                crops = [{}]

            return json.dumps({'r':True, 'crops':crops})

    except:
        logger.error('get_crops exception: {}, {}'.format(exc_info()[0], exc_info()[1]))
        return json.dumps({'server error':True})

# TODO - this routine is a hack. as the software matures it will need to refactored out.
def get_perms(perm_list):

    if (perm_list[1] or perm_list[3]) and (perm_list[0] or perm_list[2]):
        return 'admin, view'
    if perm_list[1] or perm_list[3]:
        return 'admin'
    if perm_list[0] or perm_list[2]:
        return 'view'

@app.route('/api/get_devices', methods=['GET'])
@enforce_login
def get_devices():

    logger.info('{}: api/get_devices'.format(session['user']['nick_name']))

    try:
        with DbConnection(decrypt_dict_vals(dbconfig, {'password'})) as cur:

            sql = """select uuid, local_name, grow_system_type,
                  organization_view, organization_admin, group_view, group_admin from grow_system where
                  (organization_uuid = %s and (organization_admin or organization_view)) or 
                  (group_uuid in %s and (group_admin or group_view))"""

            logger.info('get_devics SQL: {}'.format(
                cur.mogrify(sql, (session['user']['organizations'][0]['guid'],get_user_groups(session['user']['user_guid'])))))
            
            cur.execute(sql, (session['user']['organizations'][0]['guid'],get_user_groups(session['user']['user_guid'])))

            if cur.rowcount > 0:
                devices = [{'grow_system_guid':grow_system[0], 'name':grow_system[1], 'type':grow_system[2],
                            'access_type':get_perms(grow_system[3:7])} for grow_system in cur.fetchall()]
            else:
                devices = [{}]

            return json.dumps({'r':True, 'devices':devices})

    except:
        logger.error('get_devices exception: {}, {}'.format(exc_info()[0], exc_info()[1]))
        return json.dumps({'r':False})

#ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZk
#- TODO: Review all the routes beneath this line once the system is converted to be
#        entirely API driven and delete unused ones.
#
@app.route("/login", methods=['GET'])
@app.route("/")
def get_login_form():
     # show the login form 
     return render_template('login.html', error=None)

     
@app.route("/login", methods=['POST'])
def process_login():

    try:
        with DbConnection(decrypt_dict_vals(dbconfig, {'password'})) as cur:

            if authenticate(request.form['username'][0:150], request.form['password'], cur):
                logger.info('authenticate succesful')
                session['user'] = create_new_session(request.form['username'][0:150], cur)
                return render_template('home.html', devices=session['user']['devices'], selected_device=session['user']['devices'][0], chart_list=session['user']['chart_config']['chart_list'])
                #- return render_template('home.html', chart_list=session['user']['chart_config']['chart_list'])
            else:
                logger.warning('authentication failed.')
                session['user'] = None
                flash('incorrect username or password')
                return render_template('login.html')
    except:
         logger.error('process_login exception: {}, {}'.format(exc_info()[0], exc_info()[1]))
         session['user'] = None
         flash('system error F_PL')
         return render_template('login.html')

@app.route('/logout', methods=['GET'])
def logout():
    session['user'] = None
    flash('you are logged out')
    return render_template('login.html')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('/static', 'favicon.ico', mimetype='image/png')




@app.route('/doser')
@enforce_login
def doser():

    logger.info('doser request')

    return render_template('doser_2.html')

# This code assumes users are stored in a table created by Django as
# per the Django method of hashing passwords. However
# don't be confused: this is a Flask application.
# Django currently limits usernames to 150 characters.
#
def authenticate(username, password, cur):

    # Is the user in the db?
    try:
        assert ( username != None), 'empty username'
        assert (len(username) > 3 and len(username) <= 150), 'username must be 4 to 150 characters long'
        logger.info('login request from {}'.format(username))

        return check_password(cur, username, password)

    except:
        logger.error('authenticate exception: {}, {}'.format(exc_info()[0], exc_info()[1]))
        return False

def create_new_session(username, cur):

    # Create a session based upon the users database profile.

    # TODO: The ct_offset stuff won't work. figure out a way to store the users preferred time zone and refactor
    # to slide all display times from the central time (i.e. server time) to the users time.  Make server time
    # a configuration setting.
    #
    # TODO: Need a way to set ct_offset correctly.
    # ct_offset is the number of hours that the user wants their time data to be offset from central time.
    # The server (Ubuntu) generates central time as per US rules for daylight savings so 
    # one could use Ubunutu as the source of truth. The command: date +'%:z %Z' will
    # return the current offset from UTC for the Ubuntu time. 
    s = {'user_name': username, 'ct_offset':-6}

    sql = """select person.nick_name, person.guid, person.django_username 
             from person where person.django_username = %s;"""

    cur.execute(sql, (username,))

    rc = cur.rowcount
    # TEST HOOK rc = 2
    assert(rc == 1), 'create_new_sesson: django_username {} has {} associated person records.  It should only have 1.'\
                     .format(username, rc) 

    person_info = cur.fetchone()
    s['user_guid'] = person_info[1]
    s['nick_name'] = person_info[0]

    # Now get the user's organizations
    sql = """select participant.organization_guid, organization.local_name from
             participant inner join organization on
             participant.organization_guid = organization.guid where
             participant.guid = %s"""

    cur.execute(sql, (s['user_guid'],))

    if cur.rowcount > 0:
        s['organizations'] = [ {'guid':organization[0], 'name':organization[1]} for organization in cur.fetchall() ]
    else:
        s['organization'] = [{}]

    """-
    # Now find the top level devices that exist within this person's organization and sub-organizations. 
    # A top level device is defined as a device with no parent devices.
    sql = ""select device.local_name, device.guid, device.chart_config from device inner join participant on device.guid = participant.guid
             where device.parent_guid is null and 
             participant.organization_guid in 
             (with recursive org_root (organization_guid) 
             as (select root.guid from organization root where guid = %s 
             Union All
             select child.guid from org_root parent, organization child
             where child.parent_org_id = parent.organization_guid)
             select distinct organization_guid from org_root);""
 
    cur.execute(sql, (s['org_id'],))
    rc = cur.rowcount
    # TEST HOOK rc = 0
    # TODO: In the future when the user does not have any devices then show them an interface allowing them to add a device.
    assert(rc > 0), 'No devices are associated with org: {}'.format(s['org_id'])
 
    s['devices'] = [ {'name':device[0], 'id':device[1], 'chart_config':device[2]} for device in cur.fetchall() ]

    #- s['device_id'] = s['devices'][0]['id'] 
    s['chart_config'] = s['devices'][0]['chart_config']

    # Get the list of cameras for the selected device
    sql = ""select device.local_name, device.guid
             from device inner join device_type on device.device_type_id = device_type.id
             where device_type.local_name = 'camera'  and 
             device.guid in 
             (with recursive device_root (device_guid)
             as (select root.guid from device root where guid = %s
             Union All select child.guid from device_root parent, device child 
             where child.parent_guid = parent.device_guid)
             select distinct device_guid from device_root);""

    # TODO: must select camera info for all devices. For now select it for the 1st device.
    cur.execute(sql, (s['devices'][0]['id'],))
    #- cur.execute(sql, (s['device_id'],))
    rc = cur.rowcount
    if rc > 0:
        camera_info = cur.fetchone()
        s['camera_id'] = camera_info[1]
    else:
        s['camera_id'] = None
    """

    logger.debug('session: {}'.format(s))

    return s

def get_image_file(org_id, camera_id):
    # get the image via a JWT autenticated GET request to the
    # from the image download/upload server
    
    # create a JWT for authenticating fopdcw to fop
    jwt = make_image_request_jwt(org_id, camera_id)
    logger.info('jwt:{}'.format(jwt))
    headers = {'AUTHORIZATION':'BEARER ' + jwt}

    r = requests.get(url=fop_url_for_get_image, headers=headers)

    if r.status_code == 200:
        s = 'image request successful, status: {}, content-type: {}, content-length-header: {}, content length: {}'
        logger.info(s.format(r.status_code, r.headers['content-type'], r.headers['content-length'], len(r.content)))
        return {'bytes':r.content}
    else:
        logger.error('image request failed, status: {}, encoding: {}'.format(r.status_code, r.encoding))
        if r.encoding == 'text/html' or r.encoding == 'utf-8':
            logger.error('response text: {}'.format(r.text[0:100]))
        return {'bytes':None}

if __name__ == "__main__":
    #- app.run(host='0.0.0.0', port='8081')
    pass
