import os
from pymongo import MongoClient
import secrets
from flask import Flask, render_template, request, redirect, flash, jsonify, url_for, session
from bson import ObjectId
import hashlib
from flask_mail import Mail, Message
from dotenv import load_dotenv
from functools import wraps
from datetime import datetime
from os.path import join, dirname 

# Load environment variables from .env files
load_dotenv()
dotenv_path = join(dirname(__file__), '.env')


# Create and configure Flask application
app = Flask(__name__)

# Set secret key for Flask app
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(24))

# MongoDB connection string
MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME = os.environ.get("DB_NAME")

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]
collection = db.dbsparta_healthcare
# Email configuration for Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')

def time2str(date):
    """Converts a date to a human-readable relative time format."""
    now = datetime.now()
    time_diff = now - date

    if time_diff.total_seconds() < 60:
        return f"{int(time_diff.total_seconds())} seconds ago"
    elif time_diff.total_seconds() < 3600:
        return f"{int(time_diff.total_seconds() / 60)} minutes ago"
    elif time_diff.total_seconds() < 86400:
        return f"{int(time_diff.total_seconds() / 3600)} hours ago"
    else:
        return date.strftime("%Y-%m-%d %H:%M")

# Initialize Flask-Mail
mail = Mail(app)

# Check admin decorator
def check_admin(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if 'username' in session:
            user = db.user.find_one({"username": session['username']})
            if user and user.get('role') == 'admin':
                return view_func(*args, **kwargs)
            else:
                flash('Unauthorized access', 'error')
                return redirect(url_for('index'))
        return redirect(url_for('login', next=request.url))
    return wrapper

# Check user decorator
def check_user(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if 'username' in session:
            user = db.user.find_one({"username": session['username']})
            if user and user.get('role') == 'user':
                return view_func(*args, **kwargs)
        return redirect(url_for('login', next=request.url))
    return wrapper

@app.route('/profile')
@check_user
def profile():
    username = session['username']
    user = db.user.find_one({"username": username})
    if user:
        profile_name = user.get('profile_name', 'Guest')
        return render_template('profile.html', username=username, profile_name=profile_name)
    else:
        flash('User not found', 'error')
        return redirect(url_for('index'))

# New route for editing profile
@app.route('/profile/edit', methods=['GET', 'POST'])
@check_user
def edit_profile():
    username = session['username']
    user = db.user.find_one({"username": username})
    
    if request.method == 'POST':
        new_username = request.form.get('username')
        new_profile_name = request.form.get('profile_name')
        
        # Validate and update the user data in the database
        if new_username and new_profile_name:
            update_result = db.user.update_one(
                {"username": username},
                {"$set": {"username": new_username, "profile_name": new_profile_name}}
            )
            
            if update_result.modified_count > 0:
                flash('Profile updated successfully', 'success')
                # Update session username if it has changed
                session['username'] = new_username
                return redirect(url_for('profile'))
            else:
                flash('Failed to update profile', 'error')
        
    return render_template('edit_profile.html', username=username, profile_name=user.get('profile_name', 'Guest'))
# Route for the homepage
@app.route('/')
@check_user
def index():
    berita_data = list(db.berita.find({}))
    for berita_item in berita_data:
        berita_item['time_str'] = time2str(berita_item['time'])
    return render_template('index.html', berita=berita_data)

@app.route('/index')
@check_user
def home():
    berita_data = list(db.berita.find({}))
    for berita_item in berita_data:
        berita_item['time_str'] = time2str(berita_item['time'])
    return render_template('index.html', berita=berita_data)

@app.route('/berita', methods=['GET'])
@check_admin
def berita():
    berita_data = list(db.berita.find({}))
    for berita_item in berita_data:
        berita_item['time_str'] = time2str(berita_item['time'])
    return render_template('berita.html', berita=berita_data)

@app.route('/addBerita', methods=['GET', 'POST'])
@check_admin
def addberita():
    if request.method == 'POST':
        nama = request.form['nama']
        deskripsi = request.form['deskripsi']
        gambar = request.files['gambar']
        
        if gambar:
            namaGambarAsli = gambar.filename
            namafileGambar = namaGambarAsli.split('/')[-1]
            file_path = f'static/imgGambar/{namafileGambar}'
            gambar.save(file_path)
        else:
            namafileGambar = None
            
        doc = {
            'nama': nama,
            'deskripsi': deskripsi,
            'gambar': namafileGambar,
            'time': datetime.now()  # Tambahkan waktu saat ini
        }
        
        db.berita.insert_one(doc)
        return redirect(url_for("berita"))
    
    return render_template('AddBerita.html')

@app.route('/editBerita/<string:_id>', methods=['GET', 'POST'])
@check_admin
def editberita(_id):
    if request.method == 'POST':
        form_id = request.form['_id']
        nama = request.form['nama']
        deskripsi = request.form['deskripsi']
        uploaded_gambar = request.files['gambar']
        
        doc = {
            'nama': nama,
            'deskripsi': deskripsi,
        }
        
        if uploaded_gambar:
            try:
                namaGambarAsli = uploaded_gambar.filename
                namafileGambar = namaGambarAsli.split('/')[-1]
                file_path = f'static/imgGambar/{namafileGambar}'
                
                # Pastikan direktori tempat menyimpan file ada
                if not os.path.exists('static/imgGambar'):
                    os.makedirs('static/imgGambar')
                
                uploaded_gambar.save(file_path)
                doc['gambar'] = namafileGambar
            except Exception as e:
                return f"Error saving file: {str(e)}", 500  # Tanggapi jika terjadi kesalahan saat menyimpan file
        
        try:
            db.berita.update_one({"_id": ObjectId(form_id)}, {"$set": doc})
            return redirect(url_for("berita"))
        except Exception as e:
            return f"Error updating database: {str(e)}", 500  # Tanggapi jika terjadi kesalahan saat memperbarui basis data
    
    # Ambil data dari MongoDB berdasarkan _id
    data = db.berita.find_one({"_id": ObjectId(_id)})
    if not data:
        return "Data not found", 404  # Tanggapi jika data tidak ditemukan
    
    return render_template('Editberita.html', data=data)


@app.route('/delete/<string:_id>', methods=['GET'])
@check_admin
def delete(_id):
    db.berita.delete_one({"_id": ObjectId(_id)})
    return redirect(url_for("berita"))



@app.route('/about')
@check_user
def about():
    return render_template("about.html")

@app.route('/service')
@check_user
def service():
    return render_template("service.html")

# Route for the login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Example login validation
        user = db.user.find_one({"username": username})
        if user and user['password'] == hashlib.sha256(password.encode('utf-8')).hexdigest():
            session['username'] = username
            return jsonify({"result": "success", "role": user['role']})
        else:
            return jsonify({"result": "fail", "msg": "Username or password is incorrect"})
    else:
        return render_template('login.html')

# Route for the sign-in endpoint
@app.route("/sign_in", methods=["POST"])
def sign_in():
    username_receive = request.form["username_give"]
    password_receive = request.form["password_give"]
    pw_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()
    
    result = db.user.find_one(
        {
            "username": username_receive,
            "password": pw_hash,
        }
    )
    
    if result:
        session['username'] = username_receive
        return jsonify({"result": "success", "role": result['role']})
    else:
        return jsonify({"result": "fail", "msg": "Username or password is incorrect"})

# Route for the logout
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

# Route for the appointment page
@app.route('/appointment')
@check_user
def appointment():
    return render_template('appointment.html')

# Route for handling user registration (sign up)
@app.route("/sign_up/save", methods=["POST"])
def sign_up():
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']
    role_receive = request.form['role_give']
    
    password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    doc = {
        "username": username_receive,
        "password": password_hash,
        "profile_name": username_receive,
        "profile_info": "",
        "role": role_receive
    }
    
    db.user.insert_one(doc)
    return jsonify({'result': 'success'})

# Endpoint to check for duplicate username during registration
@app.route("/sign_up/check_dup", methods=["POST"])
def check_dup():
    username_receive = request.form["username_give"]
    
    # Check if the username already exists in the database
    existing_user = db.user.find_one({"username": username_receive})
    
    if existing_user:
        return jsonify({"exists": True, "msg": "Username sudah digunakan."})
    else:
        return jsonify({"exists": False, "msg": "Username tersedia untuk digunakan!"})

# Route for the admin dashboard
@app.route("/admin")
@check_admin
def admin():
    return render_template("dashboard.html")

@app.route('/schedule_appointment', methods=['POST'])
def schedule_appointment():
    # Retrieve form data
    nama = request.form['nama']
    phone = request.form['phone']
    consultation_type = request.form['consultation_type']
    discussion_topic = request.form['discussion_topic']
    date = request.form['date']
    time = request.form['time']
    
    # Create a document to insert into MongoDB
    konsultasi = {
        'nama': nama,
        'phone': phone,
        'consultation_type': consultation_type,
        'discussion_topic': discussion_topic,
        'date': date,
        'time': time,
        'timestamp': datetime.now()
    }
    
    # Insert the document into the 'konsultasi' collection
    db.konsultasi.insert_one(konsultasi)
    
    # Flash a success message
    flash('Jadwal konsultasi berhasil dikirim!', 'success')
    
    # Prepare the appointment details to be rendered on the same page
    appointment = {
        'nama': nama,
        'phone': phone,
        'consultation_type': consultation_type,
        'discussion_topic': discussion_topic,
        'date': date,
        'time': time
    }
    
    # Render the appointment page with appointment details
    return render_template('appointment.html', appointment=appointment)

@app.route('/consultations', methods=['GET'])
@check_admin
def consultations():
    consultations_data = list(db.konsultasi.find({}))
    for consultation in consultations_data:
        consultation['time_str'] = time2str(consultation['timestamp'])
    return render_template('jadwal_konsultasi.html', consultations=consultations_data)

@app.route('/delete_consultation/<consultation_id>', methods=['POST'])
@check_admin
def delete_consultation(consultation_id):
    db.konsultasi.delete_one({'_id': ObjectId(consultation_id)})
    flash('Consultation schedule deleted successfully!', 'success')
    return redirect('/consultations')

@app.route('/article_detail/<article_id>')
@check_user
def article_detail(article_id):
    article = db.berita.find_one({"_id": ObjectId(article_id)})
    if not article:
        return "Article not found", 404
    return render_template('article_detail.html', article=article)

@app.route('/pages')
@check_user
def pages():
    berita_data = list(db.berita.find({}))
    for berita_item in berita_data:
        berita_item['time_str'] = time2str(berita_item['time'])
    return render_template('pojokbaca.html', berita=berita_data)

@app.route('/messages', methods=['GET'])
@check_admin
def messages():
    messages_data = list(db.messages.find({}))
    for message in messages_data:
        message['time_str'] = time2str(message['time'])
    return render_template('message.html', messages=messages_data)

# Endpoint to handle sending email from contact form
@app.route('/send_email', methods=['POST'])
@check_user
def send_email():
    name = request.form['name']
    email = request.form['email']
    subject = request.form['subject']
    message = request.form['message']
    
    doc = {
        'name': name,
        'email': email,
        'subject': subject,
        'message': message,
        'time': datetime.now()
    }
    db.messages.insert_one(doc)

    msg = Message(subject=subject, sender=email, recipients=['dengarmama@gmail.com'])
    msg.body = f'Name: {name}\nEmail: {email}\n\n{message}'

    try:
        mail.send(msg)
        flash('Email berhasil dikirim!', 'success')
    except Exception as e:
        flash('Terjadi kesalahan saat mengirim email: ' + str(e), 'danger')

    return redirect('/contact')

@app.route('/recent-articles', methods=['GET'])
def recent_articles():
    berita_data = list(db.berita.find({}))
    sorted_berita_data = sorted(berita_data, key=lambda x: x['time'], reverse=True)
    for berita_item in sorted_berita_data:
        berita_item['time_str'] = time2str(berita_item['time'])
    
    return render_template('pojokbaca.html', berita=sorted_berita_data)

# Route for the contact page
@app.route('/contact')
@check_user
def contact():
    return render_template('contact.html')

# Main entry point of the application
if __name__ == "__main__":
    app.run("0.0.0.0", port=5000, debug=True)
