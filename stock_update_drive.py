#!/usr/bin/env python
import pickle
import os.path
import sys
from configparser import ConfigParser
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from stock_syncer import StockSyncer


# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/spreadsheets.readonly'
]


def retrieve_credentials():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return creds


def main(stock_file):
    creds = retrieve_credentials()
    # The ID and range of a sample spreadsheet (retrieve from config)
    parser = ConfigParser()
    parser.read('./config.ini')
    drive = {}
    stock = {}
    for kk in ['ID_title', 'stock_title', 'price_title']:
        drive[kk] = parser.get('drive', kk)
        stock[kk] = parser.get('stock', kk)
    drive['sheetId'] = parser.get('drive', 'spreadsheet')
    drive['sheetLabel'] = parser.get('drive', 'sheet_label')
    drive['quantity_price_title'] = parser.get('drive', 'quantity_price_title')
    drive['cond_title'] = parser.get('drive', 'cond_title')
    stockSyncer = StockSyncer(drive=drive,
                              stock=stock,
                              credentials=creds
                              )

    # Read stock file
    print("Reading xls file")
    with open(stock_file, 'rb') as f:
        xls_data = f.read()

    stockSyncer.sync(xls_data)


if __name__ == '__main__':

    stock_file = sys.argv[1]
    main(stock_file)
