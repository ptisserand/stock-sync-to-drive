#!/usr/bin/env python
import pickle
import os.path
import sys
import logging

from argparse import ArgumentParser
from configparser import ConfigParser
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from stock_syncer import StockImage


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
    kwargs = {}

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
    
    for kk in ['ID_title', 'images_title']:
        drive[kk] = parser.get('drive', kk)
    
    stockImage = StockImage(drive=drive,
                              stock=stock,
                              credentials=creds
                              )

    # Read stock file
    urls_file = args.urls
    images_mapping = {}
    with open(urls_file, 'r') as f:
        lines = f.read().split('\n')
    logger.debug(f"Number of lines: {len(lines)}")
    for line in lines:
        if line == '':
            continue
        name, url = line.split('|')
        ugs = name.split('-')[0]
        url = url.strip()
        images_mapping[ugs] = url
    logger.info(f"Number of images: {len(images_mapping)}")
    result = stockImage.doit(images_mapping=images_mapping)
    print(f"{result}")



if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('urls', help="Path to URL list file")
    parser.add_argument("--token", help="Path to store/retrieve token", required=False)
    parser.add_argument("--config", help="Path to drive/excel configuration file", required=False, default="config.ini")
    parser.add_argument("--log", dest="logLevel", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], 
        help="Set the logging level (default: %(default)s", default="INFO")
    parser.add_argument("--dry-run", help="Don't commit cell update", action="store_true", dest="dry")
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
