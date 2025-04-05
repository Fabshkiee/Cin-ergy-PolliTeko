from flask import Flask, render_template, jsonify, request, redirect, url_for, session, Blueprint
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
sheet = workbook.worksheet("logIn")
sheet2 = workbook.worksheet("pillars")
candidatesSheet = workbook.worksheet("candidates")
educationsSheet = workbook.worksheet("education")
leadershipsSheet = workbook.worksheet("leadership")
achievementsSheet = workbook.worksheet("achievement")
#candidatesSheet = client.open("candidates").sheet1



@app.route('/')
def home():
    return render_template("index.html")
    
    
@app.route('/login', methods=['POST'])
def login():
    user_id = request.form['userID']
    password = request.form['password']
    all_data = sheet.get_all_values()
    
    # Check for admin credentials first
    for row in all_data:
        if len(row) >= 3:  # Check all 3 columns exist
            if row[0] == user_id and row[1] == password:
                session['user_id'] = user_id
                session['is_admin'] = (row[2].lower() == 'true' or row[2] == '1')
                
                if session['is_admin']:
                    return redirect('/admin-dashboard')
                else:
                    return redirect('/dashboard')

# If no matching user was found, show error
    return render_template('index.html', error="Invalid ID or password")
        

@app.route('/admin-dashboard')
def admin_dashboard():
    if 'user_id' not in session or not session.get('is_admin', False):
        return redirect('/')
    return render_template('addCandidate.html')

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
        
        


@app.route('/adminAddCandi')
def addCandi():
    return render_template('addCandidate.html')
        
        
@app.route("/submitAddCandidate", methods=["POST"])
def submit():
    try:
        data = request.json

        # Get the next available row (starts from Row 2 if empty, otherwise appends)
        next_row = len(candidatesSheet.get_all_values()) + 1

        # ===== 1. Write to CANDIDATES sheet =====
        candidates_data = {
            "A": data.get("FirstName", ""),       # Column 1
            "B": data.get("MiddleName", ""),      # Column 2
            "C": data.get("LastName", ""),        # Column 3
            "D": data.get("region", ""),          # Column 4
            "E": data.get("province", ""),        # Column 5
            "F": data.get("city", ""),            # Column 6
            "G": data.get("biography", ""),       # Column 7
            "H": data.get("bday", ""),            # Column 8
            "I": f'=DATEDIF(H{next_row}, TODAY(), "Y")',  # Age formula
            "J": data.get("Party", ""),           # Column 10
            "N": data.get("ed", ""),              # Column 14
            "O": data.get("hc", ""),              # Column 15
            "P": data.get("cg", ""),              # Column 16
            "Q": data.get("econ", ""),            # Column 17
            "R": data.get("agri", "")            # Column 18
        }

        # Write to candidates sheet
        for col_letter, value in candidates_data.items():
            candidatesSheet.update_acell(f"{col_letter}{next_row}", value)

        # ===== 2. Write to EDUCATION sheet =====
        education_data = ", ".join(data.get("education", []))
        educationsSheet.update_acell(f"A{next_row}", education_data)  # Column A

        # ===== 3. Write to LEADERSHIP sheet =====
        leadership_data = ", ".join(data.get("experience", []))
        leadershipsSheet.update_acell(f"A{next_row}", leadership_data)  # Column A

        # ===== 4. Write to ACHIEVEMENTS sheet =====
        achievements_data = ", ".join(data.get("achievements", []))
        achievementsSheet.update_acell(f"A{next_row}", achievements_data)  # Column A

        return jsonify({"result": "success", "row": next_row})

    except Exception as e:
        return jsonify({"result": "error", "message": str(e)})



    
if __name__ == '__main__':
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
