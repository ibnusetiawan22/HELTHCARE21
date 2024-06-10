import os
import secrets
from flask import Flask, render_template, request, redirect, flash
from flask_mail import Mail, Message
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Membuat dan mengkonfigurasi aplikasi Flask
app = Flask(__name__)

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# Jika SECRET_KEY tidak ada di .env, tambahkan
if not app.config['SECRET_KEY']:
    secret_key = secrets.token_hex(24)
    with open('.env', 'a') as file:
        file.write(f'SECRET_KEY={secret_key}\n')
    app.config['SECRET_KEY'] = secret_key
    print('SECRET_KEY has been added to .env file.')

# Menyiapkan konfigurasi email
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')

# Inisialisasi Flask-Mail
mail = Mail(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/send_email', methods=['POST'])
def send_email():
    name = request.form['name']
    email = request.form['email']
    subject = request.form['subject']
    message = request.form['message']

    msg = Message(subject=subject, sender=email, recipients=['dengarmama@gmail.com'])
    msg.body = f'Name: {name}\nEmail: {email}\n\n{message}'

    try:
        mail.send(msg)
        flash('Email berhasil dikirim!', 'success')
    except Exception as e:
        flash(str(e), 'danger')

    return redirect('/contact')

@app.route('/contact')
def contact():
    return render_template('contact.html')

if __name__ == "__main__":
    app.run("0.0.0.0", port=5000, debug=True)