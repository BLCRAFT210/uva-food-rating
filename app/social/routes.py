from pymysql.err import IntegrityError

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.db import execute, query_all, query_one, transaction


bp = Blueprint("social", __name__)


@bp.get("/favorites")
@login_required
def favorites():
    rows = query_all(
        """
        SELECT d.dish_id, d.dish_name, l.location_name
        FROM Favorites f
        JOIN Dish d ON f.dish_id = d.dish_id
        LEFT JOIN Location l ON d.location_id = l.location_id
        WHERE f.user_id = %s
        ORDER BY d.dish_name ASC
        """,
        (current_user.user_id,),
    )
    return render_template("social/favorites.html", favorites=rows)


@bp.post("/favorites/toggle")
@login_required
def toggle_favorite():
    dish_id_raw = request.form.get("dish_id", "").strip()
    if not dish_id_raw.isdigit():
        abort(400)
    dish_id = int(dish_id_raw)

    existing = query_one(
        "SELECT 1 FROM Favorites WHERE user_id = %s AND dish_id = %s",
        (current_user.user_id, dish_id),
    )
    if existing:
        execute(
            "DELETE FROM Favorites WHERE user_id = %s AND dish_id = %s",
            (current_user.user_id, dish_id),
        )
        flash("Removed from favorites.", "info")
    else:
        execute(
            "INSERT INTO Favorites (user_id, dish_id) VALUES (%s, %s)",
            (current_user.user_id, dish_id),
        )
        flash("Added to favorites.", "success")

    return redirect(url_for("dishes.dish_detail", dish_id=dish_id))


@bp.get("/friends")
@login_required
def friends():
    rows = query_all(
        """
        SELECT
            u2.user_id AS friend_user_id,
            u2.username AS friend_username,
            u2.email AS friend_email
        FROM Friends f
        JOIN `User` u2 ON f.friend_user_id = u2.user_id
        WHERE f.user_id = %s
        ORDER BY u2.username ASC
        """,
        (current_user.user_id,),
    )

    friend_feed = query_all(
        """
        SELECT
            u.username,
            d.dish_name,
            r.score,
            r.date_time
        FROM Friends f
        JOIN Rating r ON f.friend_user_id = r.user_id
        JOIN `User` u ON r.user_id = u.user_id
        JOIN Dish d ON r.dish_id = d.dish_id
        WHERE f.user_id = %s
        ORDER BY r.date_time DESC
        LIMIT 25
        """,
        (current_user.user_id,),
    )
    return render_template("social/friends.html", friends=rows, friend_feed=friend_feed)


@bp.post("/friends/add")
@login_required
def add_friend():
    friend_username = request.form.get("friend_username", "").strip()
    if not friend_username:
        abort(400, "friend_username is required.")

    friend = query_one(
        "SELECT user_id FROM `User` WHERE username = %s",
        (friend_username,),
    )
    if not friend:
        flash("User not found.", "danger")
        return redirect(url_for("social.friends"))
    if friend["user_id"] == current_user.user_id:
        flash("You cannot add yourself.", "danger")
        return redirect(url_for("social.friends"))

    try:
        with transaction() as cursor:
            cursor.execute(
                "INSERT INTO Friends (user_id, friend_user_id) VALUES (%s, %s)",
                (current_user.user_id, friend["user_id"]),
            )
            cursor.execute(
                "INSERT INTO Friends (user_id, friend_user_id) VALUES (%s, %s)",
                (friend["user_id"], current_user.user_id),
            )
        flash("Friend added.", "success")
    except IntegrityError:
        flash("Friendship already exists.", "info")

    return redirect(url_for("social.friends"))


@bp.post("/friends/remove")
@login_required
def remove_friend():
    friend_user_id_raw = request.form.get("friend_user_id", "").strip()
    if not friend_user_id_raw.isdigit():
        abort(400)
    friend_user_id = int(friend_user_id_raw)

    with transaction() as cursor:
        cursor.execute(
            "DELETE FROM Friends WHERE user_id = %s AND friend_user_id = %s",
            (current_user.user_id, friend_user_id),
        )
        cursor.execute(
            "DELETE FROM Friends WHERE user_id = %s AND friend_user_id = %s",
            (friend_user_id, current_user.user_id),
        )

    flash("Friend removed.", "info")
    return redirect(url_for("social.friends"))
