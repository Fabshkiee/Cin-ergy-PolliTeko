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

@app.route('/PiliTugma')
def PiliTugma():
    if 'user_id' not in session:
        return redirect ('/')
    return render_template('PiliTugma.html')
    
    
    
    
@app.route('/quiz')
def quiz():
    try:
        # Get ALL non-empty cells in Column A
        cells = sheet2.range('A2:A')  # Gets all cells from A2 downward
        # Extract non-empty values (skip blank cells)
        options = [cell.value.strip() for cell in cells if cell.value.strip()]
        
        # Define a single question object
        question = {
            'id': 1,
            'text': 'What is the capital of France?',
            'description': 'Choose what applies best',
            'options': options  # Contains all non-empty A column values
        }
        
        # Render a template that matches your new HTML
        return render_template('question.html', question=question)
    
    except Exception as e:
        return f"Error loading quiz: {str(e)}", 500

@app.route('/save-results', methods=['POST'])
def save_results():
    data = request.json
    print("User selected:", data['answers'])
    return jsonify({"status": "success"})
    
if __name__ == '__main__':
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
