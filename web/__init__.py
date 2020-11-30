import os
import pickle
from configparser import ConfigParser
import logging

from flask import Flask
from flask_login import LoginManager
from flask.logging import default_handler

root = logging.getLogger()
root.addHandler(default_handler)

MAIN_DIR = os.path.dirname(os.path.dirname(__file__))

def retrieve_configuration():
    creds = None
    config_dir = os.getenv('CONFIG_DIR', MAIN_DIR)
    with open(f'{config_dir}/token.pickle', 'rb') as token:
        creds = pickle.load(token)
    # The ID and range of a sample spreadsheet (retrieve from config)
    parser = ConfigParser()
    parser.read(f'{config_dir}/config.ini')

    drive = {}
    stock = {}
    for kk in ['ID_title', 'stock_title', 'price_title']:
        drive[kk] = parser.get('drive', kk)
        stock[kk] = parser.get('stock', kk)
    stock['name_title'] = parser.get('stock', 'name_title')

    drive['sheetId'] = parser.get('drive', 'spreadsheet')
    drive['sheetLabel'] = parser.get('drive', 'sheet_label')
    drive['quantity_price_title'] = parser.get('drive', 'quantity_price_title')
    drive['cond_title'] = parser.get('drive', 'cond_title')
    return drive, stock, creds

def create_app():
    app = Flask(__name__)
    drive, stock, creds =  retrieve_configuration()
    db_dir = os.getenv('DB_DIR', None)

    app.config['SECRET_KEY'] = 'just-another-secret-here'
    if db_dir is None:
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///db.sqlite'
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_dir}/db.sqlite'
    app.config['ROB_DRIVE'] = drive
    app.config['ROB_STOCK'] = stock
    app.config['ROB_CREDS'] = creds

    from .models import db
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)
    
    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        # since the user_id is just the primary key of our user table, use it in the query for the user
        return User.query.get(int(user_id))
    
    # blueprint for auth routes in our app
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    # blueprint for non-auth parts of app
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app
