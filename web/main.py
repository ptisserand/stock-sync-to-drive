from stock_syncer import StockSyncer
import os
from random import randrange

from flask import (
    Blueprint, render_template, current_app, 
    request,
    jsonify
)
from flask_login import (
    login_required, current_user
)

from google.auth.transport.requests import Request

# XXX path hack
import sys
main_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.append(main_dir)

FAILED = [
    "https://i.giphy.com/media/MVgLEacpr9KVK172Ne/giphy.webp",
    "https://i.giphy.com/media/RJaUOmpBQAoE4RuWnj/source.gif"
]

OK = [
    "https://i.giphy.com/media/Q732zaivQ5y9aECIPd/giphy.webp",
    "https://i.giphy.com/media/HX3lSnGXZnaWk/giphy.webp"
]


def get_failed():
    id = randrange(0, len(FAILED))
    return FAILED[id]


def get_ok():
    id = randrange(0, len(OK))
    return OK[id]


main = Blueprint('main', __name__)


@main.route('/')
@login_required
def index():
    return render_template('upload.html')


@main.route("/upload", methods=["POST"])
@login_required
def upload_xls():
    print("Upload called")
    drive = current_app.config['ROB_DRIVE']
    stock = current_app.config['ROB_STOCK']
    creds = current_app.config['ROB_CREDS']    
    if request.files:
        try:
            xls = request.files["xls"]
            xls_data = xls.read()
            # refresh creds is needed
            if not creds.valid:
                if creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    # readd in config
                    current_app.config["ROB_CREDS"] = creds
                else:
                    return jsonify({"image": get_failed(), "error": "Invalid credentials"}), 500
            stockSyncer = StockSyncer(drive=drive, stock=stock, credentials=creds)
            result = stockSyncer.sync(xls_data)
        except Exception as e:
            return jsonify({"image": get_failed(), "error": str(e)}), 500
        return jsonify({"image": get_ok()})
    return jsonify({"image": get_failed(), "error": "Missing file"}), 403
