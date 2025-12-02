import os
import json
from datetime import datetime, timezone
import secrets
import re

from flask import Flask, render_template, redirect, url_for, request, session, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, EqualTo

USERS_FILE = "users.json"

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', secrets.token_urlsafe(32))

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            if not isinstance(data, dict):
                return {}
            return data
        except json.JSONDecodeError:
            return {}


def save_users(data):
    tmp = USERS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, USERS_FILE)


def iso_now():
    return datetime.now(timezone.utc).isoformat()

def is_strong_password(pw: str) -> (bool, str):
    if len(pw) < 8:
        return False, "Пароль должен содержать как минимум 8 символов."
    if not re.search(r'[a-z]', pw):
        return False, "Пароль должен содержать хотя бы одну строчную букву."
    if not re.search(r'[A-Z]', pw):
        return False, "Пароль должен содержать хотя бы одну заглавную букву."
    if not re.search(r'\d', pw):
        return False, "Пароль должен содержать хотя бы одну цифру."
    if not re.search(r'[^\w\s]', pw):
        return False, "Пароль должен содержать хотя бы один специальный символ (например !@#$%)."
    return True, ""

class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=1, max=64)])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Запомнить меня")
    submit = SubmitField("Войти")

class CreateUserForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=1, max=64)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    password2 = PasswordField("Повторите пароль", validators=[DataRequired(), EqualTo('password', message='Пароли должны совпадать')])
    is_admin = BooleanField("Дать права администратора (может создавать других пользователей)")
    submit = SubmitField("Создать аккаунт")

def ensure_initial_admin():
    users = load_users()
    if users:
        return

    admin_username = "admin"
    admin_password = "!123*"

    admin_hash = generate_password_hash(admin_password)
    users = {
        admin_username: {
            "password_hash": admin_hash,
            "registered_at": iso_now(),
            "last_login_at": None,
            "is_admin": True
            }
        }
    save_users(users)

    admin_hash = generate_password_hash(admin_password)
    users = {
        admin_username: {
            "password_hash": admin_hash,
            "registered_at": iso_now(),
            "last_login_at": None,
            "is_admin": True
        }
    }
    save_users(users)

def current_user():
    uname = session.get("username")
    if not uname:
        return None
    users = load_users()
    return users.get(uname)


def login_user(username, remember=False):
    session['username'] = username
    if remember:
        session.permanent = True
    users = load_users()
    if username in users:
        users[username]['last_login_at'] = iso_now()
        save_users(users)


def logout_user():
    session.pop('username', None)


def login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash("Требуется вход в систему.", "warning")
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return wrapped


def admin_required(f):
    from functools import wraps
    @wraps(f)
    def wrapped(*args, **kwargs):
        u = current_user()
        if not u:
            flash("Требуется вход.", "warning")
            return redirect(url_for('login', next=request.path))
        if not u.get('is_admin'):
            flash("У вас нет прав администратора.", "danger")
            return abort(403)
        return f(*args, **kwargs)
    return wrapped

@app.route("/")
def index():
    users = load_users()
    return render_template('index.html', users=users, current_user_name=session.get('username'), current_user=current_user())


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        users = load_users()
        uname = form.username.data
        pw = form.password.data
        user = users.get(uname)
        if not user:
            flash("Пользователь не найден.", "danger")
            return redirect(url_for('login'))
        if check_password_hash(user['password_hash'], pw):
            login_user(uname, remember=form.remember.data)
            flash("Успешный вход.", "success")
            next_page = request.args.get('next') or url_for('index')
            return redirect(next_page)
        else:
            flash("Неверный пароль.", "danger")
            return redirect(url_for('login'))
    return render_template('login.html', form=form)

@app.route("/logout")
def logout():
    logout_user()
    flash("Вы вышли из системы.", "info")
    return redirect(url_for('index'))

@app.route("/create_user", methods=["GET", "POST"])
@admin_required
def create_user():
    form = CreateUserForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        password = form.password.data
        is_admin_flag = bool(form.is_admin.data)

        users = load_users()
        if username in users:
            flash("Пользователь с таким username уже существует.", "danger")
            return redirect(url_for('create_user'))

        ok, reason = is_strong_password(password)
        if not ok:
            flash(f"Слабый пароль: {reason}", "danger")
            return redirect(url_for('create_user'))

        pw_hash = generate_password_hash(password)
        users[username] = {
            "password_hash": pw_hash,
            "registered_at": iso_now(),
            "last_login_at": None,
            "is_admin": is_admin_flag
        }
        save_users(users)
        flash(f"Пользователь {username} успешно создан.", "success")
        return redirect(url_for('index'))

    return render_template('create_user.html', form=form)

if __name__ == "__main__":
    ensure_initial_admin()
    app.run(debug=True)