from pymysql.err import IntegrityError

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.db import execute, query_all, query_one


bp = Blueprint("social", __name__)


def _redirect_next_or(default_endpoint):
    next_url = request.form.get("next", "").strip()
    if next_url.startswith("/"):
        return redirect(next_url)
    return redirect(url_for(default_endpoint))


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


@bp.get("/users/<string:username>")
def public_profile(username):
    profile_user = query_one(
        """
        SELECT
            u.user_id,
            u.username,
            u.profile_picture,
            u.admin,
            COALESCE(fw.following_count, 0) AS following_count,
            COALESCE(fr.follower_count, 0) AS follower_count,
            COALESCE(rt.rating_count, 0) AS rating_count,
            COALESCE(rt.avg_score, 0) AS avg_score
        FROM `User` u
        LEFT JOIN (
            SELECT user_id, COUNT(*) AS following_count
            FROM Friends
            GROUP BY user_id
        ) fw ON fw.user_id = u.user_id
        LEFT JOIN (
            SELECT friend_user_id AS user_id, COUNT(*) AS follower_count
            FROM Friends
            GROUP BY friend_user_id
        ) fr ON fr.user_id = u.user_id
        LEFT JOIN (
            SELECT user_id, COUNT(*) AS rating_count, AVG(score) AS avg_score
            FROM Rating
            GROUP BY user_id
        ) rt ON rt.user_id = u.user_id
        WHERE u.username = %s
        """,
        (username,),
    )
    if not profile_user:
        abort(404)

    activity = query_all(
        """
        SELECT
            r.rating_id,
            r.score,
            r.date_time,
            r.description,
            d.dish_id,
            d.dish_name,
            l.location_name
        FROM Rating r
        JOIN Dish d ON r.dish_id = d.dish_id
        LEFT JOIN Location l ON d.location_id = l.location_id
        WHERE r.user_id = %s
        ORDER BY r.date_time DESC
        """,
        (profile_user["user_id"],),
    )

    is_following = False
    if current_user.is_authenticated and current_user.user_id != profile_user["user_id"]:
        is_following = bool(
            query_one(
                "SELECT 1 FROM Friends WHERE user_id = %s AND friend_user_id = %s",
                (current_user.user_id, profile_user["user_id"]),
            )
        )

    return render_template(
        "social/public_profile.html",
        profile_user=profile_user,
        activity=activity,
        is_following=is_following,
    )


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
    follow_user_id_raw = request.form.get("follow_user_id", "").strip()

    user_to_follow = None
    if follow_user_id_raw.isdigit():
        user_to_follow = query_one(
            "SELECT user_id, username FROM `User` WHERE user_id = %s",
            (int(follow_user_id_raw),),
        )
    elif follow_username:
        user_to_follow = query_one(
            "SELECT user_id, username FROM `User` WHERE username = %s",
            (follow_username,),
        )
    else:
        abort(400, "follow_username or follow_user_id is required.")

    if not user_to_follow:
        flash("User not found.", "danger")
        return _redirect_next_or("social.following")
    if user_to_follow["user_id"] == current_user.user_id:
        flash("You cannot follow yourself.", "danger")
        return _redirect_next_or("social.following")

    try:
        execute(
            "INSERT INTO Friends (user_id, friend_user_id) VALUES (%s, %s)",
            (current_user.user_id, user_to_follow["user_id"]),
        )
        flash(f"Now following {user_to_follow['username']}.", "success")
    except IntegrityError:
        flash("You already follow this user.", "info")

    return _redirect_next_or("social.following")


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
    return _redirect_next_or("social.following")
