#!/usr/bin/env python
import pickle
import os.path
import sys
from configparser import ConfigParser
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from stock_syncer import StockSyncer



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

    stockSyncer = StockSyncer(sheetId=parser.get('drive', 'spreadsheet'),
        IdTitle=parser.get('drive', 'ID_title'),
        stockTitle=parser.get('drive', 'stock_title'),
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

