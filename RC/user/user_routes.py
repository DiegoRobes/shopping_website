import os
import stripe
import pdfkit
from flask import *
from projects.RC import db
from datetime import datetime
from projects.RC.random_digits import Digits
from projects.RC.models import User, Product, Orders
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, current_user, logout_user, login_required

today = datetime.today()
the_year = today.year

# some config to make good use od pdfkit. Also, you have to create an environment variable using the route as the value
path_wkhtmltopdf = r'C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe'
config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)

# create a flask blueprint for the side of the user routes. this allows us to make the code more readable and focus
# on a large slice of the project here.
user_blueprint = Blueprint('user', __name__, static_folder='static', template_folder='templates')

# get your stripe keys by creating an account, import them as environment variables to keep them save. never put
# them in the script as plain text
stripe_keys = {
    "secret_key": os.environ.get("STRIPE_SECRET_KEY"),
    "publishable_key": os.environ.get("STRIPE_PUBLISHABLE_KEY"),
}


# ---CLIENT SIDE ROUTES--- #
# index all products from products.db database.
# in the GET method: create a 'shopping_data' key in the session object to manage the client's shopping cart,
# then calculate the quantities and total to pay in the case the shopping cart has been created
# POST method: make variables from the product's display forms (check "user/index.html") to create a new dictionary
# that contains all these variables as values. finally do the calculations on the quantities and individual
# products total price, and append each dictionary in turn to the session['shopping_data'] object
# some special cases are managed there as well to avoid crashes
@user_blueprint.route("/", methods=["GET", "POST"])
def home():
    session['invoice_data'] = []

    if request.method == "POST":
        all_products = Product.query.order_by(Product.id).all()

        if 'shopping_data' not in session:
            session['shopping_data'] = []

        sku = request.form.get("sku")
        name = request.form.get("name")
        img_path = request.form.get("img")
        quant = int(request.form.get("quantity"))
        price = int(request.form.get("price"))
        description = request.form.get("description")
        price_id = request.form.get('price_id')

        try:
            for i in session['shopping_data']:
                if i["sku"] == sku:
                    i["quantity"] += quant
                    if i["quantity"] > 5:
                        i["quantity"] = 5
                        total_products = sum(list(i['quantity'] for i in session['shopping_data']))
                        total_to_pay = sum(list(i['total'] for i in session['shopping_data']))
                        flash(f"You have reached the maximum stock for '{i['name']}'")
                        return render_template("user/index.html", year=the_year, quantity=total_products,
                                               to_pay=total_to_pay, products=all_products, cart=True)
                    i["total"] = i["quantity"] * i["price"]
                    total_products = sum(list(i['quantity'] for i in session['shopping_data']))
                    total_to_pay = sum(list(i['total'] for i in session['shopping_data']))
                    flash(f"Updated quantity for '{i['name']}'")
                    return render_template("user/index.html", year=the_year, quantity=total_products,
                                           to_pay=total_to_pay, products=all_products, cart=True)
        except Exception as e:
            print(e)

        new_add = {
            'sku': sku,
            'name': name,
            'img': img_path,
            'price': price,
            'quantity': quant,
            'total': price * quant,
            'stripe_price_id': price_id,
            'description': description,
        }
        cart_list = session["shopping_data"]
        cart_list.append(new_add)
        session["shopping_data"] = cart_list

        total_products = sum(list(i['quantity'] for i in session['shopping_data']))
        total_to_pay = sum(list(i['total'] for i in session['shopping_data']))

        print(session['shopping_data'])
        flash(f"New product '{new_add['name']}' added to cart.")
        return render_template("user/index.html", year=the_year, quantity=total_products, to_pay=total_to_pay,
                               products=all_products, cart=True)

    if 'shopping_data' not in session:
        session['shopping_data'] = []
    try:
        total_products = sum(list(i['quantity'] for i in session['shopping_data']))
        total_to_pay = sum(list(i['total'] for i in session['shopping_data']))
        # print(session['shopping_data'])
    except KeyError:
        total_products = None
        total_to_pay = None

    all_products = Product.query.order_by(Product.id).all()
    return render_template("user/index.html", year=the_year, products=all_products, cart=True,
                           quantity=total_products, to_pay=total_to_pay)


@user_blueprint.route("/about", methods=["GET"])
def about():
    return render_template("user/About.html", year=the_year)


# here we check the type of user that has been authenticated and render an appropriate view.
# By default, all users have the role of 'user'. 'admin' type user are created in 'admin_routes.py'
@user_blueprint.route("/user", methods=["GET"])
def user():
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect('admin')
        return redirect(url_for("user.account"))
    else:
        return render_template("user/user.html", year=the_year)


# creation of new users with some special cases handling, such as duplicated emails or bad passwords.
# notice that passwords are being hashed with 12 rounds of salt before placing them into the users.db database
@user_blueprint.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if request.method == "POST":
        if User.query.filter_by(email=request.form.get("email")).first():
            flash("This email is already in use.")
            return render_template("user/sign_up.html")

        if request.form.get("password") != request.form.get("confirm-password"):
            flash("Please Confirm your password.")
            return render_template("user/sign_up.html")

        f_name = request.form.get("f_name").capitalize()
        l_name = request.form.get("l_name").capitalize()
        email = request.form.get("email")
        input_password = request.form.get("password")
        hash_pass = generate_password_hash(password=input_password, method="pbkdf2:sha256", salt_length=12)

        # the following warning is a bug in pycharm. the code works fine.
        new_user = User(
            f_name=f_name,
            l_name=l_name,
            email=email,
            password=hash_pass)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        flash("Thank You, your registration is complete!")
        return render_template("user/sign_up.html", year=the_year, register_complete=True)

    return render_template("user/sign_up.html", year=the_year, register_complete=False)


# login route with some basic user's error handling. We query the users database and compare those entries
# to the info submitted. If the authentication process works, we use login_user()
# func to log in the user into the app session
@user_blueprint.route("/log", methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        input_password = request.form.get("password")
        user_found = User.query.filter_by(email=email).first()

        if not user_found:
            flash("This email is not registered")
            return render_template("user/log_in.html", year=the_year, user_not_found=True)
        else:
            if check_password_hash(pwhash=user_found.password, password=input_password):
                login_user(user_found)
                return redirect(url_for("user.account"))
            else:
                flash("Incorrect Password")
                return render_template("user/log_in.html", year=the_year, logged_user=False)

    return render_template("user/log_in.html", year=the_year, logged_user=False,
                           logged_in=current_user.is_authenticated)


# handling for 'admin' and 'user' types of users. The decorator @login_required ensures this view is only
# visible to logged-in users. if the user logged-in is of the 'admin' type, they are redirected to the admin dashboard
@user_blueprint.route("/my_account", methods=["GET", "POST"])
@login_required
def account():
    if request.method == "POST":
        client = User.query.filter_by(id=current_user.id).first()
        client.address = request.form.get("update_address")
        client.city = request.form.get("update_city")
        client.state = request.form.get("update_state")
        client.zip = request.form.get("update_zip")
        db.session.commit()
        return redirect("/my_account")

    if current_user.is_admin():
        return redirect('admin')
    else:
        client = User.query.filter_by(id=current_user.id).first()
        return render_template("user/my_account.html", year=the_year, client=client)


# important to user logout_user() func here. otherwise this route does nothing
@user_blueprint.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('user.home'))


# the post method deals with a product being deleted from the session['shopping_data'], but only deleted.
# the edited quantity is handled below
@user_blueprint.route("/cart", methods=["GET", "POST"])
def cart():
    if request.method == "POST":
        to_delete = request.form.get('sku')
        try:
            for i in session['shopping_data']:
                if i['sku'] == to_delete:
                    cart_list = session["shopping_data"]
                    cart_list.remove(i)
                    session["shopping_data"] = cart_list

        except Exception as e:
            print('cart deleting exception: ', e)

        total_products = sum(list(i['quantity'] for i in session['shopping_data']))
        total_to_pay = sum(list(i['total'] for i in session['shopping_data']))
        # print(session['shopping_data'])
        return render_template("user/cart.html", year=the_year, quantity=total_products, to_pay=total_to_pay)

    total_products = sum(list(i['quantity'] for i in session['shopping_data']))
    total_to_pay = sum(list(i['total'] for i in session['shopping_data']))
    # print(session['shopping_data'])
    return render_template("user/cart.html", year=the_year, quantity=total_products, to_pay=total_to_pay)


# whe the quantity of a product is changed, we catch that new info from the form and use it to edit the
# existing object in the session['shopping_data']
@user_blueprint.route("/cart/update", methods=["GET", "POST"])
def edit_cart():
    if request.method == "POST":
        sku = request.form.get('sku')
        new_quant = int(request.form.get('save'))
        cart_list = session["shopping_data"]
        try:
            for i in cart_list:
                if i['sku'] == sku:
                    i['quantity'] = new_quant
                    i['total'] = i['quantity'] * i['price']
                    session["shopping_data"] = cart_list
        except Exception as e:
            print('cart deleting exception: ', e)

        total_products = sum(list(i['quantity'] for i in session['shopping_data']))
        total_to_pay = sum(list(i['total'] for i in session['shopping_data']))
        # print(session['shopping_data'])
        return render_template("user/cart.html", year=the_year, quantity=total_products, to_pay=total_to_pay)

    total_products = sum(list(i['quantity'] for i in session['shopping_data']))
    total_to_pay = sum(list(i['total'] for i in session['shopping_data']))
    # print(session['shopping_data'])
    return render_template("user/cart.html", year=the_year, quantity=total_products, to_pay=total_to_pay)


# use the <name> arg to find the product on the database and display it later
@user_blueprint.route("/view_product/<name>", methods=["GET", "POST"])
def view_product(name):
    product = Product.query.filter_by(item_name=name).first()
    return render_template("user/article.html", year=the_year, item=product)


# this route checks if a user is logged in, and is the user has registered their billing address,
# this way the billing details can be pre-filled.
# if none of these conditions are met, exceptions are handled and the template is rendered with generic placeholders
@user_blueprint.route("/billing-details", methods=["GET", "POST"])
def billing_details():
    session['invoice_data'] = []
    try:
        client = User.query.filter_by(id=current_user.id).first()
        if client.address is None:
            return render_template('user/billing_details.html', year=the_year, client=client, address=False)
        return render_template('user/billing_details.html', year=the_year, client=client, address=True)
    except Exception as e:
        print(e)
        return render_template('user/billing_details.html', year=the_year, client=None)


# creates a checkout session in Stripe using their api service. to do so, we create a line_items list and a couple
# of urls to feed the params of the api request. if payment goes through we send client to an invoice view,
# if not, we send them back to their cart
@user_blueprint.route("/create-checkout-session", methods=["GET", "POST"])
def create_checkout_session():
    now = datetime.now()

    total_to_pay = sum(list(i['total'] for i in session['shopping_data']))

    digits = Digits()
    random_digits = digits.create_new()

    session['invoice_data'] = []

    new_invoice = {
        "client": request.form.get('fullname'),
        "email": request.form.get('email'),
        "order_id": f"{now.strftime('%m%d%y-%H%M%S-%f')}-{random_digits}",
        "date": now.strftime('%m-%d-%y %H:%M:%S.%f'),
        "address": request.form.get('address'),
        "city": request.form.get('city'),
        "state": request.form.get('state'),
        "zip": request.form.get('zip'),
        "total": total_to_pay,
    }
    session['invoice_data'].append(new_invoice)

    domain_url = "http://127.0.0.1:5000/"
    stripe.api_key = stripe_keys["secret_key"]

    line_items = []
    print(session['shopping_data'])
    for i in session['shopping_data']:
        item = {
            'quantity': i['quantity'],
            'price': i['stripe_price_id']
        }
        line_items.append(item)
    print(line_items)
    try:
        # Create new Checkout Session for the order
        # Other optional params include:
        # [billing_address_collection] - to display billing address details on the page
        # [customer] - if you have an existing Stripe Customer ID
        # [payment_intent_data] - capture the payment later
        # [customer_email] - prefill the email input in the form
        # For full details see https://stripe.com/docs/api/checkout/sessions/create

        # ?session_id={CHECKOUT_SESSION_ID} means the redirect will have the session ID set as a query param
        checkout_session = stripe.checkout.Session.create(
            success_url=domain_url + "order_completed",
            cancel_url=domain_url + "billing_details",
            payment_method_types=["card"],
            mode="payment",
            line_items=line_items
        )
        # return jsonify({"sessionId": checkout_session["id"]})
        return redirect(checkout_session.url)
    except Exception as e:
        return jsonify(error=str(e)), 403


# only after the payment is done we create and place the order inside the orders database.
# To feed to the model we use the info from the session['invoice_data'] key.
# we use the same session['invoice_data'] key to create an invoice view and later the
# generation of and invoice pdf
# in the POST method we clear the client's cart now that the transaction is complete, and send them back to the
# main page
@user_blueprint.route("order_completed", methods=["GET", "POST"])
def success():
    if not session['invoice_data']:
        return redirect("/")

    if request.method == "POST":
        session['shopping_data'] = []
        return redirect("/")

    order_dict = {}
    for i in session['shopping_data']:
        order_dict[i['sku']] = i['quantity']

    new_order = Orders(
        client=session['invoice_data'][0]['client'],
        date=session['invoice_data'][0]['date'],
        email=session['invoice_data'][0]['email'],
        address=session['invoice_data'][0]['address'],
        city=session['invoice_data'][0]['city'],
        state=session['invoice_data'][0]['state'],
        zip=session['invoice_data'][0]['zip'],
        products_sku=str(order_dict),
        total=session['invoice_data'][0]['total'],
        order_id=session['invoice_data'][0]['order_id']
    )
    db.session.add(new_order)
    db.session.commit()
    if not session['invoice_data']:
        return redirect("/")

    total_to_pay = sum(list(i['total'] for i in session['shopping_data']))
    now = datetime.now()
    date = now.strftime('%m-%d-%y')
    return render_template("user/invoice.html", year=the_year, total_to_pay=total_to_pay, buttons=True, date=date)


# allows the user to download the invoice.html file as a pdf, after dynamically replacing the contents using the
# session['invoice_data'] and session['shopping_data'] objects created beforehand. after everything is done and
# the pdf is dispatched, we clear both objects to finish the client's shopping session
@user_blueprint.route("invoice", methods=["GET"])
def invoice():
    if not session['invoice_data']:
        return redirect("/")

    now = datetime.now()
    date = now.strftime('%m-%d-%y')

    total_to_pay = sum(list(i['total'] for i in session['shopping_data']))

    template = render_template("user/invoice.html", year=the_year, total_to_pay=total_to_pay, date=date, buttons=False)

    pdf = pdfkit.from_string(template, False, options={"enable-local-file-access": True,
                                                       'encoding': "UTF-8"})

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=invoice.pdf'

    session['shopping_data'] = []
    session['invoice_data'] = []
    return response
