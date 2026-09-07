import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///thunder.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    bookings = db.relationship('Booking', backref='user', lazy=True)

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    features = db.Column(db.Text, nullable=True)
    price_label = db.Column(db.String(50), nullable=False)
    badge = db.Column(db.String(50), nullable=True)
    icon = db.Column(db.String(10), default='✦')
    featured = db.Column(db.Boolean, default=False)
    sort_order = db.Column(db.Integer, default=0)
    bookings = db.relationship('Booking', backref='service', lazy=True)

    def feature_list(self):
        return [f.strip() for f in (self.features or '').split('\n') if f.strip()]

class GalleryItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    label = db.Column(db.String(100), nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    color = db.Column(db.String(20), default='#1a2535')
    height = db.Column(db.Integer, default=280)
    sort_order = db.Column(db.Integer, default=0)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=True)
    event_date = db.Column(db.String(50), nullable=True)
    message = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='new')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/services')
def services():
    services_list = Service.query.order_by(Service.sort_order).all()
    return render_template('services.html', services=services_list)

@app.route('/gallery')
def gallery():
    items = GalleryItem.query.order_by(GalleryItem.sort_order).all()
    categories = sorted(list({item.category for item in items}))
    return render_template('gallery.html', items=items, categories=categories)

@app.route('/book', methods=['GET', 'POST'])
def book():
    selected_service_id = request.args.get('service_id', type=int)
    services_list = Service.query.order_by(Service.sort_order).all()
    if request.method == 'POST':
        booking = Booking(
            user_id=current_user.id if current_user.is_authenticated else None,
            service_id=request.form.get('service_id', type=int) or None,
            name=request.form.get('name'),
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            event_date=request.form.get('event_date'),
            message=request.form.get('message')
        )
        db.session.add(booking)
        db.session.commit()
        flash('Booking request sent successfully!', 'success')
        return redirect(url_for('account' if current_user.is_authenticated else 'index'))
    return render_template('book.html', services=services_list, selected_service_id=selected_service_id)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('signup.html')
        user = User(
            email=email,
            name=request.form.get('name'),
            password_hash=generate_password_hash(request.form.get('password'))
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('account'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email')).first()
        if user and check_password_hash(user.password_hash, request.form.get('password')):
            login_user(user)
            return redirect(url_for('account'))
        flash('Invalid credentials', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/account')
@login_required
def account():
    user_bookings = Booking.query.filter_by(user_id=current_user.id).all()
    return render_template('account.html', bookings=user_bookings)

@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    stats = {
        'users': User.query.count(),
        'services': Service.query.count(),
        'gallery': GalleryItem.query.count(),
        'bookings': Booking.query.count(),
        'new_bookings': Booking.query.filter_by(status='new').count()
    }
    recent = Booking.query.order_by(Booking.created_at.desc()).limit(5).all()
    return render_template('dashboard.html', stats=stats, recent=recent)

@app.route('/admin/services')
@login_required
def admin_services():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    return render_template('services_2.html', services=Service.query.order_by(Service.sort_order).all())

@app.route('/admin/services/new', methods=['GET', 'POST'])
@login_required
def admin_service_new():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    if request.method == 'POST':
        s = Service(
            icon=request.form.get('icon'),
            title=request.form.get('title'),
            description=request.form.get('description'),
            features=request.form.get('features'),
            price_label=request.form.get('price_label'),
            badge=request.form.get('badge'),
            featured='featured' in request.form,
            sort_order=int(request.form.get('sort_order', 0))
        )
        db.session.add(s)
        db.session.commit()
        return redirect(url_for('admin_services'))
    return render_template('service_form.html', service=None)

@app.route('/admin/gallery')
@login_required
def admin_gallery():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    return render_template('gallery_2.html', items=GalleryItem.query.order_by(GalleryItem.sort_order).all())

@app.route('/admin/bookings')
@login_required
def admin_bookings():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    return render_template('bookings.html', bookings=Booking.query.order_by(Booking.created_at.desc()).all())

@app.route('/admin/bookings/<int:booking_id>/status', methods=['POST'])
@login_required
def admin_booking_status(booking_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    b = Booking.query.get_or_404(booking_id)
    b.status = request.form.get('status')
    db.session.commit()
    return redirect(url_for('admin_bookings'))

def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(email='admin@thunderstudio.test').first():
            admin = User(
                email='admin@thunderstudio.test',
                name='Admin',
                password_hash=generate_password_hash('admin123'),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()

init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
