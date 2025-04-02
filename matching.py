from flask import Flask, render_template, request, redirect, url_for, session
import gspread
import os
from google.oauth2.service_account import Credentials

client = gspread.authorize(creds)

sheet_id = "15P43fHag6Va8upWyhvUJwV0ECbtU4zeMsFp5DiPUXzM"
workbook = client.open_by_key(sheet_id)
sheet = workbook.worksheet("pillars")

def getOptions():
    getAllValues = sheet.get_all_values()
    
    
    