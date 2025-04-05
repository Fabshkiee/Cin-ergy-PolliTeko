from flask import Flask, render_template, request, redirect, url_for, session, Blueprint
import gspread
import os
from google.oauth2.service_account import Credentials

scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("/storage/emulated/0/MGIT/Cin-ergy-PolliTeko/upvhackathonCreds.json", scopes=scopes)

client = gspread.authorize(creds)

sheet_id = "15P43fHag6Va8upWyhvUJwV0ECbtU4zeMsFp5DiPUXzM"
workbook = client.open_by_key(sheet_id)
sheet = workbook.worksheet("candidates")
educSheet = workbook.worksheet("education")
experienceSheet = workbook.worksheet("experience")
achievementsSheet = workbook.worksheet("achievements")

candidatesBP = Blueprint('matching', __name__)

def getAllOptions():
    keyWords = sheet.get_values('A2:A5')
    
    return [item for sublist in keywords for item in sublist]
    
    
@candidatesBP.route('/quiz')
def quizCard():
    render_templates("pretest.html")
    options = getAllOptions()
    
    questions = [
        {
            'id': 1,
            'text': 'Select the most relevant keyword:',
            'options': options  # Use the keywords from your sheet
        },
        # Add more questions as needed
    ]
    
    return render_template('quiz.html', questions=questions)

#add candidates credentials to sheet from addCandidate.html
@candidatesBP.route('/addCandidate', methods=['POST'])
def addCandidate():
    if request.method == 'POST':
        # Get the form data
        fname  = "FirstName"
        Mname = "MiddleName"
        lname = "LastName"
        region = "region"
        prov = "province"
        city = "city"
        bio = "biography"
        birthday = "bday"
        politicalParty = "party"
        education = "education[]"
        experience = "experience[]"
        achievements = "achievements[]" 
        photo = "photo"

        for edu in education:
            educSheet.append_col.max_row(['education', edu])
        for exp in experience:
            experienceSheet.append_col(['experience', exp])
        for ach in achievements:
            achievementsSheet.append_col(['achievements', ach])
        
        row = sheet.row_count + 1
        sheet.update_cell(row, 1, fname)
        sheet.update_cell(row, 2, Mname)
        sheet.update_cell(row, 3, lname)
        sheet.update_cell(row, 4, region)
        sheet.update_cell(row, 5, prov)
        sheet.update_cell(row, 6, city)
        sheet.update_cell(row, 7, bio)
        sheet.update_cell(row, 8, birthday)
        sheet.update_cell(row, 9, politicalParty)
        sheet.update_cell(row, 10, photo)


        