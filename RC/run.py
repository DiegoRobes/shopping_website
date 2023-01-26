from projects.RC import app
from admin.admin_routes import second
from user.user_routes import user_blueprint
from flask_login import LoginManager
from projects.RC.models import User

# this is the main script we run to make the show go. Two different blueprints are registered here in the main after
# being imported from their respective scripts (check import lines 2 & 3). This has the objective of dividing
# the whole project so maintenance can be easier. one blueprint for the user-side routes, another for all
# admin-related activities
app.register_blueprint(user_blueprint, url_prefix='/')
app.register_blueprint(second, url_prefix='/admin')

# login_manager function is kept here to be able to serve both sides of the project
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


if __name__ == '__main__':
    app.run(debug=True)
