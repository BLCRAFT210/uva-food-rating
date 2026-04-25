from pymysql.err import IntegrityError, OperationalError

from flask import Blueprint, abort, flash, redirect, request, url_for
from flask_login import current_user, login_required

from app.db import execute, execute_and_get_id, query_one, transaction


bp = Blueprint("ratings", __name__, url_prefix="/ratings")


def _parse_score(raw_score):
    try:
        score = int(raw_score)
    except (TypeError, ValueError):
        return None
    if score < 0 or score > 100:
        return None
    return score


def _assert_can_modify_rating(rating_id):
    rating = query_one(
        "SELECT rating_id, user_id, dish_id FROM Rating WHERE rating_id = %s",
        (rating_id,),
    )
    if not rating:
        abort(404)
    if not current_user.admin and rating["user_id"] != current_user.user_id:
        abort(403)
    return rating


def _split_csv_values(raw_value):
    if not raw_value:
        return []
    values = []
    seen = set()
    for token in raw_value.split(","):
        item = token.strip()
        if item and item.lower() not in seen:
            seen.add(item.lower())
            values.append(item)
    return values


@bp.post("/")
@login_required
def create_rating():
    dish_id_raw = request.form.get("dish_id", "").strip()
    score = _parse_score(request.form.get("score"))
    description = request.form.get("description", "").strip() or None
    tags = _split_csv_values(request.form.get("tags", ""))
    images = _split_csv_values(request.form.get("images", ""))

    if not dish_id_raw.isdigit() or score is None:
        abort(400, "Invalid dish or score.")
    dish_id = int(dish_id_raw)

    with transaction() as cursor:
        cursor.execute(
            """
            INSERT INTO Rating (user_id, score, date_time, description, dish_id)
            VALUES (%s, %s, NOW(), %s, %s)
            """,
            (current_user.user_id, score, description, dish_id),
        )
        rating_id = cursor.lastrowid

        for tag in tags:
            cursor.execute(
                "INSERT INTO Rating_Tags (rating_id, tag) VALUES (%s, %s)",
                (rating_id, tag),
            )
        for image in images:
            cursor.execute(
                "INSERT INTO Rating_Images (rating_id, image) VALUES (%s, %s)",
                (rating_id, image),
            )

    flash("Rating added.", "success")
    return redirect(url_for("dishes.dish_detail", dish_id=dish_id))


@bp.post("/<int:rating_id>/edit")
@login_required
def edit_rating(rating_id):
    rating = _assert_can_modify_rating(rating_id)
    score = _parse_score(request.form.get("score"))
    description = request.form.get("description", "").strip() or None
    tags = _split_csv_values(request.form.get("tags", ""))
    images = _split_csv_values(request.form.get("images", ""))

    if score is None:
        abort(400, "Score must be between 0 and 100.")

    with transaction() as cursor:
        cursor.execute(
            """
            UPDATE Rating
            SET score = %s, description = %s
            WHERE rating_id = %s
            """,
            (score, description, rating_id),
        )
        cursor.execute("DELETE FROM Rating_Tags WHERE rating_id = %s", (rating_id,))
        cursor.execute("DELETE FROM Rating_Images WHERE rating_id = %s", (rating_id,))

        for tag in tags:
            cursor.execute(
                "INSERT INTO Rating_Tags (rating_id, tag) VALUES (%s, %s)",
                (rating_id, tag),
            )
        for image in images:
            cursor.execute(
                "INSERT INTO Rating_Images (rating_id, image) VALUES (%s, %s)",
                (rating_id, image),
            )

    flash("Rating updated.", "success")
    return redirect(url_for("dishes.dish_detail", dish_id=rating["dish_id"]))


@bp.post("/<int:rating_id>/delete")
@login_required
def delete_rating(rating_id):
    rating = _assert_can_modify_rating(rating_id)
    execute("DELETE FROM Rating WHERE rating_id = %s", (rating_id,))
    flash("Rating deleted.", "info")
    return redirect(url_for("dishes.dish_detail", dish_id=rating["dish_id"]))


@bp.post("/<int:rating_id>/boost")
@login_required
def boost_rating(rating_id):
    rating = _assert_can_modify_rating(rating_id)
    execute("UPDATE Rating SET score = LEAST(score + 5, 100) WHERE rating_id = %s", (rating_id,))
    flash("Rating boosted by 5.", "success")
    return redirect(url_for("dishes.dish_detail", dish_id=rating["dish_id"]))


@bp.post("/reviews")
@login_required
def upsert_rating_review():
    rating_id_raw = request.form.get("rating_id", "").strip()
    thumbs_raw = request.form.get("thumbs_up_down", "").strip().lower()

    if not rating_id_raw.isdigit():
        abort(400, "rating_id is required.")
    if thumbs_raw not in {"up", "down", "1", "0", "true", "false"}:
        abort(400, "thumbs_up_down must be up or down.")

    rating_id = int(rating_id_raw)
    thumbs_up_down = thumbs_raw in {"up", "1", "true"}

    rating = query_one("SELECT dish_id FROM Rating WHERE rating_id = %s", (rating_id,))
    if not rating:
        abort(404)

    try:
        execute_and_get_id(
            """
            INSERT INTO RatingReview (rating_id, user_id, thumbs_up_down)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE thumbs_up_down = VALUES(thumbs_up_down)
            """,
            (rating_id, current_user.user_id, thumbs_up_down),
        )
        flash("Review vote saved.", "success")
    except (IntegrityError, OperationalError) as error:
        flash(str(error), "danger")

    return redirect(url_for("dishes.dish_detail", dish_id=rating["dish_id"]))


@bp.post("/reviews/delete")
@login_required
def delete_rating_review():
    rating_id_raw = request.form.get("rating_id", "").strip()
    if not rating_id_raw.isdigit():
        abort(400)
    rating_id = int(rating_id_raw)

    rating = query_one("SELECT dish_id FROM Rating WHERE rating_id = %s", (rating_id,))
    if not rating:
        abort(404)

    execute(
        "DELETE FROM RatingReview WHERE rating_id = %s AND user_id = %s",
        (rating_id, current_user.user_id),
    )
    flash("Vote removed.", "info")
    return redirect(url_for("dishes.dish_detail", dish_id=rating["dish_id"]))
