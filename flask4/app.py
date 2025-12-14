from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin,
    login_user, login_required,
    logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'




class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='user')  # admin / user


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_private = db.Column(db.Boolean, default=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))




@app.route('/')
def index():
    if current_user.is_authenticated:
        posts = Post.query.all()
    else:
        posts = Post.query.filter_by(is_private=False).all()

    return render_template('index.html', posts=posts)



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()

        if user and check_password_hash(user.password_hash, request.form['password']):
            login_user(user)
            return redirect(url_for('index'))

        flash('Неверный логин или пароль')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))




@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            flash('Пользователь уже существует')
            return redirect(url_for('register'))

        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            role='user'
        )

        db.session.add(user)
        db.session.commit()
        login_user(user)

        return redirect(url_for('index'))

    return render_template('register.html')


@app.route('/post/new', methods=['GET', 'POST'])
@login_required
def create_post():
    if current_user.role != 'admin':
        flash('Недостаточно прав')
        return redirect(url_for('index'))

    if request.method == 'POST':
        post = Post(
            title=request.form['title'],
            content=request.form['content'],
            is_private=('is_private' in request.form),
            author_id=current_user.id
        )
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('index'))

    return render_template('post_form.html')


@app.route('/post/edit/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    if current_user.role != 'admin':
        flash('Недостаточно прав')
        return redirect(url_for('index'))

    post = Post.query.get_or_404(post_id)

    if request.method == 'POST':
        post.title = request.form['title']
        post.content = request.form['content']
        post.is_private = ('is_private' in request.form)
        db.session.commit()
        return redirect(url_for('index'))

    return render_template('post_form.html', post=post)


@app.cli.command('init-db')
def init_db():
    db.create_all()

    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            password_hash=generate_password_hash('admin'),
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()

    print('БД создана. Админ: admin / admin')
