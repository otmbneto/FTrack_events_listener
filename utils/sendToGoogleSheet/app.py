"""
Shows basic usage of the Apps Script API.
Call the Apps Script API to create a new script project, upload a file to the
project, and log the script's URL to the user.
"""
from __future__ import print_function

import os
import sys
import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient import errors
from googleapiclient.discovery import build
import httplib2

class ShotsSheet():


    def __init__(self):

        self.credentials = self.getCredentials()
        self.service = build('sheets', 'v4',credentials=self.credentials)
        self.sheet = self.service.spreadsheets()
        self.ftrack_data = {}
        self.google_data = {}

        return

    def getSpreadsheets(self,input_data):

        self.ftrack_data[input_data["spreadsheet_id"]] = input_data
        self.google_data[input_data["spreadsheet_id"]] = self.sheet.values().get(spreadsheetId = self.ftrack_data[input_data["spreadsheet_id"]]["spreadsheet_id"],range = self.ftrack_data[input_data["spreadsheet_id"]]["sheet_name"]).execute()["values"]
        self.getImportantCollumns(input_data["spreadsheet_id"])

        return input_data["spreadsheet_id"]

    def getSheetData(self,gid):

        return self.google_data[gid]

    def getImportantCollumns(self,gid):


        if self.ftrack_data[gid]["spreadsheet_type"] == "animation":

            self.status = 14
            self.statusBlo = 15
            self.statusPol = 16
            self.shotsCol = 2
            self.sequenceCol = 1
            self.startLine = 1

        elif self.ftrack_data[gid]["spreadsheet_type"] == "render":

            self.status = 14
            self.assigneeRender = 8
            self.statusRender = 9
            self.dateRender = 10
            self.assigneeComp = 13
            self.statusComp = 14
            self.dateComp = 15
            self.shotsCol = 2
            self.sequenceCol = 1
            self.startLine = 2

        elif self.ftrack_data[gid]["spreadsheet_type"] == "geral":

            self.framesCol = 2
            self.status = 5
            self.assignee = 3
            self.taskCol = 4
            self.startDate = 8
            self.dueDate = 9
            self.shotsCol = 1
            self.sequenceCol = 0
            self.description = 7
            self.startLine = 197


    def xl_rowcol_to_cell(self,row_num, col_num):

        # Removed these 2 lines if your row, col is 1 indexed.
        row_num += 1
        col_num += 1

        col_str = ''

        while col_num:
            remainder = col_num % 26

            if remainder == 0:
                remainder = 26

            # Convert the remainder to a character.
            col_letter = chr(ord('A') + remainder - 1)

            # Accumulate the column letters, right to left.
            col_str = col_letter + col_str

            # Get the next order of magnitude.
            col_num = int((col_num - 1) / 26)

        return col_str + str(row_num)


    def findShot(self,gid,shot_code):

        for i in range(len(self.google_data[gid])):

            if self.shotsCol < len(self.google_data[gid][i]) and shot_code == self.google_data[gid][i][self.shotsCol]:

                return i

        return None

    def findTask(self,gid,task_name,start_line):

        for i in range(start_line,len(self.google_data[gid])):

            print(task_name + " =? " + self.google_data[gid][i][self.taskCol])
            if task_name == self.google_data[gid][i][self.taskCol]:

                return i

        return None


    def update_value(self,gid,range_name,cells):
        """
        Creates the batch_update the user has access to.
        Load pre-authorized user credentials from the environment.
        TODO(developer) - See https://developers.google.com/identity
        for guides on implementing OAuth2 for the application.
            """

        range_name = self.ftrack_data[gid]["sheet_name"] + "!" + range_name
        try:
            values = [cells]
            body = {
                'values': values
            }
            result = self.sheet.values().update(spreadsheetId=gid, range=range_name,valueInputOption="USER_ENTERED",body=body).execute()
            print(f"{result.get('updatedCells')} cells updated.")
            return result
        except errors.HttpError as error:
            print(f"An error occurred: {error}")
            return error

    def setShotStatus(self,input_data):

        gid = self.getSpreadsheets(input_data)
        
        line = self.findShot(gid,self.ftrack_data[gid]["shot"])
        if self.ftrack_data[gid]["spreadsheet_type"] == "animation":
            col = self.statusBlo if self.ftrack_data[gid]["task"] == "blocking" else self.statusPol
            srange = self.xl_rowcol_to_cell(line,col)
            self.update_value(gid,self.xl_rowcol_to_cell(line,col),[self.ftrack_data[gid]["status"]])
        elif self.ftrack_data[gid]["spreadsheet_type"] == "render":
            start_col = self.assigneeRender if self.ftrack_data[gid]["task"] == "render" else self.assigneeComp
            end_col = self.dateRender if self.ftrack_data[gid]["task"] == "render" else self.dateComp
            srange = self.xl_rowcol_to_cell(line,start_col) + ":" + self.xl_rowcol_to_cell(line,end_col)
            self.update_value(gid,srange,[self.ftrack_data[gid]["assignees"],self.ftrack_data[gid]["status"],self.ftrack_data[gid]["date"]])

        elif self.ftrack_data[gid]["spreadsheet_type"] == "geral":
            line = self.findTask(gid,self.ftrack_data[gid]["task"],line)
            srange = self.xl_rowcol_to_cell(line,self.framesCol) + ":" + self.xl_rowcol_to_cell(line,self.dueDate)
            cells = [self.ftrack_data[gid]["fps"],self.ftrack_data[gid]["assignees"],self.ftrack_data[gid]["task"],self.ftrack_data[gid]["status"],self.ftrack_data[gid]["task_type"],self.ftrack_data[gid]["description"],self.ftrack_data[gid]["start"],self.ftrack_data[gid]["end"]]
            self.update_value(gid,srange,cells)


        return


    def getCredentials(self):

        SCOPES = os.getenv("GOOGLE_SCOPES").split(",")
        """Calls the Apps Script API.
        """
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.

        current_path = os.path.dirname(os.path.realpath(__file__))
        if os.path.exists(os.path.join(current_path,'token.json')):
            creds = Credentials.from_authorized_user_file(os.path.join(current_path,'token.json'), SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(os.path.join(current_path,'credentials.json'), SCOPES)
                
                http = httplib2.Http(timeout=300)
                creds = flow.run_local_server(http=http,access_type='offline')
            # Save the credentials for the next run
            with open(os.path.join(current_path,'token.json'), 'w') as token:
                token.write(creds.to_json())

        return creds


def main():

    argv = sys.argv
    try:
        data = json.loads(argv[1])
        sheet = ShotsSheet()
        sheet.setShotStatus(data)
    except errors.HttpError as error:
        # The API encountered a problem.
        print(error.content)

if __name__ == '__main__':
    main()