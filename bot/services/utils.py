from services.user_service import UserService
from models.user import User
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os

def setupGC():
    return gspread.service_account("./google_auth.json")
    credentials = Credentials.from_service_account_file(
        "./google_auth.json",
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    return gspread.authorize(credentials)

async def parse_users_to_sheet(filename: str) -> bool:
    FILE_KEY="1cxSorMRLJ7toj0TK3Cdp77_79lN15cfzXGne0qSApu8"
    gc = setupGC()
    #sheet = gc.create(filename)
    sheet = gc.open_by_key(FILE_KEY)
    wsheet = sheet.sheet1

    sheet.update_title(filename)

    sheet.share(None, perm_type="anyone", role="writer")
    
    columns = [col.name for col in User.__table__.columns]
    # print(columns)
    # columns = [col.name for col in User.__table__.columns if col.name not in ["team_id"]]

    wsheet.clear()
    wsheet.append_row(columns)

    users = await UserService().get_all()
    for user in users:
        row = []
        for col in columns:
            value = getattr(user, col)
            if isinstance(value, datetime):
                value = value.isoformat()
            row.append(value)
        wsheet.append_row(row)
    return sheet.url

