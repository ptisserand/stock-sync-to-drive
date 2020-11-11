#!/usr/bin/env python
import pickle
import os.path
import sys
from configparser import ConfigParser

from flask import Flask
from flask import request, redirect, send_from_directory, Response
from flask import jsonify
from stock_syncer import StockSyncer

app = Flask(__name__)
FAILED = [
    "https://i.giphy.com/media/MVgLEacpr9KVK172Ne/giphy.webp",
    "https://i.giphy.com/media/RJaUOmpBQAoE4RuWnj/source.gif"
]

OK = [
    "https://i.giphy.com/media/Q732zaivQ5y9aECIPd/giphy.webp",
    "https://i.giphy.com/media/HX3lSnGXZnaWk/giphy.webp"
]

@app.route("/upload", methods=["POST"])
def upload_xls():
    print("Upload called")  
    if request.files:
        try:
            xls = request.files["xls"]
            print(xls)
            xls_data = xls.read()
            print(len(xls_data))
            # app.stockSyncer.sync(xls_data)
        except Exception as e:
            return jsonify(error=str(e)), 500
        return jsonify({})
    return jsonify(error="Missing file"), 403

@app.route("/", methods=["GET"])
def home():
    return app.send_static_file("html/upload.html")

if __name__ == "__main__":
    creds = None
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
    # The ID and range of a sample spreadsheet (retrieve from config)
    parser = ConfigParser()
    parser.read('./config.ini')

    stockSyncer = StockSyncer(sheetId=parser.get('drive', 'spreadsheet'),
        IdTitle=parser.get('drive', 'ID_title'),
        stockTitle=parser.get('drive', 'stock_title'),
        credentials=creds
        )
    app.stockSyncer = stockSyncer
    app.run()