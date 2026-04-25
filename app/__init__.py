from flask import Flask, redirect, render_template, url_for
from flask_login import LoginManager, current_user

from app.config import Config
from app.db import init_app as init_db
from app.models import load_user_from_db


login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"


@login_manager.user_loader
def load_user(user_id):
    return load_user_from_db(user_id)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    init_db(app)
    login_manager.init_app(app)

    from app.auth.routes import bp as auth_bp
    from app.dishes.routes import bp as dishes_bp
    from app.ratings.routes import bp as ratings_bp
    from app.social.routes import bp as social_bp
    from app.admin.routes import bp as admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dishes_bp)
    app.register_blueprint(ratings_bp)
    app.register_blueprint(social_bp)
    app.register_blueprint(admin_bp)

    @app.get("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("dishes.list_dishes"))
        return render_template("index.html")

    return app
