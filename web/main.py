from stock_syncer import StockSyncer
import os
from random import randrange

from flask import Blueprint, render_template, current_app, request, jsonify
from flask_login import login_required, current_user

from google.auth.transport.requests import Request

import logging

logger = logging.getLogger("main")

# XXX path hack
import sys

main_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.append(main_dir)

FAILED = [
    "https://i.giphy.com/media/MVgLEacpr9KVK172Ne/giphy.gif",
    "https://i.giphy.com/media/RJaUOmpBQAoE4RuWnj/giphy.gif",
    "https://i.giphy.com/media/3o7buakWd3wWO9xKDe/giphy.gif",
    "https://i.giphy.com/media/gLK3zNP5T51zfGeMmk/giphy.gif",
]

OK = [
    "https://i.giphy.com/media/Q732zaivQ5y9aECIPd/giphy.gif",
    "https://i.giphy.com/media/HX3lSnGXZnaWk/giphy.gif",
    "https://i.giphy.com/media/lxcz7ntpCKJfq/giphy.gif",
    "https://i.giphy.com/media/tyxovVLbfZdok/giphy.gif",
    "https://i.giphy.com/media/nXxOjZrbnbRxS/giphy.gif",
]


def get_failed():
    id = randrange(0, len(FAILED))
    return FAILED[id]


def get_ok():
    id = randrange(0, len(OK))
    return OK[id]


main = Blueprint("main", __name__)


@main.route("/")
@login_required
def index():
    drive = current_app.config["ROB_DRIVE"]
    spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{drive['sheetId']}"
    return render_template("upload.html", spreadsheet_url=spreadsheet_url)


@main.route("/upload", methods=["POST"])
@login_required
def upload_xls():
    logger.info("Upload called")
    drive = current_app.config["ROB_DRIVE"]
    stock = current_app.config["ROB_STOCK"]
    creds = current_app.config["ROB_CREDS"]
    dry_run = drive["dry_run"]
    if request.files:
        try:
            xls = request.files["xls"]
            xls_data = xls.read()
            # refresh creds is needed
            if not creds.valid:
                logger.warning("Invalid creds")
                if creds.expired and creds.refresh_token:
                    logger.info("Try to refresh credentials")
                    creds.refresh(Request())
                    # readd in config
                    current_app.config["ROB_CREDS"] = creds
                else:
                    logger.error("Invalid credentials")
                    return (
                        jsonify(
                            {"image": get_failed(), "error": "Invalid credentials"}
                        ),
                        500,
                    )
            stockSyncer = StockSyncer(drive=drive, stock=stock, credentials=creds)
            result = stockSyncer.sync(xls_data, dry=dry_run)
            logger.debug("Call stockSyncer update error")
            stockSyncer.update_error(result=result)
        except Exception as e:
            logger.error(f"Exception: {e}")
            return jsonify({"image": get_failed(), "error": str(e)}), 500
        return jsonify({"image": get_ok(), "missing_ids": result["missing_ids"]})
    return jsonify({"image": get_failed(), "error": "Missing file"}), 403
