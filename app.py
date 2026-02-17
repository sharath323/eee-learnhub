from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import os
from threading import Lock
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'change-this-secret-key')

# ==================== DATABASE SETUP ====================

basedir = os.path.abspath(os.path.dirname(__file__))
db_dir = os.path.join(basedir, 'instance')
os.makedirs(db_dir, exist_ok=True)
database_url = os.getenv('DATABASE_URL', '').strip()
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
if database_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(db_dir, 'eee_learnhub.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'uploads', 'notes')
app.config['INTERVIEW_UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'uploads', 'interview')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

db = SQLAlchemy(app)
db_init_lock = Lock()
db_bootstrapped = False

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['INTERVIEW_UPLOAD_FOLDER'], exist_ok=True)


# ==================== MODELS ====================

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

    topics = db.relationship('Topic', backref='subject', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Subject {self.name}>'


class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)

    videos = db.relationship('Video', backref='topic', lazy=True, cascade='all, delete-orphan')
    notes = db.relationship('Note', backref='topic', lazy=True, cascade='all, delete-orphan')
    questions = db.relationship('Question', backref='topic', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Topic {self.name}>'


class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    youtube_id = db.Column(db.String(50), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=False)

    def __repr__(self):
        return f'<Video {self.title}>'


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    file_path = db.Column(db.String(300), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=False)

    def __repr__(self):
        return f'<Note {self.title}>'


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(300), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=False)

    def __repr__(self):
        return f'<Question {self.text[:30]}>'


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(200), nullable=False)
    last_seen_admin_message_id = db.Column(db.Integer, nullable=False, default=0)

    def __repr__(self):
        return f'<User {self.email}>'


class TopicCompletion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=False)


class VideoCompletion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'), nullable=False)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user_name = db.Column(db.String(100), nullable=False)
    user_email = db.Column(db.String(120), nullable=False)
    text = db.Column(db.String(500), nullable=False)
    sender = db.Column(db.String(20), nullable=False, default='student')


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.String(800), nullable=False)


class NotificationRead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    notification_id = db.Column(db.Integer, db.ForeignKey('notification.id'), nullable=False)


class InterviewPrep(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.String(1200), nullable=False)
    pdf_path = db.Column(db.String(300), nullable=True)


# ==================== SEED DATA ====================

def seed_data():
    if Subject.query.first():
        return

    subjects_data = [
        {
            "name": "Power Systems",
            "topics": [
                {
                    "name": "Generation of Power",
                    "videos": [
                        {"title": "Power Generation Basics", "youtube_id": "x3kDqKClUS4"},
                        {"title": "Thermal Power Plants", "youtube_id": "1J5j4Qy2F8Q"},
                    ],
                    "notes": [
                        {"title": "Generation of Power - PDF", "file_path": ""},
                    ],
                    "questions": [
                        "Explain different types of power generation.",
                        "Describe the working of a thermal power plant.",
                    ],
                },
                {
                    "name": "Transmission Lines",
                    "videos": [
                        {"title": "Transmission Line Parameters", "youtube_id": "8H0x8pQW8jM"},
                    ],
                    "notes": [
                        {"title": "Transmission Lines - PDF", "file_path": ""},
                    ],
                    "questions": [
                        "Define line constants and their significance.",
                        "Explain the concept of surge impedance.",
                    ],
                },
                {
                    "name": "Distribution Systems",
                    "videos": [
                        {"title": "Distribution System Overview", "youtube_id": "uSGYqS8JfX4"},
                    ],
                    "notes": [
                        {"title": "Distribution Systems - PDF", "file_path": ""},
                    ],
                    "questions": [
                        "List types of distribution systems.",
                        "Explain feeder, distributor, and service mains.",
                    ],
                },
            ],
        },
        {
            "name": "Electrical Machines",
            "topics": [
                {
                    "name": "DC Machines",
                    "videos": [
                        {"title": "DC Machine Basics", "youtube_id": "5nq7eR2c0xw"},
                    ],
                    "notes": [
                        {"title": "DC Machines - PDF", "file_path": ""},
                    ],
                    "questions": [
                        "Explain the construction of DC machines.",
                        "Derive the EMF equation of DC generator.",
                    ],
                },
                {
                    "name": "Induction Motors",
                    "videos": [
                        {"title": "Induction Motor Working", "youtube_id": "pq9w8sXHk0I"},
                    ],
                    "notes": [
                        {"title": "Induction Motors - PDF", "file_path": ""},
                    ],
                    "questions": [
                        "Define slip in induction motors.",
                        "Explain torque-slip characteristics.",
                    ],
                },
                {
                    "name": "Synchronous Machines",
                    "videos": [
                        {"title": "Synchronous Generator Basics", "youtube_id": "m9qJk9Q8o4A"},
                    ],
                    "notes": [
                        {"title": "Synchronous Machines - PDF", "file_path": ""},
                    ],
                    "questions": [
                        "Explain alternator construction.",
                        "Define voltage regulation of alternators.",
                    ],
                },
            ],
        },
        {
            "name": "Control Systems",
            "topics": [
                {
                    "name": "Transfer Function",
                    "videos": [
                        {"title": "Transfer Function Explained", "youtube_id": "o9o0X9z5c4k"},
                    ],
                    "notes": [
                        {"title": "Transfer Function - PDF", "file_path": ""},
                    ],
                    "questions": [
                        "Define transfer function.",
                        "Obtain transfer function of a simple system.",
                    ],
                },
                {
                    "name": "Time Response",
                    "videos": [
                        {"title": "Time Response of Systems", "youtube_id": "Kp1mE2b4cXg"},
                    ],
                    "notes": [
                        {"title": "Time Response - PDF", "file_path": ""},
                    ],
                    "questions": [
                        "Explain transient and steady-state response.",
                        "Define overshoot and settling time.",
                    ],
                },
                {
                    "name": "Stability Analysis",
                    "videos": [
                        {"title": "Stability Analysis Basics", "youtube_id": "u9vV9qg7y2E"},
                    ],
                    "notes": [
                        {"title": "Stability Analysis - PDF", "file_path": ""},
                    ],
                    "questions": [
                        "Explain Routh-Hurwitz criterion.",
                        "What is relative stability?",
                    ],
                },
            ],
        },
        {
            "name": "Signals & Systems",
            "topics": [
                {
                    "name": "Signal Classification",
                    "videos": [
                        {"title": "Signal Classification", "youtube_id": "S0v4n5m1t7Y"},
                    ],
                    "notes": [
                        {"title": "Signals - PDF", "file_path": ""},
                    ],
                    "questions": [
                        "Differentiate between continuous and discrete signals.",
                        "Explain energy and power signals.",
                    ],
                },
                {
                    "name": "LTI Systems",
                    "videos": [
                        {"title": "LTI System Properties", "youtube_id": "7q2r8Z1eVd0"},
                    ],
                    "notes": [
                        {"title": "LTI Systems - PDF", "file_path": ""},
                    ],
                    "questions": [
                        "Define LTI system.",
                        "Explain convolution in time domain.",
                    ],
                },
                {
                    "name": "Fourier Series",
                    "videos": [
                        {"title": "Fourier Series Basics", "youtube_id": "V3F3hS3F1F4"},
                    ],
                    "notes": [
                        {"title": "Fourier Series - PDF", "file_path": ""},
                    ],
                    "questions": [
                        "Write the trigonometric Fourier series.",
                        "Explain convergence of Fourier series.",
                    ],
                },
            ],
        },
        {
            "name": "Power Electronics",
            "topics": [
                {
                    "name": "Power Semiconductor Devices",
                    "videos": [
                        {"title": "Power Devices Overview", "youtube_id": "FQj8n9s2g6o"},
                    ],
                    "notes": [
                        {"title": "Power Devices - PDF", "file_path": ""},
                    ],
                    "questions": [
                        "Compare SCR, MOSFET, and IGBT.",
                        "Explain SCR characteristics.",
                    ],
                },
                {
                    "name": "DC-DC Converters",
                    "videos": [
                        {"title": "Buck and Boost Converters", "youtube_id": "2qBz8y3mH7w"},
                    ],
                    "notes": [
                        {"title": "DC-DC Converters - PDF", "file_path": ""},
                    ],
                    "questions": [
                        "Explain working of buck converter.",
                        "Explain working of boost converter.",
                    ],
                },
                {
                    "name": "Inverters",
                    "videos": [
                        {"title": "Single Phase Inverter", "youtube_id": "g4pF9t6c1nM"},
                    ],
                    "notes": [
                        {"title": "Inverters - PDF", "file_path": ""},
                    ],
                    "questions": [
                        "What is an inverter?",
                        "Explain PWM techniques.",
                    ],
                },
            ],
        },
    ]

    for subject_data in subjects_data:
        subject = Subject(name=subject_data["name"])
        db.session.add(subject)
        db.session.flush()

        for topic_data in subject_data["topics"]:
            topic = Topic(name=topic_data["name"], subject_id=subject.id)
            db.session.add(topic)
            db.session.flush()

            for video_data in topic_data["videos"]:
                video = Video(
                    title=video_data["title"],
                    youtube_id=video_data["youtube_id"],
                    topic_id=topic.id
                )
                db.session.add(video)

            for note_data in topic_data["notes"]:
                note = Note(
                    title=note_data["title"],
                    file_path=note_data["file_path"],
                    topic_id=topic.id
                )
                db.session.add(note)

            for question_text in topic_data["questions"]:
                question = Question(
                    text=question_text,
                    topic_id=topic.id
                )
                db.session.add(question)

    db.session.commit()


def ensure_database_initialized():
    global db_bootstrapped
    if db_bootstrapped:
        return

    with db_init_lock:
        if db_bootstrapped:
            return
        try:
            with app.app_context():
                db.create_all()
                seed_data()
            db_bootstrapped = True
        except Exception:
            app.logger.exception('Database initialization failed')


# ==================== AUTH HELPERS ====================

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin123'


def is_admin_logged_in():
    return session.get('is_admin') is True


def is_user_logged_in():
    return session.get('user_id') is not None


def require_admin():
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    return None


def get_unread_count(user_id):
    total = Notification.query.count()
    read_count = NotificationRead.query.filter_by(user_id=user_id).count()
    return max(total - read_count, 0)


def get_unread_admin_replies_count(user_id):
    user = User.query.get(user_id)
    if not user:
        return 0
    latest_admin_msg = Message.query.filter_by(user_id=user_id, sender='admin').order_by(Message.id.desc()).first()
    if not latest_admin_msg:
        return 0
    return 1 if latest_admin_msg.id > (user.last_seen_admin_message_id or 0) else 0


# ==================== ROUTES ====================

@app.before_request
def bootstrap_database():
    ensure_database_initialized()


@app.route('/health')
def health():
    return {'status': 'ok'}, 200


@app.route('/')
def index():
    return render_template('login.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            return redirect(url_for('dashboard'))
        return render_template('login.html', error='Invalid email or password')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        if not name or not email or not password:
            return render_template('register.html', error='All fields are required')

        existing = User.query.filter_by(email=email).first()
        if existing:
            return render_template('register.html', error='Email already registered')

        user = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    return redirect(url_for('login'))


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if not is_user_logged_in():
        return redirect(url_for('login'))

    user = User.query.get_or_404(session['user_id'])
    message = None

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        new_password = request.form.get('password', '').strip()

        if name:
            user.name = name
            session['user_name'] = name

        if new_password:
            user.password_hash = generate_password_hash(new_password)

        db.session.commit()
        message = 'Profile updated successfully'

    return render_template('profile.html', user=user, message=message)


@app.route('/notifications')
def notifications():
    if not is_user_logged_in():
        return redirect(url_for('login'))

    user_id = session['user_id']
    items = Notification.query.order_by(Notification.id.desc()).all()

    existing_reads = NotificationRead.query.filter_by(user_id=user_id).all()
    read_ids = {r.notification_id for r in existing_reads}
    for n in items:
        if n.id not in read_ids:
            db.session.add(NotificationRead(user_id=user_id, notification_id=n.id))
    db.session.commit()

    return render_template('notifications.html', notifications=items)


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if not is_user_logged_in():
        return redirect(url_for('login'))

    user = User.query.get_or_404(session['user_id'])
    message = None
    user_messages = Message.query.filter_by(user_id=user.id).order_by(Message.id.desc()).all()
    latest_admin_msg = Message.query.filter_by(user_id=user.id, sender='admin').order_by(Message.id.desc()).first()

    if request.method == 'POST':
        text = request.form.get('message', '').strip()
        if text:
            db.session.add(Message(
                user_id=user.id,
                user_name=user.name,
                user_email=user.email,
                text=text,
                sender='student'
            ))
            db.session.commit()
            message = 'Message sent to admin'

    if latest_admin_msg and latest_admin_msg.id > (user.last_seen_admin_message_id or 0):
        user.last_seen_admin_message_id = latest_admin_msg.id
        db.session.commit()

    unread_count = get_unread_count(user.id)
    return render_template('contact.html', message=message, messages=user_messages, unread_count=unread_count)


@app.route('/dashboard')
def dashboard():
    if not is_user_logged_in():
        return redirect(url_for('login'))
    subjects = Subject.query.order_by(Subject.name).all()
    user_id = session['user_id']
    unread_count = get_unread_count(user_id)
    admin_reply_unread = get_unread_admin_replies_count(user_id)
    completed_videos = VideoCompletion.query.filter_by(user_id=user_id).all()
    completed_video_ids = {c.video_id for c in completed_videos}

    progress = {}
    for subject in subjects:
        topics = Topic.query.filter_by(subject_id=subject.id).all()
        total_videos = 0
        completed_count = 0
        for topic in topics:
            videos = Video.query.filter_by(topic_id=topic.id).all()
            total_videos += len(videos)
            completed_count += sum(1 for v in videos if v.id in completed_video_ids)
        percent = 0
        if total_videos > 0:
            percent = int((completed_count / total_videos) * 100)
        progress[subject.id] = {
            'completed': completed_count,
            'total': total_videos,
            'percent': percent
        }

    return render_template(
        'subjects.html',
        subjects=subjects,
        progress=progress,
        unread_count=unread_count,
        admin_reply_unread=admin_reply_unread
    )


@app.route('/subjects')
def subjects():
    if not is_user_logged_in():
        return redirect(url_for('login'))
    subjects = Subject.query.order_by(Subject.name).all()
    user_id = session['user_id']
    unread_count = get_unread_count(user_id)
    admin_reply_unread = get_unread_admin_replies_count(user_id)
    completed_videos = VideoCompletion.query.filter_by(user_id=user_id).all()
    completed_video_ids = {c.video_id for c in completed_videos}

    progress = {}
    for subject in subjects:
        topics = Topic.query.filter_by(subject_id=subject.id).all()
        total_videos = 0
        completed_count = 0
        for topic in topics:
            videos = Video.query.filter_by(topic_id=topic.id).all()
            total_videos += len(videos)
            completed_count += sum(1 for v in videos if v.id in completed_video_ids)
        percent = 0
        if total_videos > 0:
            percent = int((completed_count / total_videos) * 100)
        progress[subject.id] = {
            'completed': completed_count,
            'total': total_videos,
            'percent': percent
        }

    return render_template(
        'subjects.html',
        subjects=subjects,
        progress=progress,
        unread_count=unread_count,
        admin_reply_unread=admin_reply_unread
    )


@app.route('/subjects/<int:subject_id>/topics')
def topics(subject_id):
    if not is_user_logged_in():
        return redirect(url_for('login'))
    subject = Subject.query.get_or_404(subject_id)
    topic_list = Topic.query.filter_by(subject_id=subject_id).order_by(Topic.name).all()
    user_id = session['user_id']
    unread_count = get_unread_count(user_id)
    admin_reply_unread = get_unread_admin_replies_count(user_id)
    completed_videos = VideoCompletion.query.filter_by(user_id=user_id).all()
    completed_video_ids = {c.video_id for c in completed_videos}
    topic_progress = {}
    for topic in topic_list:
        videos = Video.query.filter_by(topic_id=topic.id).all()
        total_videos = len(videos)
        completed_count = sum(1 for v in videos if v.id in completed_video_ids)
        topic_progress[topic.id] = {
            'completed': completed_count,
            'total': total_videos,
            'done': total_videos > 0 and completed_count == total_videos
        }
    return render_template(
        'topics.html',
        subject=subject,
        topics=topic_list,
        topic_progress=topic_progress,
        unread_count=unread_count,
        admin_reply_unread=admin_reply_unread
    )


@app.route('/topics/<int:topic_id>/learning')
def learning(topic_id):
    if not is_user_logged_in():
        return redirect(url_for('login'))
    topic = Topic.query.get_or_404(topic_id)
    videos = Video.query.filter_by(topic_id=topic_id).all()
    notes = Note.query.filter_by(topic_id=topic_id).all()
    questions = Question.query.filter_by(topic_id=topic_id).all()
    user_id = session['user_id']
    unread_count = get_unread_count(user_id)
    admin_reply_unread = get_unread_admin_replies_count(user_id)
    completed_videos = VideoCompletion.query.filter_by(user_id=user_id).all()
    completed_video_ids = {c.video_id for c in completed_videos}
    topic_completed = len(videos) > 0 and all(v.id in completed_video_ids for v in videos)
    return render_template(
        'learning.html',
        topic=topic,
        videos=videos,
        notes=notes,
        questions=questions,
        completed_video_ids=completed_video_ids,
        topic_completed=topic_completed,
        unread_count=unread_count,
        admin_reply_unread=admin_reply_unread
    )


@app.route('/topics/<int:topic_id>/complete', methods=['POST'])
def complete_topic(topic_id):
    if not is_user_logged_in():
        return redirect(url_for('login'))

    user_id = session['user_id']
    existing = TopicCompletion.query.filter_by(user_id=user_id, topic_id=topic_id).first()
    if not existing:
        db.session.add(TopicCompletion(user_id=user_id, topic_id=topic_id))
        db.session.commit()
    return redirect(url_for('learning', topic_id=topic_id))


@app.route('/videos/<int:video_id>/complete', methods=['POST'])
def complete_video(video_id):
    if not is_user_logged_in():
        return redirect(url_for('login'))

    user_id = session['user_id']
    existing = VideoCompletion.query.filter_by(user_id=user_id, video_id=video_id).first()
    if not existing:
        db.session.add(VideoCompletion(user_id=user_id, video_id=video_id))
        db.session.commit()
    return redirect(request.referrer or url_for('subjects'))


@app.route('/videos/<int:video_id>/uncomplete', methods=['POST'])
def uncomplete_video(video_id):
    if not is_user_logged_in():
        return redirect(url_for('login'))

    user_id = session['user_id']
    VideoCompletion.query.filter_by(user_id=user_id, video_id=video_id).delete()
    db.session.commit()
    return redirect(request.referrer or url_for('subjects'))


@app.route('/subjects/<int:subject_id>/interview')
def interview(subject_id):
    if not is_user_logged_in():
        return redirect(url_for('login'))
    subject = Subject.query.get_or_404(subject_id)
    items = InterviewPrep.query.filter_by(subject_id=subject_id).order_by(InterviewPrep.id.desc()).all()
    user_id = session['user_id']
    unread_count = get_unread_count(user_id)
    return render_template('interview_prep.html', subject=subject, items=items, unread_count=unread_count)


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    guard = require_admin()
    if guard:
        return guard
    if request.method == 'POST':
        form_type = request.form.get('form_type')

        if form_type == 'subject':
            name = request.form.get('subject_name', '').strip()
            if name:
                db.session.add(Subject(name=name))
                db.session.commit()
            return redirect(url_for('admin'))

        if form_type == 'topic':
            name = request.form.get('topic_name', '').strip()
            subject_id = request.form.get('subject_id')
            if name and subject_id:
                db.session.add(Topic(name=name, subject_id=int(subject_id)))
                db.session.commit()
            return redirect(url_for('admin'))

        if form_type == 'video':
            title = request.form.get('video_title', '').strip()
            youtube_id = request.form.get('youtube_id', '').strip()
            topic_id = request.form.get('topic_id')
            if title and youtube_id and topic_id:
                db.session.add(Video(title=title, youtube_id=youtube_id, topic_id=int(topic_id)))
                db.session.commit()
            return redirect(url_for('admin'))

        if form_type == 'note':
            title = request.form.get('note_title', '').strip()
            topic_id = request.form.get('topic_id')
            file = request.files.get('note_file')

            if title and topic_id and file and file.filename.lower().endswith('.pdf'):
                filename = secure_filename(file.filename)
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(save_path)

                relative_path = os.path.join('uploads', 'notes', filename).replace('\\', '/')
                db.session.add(Note(title=title, file_path=relative_path, topic_id=int(topic_id)))
                db.session.commit()

            return redirect(url_for('admin'))

        if form_type == 'question':
            text = request.form.get('question_text', '').strip()
            topic_id = request.form.get('topic_id')
            if text and topic_id:
                db.session.add(Question(text=text, topic_id=int(topic_id)))
                db.session.commit()
            return redirect(url_for('admin'))

        if form_type == 'notification':
            title = request.form.get('notification_title', '').strip()
            body = request.form.get('notification_body', '').strip()
            if title and body:
                db.session.add(Notification(title=title, body=body))
                db.session.commit()
            return redirect(url_for('admin'))

        if form_type == 'interview':
            subject_id = request.form.get('subject_id')
            title = request.form.get('interview_title', '').strip()
            content = request.form.get('interview_content', '').strip()
            file = request.files.get('interview_file')
            pdf_path = None

            if file and file.filename.lower().endswith('.pdf'):
                filename = secure_filename(file.filename)
                save_path = os.path.join(app.config['INTERVIEW_UPLOAD_FOLDER'], filename)
                file.save(save_path)
                pdf_path = os.path.join('uploads', 'interview', filename).replace('\\', '/')

            if subject_id and title and content:
                db.session.add(InterviewPrep(
                    subject_id=int(subject_id),
                    title=title,
                    content=content,
                    pdf_path=pdf_path
                ))
                db.session.commit()
            return redirect(url_for('admin'))

    subjects = Subject.query.order_by(Subject.id).all()
    topics = Topic.query.order_by(Topic.id).all()
    videos = Video.query.order_by(Video.id).all()
    notes = Note.query.order_by(Note.id).all()
    questions = Question.query.order_by(Question.id).all()
    messages = Message.query.order_by(Message.id.desc()).all()
    students = User.query.order_by(User.name).all()
    notifications = Notification.query.order_by(Notification.id.desc()).all()
    interviews = InterviewPrep.query.order_by(InterviewPrep.id.desc()).all()
    messages_by_user = {}
    admin_seen = session.get('admin_seen_msgs', {})
    for msg in messages:
        if msg.user_email not in messages_by_user:
            messages_by_user[msg.user_email] = {
                'user_id': msg.user_id,
                'name': msg.user_name,
                'email': msg.user_email,
                'messages': [],
                'new': False,
                'latest_student_id': 0
            }
        messages_by_user[msg.user_email]['messages'].append(msg)
        if msg.sender == 'student' and msg.id > messages_by_user[msg.user_email]['latest_student_id']:
            messages_by_user[msg.user_email]['latest_student_id'] = msg.id

    # Mark "new" per student based on last seen id stored in session
    for thread in messages_by_user.values():
        last_seen = int(admin_seen.get(str(thread['user_id']), 0))
        if thread['latest_student_id'] > last_seen:
            thread['new'] = True
    response = render_template(
        'admin.html',
        subjects=subjects,
        topics=topics,
        videos=videos,
        notes=notes,
        questions=questions,
        messages=messages,
        messages_by_user=messages_by_user,
        students=students,
        notifications=notifications,
        interviews=interviews,
        admin_unread_msg=any(t['new'] for t in messages_by_user.values())
    )
    # Update session seen ids after viewing
    for thread in messages_by_user.values():
        if thread['latest_student_id'] > 0:
            admin_seen[str(thread['user_id'])] = thread['latest_student_id']
    session['admin_seen_msgs'] = admin_seen
    return response


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect(url_for('admin'))
        return render_template('admin_login.html', error='Invalid admin credentials')
    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect(url_for('admin_login'))


@app.route('/admin/messages/<int:user_id>/reply', methods=['POST'])
def admin_reply(user_id):
    guard = require_admin()
    if guard:
        return guard
    user = User.query.get_or_404(user_id)
    text = request.form.get('reply_text', '').strip()
    if text:
        db.session.add(Message(
            user_id=user.id,
            user_name=user.name,
            user_email=user.email,
            text=text,
            sender='admin'
        ))
        db.session.commit()
    return redirect(url_for('admin'))


@app.route('/admin/messages/<int:user_id>/mark_read', methods=['POST'])
def admin_mark_read(user_id):
    guard = require_admin()
    if guard:
        return guard
    latest_student = Message.query.filter_by(user_id=user_id, sender='student').order_by(Message.id.desc()).first()
    if latest_student:
        admin_seen = session.get('admin_seen_msgs', {})
        admin_seen[str(user_id)] = latest_student.id
        session['admin_seen_msgs'] = admin_seen
    return ('', 204)


@app.route('/admin/notifications/<int:notification_id>/edit', methods=['POST'])
def edit_notification(notification_id):
    guard = require_admin()
    if guard:
        return guard
    notification = Notification.query.get_or_404(notification_id)
    title = request.form.get('notification_title', '').strip()
    body = request.form.get('notification_body', '').strip()
    if title:
        notification.title = title
    if body:
        notification.body = body
    db.session.commit()
    return redirect(url_for('admin'))


@app.route('/admin/notifications/<int:notification_id>/delete', methods=['POST'])
def delete_notification(notification_id):
    guard = require_admin()
    if guard:
        return guard
    notification = Notification.query.get_or_404(notification_id)
    NotificationRead.query.filter_by(notification_id=notification.id).delete()
    db.session.delete(notification)
    db.session.commit()
    return redirect(url_for('admin'))


@app.route('/admin/interview/<int:interview_id>/edit', methods=['POST'])
def edit_interview(interview_id):
    guard = require_admin()
    if guard:
        return guard
    interview = InterviewPrep.query.get_or_404(interview_id)
    title = request.form.get('interview_title', '').strip()
    content = request.form.get('interview_content', '').strip()
    file = request.files.get('interview_file')

    if title:
        interview.title = title
    if content:
        interview.content = content

    if file and file.filename.lower().endswith('.pdf'):
        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config['INTERVIEW_UPLOAD_FOLDER'], filename)
        file.save(save_path)
        interview.pdf_path = os.path.join('uploads', 'interview', filename).replace('\\', '/')

    db.session.commit()
    return redirect(url_for('admin'))


@app.route('/admin/interview/<int:interview_id>/delete', methods=['POST'])
def delete_interview(interview_id):
    guard = require_admin()
    if guard:
        return guard
    interview = InterviewPrep.query.get_or_404(interview_id)
    if interview.pdf_path:
        file_to_remove = os.path.join(app.static_folder, interview.pdf_path)
        if os.path.exists(file_to_remove):
            os.remove(file_to_remove)
    db.session.delete(interview)
    db.session.commit()
    return redirect(url_for('admin'))


@app.route('/admin/subjects/<int:subject_id>/delete', methods=['POST'])
def delete_subject(subject_id):
    guard = require_admin()
    if guard:
        return guard
    subject = Subject.query.get_or_404(subject_id)
    db.session.delete(subject)
    db.session.commit()
    return redirect(url_for('admin'))


@app.route('/admin/subjects/<int:subject_id>/edit', methods=['POST'])
def edit_subject(subject_id):
    guard = require_admin()
    if guard:
        return guard
    subject = Subject.query.get_or_404(subject_id)
    name = request.form.get('subject_name', '').strip()
    if name:
        subject.name = name
        db.session.commit()
    return redirect(url_for('admin'))


@app.route('/admin/topics/<int:topic_id>/delete', methods=['POST'])
def delete_topic(topic_id):
    guard = require_admin()
    if guard:
        return guard
    topic = Topic.query.get_or_404(topic_id)
    db.session.delete(topic)
    db.session.commit()
    return redirect(url_for('admin'))


@app.route('/admin/topics/<int:topic_id>/edit', methods=['POST'])
def edit_topic(topic_id):
    guard = require_admin()
    if guard:
        return guard
    topic = Topic.query.get_or_404(topic_id)
    name = request.form.get('topic_name', '').strip()
    if name:
        topic.name = name
        db.session.commit()
    return redirect(url_for('admin'))


@app.route('/admin/videos/<int:video_id>/delete', methods=['POST'])
def delete_video(video_id):
    guard = require_admin()
    if guard:
        return guard
    video = Video.query.get_or_404(video_id)
    db.session.delete(video)
    db.session.commit()
    return redirect(url_for('admin'))


@app.route('/admin/videos/<int:video_id>/edit', methods=['POST'])
def edit_video(video_id):
    guard = require_admin()
    if guard:
        return guard
    video = Video.query.get_or_404(video_id)
    title = request.form.get('video_title', '').strip()
    youtube_id = request.form.get('youtube_id', '').strip()
    if title:
        video.title = title
    if youtube_id:
        video.youtube_id = youtube_id
    db.session.commit()
    return redirect(url_for('admin'))


@app.route('/admin/notes/<int:note_id>/delete', methods=['POST'])
def delete_note(note_id):
    guard = require_admin()
    if guard:
        return guard
    note = Note.query.get_or_404(note_id)
    if note.file_path:
        file_to_remove = os.path.join(app.static_folder, note.file_path)
        if os.path.exists(file_to_remove):
            os.remove(file_to_remove)
    db.session.delete(note)
    db.session.commit()
    return redirect(url_for('admin'))


@app.route('/admin/notes/<int:note_id>/edit', methods=['POST'])
def edit_note(note_id):
    guard = require_admin()
    if guard:
        return guard
    note = Note.query.get_or_404(note_id)
    title = request.form.get('note_title', '').strip()
    if title:
        note.title = title
        db.session.commit()
    return redirect(url_for('admin'))


@app.route('/admin/questions/<int:question_id>/delete', methods=['POST'])
def delete_question(question_id):
    guard = require_admin()
    if guard:
        return guard
    question = Question.query.get_or_404(question_id)
    db.session.delete(question)
    db.session.commit()
    return redirect(url_for('admin'))


@app.route('/admin/questions/<int:question_id>/edit', methods=['POST'])
def edit_question(question_id):
    guard = require_admin()
    if guard:
        return guard
    question = Question.query.get_or_404(question_id)
    text = request.form.get('question_text', '').strip()
    if text:
        question.text = text
        db.session.commit()
    return redirect(url_for('admin'))


if __name__ == '__main__':
    ensure_database_initialized()
    app.run(debug=True)
