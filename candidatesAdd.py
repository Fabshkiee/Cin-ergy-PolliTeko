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

candidatesBP = Blueprint('matching', __name__)

def getAllOptions():
    keyWords = sheet.get_values('A2:A5')
    
    return [item for sublist in keywords for item in sublist]
    
    
@candidatesBP.route('/quiz')
def quizCard():
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