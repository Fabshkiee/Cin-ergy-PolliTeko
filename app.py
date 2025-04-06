from flask import Flask, render_template, jsonify, request, redirect, url_for, session, Blueprint
import gspread
import os
from google.oauth2.service_account import Credentials
import json
import requests
from functools import lru_cache


@lru_cache(maxsize=None)
def get_location_name(code, endpoint):
    """
    Fetches the location name (region, province, or city) from the API and caches the result.
    """
    try:
        response = requests.get(f"https://psgc.gitlab.io/api/{endpoint}/{code}/")
        if response.status_code == 200:
            return response.json().get('name', 'Unknown')
        return 'Unknown'
    except Exception as e:
        print(f"Error fetching location name for {code} from {endpoint}: {e}")
        return 'Unknown'

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
resultsSheet = workbook.worksheet("results")
questionsSheet = workbook.worksheet("questions")

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
    return render_template('/admin/admin.html')

@app.route('/candidate')
def candidate():
    if 'user_id' not in session:
        return redirect('/')

    try:
        # Fetch all data from the candidates sheet
        all_data = candidatesSheet.get_all_values()

        # Extract column indices for relevant data
        first_name_col = 0  # Column A (index 0)
        last_name_col = 2   # Column C (index 2)
        bio_col = 7         # Column H (index 7)
        position_col = 3    # Column D (index 3)
        photo_col = 16      # Column Q (index 16)

        # Skip the header row and filter candidates by position
        chairpersons = []
        vice_chairpersons = []

        for index, row in enumerate(all_data[1:], start=2):  # Skip the header row, start row IDs at 2
            if len(row) > position_col:  # Ensure the row has enough columns
                position = row[position_col].strip()
                first_name = row[first_name_col].strip()
                last_name = row[last_name_col].strip()
                biography = row[bio_col].strip()
                photo = row[photo_col].strip() if len(row) > photo_col else "/static/default-profile.png"

                candidate = {
                    "row_id": index,  # Add the row ID
                    "first_name": first_name,
                    "last_name": last_name,
                    "biography": biography,
                    "photo": photo  # Include the photo path
                }

                if position.lower() == "chair person":
                    chairpersons.append(candidate)
                elif position.lower() == "vice chair person":
                    vice_chairpersons.append(candidate)

        # Pass the filtered data to the template
        return render_template(
            'candidates.html',
            chairpersons=chairpersons,
            vice_chairpersons=vice_chairpersons
        )

    except Exception as e:
        return f"Error fetching candidates: {str(e)}", 500

@app.route('/api/candidate/<int:row_id>')
def get_candidate_profile(row_id):
    try:
        # Fetch candidate data from the candidates sheet
        candidate_row = candidatesSheet.row_values(row_id)
        if not candidate_row:
            return jsonify({"error": "Candidate not found"}), 404

        # Ensure the row has enough columns
        while len(candidate_row) < 16:  # Assuming 16 columns are required
            candidate_row.append("")

        # Get location codes from candidate data
        region_code = candidate_row[4]
        province_code = candidate_row[5]
        city_code = candidate_row[6]

        # Get location names using cached function
        region_name = get_location_name(region_code, 'regions')
        province_name = get_location_name(province_code, 'provinces')
        city_name = get_location_name(city_code, 'cities-municipalities')

        # Extract platform details
        platforms = {
            "Education": candidate_row[11],  # Column L
            "Healthcare": candidate_row[12],  # Column M
            "Clean Government": candidate_row[13],  # Column N
            "Economy": candidate_row[14],  # Column O
            "Agriculture": candidate_row[15],  # Column P
        }

        # Filter out empty platform details
        platform_details = {key: value for key, value in platforms.items() if value.strip()}

        # Extract candidate details
        candidate = {
            "first_name": candidate_row[0],
            "middle_name": candidate_row[1],
            "last_name": candidate_row[2],
            "position": candidate_row[3],
            "region": region_code,
            "region_name": region_name,
            "province": province_code,
            "province_name": province_name,
            "city": city_code,
            "city_name": city_name,
            "biography": candidate_row[7],
            "birthday": candidate_row[8],
            "age": candidate_row[9],
            "party": candidate_row[10],
            "photo": candidate_row[16] if len(candidate_row) > 16 else "/static/default-profile.png",  # Include photo
            "platforms": platform_details,  # Include only non-empty platform details
            "education": educationsSheet.row_values(row_id) if educationsSheet.row_values(row_id) else [],
            "leadership": leadershipsSheet.row_values(row_id) if leadershipsSheet.row_values(row_id) else [],
            "achievements": achievementsSheet.row_values(row_id) if achievementsSheet.row_values(row_id) else [],
        }

        return jsonify(candidate)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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

@app.route('/voting')
def voting():
    if 'user_id' not in session:
        return redirect('/')
    return render_template('voting.html')

@app.route('/casting')
def casting():
    if 'user_id' not in session:
        return redirect('/')

    try:
        # Fetch all data from the candidates sheet
        all_data = candidatesSheet.get_all_values()

        # Extract column indices for relevant data
        first_name_col = 0  # Column A (index 0)
        last_name_col = 2   # Column C (index 2)
        position_col = 3    # Column D (index 3)

        # Skip the header row and filter candidates by position
        chairpersons = []
        vice_chairpersons = []

        for index, row in enumerate(all_data[1:], start=2):  # Skip header, start at row 2
            if len(row) > position_col:
                position = row[position_col].strip().lower()
                first_name = row[first_name_col].strip()
                last_name = row[last_name_col].strip()

                candidate = {
                    "id": str(index),  # Convert to string to match form submission
                    "first_name": first_name,
                    "last_name": last_name,
                }

                if position == "chair person":
                    chairpersons.append(candidate)
                elif position == "vice chair person":
                    vice_chairpersons.append(candidate)

        return render_template(
            'casting.html',
            chairpersons=chairpersons,
            vice_chairpersons=vice_chairpersons
        )

    except Exception as e:
        return f"Error fetching candidates: {str(e)}", 500

@app.route('/api/vote', methods=['POST'])
def record_vote():
    try:
        data = request.json
        vote_rows = data.get('results', [])
        
        if not vote_rows:
            return jsonify({"success": False, "message": "No votes provided"}), 400
        
        # Initialize votes sheet if needed
        max_row = max(vote_rows) if vote_rows else 0
        if len(resultsSheet.get_all_values()) < max_row:
            for _ in range(max_row - len(resultsSheet.get_all_values())):
                resultsSheet.append_row([""])
        
        # Update vote counts
        for row in vote_rows:
            current_votes = resultsSheet.acell(f'A{row}').value
            current_votes = int(current_votes) if current_votes and current_votes.isdigit() else 0
            resultsSheet.update_acell(f'A{row}', str(current_votes + 1))
        
        return jsonify({
            "success": True,
            "message": f"Recorded {len(vote_rows)} votes",
            "votes_recorded": len(vote_rows)
        })
    
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/results')
def results():
    if 'user_id' not in session:
        return redirect('/')

    try:
        # Fetch all data from the candidates sheet
        all_data = candidatesSheet.get_all_values()
        # Fetch all data from the results sheet
        results_data = resultsSheet.get_all_values()
        
        # Create a dictionary to map candidate names to their vote counts
        vote_counts = {}
        for row in results_data:
            if len(row) >= 2:  # Ensure there's at least a name and vote count
                candidate_name = row[0]
                vote_count = row[1] if len(row) > 1 else "0"
                vote_counts[candidate_name] = vote_count

        # Extract column indices for relevant data
        first_name_col = 0  # Column A (index 0)
        last_name_col = 2   # Column C (index 2)
        bio_col = 7         # Column H (index 7)
        position_col = 3    # Column D (index 3)
        photo_col = 16      # Column Q (index 16)

        # Skip the header row and filter candidates by position
        chairpersons = []
        vice_chairpersons = []

        for index, row in enumerate(all_data[1:], start=2):  # Skip the header row, start row IDs at 2
            if len(row) > position_col:  # Ensure the row has enough columns
                position = row[position_col].strip()
                first_name = row[first_name_col].strip()
                last_name = row[last_name_col].strip()
                photo = row[photo_col].strip() if len(row) > photo_col else "/static/default-profile.png"
                candidate_name = f"{last_name}, {first_name}"

                candidate = {
                    "row_id": index,  # Add the row ID
                    "first_name": first_name,
                    "last_name": last_name,
                    "photo": photo,  # Include the photo path
                    "votes": vote_counts.get(candidate_name, "0")  # Get votes from results sheet
                }

                if position.lower() == "chair person":
                    chairpersons.append(candidate)
                elif position.lower() == "vice chair person":
                    vice_chairpersons.append(candidate)

        # Sort candidates by vote count (descending)
        chairpersons.sort(key=lambda x: int(x["votes"]), reverse=True)
        vice_chairpersons.sort(key=lambda x: int(x["votes"]), reverse=True)

        # Pass the filtered data to the template
        return render_template(
            'results.html',
            chairpersons=chairpersons,
            vice_chairpersons=vice_chairpersons
        )

    except Exception as e:
        return f"Error fetching results: {str(e)}", 500

    
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
        
import os

@app.route("/submitAddCandidate", methods=["POST"])
def submit():
    try:
        data = request.form.to_dict()
        photo = request.files.get("photo")

        # Ensure the uploads directory exists
        upload_dir = os.path.join("static", "uploads")
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)

        # Save the photo file if it exists
        if photo:
            photo_filename = os.path.join(upload_dir, photo.filename)
            photo.save(photo_filename)
            data["photo"] = photo_filename  # Save the file path in the data

        # Get next row for candidates sheet (this will be our master row number)
        candidate_row = len(candidatesSheet.get_all_values()) + 1

        # Write candidate data to the candidates sheet
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
            "P": data.get("agri", ""),
            "Q": data.get("photo", ""),  # Save the photo path in column Q
        }

        for col_letter, value in candidates_data.items():
            candidatesSheet.update_acell(f"{col_letter}{candidate_row}", value)

        # Write achievements, leadership, and educational background to their respective sheets
        achievements = json.loads(data.get("achievements", "[]"))
        leadership = json.loads(data.get("experience", "[]"))
        education = json.loads(data.get("education", "[]"))

        # Write achievements to the achievements sheet
        for col_index, achievement in enumerate(achievements, start=1):
            achievementsSheet.update_cell(candidate_row, col_index, achievement)

        # Write leadership experiences to the leadership sheet
        for col_index, exp in enumerate(leadership, start=1):
            leadershipsSheet.update_cell(candidate_row, col_index, exp)

        # Write educational background to the education sheet
        for col_index, edu in enumerate(education, start=1):
            educationsSheet.update_cell(candidate_row, col_index, edu)

        return jsonify({
            "result": "success",
            "row": candidate_row,
            "message": f"Data written to row {candidate_row} across all sheets"
        })

    except Exception as e:
        return jsonify({"result": "error", "message": str(e)})

@app.route('/submit_votes', methods=['POST'])
def submit_votes():
    try:
        # Get the votes from the request
        votes = request.json.get('votes', {})
        
        # Process each vote
        for position, candidate_id in votes.items():
            try:
                # Convert candidate_id to integer (row number)
                candidate_row = int(candidate_id)
                
                # Get candidate details from candidates sheet
                try:
                    candidate_data = candidatesSheet.row_values(candidate_row)
                    if not candidate_data:
                        return jsonify({
                            "success": False,
                            "message": f"Candidate in row {candidate_row} not found"
                        }), 404
                except Exception as e:
                    return jsonify({
                        "success": False,
                        "message": f"Error accessing candidate data: {str(e)}"
                    }), 500
                
                # Format candidate name as "Last, First"
                candidate_name = f"{candidate_data[2]}, {candidate_data[0]}"
                
                # Check if candidate exists in results sheet
                try:
                    # Get all candidate names from column A
                    existing_names = resultsSheet.col_values(1)
                    
                    if candidate_name in existing_names:
                        # Candidate exists - find their row and increment vote count
                        row_number = existing_names.index(candidate_name) + 1
                        current_votes = int(resultsSheet.cell(row_number, 2).value)
                        resultsSheet.update_cell(row_number, 2, current_votes + 1)
                    else:
                        # Candidate doesn't exist - append new row
                        resultsSheet.append_row([candidate_name, 1])
                        
                except Exception as e:
                    return jsonify({
                        "success": False,
                        "message": f"Error updating results: {str(e)}"
                    }), 500
                
            except ValueError:
                return jsonify({
                    "success": False,
                    "message": f"Invalid candidate ID: {candidate_id}"
                }), 400
        
        return jsonify({
            "success": True,
            "message": "Votes recorded successfully"
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error recording votes: {str(e)}"
        }), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
