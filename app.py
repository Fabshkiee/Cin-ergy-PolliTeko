from flask import Flask, render_template, request, redirect, url_for, session, Blueprint
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
sheet2 = workbook.worksheet("pillars")



@app.route('/')
def home():
    return render_template("index.html")
    
    
@app.route('/login', methods=['POST'])
def login():
    user_id = request.form['userID']
    password = request.form['password']
    all_data = sheet.get_all_values()
    
    
    
    for row in all_data:
        if len(row)>=2:
            if row[0] == user_id and row[1] == password:
                session['user_id'] = user_id
                return redirect('/dashboard')
    return render_template('index.html', error="User ID not found")
        
        
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect ('/')
    return render_template('landingpage.html')
    
    
    
    
@app.route('/quiz')
def quiz():
    try:
        # Get ALL non-empty cells in Column A
        column_a = sheet2.range('A2:A')  # Gets all values in Column A
        options = [column_a.value.strip() for cell in column_a if column_a.value.strip()]
        
        questions = [{
            'id': 1,
            'text': 'What is the capital of France?',
            'options': options  # Now contains all non-empty A column values
        }]
        
        return render_template('pretest.html', questions=questions)
    
    except Exception as e:
        return f"Error loading quiz: {str(e)}", 500

@app.route('/save-results', methods=['POST'])
def save_results():
    data = request.json
    print("User selected:", data['answers'])
    return jsonify({"status": "success"})
    
if __name__ == '__main__':
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
