from projects.RC import db, app
from flask_login import UserMixin


# context-sensitive func that creates mutable default values. this is necessary to create a value that is at the
# same time a default and unique. check 'employee_id' on the User Model
def default(context):
    return context.get_current_parameters()['email']


# to add users to the users.db database, give them the default user type of 'user'. 'admin' type users are
# created in admin_routes.py
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    f_name = db.Column(db.String(100), unique=False, nullable=False)
    l_name = db.Column(db.String(100), unique=False, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(500), unique=False, nullable=False)
    address = db.Column(db.String(200), unique=False, nullable=True, default=None)
    city = db.Column(db.String(50), unique=False, nullable=True, default=None)
    state = db.Column(db.String(50), unique=False, nullable=True, default=None)
    zip = db.Column(db.String(20), unique=False, nullable=True, default=None)
    employee_id = db.Column(db.String(100), unique=True, nullable=False, default=default)
    user_type = db.Column(db.String(20), default='user')

    # a simple function to check if the user type is 'admin'. it becomes useful in the user_routes script
    def is_admin(self):
        if self.user_type == 'admin':
            return True
        else:
            return False


# to add products to the products.db database. it is important to create stripe products and import their codes.
# see stripe documentation
class Product(db.Model):
    __bind_key__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(100), unique=False)
    item_name = db.Column(db.String(100), unique=True, nullable=False)
    price = db.Column(db.String(50), unique=False, nullable=False)
    description = db.Column(db.String(1000), unique=False, nullable=False)
    sku = db.Column(db.String(100), unique=True, nullable=True)
    item_img_name = db.Column(db.String(500), unique=False, nullable=False)
    img_path = db.Column(db.String(1000), unique=True, nullable=False)
    stripe_price_id = db.Column(db.String(1000), unique=True, nullable=False)


class Orders(db.Model):
    __bind_key__ = 'orders'
    id = db.Column(db.Integer, primary_key=True, unique=True)
    date = db.Column(db.String(100), unique=False)
    client = db.Column(db.String(100), unique=False)
    email = db.Column(db.String(100), unique=False)
    address = db.Column(db.String(200), unique=False)
    city = db.Column(db.String(50), unique=False)
    state = db.Column(db.String(50), unique=False)
    zip = db.Column(db.String(20), unique=False)
    products_sku = db.Column(db.String(100), unique=False)
    total = db.Column(db.String(20), unique=False)
    order_id = db.Column(db.String(100), unique=True)


with app.app_context():
    db.create_all()
