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
positionsSheet = workbook.worksheet("positions")

@app.route('/')
def home():
    return render_template("index.html")
    
@app.route('/login', methods=['POST'])
def login():
    user_id = request.form['userID']
    password = request.form['password']
    all_data = sheet.get_all_values()
    
    for row in all_data:
        if len(row) >= 3:
            if row[0] == user_id and row[1] == password:
                session['user_id'] = user_id
                session['is_admin'] = (row[2].lower() == 'true' or row[2] == '1')
                
                if session['is_admin']:
                    return redirect('/admin-dashboard')
                else:
                    return redirect('/dashboard')
    return render_template('index.html', error="Invalid ID or password")

@app.route('/api/positions')
def get_positions():
    try:
        positions = positionsSheet.col_values(1)[1:]  # Skip header row
        return jsonify({"positions": positions})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin-dashboard')
def admin_dashboard():
    if 'user_id' not in session or not session.get('is_admin', False):
        return redirect('/')
    return render_template('addCandidate.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')
    return render_template('landingpage.html')

@app.route('/PiliTugma')
def PiliTugma():
    if 'user_id' not in session:
        return redirect('/')
    return render_template('PiliTugma.html')
    
@app.route('/quiz')
def quiz():
    try:
        cells = sheet2.range('A2:A')
        options = [cell.value.strip() for cell in cells if cell.value.strip()]
        
        question = {
            'id': 1,
            'text': 'What is the capital of France?',
            'description': 'Choose what applies best',
            'options': options
        }
        
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
        
        # Get next row for candidates sheet (this will be our master row number)
        candidate_row = len(candidatesSheet.get_all_values()) + 1
        
        # First ensure all sheets have at least this many rows
        for sheet in [educationsSheet, leadershipsSheet, achievementsSheet]:
            current_rows = len(sheet.get_all_values())
            if current_rows < candidate_row - 1:  # -1 because append_row adds a row
                for _ in range(candidate_row - 1 - current_rows):
                    sheet.append_row([""])  # Add empty rows if needed

        # Write candidate data
        candidates_data = {
            "A": data.get("FirstName", ""),
            "B": data.get("MiddleName", ""),
            "C": data.get("LastName", ""),
            "D": data.get("Position", ""),
            "E": data.get("region", ""),
            "F": data.get("province", ""),
            "G": data.get("city", ""),
            "H": data.get("biography", ""),
            "I": data.get("bday", ""),
            "J": f'=DATEDIF(I{candidate_row}, TODAY(), "Y")',
            "K": data.get("Party", ""),
            "L": data.get("ed", ""),
            "M": data.get("hc", ""),
            "N": data.get("cg", ""),
            "O": data.get("econ", ""),
            "P": data.get("agri", "")
        }
        
        # Write to candidates sheet
        for col_letter, value in candidates_data.items():
            candidatesSheet.update_acell(f"{col_letter}{candidate_row}", value)

        # Write to other sheets at the SAME row number
        educationsSheet.update(f"A{candidate_row}", [[", ".join(data.get("education", []))]])
        leadershipsSheet.update(f"A{candidate_row}", [[", ".join(data.get("experience", []))]])
        achievementsSheet.update(f"A{candidate_row}", [[", ".join(data.get("achievements", []))]])

        return jsonify({
            "result": "success",
            "row": candidate_row,
            "message": f"Data written to row {candidate_row} across all sheets"
        })

    except Exception as e:
        return jsonify({"result": "error", "message": str(e)})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)