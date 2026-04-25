from pymysql import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.db import execute, execute_and_get_id, query_one
from app.models import AppUser


bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dishes.list_dishes"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        profile_picture = request.form.get("profile_picture", "").strip() or None

        if not username or not email or not password:
            flash("Username, email, and password are required.", "danger")
            return render_template("auth/register.html")

        user_count_row = query_one("SELECT COUNT(*) AS cnt FROM `User`")
        is_first_user = user_count_row and user_count_row["cnt"] == 0

        try:
            user_id = execute_and_get_id(
                """
                INSERT INTO `User` (username, email, password, admin, profile_picture)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (username, email, generate_password_hash(password), is_first_user, profile_picture),
            )
        except IntegrityError:
            flash("That username or email is already in use.", "danger")
            return render_template("auth/register.html")

        user_row = query_one(
            """
            SELECT user_id, username, email, admin, profile_picture
            FROM `User`
            WHERE user_id = %s
            """,
            (user_id,),
        )
        login_user(AppUser.from_row(user_row))
        flash("Account created successfully.", "success")
        return redirect(url_for("dishes.list_dishes"))

    return render_template("auth/register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dishes.list_dishes"))

    if request.method == "POST":
        identity = request.form.get("identity", "").strip()
        password = request.form.get("password", "")

        user_row = query_one(
            """
            SELECT user_id, username, email, password, admin, profile_picture
            FROM `User`
            WHERE username = %s OR email = %s
            """,
            (identity, identity),
        )

        if not user_row or not check_password_hash(user_row["password"], password):
            flash("Invalid credentials.", "danger")
            return render_template("auth/login.html")

        login_user(AppUser.from_row(user_row))
        flash("Welcome back.", "success")
        return redirect(url_for("dishes.list_dishes"))

    return render_template("auth/login.html")


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        profile_picture = request.form.get("profile_picture", "").strip() or None

        if not username or not email:
            flash("Username and email are required.", "danger")
            return redirect(url_for("auth.profile"))

        try:
            execute(
                """
                UPDATE `User`
                SET username = %s, email = %s, profile_picture = %s
                WHERE user_id = %s
                """,
                (username, email, profile_picture, current_user.user_id),
            )
            flash("Profile updated.", "success")
        except IntegrityError:
            flash("Username or email already exists.", "danger")

        return redirect(url_for("auth.profile"))

    user_row = query_one(
        """
        SELECT user_id, username, email, admin, profile_picture
        FROM `User`
        WHERE user_id = %s
        """,
        (current_user.user_id,),
    )
    return render_template("auth/profile.html", profile=user_row)


@bp.post("/password")
@login_required
def change_password():
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")

    if not new_password:
        flash("New password is required.", "danger")
        return redirect(url_for("auth.profile"))

    user_row = query_one(
        "SELECT password FROM `User` WHERE user_id = %s",
        (current_user.user_id,),
    )
    if not user_row or not check_password_hash(user_row["password"], current_password):
        flash("Current password is incorrect.", "danger")
        return redirect(url_for("auth.profile"))

    execute(
        "UPDATE `User` SET password = %s WHERE user_id = %s",
        (generate_password_hash(new_password), current_user.user_id),
    )
    flash("Password updated.", "success")
    return redirect(url_for("auth.profile"))


@bp.post("/delete-account")
@login_required
def delete_account():
    user_id = current_user.user_id
    logout_user()
    execute("DELETE FROM `User` WHERE user_id = %s", (user_id,))
    flash("Account deleted.", "info")
    return redirect(url_for("auth.register"))
