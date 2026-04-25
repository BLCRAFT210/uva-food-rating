from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.db import execute, query_all
from app.security import admin_required


bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.get("/")
@login_required
@admin_required
def dashboard():
    users = query_all(
        """
        SELECT user_id, username, email, admin, profile_picture
        FROM `User`
        ORDER BY user_id ASC
        """
    )

    top_favorites = query_all(
        """
        SELECT d.dish_name, COUNT(f.user_id) AS favorite_count
        FROM Dish d
        LEFT JOIN Favorites f ON d.dish_id = f.dish_id
        GROUP BY d.dish_id, d.dish_name
        ORDER BY favorite_count DESC, d.dish_name ASC
        LIMIT 10
        """
    )

    recent_by_user = query_all(
        """
        SELECT u.username, r.score, r.date_time, d.dish_name
        FROM Rating r
        JOIN `User` u ON r.user_id = u.user_id
        JOIN Dish d ON r.dish_id = d.dish_id
        WHERE (r.user_id, r.date_time) IN (
            SELECT user_id, MAX(date_time)
            FROM Rating
            GROUP BY user_id
        )
        ORDER BY r.date_time DESC
        """
    )

    return render_template(
        "admin/dashboard.html",
        users=users,
        top_favorites=top_favorites,
        recent_by_user=recent_by_user,
    )


@bp.post("/users/<int:user_id>/toggle-admin")
@login_required
@admin_required
def toggle_admin(user_id):
    if user_id == current_user.user_id:
        flash("You cannot change your own admin role here.", "warning")
        return redirect(url_for("admin.dashboard"))

    execute(
        "UPDATE `User` SET admin = NOT admin WHERE user_id = %s",
        (user_id,),
    )
    flash("User role updated.", "success")
    return redirect(url_for("admin.dashboard"))


@bp.post("/users/<int:user_id>/delete")
@login_required
@admin_required
def delete_user(user_id):
    if user_id == current_user.user_id:
        abort(400, "You cannot delete your own account from admin dashboard.")
    execute("DELETE FROM `User` WHERE user_id = %s", (user_id,))
    flash("User deleted.", "info")
    return redirect(url_for("admin.dashboard"))
