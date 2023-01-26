import os
from flask import *
from flask_sqlalchemy import SQLAlchemy

# create file routes for databases and img managing folder
databases = os.path.abspath(os.path.dirname(__file__)) + r'\databases'
img_folder_path = os.path.abspath(os.path.dirname(__file__)) + r'\static\products'

# app config to create multiple databases and an img folder to manage the products pictures
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SERVER_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(databases, 'users.db')
app.config['SQLALCHEMY_BINDS'] = {'products': 'sqlite:///' + os.path.join(databases, 'products.db'),
                                  'orders': 'sqlite:///' + os.path.join(databases, 'orders.db')}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOADED_PHOTOS_DEST'] = img_folder_path

db = SQLAlchemy(app)
