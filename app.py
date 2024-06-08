import os
from flask import Flask, render_template, url_for, request, redirect, flash, g, make_response, session
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash
from flask_jwt_extended import (JWTManager, create_access_token, jwt_required,
                                get_jwt_identity, get_jwt, get_csrf_token)
from datetime import timedelta
from DBRequests import DBRequests
import string
import random
import time
from captcha.image import ImageCaptcha
import threading
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__)
app.secret_key = 'my_secret_key'


# Настройка логирования
def setup_logger(app):
    # Путь к файлу журнала
    log_file_path = os.path.join(app.root_path, 'app.log')

    # Настройка формата журнала
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')

    # Настройка обработчика журнала
    file_handler = RotatingFileHandler(log_file_path, maxBytes=10240, backupCount=10)
    file_handler.setFormatter(formatter)

    # Добавление обработчика к приложению
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)

    return app.logger


logger = setup_logger(app)

menu = [{"name": "Главная", "url": "index"},
        {"name": "Подать заявку", "url": "applicationSub"},
        {"name": "Отозвать заявку", "url": "applicationCan"},
        {"name": "Вход", "url": "login"},
        {"name": "Регистрация", "url": "registration"}]

# конфигурация
DATABASE = '/tmp/flsite.db'
DEBUG = True
SECRET_KEY = 'my_secret_key'

app.config["JWT_SECRET_KEY"] = "secretniy_klyuch"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(seconds=300)
app.config['JWT_TOKEN_LOCATION'] = ['cookies']
app.config['JWT_CSRF_CHECK_FORM'] = True

jwt = JWTManager(app)
app.config.from_object(__name__)

app.config.update(dict(DATABASE=os.path.join(app.root_path, 'flsite.db')))


@jwt.unauthorized_loader
def custom_unauthorized_response(_err):
    logger.error(f"Error: {str(_err)}")
    logger.info(f"Ссылка {request.url}")
    response = make_response(redirect('/login'))
    response.set_cookie('redirected_url', request.url, max_age=300)
    logger.info("User passed!")
    return response

def connect_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def create_db():
    db = connect_db()
    with app.open_resource('sq_db.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()
    db.close()

def get_db():
    if not hasattr(g, 'link_db'):
        g.link_db = connect_db()
    return g.link_db

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'link_db'):
        g.link_db.close()

db = None
@app.before_request
def before_request():
    global db
    dbase = get_db()
    db = DBRequests(dbase)


@app.after_request
def refresh_expiring_jwt(response):
    try:
        exp_timestamp = get_jwt()["exp"]
        now = datetime.now()
        target_timestamp = datetime.timestamp(now + timedelta(seconds=120))
        if target_timestamp > exp_timestamp:
            access_token = create_access_token(identity=get_jwt_identity())
            response.set_cookie('access_token_cookie', access_token, httponly=True, samesite='Strict',
                                max_age=timedelta(seconds=300))
        return response

    except (RuntimeError, KeyError):
        return response


@app.route('/')
@jwt_required(optional=True)
def index():
    token = get_jwt_identity()
    if token:
        return render_template('index.html', menu=menu, auth=db.getUserById(token))
    return render_template('index.html', menu=menu, auth=None)


def generate_captcha():
    captcha_length = 6
    characters = string.digits
    pattern = ''.join(random.choices(characters, k=captcha_length))

    # Сохраняем изображение CAPTCHA в папку static
    static_dir = 'static'
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
    captcha_image_name = f"captcha_{int(time.time())}.png"
    captcha_image = os.path.join(static_dir, captcha_image_name)
    image_captcha = ImageCaptcha(width=150, height=100)
    image_captcha.write(pattern, captcha_image)
    session['captcha_code'] = pattern
    session['captcha_name'] = captcha_image_name
    return pattern, captcha_image_name


def captcha_delete():  # Удаление использованных капч
    if 'captcha_code' in session:
        session.pop('captcha_code', None)

    if session.get('captcha_name') is not None:
        try:
            captcha_path = os.path.join("static", session.get('captcha_name'))
            os.remove(captcha_path)
        except:
            print("No file found!")
        session.pop('captcha_name', None)


def delete_captcha_image(filename):
    try:
        captcha_path = os.path.join("static", filename)
        os.remove(captcha_path)
    except:
        print("File not found!")


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'GET':
        flash_message = request.cookies.get('flash_message')
        if flash_message:
            flash(flash_message, category="success")
        captcha_delete()
        captcha_pattern, captcha_image_name = generate_captcha()
        timer = threading.Timer(5.0, delete_captcha_image, args=[captcha_image_name])
        timer.start()
        return render_template('login.html', title="Вход", menu=menu, captcha_pattern=captcha_pattern,
                               captcha_image=captcha_image_name)

    if request.method == 'POST':
        logger.info(f"captcha_code_generated: {str(session.get('captcha_code'))}")
        logger.info(f"captcha_code_got: {str(request.form['kapcha'])}")
        if session.get('captcha_code') == request.form['kapcha']:
            user = db.getUserByPhone(request.form['phone'])
            if user is not None:
                if not check_password_hash(user['passwd'], request.form['password']):
                    logger.warning("Wrong password!")
                    flash("Неверный пароль", "error")
                    captcha_delete()
                    captcha_pattern, captcha_image_name = generate_captcha()
                    timer = threading.Timer(5.0, delete_captcha_image, args=[captcha_image_name])
                    timer.start()
                    return render_template('login.html', title="Вход", menu=menu, captcha_pattern=captcha_pattern,
                                           captcha_image=captcha_image_name)
                else:
                    access_token = create_access_token(identity=user['id'])
                    response = make_response(redirect(url_for('profile')))
                    response.set_cookie('access_token_cookie', access_token, httponly=True, samesite='Strict',
                                        max_age=300)
                    logger.info("User passed!")
                    captcha_delete()
                    return response
            else:
                logger.warning("User not found!")
                flash("Пользователь не найден", "error")
                captcha_delete()
                captcha_pattern, captcha_image_name = generate_captcha()
                timer = threading.Timer(5.0, delete_captcha_image, args=[captcha_image_name])
                timer.start()
                return render_template('login.html', title="Вход", menu=menu, captcha_pattern=captcha_pattern,
                                       captcha_image=captcha_image_name)
        else:
            logger.warning("Капча введена неверно")
            flash("Капча введена неверно", "error")
            captcha_delete()
            captcha_pattern, captcha_image_name = generate_captcha()
            timer = threading.Timer(5.0, delete_captcha_image, args=[captcha_image_name])
            timer.start()
            return render_template('login.html', title="Вход", menu=menu, captcha_pattern=captcha_pattern,
                                   captcha_image=captcha_image_name)


@app.route('/logout', methods=['GET'])
def logout():
    return redirect(url_for('user_logout'))


@app.route('/user_logout')
@jwt_required()
def user_logout():
    response = make_response(redirect('/'))
    response.set_cookie('access_token_cookie', '')
    logger.info("User logged out")
    return response


@app.route('/registration', methods=['GET', 'POST'])
def registration():
    return redirect(url_for('user_registration'))


@app.route('/user_registration', methods=['POST', 'GET'])
def user_registration():
    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']
        phone = request.form['phone']
        password = request.form['password']

        hash_password = generate_password_hash(password)
        db.addUser(name, surname, phone, hash_password)
        logger.info('Успешная регистрация нового пользователя')
        response = make_response(redirect(url_for('login')))
        response.set_cookie("flash_message", "Регистрация прошла успешно!", max_age=1)
        return response
    return render_template('registration.html', menu=menu)


@app.route('/applicationSub', methods=['POST', 'GET'])
@jwt_required()
def applicationSub():
    user_id = get_jwt_identity()
    token = request.cookies.get('access_token_cookie')
    csrf_token = get_csrf_token(token)
    if request.method == 'POST':
        if 'latitude' in request.form:
            latitude = request.form['latitude']
            longitude = request.form['longitude']
            service_id = request.form['service']
            address = request.form['address']
            city = request.form['city']
            if city == "Новосибирск":
                status = "Заявка создана"
                description = request.form['comment']
                request_id = db.addRequest(user_id, service_id, address, latitude, longitude, status, description)
                logger.info(f'Новая заявка от пользователя {user_id} успешно создана. ID заявки: {request_id}')
                return redirect(url_for('profile'))
            else:
                logger.warning(f'Пользователь {user_id} пытается подать заявку за пределами Новосибирска')
                flash('Выбран некорректный адрес. Мы работаем только на территории г. Новосибирска', 'error')
                return render_template('applicationSub.html', title="Подача заявки", menu=menu, csrf_token=csrf_token)
    return render_template('applicationSub.html', title="Подача заявки", menu=menu, csrf_token=csrf_token)

@app.route('/applicationCan', methods=['POST', 'GET'])
@jwt_required()
def applicationCan():
    token = request.cookies.get('access_token_cookie')
    csrf_token = get_csrf_token(token)
    if request.method == 'POST':
        application_id = request.form['application_number']
        status = "Заявка отозвана"
        description = request.form['description']
        db.updateRequest(application_id, status, description)
        logger.info(f'Заявка {application_id} успешно отозвана')
        return redirect(url_for('index'))
    return render_template('applicationCan.html', title="Отзыв заявки", menu=menu, csrf_token=csrf_token)

@app.route('/profile', methods=['GET'])
@jwt_required()
def profile():
    user_id = get_jwt_identity()
    user = db.getUserById(user_id)
    user_requests = db.getRequests(user_id)
    for request in user_requests:
        request_id = request['id']
        current_time = request['date']
        time_diff = datetime.now() - datetime.strptime(current_time, "%H:%M %d-%m-%y")
        if 300 < time_diff.total_seconds() <= 600:
            db.updateRequestStatus(request_id, "В обработке")
            logger.info(f'Заявка {request_id} перешла в статус "В обработке"')
        if time_diff.total_seconds() > 600:
            db.updateRequestStatus(request_id, "Выполняется")
            logger.info(f'Заявка {request_id} перешла в статус "Выполняется"')

    return render_template('profile.html', user=user, user_requests=user_requests)

@app.errorhandler(404)
def pageNotFound(error):
    return render_template('page404.html', title="Страница не найдена", menu=menu)

if __name__ == "__main__":
    app.run(debug=True)

