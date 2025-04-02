from flask import Flask, render_template, request, redirect, url_for, session
import gspread
import os
from google.oauth2.service_account import Credentials



app = Flask(__name__)
app.secret_key = 'your-secret-key-here'
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("upvhackathonCreds.json", scopes=scopes)
client = gspread.authorize(creds)

sheet_id = "15P43fHag6Va8upWyhvUJwV0ECbtU4zeMsFp5DiPUXzM"
workbook = client.open_by_key(sheet_id)
sheet = workbook.worksheet("Sheet1")



@app.route('/')
def home():
    return render_template("index.html")
    
    
@app.route('/login', methods=['POST'])
def login():
    user_id = request.form['userID']
    
    
    user_ids = sheet.col_values(1)
    
    if user_id in user_ids:
        session['user_id'] = user_id
        return redirect('/dashboard')
    else:
        return render_template('index.html', error="User ID not found")
        
        
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect ('/')
    return render_template('landingpage.html')
            
    
    
if __name__ == '__main__':
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))