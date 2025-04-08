from flask import Flask, render_template, jsonify, request, redirect, url_for, session, Blueprint
import gspread
import os
from google.oauth2.service_account import Credentials
import json
import requests
from functools import lru_cache
import cloudinary
import cloudinary.uploader
import cloudinary.api

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

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
#google_creds_json = os.environ.get('GOOGLE_CREDENTIALS')
#creds = Credentials.from_service_account_info(json.loads(google_creds_json), scopes=scopes)
google_creds_json = os.environ.get('GOOGLE_CREDENTIALS')
creds = Credentials.from_service_account_info(json.loads(google_creds_json), scopes=scopes)
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
issuesSheet = workbook.worksheet("stances")
stancesSheet = workbook.worksheet("stances")
photosSheet = workbook.worksheet("photos")  # Make sure this sheet exists

issue_titles = [issue.strip().lower() for issue in stancesSheet.row_values(1)]  # Fetch issue titles from the first row

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

        # Fetch photo paths from the photosSheet
        photo_paths = photosSheet.col_values(2)[1:]  # Skip header row

        # Extract column indices for relevant data
        first_name_col = 0  # Column A (index 0)
        last_name_col = 2   # Column C (index 2)
        bio_col = 7         # Column H (index 7)
        position_col = 3    # Column D (index 3)

        # Group candidates by position
        positions = {}

        for index, row in enumerate(all_data[1:], start=2):  # Skip the header row, start row IDs at 2
            if len(row) > position_col:  # Ensure the row has enough columns
                position = row[position_col].strip()
                first_name = row[first_name_col].strip()
                last_name = row[last_name_col].strip()
                biography = row[bio_col].strip()
                photo = photo_paths[index - 2] if index - 2 < len(photo_paths) else "/static/default-profile.png"

                candidate = {
                    "row_id": index,  # Add the row ID
                    "first_name": first_name,
                    "last_name": last_name,
                    "biography": biography,
                    "photo": photo  # Include the photo path
                }

                # Add candidate to the corresponding position group
                if position not in positions:
                    positions[position] = []
                positions[position].append(candidate)

        # Pass the grouped data to the template
        return render_template(
            'candidates.html',
            positions=positions
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

        photo_path = photosSheet.cell(row_id, 2).value if row_id <= len(photosSheet.get_all_values()) else ""

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

        # Fetch platform titles and candidate's platform values from the pillarsSheet
        platform_titles = sheet2.row_values(1)  # First row contains platform titles
        platform_values = sheet2.row_values(row_id) if row_id <= len(sheet2.get_all_values()) else []

        # Create a dictionary of platforms
        platforms = {title: value for title, value in zip(platform_titles, platform_values) if value.strip()}

        # Fetch issues and stances from the stancesSheet
        issues = stancesSheet.row_values(1)  # First row contains issues
        stances = stancesSheet.row_values(row_id) if row_id <= len(stancesSheet.get_all_values()) else []

        # Create a dictionary of stances
        stance_data = {issue: stance for issue, stance in zip(issues, stances) if stance.strip()}

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
            "photo": photo_path or "/static/default-profile.png",
            "platforms": platforms,
            "stances": stance_data,
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

# ====== ADD THESE HELPER FUNCTIONS ======
def calculate_platform_match(candidate):
    """Calculate actual platform match percentage"""
    try:
        user_answers = session.get('quiz_answers', {})
        if not user_answers:
            return 0
            
        candidate_row = sheet2.row_values(candidate['row_id'])
        platform_titles = sheet2.row_values(1)
        candidate_platforms = dict(zip(platform_titles, candidate_row))
        
        matches = 0
        total = 0
        for pillar, user_answer in user_answers.items():
            if pillar in candidate_platforms and candidate_platforms[pillar]:
                total += 1
                if candidate_platforms[pillar].strip().lower() == user_answer.strip().lower():
                    matches += 1
                    
        return round((matches / total) * 100) if total > 0 else 0
    except Exception as e:
        print(f"Error calculating platform match: {e}")
        return 0

def calculate_stance_match(candidate):
    """Calculate actual stance match percentage"""
    try:
        user_stances = session.get('quiz_stances', {})
        if not user_stances:
            return 0
            
        candidate_row = stancesSheet.row_values(candidate['row_id'])
        issue_titles = stancesSheet.row_values(1)
        candidate_stances = dict(zip(issue_titles, candidate_row))
        
        matches = 0
        total = 0
        for issue, user_stance in user_stances.items():
            if issue in candidate_stances and candidate_stances[issue]:
                total += 1
                if candidate_stances[issue].strip().lower() == user_stance.strip().lower():
                    matches += 1
                    
        return round((matches / total) * 100) if total > 0 else 0
    except Exception as e:
        print(f"Error calculating stance match: {e}")
        return 0

def generate_match_summary(candidate, platform_match, stance_match):
    """Generate a dynamic summary based on match percentages"""
    strengths = []
    if platform_match >= 80:
        strengths.append("excellent platform alignment")
    elif platform_match >= 60:
        strengths.append("strong platform alignment")
    
    if stance_match >= 80:
        strengths.append("excellent stance agreement")
    elif stance_match >= 60:
        strengths.append("strong stance agreement")
    
    if strengths:
        return f"You and {candidate['first_name']} show {', '.join(strengths)}."
    elif platform_match >= 40 or stance_match >= 40:
        return f"You and {candidate['first_name']} have some common ground."
    else:
        return f"You and {candidate['first_name']} have limited alignment."

# ====== REPLACE YOUR matchResults ROUTE WITH THIS ======
@app.route('/save-results', methods=['POST'])
def save_results():
    try:
        data = request.json
        user_answers = data.get('answers', {})
        
        if not user_answers:
            return jsonify({"success": False, "message": "No answers provided"}), 400

        # Get all candidates data
        all_candidates = candidatesSheet.get_all_values()[1:]  # Skip header
        candidate_scores = {}

        # Get photos mapping first - ensure this matches your photos sheet structure
        # Replace the photo handling section with:
# Replace the photo handling section with:
        photo_map = {}
        photos_data = photosSheet.get_all_values()
        for row in photos_data[1:]:  # Skip header row
          if len(row) >= 2:  # Ensure there's at least 2 columns (name and photo URL)
            candidate_name = f"{row[0].strip().lower()}"  # Standardize name format
            photo_url = row[1].strip()  # Get the photo URL from column B
            photo_map[candidate_name] = photo_url if photo_url else "/static/default-profile.png"

        # Rest of your code...

        # Initialize scores
        for index in range(len(all_candidates)):
            candidate_row = all_candidates[index]
            # Create matching key - adjust this to match your photos sheet format
            first_name = candidate_row[0].strip().lower()
            last_name = candidate_row[2].strip().lower()
            full_name = f"{first_name} {last_name}"
            
            candidate_scores[index + 2] = {  # +2 for sheet row (1 header + 1 base)
                'score': 0,
                'photo': photo_map.get(full_name, '/static/default-profile.png'),
                'first_name': candidate_row[0].strip(),
                'last_name': candidate_row[2].strip()
            }

        # Rest of your matching logic remains the same...
        for question_id, user_answer in user_answers.items():
            user_keywords = user_answer.strip().lower().split()
            
            for candidate_row in range(len(all_candidates)):
                candidate_data = all_candidates[candidate_row]
                candidate_row_num = candidate_row + 2
                
                candidate_details = " ".join([
                    str(value).lower() for value in candidate_data 
                    if value and str(value).strip()
                ])
                
                for keyword in user_keywords:
                    if keyword in candidate_details:
                        candidate_scores[candidate_row_num]['score'] += 1

        # Prepare results
        results = []
        for row_num, data in candidate_scores.items():
            candidate_data = candidatesSheet.row_values(row_num)
            if len(candidate_data) >= 4:
                results.append({
                    "row_id": row_num,
                    "first_name": data['first_name'],
                    "last_name": data['last_name'],
                    "position": candidate_data[3],
                    "photo": data['photo'],
                    "score": data['score'],
                    "total_keywords": sum(len(ans.split()) for ans in user_answers.values())
                })

        # Sort and store results
        results.sort(key=lambda x: x['score'], reverse=True)
        session['match_results'] = results

        return jsonify({"success": True, "results": results})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/matchResults')
def matchResults():
    if 'user_id' not in session:
        return redirect('/')

    if 'match_results' not in session:
        return redirect('/quiz')
    
    results = session['match_results']
    if not results:
        return render_template('matchResults.html', 
                           top_candidate=None,
                           similar_candidates=[])

    try:
        # Get all candidates data for reference
        all_candidates = candidatesSheet.get_all_values()[1:]  # Skip header
        photo_paths = photosSheet.col_values(2)[1:]  # Skip header row

        # Process results with match percentages and photos
        processed_results = []
        for candidate in results:
            # Get candidate data from candidates sheet
            candidate_row = candidatesSheet.row_values(candidate['row_id'])
            if not candidate_row or len(candidate_row) < 4:
                continue  # Skip invalid candidates

            # Get photo path
            photo_index = candidate['row_id'] - 2  # Convert to 0-based index
            photo_path = photo_paths[photo_index] if photo_index < len(photo_paths) else "/static/default-profile.png"

            # Calculate match percentage
            if candidate['total_keywords'] > 0:
                match_percentage = round((candidate['score'] / candidate['total_keywords']) * 100)
                summary = f"Found {candidate['score']} matching keywords out of {candidate['total_keywords']} total"
            else:
                match_percentage = 0
                summary = "No keywords to match"

            processed_results.append({
                "row_id": candidate['row_id'],
                "first_name": candidate_row[0],
                "last_name": candidate_row[2],
                "position": candidate_row[3],
                "photo": photo_path,
                "score": candidate['score'],
                "total_keywords": candidate['total_keywords'],
                "match_percentage": match_percentage,
                "match_summary": summary
            })

        # Sort by score descending
        processed_results.sort(key=lambda x: x['score'], reverse=True)

        return render_template(
            'matchResults.html',
            top_candidate=processed_results[0] if processed_results else None,
            similar_candidates=processed_results[1:]  # Show all remaining candidates
        )

    except Exception as e:
        print(f"Error processing match results: {str(e)}")
        return render_template('matchResults.html', 
                           top_candidate=None,
                           similar_candidates=[])

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
        # Fetch all candidate data
        all_candidates = candidatesSheet.get_all_values()
        
        # Fetch photo paths from the photosSheet
        photo_paths = photosSheet.col_values(2)[1:]  # Skip header row

        # Fetch vote data from results sheet (Column A: names, Column B: counts)
        results_data = resultsSheet.get_all_values()
        
        # Create a dictionary mapping full names to vote counts
        vote_dict = {}
        for row in results_data[1:]:  # Skip header row
            if len(row) >= 2:
                full_name = row[0].strip()
                # Remove commas and convert to integer for sorting
                raw_votes = row[1].replace(',', '') if row[1] else '0'
                vote_count = int(raw_votes) if raw_votes.isdigit() else 0
                vote_dict[full_name] = {
                    'raw': vote_count,  # For sorting
                    'formatted': "{:,}".format(vote_count)  # For display with commas
                }

        # Group candidates by position
        positions = {}

        for index, row in enumerate(all_candidates[1:], start=2):  # Skip header row
            if len(row) > 3:  # Ensure row has enough columns
                position = row[3].strip()
                first_name = row[0].strip()
                last_name = row[2].strip()
                full_name = f"{last_name}, {first_name}"  # Match the format in results sheet
                photo = photo_paths[index - 2] if index - 2 < len(photo_paths) else "/static/default-profile.png"
                
                # Get vote count from dictionary (default to 0 if not found)
                votes_data = vote_dict.get(full_name, {'raw': 0, 'formatted': '0'})

                candidate = {
                    "row_id": index,
                    "first_name": first_name,
                    "last_name": last_name,
                    "photo": photo,
                    "votes": votes_data['raw'],  # For sorting
                    "votes_formatted": votes_data['formatted']  # For display
                }

                # Add candidate to the corresponding position group
                if position not in positions:
                    positions[position] = []
                positions[position].append(candidate)

        # Sort candidates within each position by raw vote count in descending order
        for position, candidates in positions.items():
            candidates.sort(key=lambda x: x['votes'], reverse=True)

        return render_template(
            'results.html',
            positions=positions
        )

    except Exception as e:
        return f"Error fetching results: {str(e)}", 500

    
@app.route('/quiz')
def quiz():
    try:
        # Fetch all questions from the first row of the questions sheet
        questions_row = questionsSheet.row_values(1)
        questions = []
        
        # For each question (column in row 1), create a question object
        for col_idx, question_text in enumerate(questions_row, start=1):
            if not question_text.strip():
                continue  # Skip empty columns
                
            # Get corresponding options from pillars sheet (same column)
            pillar_col = sheet2.get_all_values()
            options = []
            if len(pillar_col) >= col_idx:  # Check if column exists in pillars sheet
                # Skip header row and get all values in this column
                options = [row[col_idx-1].strip() for row in pillar_col[1:] if len(row) >= col_idx and row[col_idx-1].strip()]
            
            questions.append({
                'id': col_idx,
                'text': question_text,
                'description': 'Choose what applies best',
                'options': options,
                'column': chr(64 + col_idx)  # A, B, C, etc. for reference
            })
        
        if not questions:
            return "No questions found in the questions sheet", 404
            
        return render_template('question.html', questions=questions)
    
    except Exception as e:
        return f"Error loading quiz: {str(e)}", 500



@app.route('/adminAddCandi')
def addCandi():
    return render_template('addCandidate.html')
        
import os

@app.route('/api/platforms')
def get_platforms():
    try:
        # Fetch platform titles from first row of pillars sheet (A1, B1, C1)
        platforms = sheet2.row_values(1)  # Get first 3 columns of row 1
        platforms = [p for p in platforms if p and str(p).strip()]  # Remove empty/None values
        return jsonify(platforms)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/submitAddCandidate", methods=["POST"])
def submit_candidate():
    try:
        # Fetch candidate data
        data = request.form.to_dict()
        photo = request.files.get("photo")

        # Process platforms, stances, education, leadership, and achievements
        platforms = json.loads(data.get("platforms", "{}"))
        stances = json.loads(data.get("stances", "{}"))
        education = json.loads(data.get("education", "[]"))
        leadership = json.loads(data.get("experience", "[]"))
        achievements = json.loads(data.get("achievements", "[]"))

        # Fetch issue titles from the stancesSheet
        issue_titles = [issue.strip().lower() for issue in stancesSheet.row_values(1)]

        # Upload the photo to Cloudinary if it exists
        photo_url = ""
        if photo:
            upload_result = cloudinary.uploader.upload(photo, folder="candidates")
            photo_url = upload_result.get("secure_url", "")

        # Calculate age from the provided birthdate
        birthdate = data.get("bday", "")
        age = ""
        if birthdate:
            from datetime import datetime
            birthdate_obj = datetime.strptime(birthdate, "%Y-%m-%d")
            today = datetime.today()
            age = today.year - birthdate_obj.year - ((today.month, today.day) < (birthdate_obj.month, birthdate_obj.day))

        # Write candidate data to the candidates sheet
        candidate_data = [
            data.get("FirstName", ""),
            data.get("MiddleName", ""),
            data.get("LastName", ""),
            data.get("Position", ""),
            data.get("region", ""),
            data.get("province", ""),
            data.get("city", ""),
            data.get("biography", ""),
            birthdate,
            age,  # Save calculated age in column J
            data.get("Party", ""),  # Save political party in column K
        ]
        candidatesSheet.append_row(candidate_data)

        # Save platforms to the pillarsSheet
        pillar_titles = [pillar.strip() for pillar in sheet2.row_values(1)]
        platform_row = [platforms.get(pillar, "") for pillar in pillar_titles]
        sheet2.insert_row(platform_row, len(sheet2.get_all_values()) + 1)

        # Save platforms dynamically to the candidatesSheet (starting at column L)
        candidate_row_index = len(candidatesSheet.get_all_values())  # Get the row index of the newly added candidate
        candidatesSheet.update(
            f"L{candidate_row_index}:{chr(64 + len(pillar_titles) + 12)}{candidate_row_index}",
            [platform_row]
        )

        # Save stances to the stancesSheet
        stances_row = [stances.get(issue, "No Answer") for issue in issue_titles]
        stancesSheet.insert_row(stances_row, len(stancesSheet.get_all_values()) + 1)

        # Save education to the educationsSheet
        for edu in education:
            educationsSheet.append_row([edu])

        # Save leadership to the leadershipsSheet
        for lead in leadership:
            leadershipsSheet.append_row([lead])

        # Save achievements to the achievementsSheet
        for achieve in achievements:
            achievementsSheet.append_row([achieve])

        # Save photo information to the photosSheet
        photosSheet.append_row([
            f"{data.get('FirstName', '')} {data.get('LastName', '')}",
            photo_url
        ])

        return jsonify({"success": True, "message": "Candidate added successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/add-position', methods=['POST'])
def add_position():
    if 'user_id' not in session or not session.get('is_admin', False):
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        # Parse form data
        position = request.json.get('position', '').strip()
        number = int(request.json.get('number', 1))

        # Validate input
        if number < 0:
            return jsonify({"success": False, "message": "Number cannot be negative"}), 400

        # Check if position already exists
        all_positions = positionsSheet.col_values(1)
        if position in all_positions:
            return jsonify({"success": False, "message": f"Position '{position}' already exists."}), 400

        # Prepare value for Google Sheets - empty string for 0
        sheet_number = '' if number == 0 else number

        # Find next empty row
        next_row = len(all_positions) + 1

        # Update the sheet
        positionsSheet.update(
            f"A{next_row}:B{next_row}",
            [[position, sheet_number]],
            value_input_option='USER_ENTERED'  # This ensures proper handling of empty strings
        )

        return jsonify({
            "success": True,
            "message": f"Position '{position}' added successfully.",
            "display_number": "Infinite" if number == 0 else number
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/list-positions')
def list_positions():
     if 'user_id' not in session or not session.get('is_admin', False):
         return redirect('/')
 
     try:
         # Fetch all positions and numbers from the sheet
         all_positions = positionsSheet.get_all_values()
         positions = []
         for row in all_positions[1:]:  # Skip header row
             position = row[0]
             number = row[1] if len(row) > 1 else ''
             # Convert empty string to "Infinite"
             display_number = "Infinite" if number == '' else number
             positions.append((position, display_number))
 
         return render_template('listposition.html', positions=positions)
     except Exception as e:
         return f"Error fetching positions: {str(e)}", 500
     
@app.route('/delete-position', methods=['POST'])
def delete_position():
    if 'user_id' not in session or not session.get('is_admin', False):
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        # Parse the position to delete
        data = request.json
        position_to_delete = data.get('position', '').strip()

        # Fetch all positions from the sheet
        all_positions = positionsSheet.get_all_values()

        # Find the row number of the position to delete
        for index, row in enumerate(all_positions):
            if row[0] == position_to_delete:  # Match the position in column A
                positionsSheet.delete_rows(index + 1)  # Delete the row (1-based index)
                return jsonify({"success": True, "message": f"Position '{position_to_delete}' deleted successfully."})

        return jsonify({"success": False, "message": f"Position '{position_to_delete}' not found."}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500



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
                        current_votes_str = resultsSheet.cell(row_number, 2).value
                        # Remove commas and convert to integer
                        current_votes = int(current_votes_str.replace(',', '')) if current_votes_str else 0
                        # Format back with commas for storage
                        resultsSheet.update_cell(row_number, 2, "{:,}".format(current_votes + 1))
                    else:
                        # Candidate doesn't exist - append new row
                        resultsSheet.append_row([candidate_name, "1"])
                        
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

@app.route('/api/pillars', methods=['GET'])
def get_pillars():
    try:
        # Fetch all pillars from the first row of the pillarsSheet
        pillars = sheet2.row_values(1)  # Get all values from row 1
        return jsonify({"success": True, "pillars": pillars})
    except Exception as e:
        print(f"Error fetching pillars: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/save-question', methods=['POST'])
def save_question():
    try:
        data = request.json
        question_text = data.get('questionText')
        pillar = data.get('pillar')

        if not question_text or not pillar:
            return jsonify({"success": False, "message": "Question and pillar are required"}), 400

        # Fetch pillar titles and find the column index for the selected pillar
        pillar_titles = sheet2.row_values(1)
        if pillar not in pillar_titles:
            return jsonify({"success": False, "message": "Invalid pillar selected"}), 400

        pillar_index = pillar_titles.index(pillar) + 1  # Convert to 1-based index for Google Sheets

        # Check if the pillar already has a question
        existing_questions = questionsSheet.col_values(pillar_index)
        if len(existing_questions) > 1:  # More than just the header
            return jsonify({"success": False, "message": f"The pillar '{pillar}' already has a question."}), 400

        # Append question to the corresponding pillar column
        questionsSheet.update_cell(len(existing_questions) + 1, pillar_index, question_text)

        return jsonify({"success": True, "message": "Question saved successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/submit-issues', methods=['POST'])
def submit_issues():
    if 'user_id' not in session or not session.get('is_admin', False):
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        data = request.json
        new_issues = data.get('issues', [])

        if not new_issues:
            return jsonify({"success": False, "message": "No issues provided"}), 400

        # Fetch existing issues from the first row of the stancesSheet
        existing_issues = stancesSheet.row_values(1)

        # Append new issues to the existing list, avoiding duplicates
        updated_issues = list(dict.fromkeys(existing_issues + new_issues))  # Remove duplicates while preserving order

        # Update the first row of the stancesSheet with the updated list
        stancesSheet.update('1:1', [updated_issues])

        return jsonify({"success": True, "message": "Issues updated successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/adminAddCandi')
def addCandi_new():
    if 'user_id' not in session or not session.get('is_admin', False):
        return redirect('/')

    try:
        # Fetch all issues from the stancesSheet
        issues = stancesSheet.row_values(1)  # Assuming issues are stored in the first row

        # Remove duplicates (if any)
        issues = list(dict.fromkeys(issues))  # Ensures order is preserved while removing duplicates

        # Debugging: Print the fetched issues
        print("Fetched issues:", issues)

        return render_template('addCandidate.html', issues=issues)
    except Exception as e:
        return f"Error fetching issues: {str(e)}", 500

@app.route('/api/issues', methods=['GET'])
def get_issues():
    try:
        # Fetch all issues from the first row of the stancesSheet
        issues = stancesSheet.row_values(1)  # Get all values from row 1
        return jsonify({"success": True, "issues": issues})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/add-question')
def add_question():
    if 'user_id' not in session or not session.get('is_admin', False):
        return redirect('/')
    return render_template('createQuestions.html')

@app.route('/api/questions', methods=['GET'])
def get_questions():
    try:
        # Fetch all questions from the first row of the questionsSheet
        questions = questionsSheet.row_values(1)  # Get all values from row 1
        return jsonify({"success": True, "questions": questions})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/delete-question', methods=['POST'])
def delete_question():
    try:
        question_id = request.json.get('id')
        # Find the row of the question to delete
        all_questions = questionsSheet.get_all_records()
        for index, question in enumerate(all_questions, start=2):  # Start at row 2 (after headers)
            if question['id'] == question_id:
                questionsSheet.delete_rows(index)
                return jsonify({"success": True, "message": "Question deleted successfully"})
        return jsonify({"success": False, "message": "Question not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/edit-question', methods=['POST'])
def edit_question():
    try:
        question_id = request.json.get('id')
        updated_text = request.json.get('text')
        updated_pillar = request.json.get('pillar')

        # Find the row of the question to edit
        all_questions = questionsSheet.get_all_records()
        for index, question in enumerate(all_questions, start=2):  # Start at row 2 (after headers)
            if question['id'] == question_id:
                questionsSheet.update(f"A{index}:B{index}", [[updated_text, updated_pillar]])
                return jsonify({"success": True, "message": "Question updated successfully"})
        return jsonify({"success": False, "message": "Question not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/delete-column', methods=['POST'])
def delete_column():
    try:
        column_name = request.json.get('columnName')
        sheet_type = request.json.get('sheetType')  # Either 'questions' or 'stances'

        # Select the correct sheet
        if sheet_type == 'questions':
            sheet = questionsSheet
        elif sheet_type == 'stances':
            sheet = stancesSheet
        else:
            return jsonify({"success": False, "message": "Invalid sheet type"}), 400

        # Get the header row
        headers = sheet.row_values(1)

        if column_name not in headers:
            return jsonify({"success": False, "message": "Column not found"}), 404

        # Find the column index (0-based for Google Sheets API)
        column_index = headers.index(column_name)

        if sheet_type == 'stances':
            # Delete the entire column for "Issues and Controversies"
            sheet.delete_dimension('COLUMNS', column_index + 1)  # Convert to 1-based index for API
            return jsonify({"success": True, "message": f"Column '{column_name}' deleted successfully"})
        elif sheet_type == 'questions':
            # Clear the entire column for "Multiple Choice Questions"
            column_letter = chr(65 + column_index)  # Convert column index to letter (A, B, C, etc.)
            num_rows = len(sheet.col_values(column_index + 1))  # Get the number of rows in the column
            # Clear the header and all rows in the column
            sheet.update(f"{column_letter}1:{column_letter}{num_rows}", [[""] for _ in range(num_rows)])
            return jsonify({"success": True, "message": f"Contents of column '{column_name}' cleared successfully"})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/add-pillar', methods=['POST'])
def add_pillar():
    try:
        # Get the pillar name from the request
        pillar_name = request.json.get('pillarName', '').strip()

        if not pillar_name:
            return jsonify({"success": False, "message": "Pillar name cannot be empty"}), 400

        # Fetch existing pillars from the first row of the pillarsSheet
        existing_pillars = sheet2.row_values(1)

        # Check if the pillar already exists
        if pillar_name in existing_pillars:
            return jsonify({"success": False, "message": f"Pillar '{pillar_name}' already exists."}), 400

        # Add the new pillar to the next empty column in the pillarsSheet
        next_column = len(existing_pillars) + 1
        sheet2.update_cell(1, next_column, pillar_name)

        # Add the new pillar to the next empty column in the candidatesSheet
        candidates_existing_pillars = candidatesSheet.row_values(1)[11:]  # Starting from column L (index 11)
        candidates_next_column = len(candidates_existing_pillars) + 12  # Adjust for column L (index 12)
        candidatesSheet.update_cell(1, candidates_next_column, pillar_name)

        return jsonify({"success": True, "message": f"Pillar '{pillar_name}' added successfully to both sheets."})
    except Exception as e:
        print(f"Error adding pillar: {e}")
        return jsonify({"success": False, "message": "An error occurred while adding the pillar."}), 50

@app.route('/api/delete-pillar', methods=['POST'])
def delete_pillar():
    try:
        pillar_name = request.json.get('pillarName', '').strip()

        # Get the header row from the pillarsSheet
        pillars = sheet2.row_values(1)

        if pillar_name not in pillars:
            return jsonify({"success": False, "message": "Pillar not found"}), 404

        # Find the column index of the pillar (0-based for Google Sheets API)
        pillar_index = pillars.index(pillar_name)

        # Delete the pillar column from the pillarsSheet
        sheet2.delete_dimension('COLUMNS', pillar_index + 1)  # Convert to 1-based index

        # Delete the corresponding column from the questionsSheet
        questionsSheet.delete_dimension('COLUMNS', pillar_index + 1)  # Use the same column index

        return jsonify({"success": True, "message": f"Pillar '{pillar_name}' and its associated questions deleted successfully"})
    except Exception as e:
        print(f"Error deleting pillar: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/add-pillar')
def add_pillar_page():
    if 'user_id' not in session or not session.get('is_admin', False):
        return redirect('/')
    return render_template('addPillar.html')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))