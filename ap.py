from flask import Flask, render_template, request, redirect, session
import gspread
import os
from google.oauth2.service_account import Credentials

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Required for session management

# Configure Google Sheets
try:
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(
        "/storage/emulated/0/UOV HACK/upvhackathonCreds.json", 
        scopes=scopes
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key("15P43fHag6Va8upWyhvUJwV0ECbtU4zeMsFp5DiPUXzM").worksheet("Sheet1")
except Exception as e:
    print(f"Google Sheets initialization error: {str(e)}")
    sheet = None

@app.route('/')
def home():
    return render_template("index.html")
    
@app.route('/login', methods=['POST'])
def login():
    if not sheet:
        return render_template('index.html', error="Server configuration error")
    
    try:
        user_id = request.form['userID']
        user_ids = sheet.col_values(1)
        
        if user_id in user_ids:
            session['user_id'] = user_id
            return redirect('/dashboard')
        return render_template('index.html', error="User ID not found")
    
    except Exception as e:
        print(f"Login error: {str(e)}")
        return render_template('index.html', error="Server error occurred")

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')
    return f"Welcome user #{session['user_id']}!"

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))