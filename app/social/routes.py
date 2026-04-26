from pymysql.err import IntegrityError

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.db import execute, query_all, query_one


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


@bp.get("/following")
@bp.get("/friends")
@login_required
def following():
    following_rows = query_all(
        """
        SELECT
            u2.user_id AS followed_user_id,
            u2.username AS followed_username,
            u2.email AS followed_email
        FROM Friends f
        JOIN `User` u2 ON f.friend_user_id = u2.user_id
        WHERE f.user_id = %s
        ORDER BY u2.username ASC
        """,
        (current_user.user_id,),
    )

    follower_rows = query_all(
        """
        SELECT
            u1.user_id AS follower_user_id,
            u1.username AS follower_username,
            u1.email AS follower_email
        FROM Friends f
        JOIN `User` u1 ON f.user_id = u1.user_id
        WHERE f.friend_user_id = %s
        ORDER BY u1.username ASC
        """,
        (current_user.user_id,),
    )

    following_feed = query_all(
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
    return render_template(
        "social/following.html",
        following=following_rows,
        followers=follower_rows,
        following_feed=following_feed,
    )


@bp.post("/following/add")
@bp.post("/friends/add")
@login_required
def add_following():
    follow_username = request.form.get("follow_username", "").strip()
    if not follow_username:
        abort(400, "follow_username is required.")

    user_to_follow = query_one(
        "SELECT user_id FROM `User` WHERE username = %s",
        (follow_username,),
    )
    if not user_to_follow:
        flash("User not found.", "danger")
        return redirect(url_for("social.following"))
    if user_to_follow["user_id"] == current_user.user_id:
        flash("You cannot follow yourself.", "danger")
        return redirect(url_for("social.following"))

    try:
        execute(
            "INSERT INTO Friends (user_id, friend_user_id) VALUES (%s, %s)",
            (current_user.user_id, user_to_follow["user_id"]),
        )
        flash("Now following user.", "success")
    except IntegrityError:
        flash("You already follow this user.", "info")

    return redirect(url_for("social.following"))


@bp.post("/following/remove")
@bp.post("/friends/remove")
@login_required
def remove_following():
    followed_user_id_raw = request.form.get("followed_user_id", "").strip()
    if not followed_user_id_raw.isdigit():
        abort(400)
    followed_user_id = int(followed_user_id_raw)

    execute(
        "DELETE FROM Friends WHERE user_id = %s AND friend_user_id = %s",
        (current_user.user_id, followed_user_id),
    )

    flash("Unfollowed user.", "info")
    return redirect(url_for("social.following"))
