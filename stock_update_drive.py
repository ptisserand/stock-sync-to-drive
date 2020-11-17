#!/usr/bin/env python
import pickle
import os.path
import sys

from argparse import ArgumentParser
from configparser import ConfigParser
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from stock_syncer import StockSyncer


# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/spreadsheets.readonly'
]


def retrieve_credentials(token_path='token.pickle'):
    creds = None
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
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
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
    return creds


def main(args):
    stock_file = args.stock
    kwargs = {}
    if args.token:
        kwargs['token_path'] = args.token
    creds = retrieve_credentials(**kwargs)

    # The ID and range of a sample spreadsheet (retrieve from config)
    parser = ConfigParser()
    parser.read(args.config)
    drive = {}
    stock = {}
    for kk in ['ID_title', 'stock_title', 'price_title', 'TVA_title']:
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

    stockSyncer.sync(xls_data, tva=args.tva)


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('stock', help="Path to xls exported stock file")
    parser.add_argument("--token", help="Path to store/retrieve token", required=False)
    parser.add_argument("--enable-tva", help="Enable TVA sync", action="store_true", dest="tva")
    parser.add_argument("--config", help="Path to drive/excel configuration file", required=False, default="config.ini")
    args = parser.parse_args()
    main(args)
