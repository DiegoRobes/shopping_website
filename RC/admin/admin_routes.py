import os
from flask import *
from functools import wraps
from datetime import datetime
from projects.RC import db, app
from werkzeug.utils import secure_filename
from projects.RC.models import User, Product, Orders
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, current_user, logout_user, login_required

today = datetime.today()
the_year = today.year

# this single line creates the blueprint for this side of the project, which later will be sent to and registered in
# the main run script
second = Blueprint('second', __name__, static_folder='static', template_folder='templates')

# to make sure the files updated by the admins are safe to store
img_folder_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__))) + r'\static\products'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# uses the is_admin func defined on the Models script
def check_admin():
    try:
        if current_user.is_admin():
            return True
        else:
            return False
    except AttributeError:
        pass


# this one is to make sure the authenticated user is of the 'admin' type
def check_role(roles):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if current_user.is_authenticated:
                if current_user.is_admin():
                    return func(*args, **kwargs)
                else:
                    return redirect('/')
            else:
                return redirect('/')
        return wrapper
    return decorator


# ---ADMIN SIDE ROUTES--- #
# the main admin view has two versions, and the different methods deal with each one
@second.route("/", methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        employee = request.form.get('employee')
        if "@" in employee:
            flash('Wrong ID, please check it')
            return render_template("admin/admin.html", year=the_year, admin_logged=False)

        password = request.form.get('password')
        emp_found = User.query.filter_by(employee_id=employee).first()

        if not emp_found:
            flash('Wrong ID, please check it')
            return render_template("admin/admin.html", year=the_year, admin_logged=False)
        if check_password_hash(pwhash=emp_found.password, password=password):
            login_user(emp_found)
            return redirect("/admin/dashboard")
        else:
            flash('Wrong password')
            return render_template("admin/admin.html", year=the_year, admin_logged=False)

    if current_user.is_authenticated:
        return redirect("/admin/dashboard")

    return render_template("admin/admin.html", year=the_year, admin_logged=False)


# if the user is logged in and the @check_role decorator determines they are a 'admin' type user, they are
# redirected to the admin dashboard
@second.route("/dashboard", methods=['GET'])
@login_required
@check_role(['admin'])
def dashboard():
    return render_template("admin/admin.html", year=the_year, admin_logged=True)


# this route manages the registration of employees using their company information.
# this is not safe on its own, since there is no way to know if the information provided is accurate.
# a database hosting the employees' information is necessary to compare the registration form
@second.route("/employee-registration", methods=['GET', 'POST'])
def emp_register():
    if request.method == "POST":
        if User.query.filter_by(employee_id=request.form.get("emp-id")).first():
            flash("This ID is already in use.")
            return render_template("admin/employee-registration.html")

        if request.form.get("password") != request.form.get("confirm-password"):
            flash("Please Confirm your password.")
            return render_template("admin/employee-registration.html")

        input_password = request.form.get("password")

        # ignore this warning, it is a bug from pycharm.
        new_employee = User(
            f_name=request.form.get("f_name"),
            l_name=request.form.get("l_name"),
            employee_id=request.form.get("emp-id"),
            email=request.form.get('email'),
            user_type='admin',
            password=generate_password_hash(password=input_password, method="pbkdf2:sha256", salt_length=12))
        db.session.add(new_employee)
        db.session.commit()
        login_user(new_employee)
        flash("Thank You, your registration is complete!")
        return render_template("admin/employee-registration.html", year=the_year, register_complete=True)

    return render_template("admin/employee-registration.html", year=the_year, register_complete=False)


# to update the features of the products on the products' database, we ask the user to search by sku code,
# and then we query the products on the db using this code. some exceptions are expected and handled
@second.route("/update-product", methods=["GET", "POST"])
@login_required
@check_role(['admin'])
def update():
    if request.method == 'POST':
        sku = request.form.get("sku").upper()
        find_product = Product.query.filter_by(sku=sku).first()
        if not find_product:
            flash("Unable to find SKU.")
            return render_template("admin/update.html", year=the_year, product_found=False, complete=False)
        else:
            return render_template("admin/update.html", year=the_year, product_found=True, product=find_product,
                                   complete=False)
    return render_template("admin/update.html", year=the_year, product_found=False, complete=False)


# after the user edits the product, we catch the form's information and use it to  change the located products
# and commit the changes. if the product's picture if updated, we use the allowed_file() function to check its
# format before catching the file and moving it into the pre-established img folder
@second.route("/update-complete", methods=["POST"])
@login_required
@check_role(['admin'])
def update_complete():
    if request.method == 'POST':
        sku = request.form.get("sku").upper()
        find_product = Product.query.filter_by(sku=sku).first()
        img = request.files['img']

        if not img:
            find_product.brand = request.form.get('brand')
            find_product.item_name = request.form.get('item_name')
            find_product.price = request.form.get('price').strip('$')
            find_product.description = request.form.get('description')
            db.session.commit()
            flash(f'Article "{request.form.get("item_name")}" updated successfully')
            return render_template("admin/update.html", year=the_year, updated=True, complete=True)

        if img.filename == '':
            flash('This file is not a valid image')
            return render_template("admin/update.html", year=the_year, product_found=True, product=find_product)

        if img and allowed_file(img.filename):
            to_delete = os.path.join(img_folder_path, find_product.item_img_name)
            os.remove(to_delete)
            filename = secure_filename(img.filename)
            find_product.brand = request.form.get('brand')
            find_product.item_name = request.form.get('item_name')
            find_product.price = request.form.get('price').strip('$')
            find_product.description = request.form.get('description')
            find_product.item_img_name = filename
            find_product.img_path = os.path.join(img_folder_path, filename)
            db.session.commit()
            img.seek(0)
            img.save(os.path.join(app.config['UPLOADED_PHOTOS_DEST'], filename))
            flash(f'Article "{request.form.get("item_name")}" updated successfully')
            return render_template("admin/update.html", year=the_year, updated=True, complete=True)


# this proces is very similar to the one in the update route. catch info from forms, check if image is safe to store,
# create a new object using the Product model, and finally commit it to the database
@second.route("/create-product", methods=['GET', 'POST'])
@login_required
@check_role(['admin'])
def create():
    if request.method == "POST":
        img = request.files['img']

        if not img or img.filename == '':
            flash('This file is not a valid image')
            return render_template("admin/create.html", year=the_year, created=False)

        if img and allowed_file(img.filename):
            filename = secure_filename(img.filename)
            new_product = Product(
                brand=request.form.get('brand'),
                item_name=request.form.get('item_name'),
                price=request.form.get('price'),
                description=request.form.get('description'),
                sku=request.form.get('sku'),
                item_img_name=filename,
                img_path=os.path.join(img_folder_path, filename),
                stripe_price_id=request.form.get('price_id')
            )
            db.session.add(new_product)
            db.session.commit()

            img.seek(0)
            img.save(os.path.join(app.config['UPLOADED_PHOTOS_DEST'], filename))

            flash(f'Product {filename} created successfully.')
            return render_template("admin/create.html", year=the_year, created=True)

    return render_template("admin/create.html", year=the_year, created=False)


# query all the products on the database using the Product model, and send them into the view to be rendered
@second.route("/all-products", methods=['GET', 'POST'])
@login_required
@check_role(['admin'])
def all_products():
    products = Product.query.order_by(Product.id).all()
    return render_template('admin/all-products.html', products=products)


@second.route("/report", methods=['GET', 'POST'])
@login_required
@check_role(['admin'])
def report():
    if request.method == "POST":

        date = request.form.get("date")
        requested_date = Orders.query.filter_by(date=date).all()

        if not requested_date:
            flash("No orders found, please try another date.")
            return render_template("admin/report.html", year=the_year, found=False)

        total_orders = 0
        earnings = 0
        outer_list = []

        for i in requested_date:
            total_orders += 1
            earnings += int(i.total)
            skus = i.products_sku.replace("{", "").replace("}", "").replace("'", "").replace(" ", "")

            if "," in skus:
                new = skus.replace(",", " ")
                new_new = new.split(" ")

                for j in new_new:
                    outer_list.append(j.split(":"))

            inner = skus.split(":")
            outer_list.append(inner)

            for x in outer_list:
                if len(x) > 2:
                    outer_list.remove(x)

        total_articles = 0
        day_articles = {}

        for i in outer_list:
            total_articles += int(i[1])
            day_articles[i[0]] = 0

        for x in day_articles:
            for i in outer_list:
                if x == i[0]:
                    day_articles[x] += int(i[1])

        return render_template("admin/report.html", year=the_year, found=True, date=date, report=requested_date,
                               orders=total_orders, articles=total_articles, by_sku=day_articles, earnings=earnings)

    return render_template("admin/report.html", year=the_year, found=False)


# hast la vista, baby
@second.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('user.home'))
