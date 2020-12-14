#!/usr/bin/env python
import pickle
import os.path
import sys
import logging
import pandas as pd

from argparse import ArgumentParser
from configparser import ConfigParser
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from stock_syncer import StockSyncer


logger = logging.getLogger('syncer')

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
    if args.dry is True:
        logger.info("Running dry run")

    if args.token:
        kwargs['token_path'] = args.token
    logger.info("Retrieving credentials")
    creds = retrieve_credentials(**kwargs)

    # The ID and range of a sample spreadsheet (retrieve from config)
    parser = ConfigParser()
    parser.read(args.config)
    drive = {}
    stock = {}
    drive['sheetId'] = parser.get('drive', 'spreadsheet')
    drive['sheetLabel'] = parser.get('drive', 'sheet_label')
    
    for kk in ['ID_title', 'stock_title', 'price_title', 'TVA_title']:
        drive[kk] = parser.get('drive', kk)
        stock[kk] = parser.get('stock', kk)
    
    stock['name_title'] = parser.get('stock', 'name_title')
    stock['by_unit_title'] = parser.get('stock', 'by_unit_title')

    drive['quantity_price_title'] = parser.get('drive', 'quantity_price_title')
    drive['cond_title'] = parser.get('drive', 'cond_title')
    stockSyncer = StockSyncer(drive=drive,
                              stock=stock,
                              credentials=creds
                              )

    # Read stock file
    logger.info("Reading xls file")
    with open(stock_file, 'rb') as f:
        xls_data = f.read()

    result = stockSyncer.sync(xls_data, dry=args.dry)
    for elem in result['missing_ids']:
        print(f"{elem['id']}, {elem['name']}")
    if args.output:
        ids = [elem['id'] for elem in result['missing_ids']]
        names = [elem['name'] for elem in result['missing_ids']]
        df = pd.DataFrame({"ID": ids, "Name": names})
        # Create a Pandas Excel writer using XlsxWriter as the engine.
        writer = pd.ExcelWriter(args.output, engine='xlsxwriter')
        # Convert the dataframe to an XlsxWriter Excel object.
        df.to_excel(writer, sheet_name='IDs manquants', index=False)
        # Close the Pandas Excel writer and output the Excel file.
        writer.save()


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('stock', help="Path to xls exported stock file")
    parser.add_argument("--token", help="Path to store/retrieve token", required=False)
    parser.add_argument("--config", help="Path to drive/excel configuration file", required=False, default="config.ini")
    parser.add_argument("--dry-run", help="Don't commit cell update", action="store_true", dest="dry")
    parser.add_argument("--log", dest="logLevel", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], 
        help="Set the logging level (default: %(default)s", default="INFO")
    parser.add_argument("--output", help="Path to report file")

    args = parser.parse_args()
    log_level = logging.getLevelName(args.logLevel)
    logger.setLevel(log_level)
    ch = logging.StreamHandler()
    # ch.setLevel(logging.DEBUG)
    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')    
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(ch)
    
    main(args)
