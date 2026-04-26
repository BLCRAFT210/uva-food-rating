from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.db import execute, execute_and_get_id, query_all, query_one, transaction
from app.security import admin_required


bp = Blueprint("dishes", __name__, url_prefix="/dishes")

SORT_OPTIONS = {
    "avg_desc": "avg_score DESC, d.dish_name ASC",
    "avg_asc": "avg_score ASC, d.dish_name ASC",
    "name_asc": "d.dish_name ASC",
    "name_desc": "d.dish_name DESC",
    "favorites_desc": "favorite_count DESC, d.dish_name ASC",
    "newest_rating_desc": "latest_rating DESC, d.dish_name ASC",
}


def _parse_bool(name):
    return request.args.get(name) in {"1", "true", "True", "on"}


def _fetch_locations():
    return query_all("SELECT location_id, location_name FROM Location ORDER BY location_name ASC")


def _fetch_dishes():
    search = request.args.get("search", "").strip()
    location_id = request.args.get("location_id", "").strip()
    vegan = _parse_bool("vegan")
    gluten_free = _parse_bool("gluten_free")
    sort = request.args.get("sort", "avg_desc")
    sort_sql = SORT_OPTIONS.get(sort, SORT_OPTIONS["avg_desc"])

    where_clauses = []
    params = []

    if search:
        where_clauses.append("(d.dish_name LIKE %s OR l.location_name LIKE %s)")
        like_query = f"%{search}%"
        params.extend([like_query, like_query])

    if location_id.isdigit():
        where_clauses.append("d.location_id = %s")
        params.append(int(location_id))

    if vegan:
        where_clauses.append("a.vegan = TRUE")
    if gluten_free:
        where_clauses.append("a.gluten_free = TRUE")

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    dishes = query_all(
        f"""
        SELECT
            d.dish_id,
            d.dish_name,
            d.location_id,
            l.location_name,
            d.accomm_id,
            COALESCE(AVG(r.score), 0) AS avg_score,
            COUNT(DISTINCT r.rating_id) AS rating_count,
            COUNT(DISTINCT f.user_id) AS favorite_count,
            MAX(r.date_time) AS latest_rating
        FROM Dish d
        LEFT JOIN Location l ON d.location_id = l.location_id
        LEFT JOIN Accommodations a ON d.accomm_id = a.accomm_id
        LEFT JOIN Rating r ON d.dish_id = r.dish_id
        LEFT JOIN Favorites f ON d.dish_id = f.dish_id
        {where_sql}
        GROUP BY d.dish_id, d.dish_name, d.location_id, l.location_name, d.accomm_id
        ORDER BY {sort_sql}
        """,
        params,
    )
    return dishes


def _create_dish_from_form():
    dish_name = request.form.get("dish_name", "").strip()
    location_id_raw = request.form.get("location_id", "").strip()
    location_id = int(location_id_raw) if location_id_raw.isdigit() else None

    if not dish_name:
        abort(400, "Dish name is required.")

    vegan = bool(request.form.get("vegan"))
    gluten_free = bool(request.form.get("gluten_free"))
    nuts = bool(request.form.get("nuts"))
    dairy = bool(request.form.get("dairy"))
    seafood = bool(request.form.get("seafood"))

    with transaction() as cursor:
        cursor.execute(
            """
            INSERT INTO Accommodations (vegan, gluten_free, nuts, dairy, seafood)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (vegan, gluten_free, nuts, dairy, seafood),
        )
        accomm_id = cursor.lastrowid
        cursor.execute(
            """
            INSERT INTO Dish (dish_name, accomm_id, location_id)
            VALUES (%s, %s, %s)
            """,
            (dish_name, accomm_id, location_id),
        )
        dish_id = cursor.lastrowid

    return dish_id


@bp.get("/")
def list_dishes():
    dishes = _fetch_dishes()
    locations = _fetch_locations()
    return render_template(
        "dishes/index.html",
        dishes=dishes,
        locations=locations,
        sort=request.args.get("sort", "avg_desc"),
    )


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new_dish():
    if request.method == "POST":
        dish_id = _create_dish_from_form()
        flash("Dish created.", "success")
        return redirect(url_for("dishes.dish_detail", dish_id=dish_id))

    locations = _fetch_locations()
    return render_template("dishes/new.html", locations=locations)


@bp.get("/table")
def dishes_table():
    dishes = _fetch_dishes()
    return render_template("dishes/_table.html", dishes=dishes)


@bp.get("/<int:dish_id>")
def dish_detail(dish_id):
    dish = query_one(
        """
        SELECT
            d.dish_id,
            d.dish_name,
            d.location_id,
            l.location_name,
            d.accomm_id,
            a.vegan,
            a.gluten_free,
            a.nuts,
            a.dairy,
            a.seafood
        FROM Dish d
        LEFT JOIN Location l ON d.location_id = l.location_id
        LEFT JOIN Accommodations a ON d.accomm_id = a.accomm_id
        WHERE d.dish_id = %s
        """,
        (dish_id,),
    )
    if not dish:
        abort(404)

    ratings = query_all(
        """
        SELECT
            r.rating_id,
            r.user_id,
            u.username,
            r.score,
            r.date_time,
            r.description,
            COALESCE(GROUP_CONCAT(DISTINCT rt.tag ORDER BY rt.tag SEPARATOR ', '), '') AS tags,
            COALESCE(GROUP_CONCAT(DISTINCT ri.image ORDER BY ri.image SEPARATOR ', '), '') AS images,
            COALESCE(SUM(CASE WHEN rr.thumbs_up_down = TRUE THEN 1 ELSE 0 END), 0) AS thumbs_up,
            COALESCE(SUM(CASE WHEN rr.thumbs_up_down = FALSE THEN 1 ELSE 0 END), 0) AS thumbs_down
        FROM Rating r
        JOIN `User` u ON r.user_id = u.user_id
        LEFT JOIN Rating_Tags rt ON r.rating_id = rt.rating_id
        LEFT JOIN Rating_Images ri ON r.rating_id = ri.rating_id
        LEFT JOIN RatingReview rr ON r.rating_id = rr.rating_id
        WHERE r.dish_id = %s
        GROUP BY r.rating_id, r.user_id, u.username, r.score, r.date_time, r.description
        ORDER BY r.date_time DESC
        """,
        (dish_id,),
    )

    is_favorite = False
    if current_user.is_authenticated:
        favorite_row = query_one(
            "SELECT 1 FROM Favorites WHERE user_id = %s AND dish_id = %s",
            (current_user.user_id, dish_id),
        )
        is_favorite = bool(favorite_row)

    locations = _fetch_locations()
    return render_template(
        "dishes/detail.html",
        dish=dish,
        ratings=ratings,
        is_favorite=is_favorite,
        locations=locations,
    )


@bp.post("/")
@login_required
def create_dish():
    dish_id = _create_dish_from_form()
    flash("Dish created.", "success")
    return redirect(url_for("dishes.dish_detail", dish_id=dish_id))


@bp.post("/<int:dish_id>/edit")
@login_required
@admin_required
def edit_dish(dish_id):
    dish_name = request.form.get("dish_name", "").strip()
    location_id_raw = request.form.get("location_id", "").strip()
    location_id = int(location_id_raw) if location_id_raw.isdigit() else None

    vegan = bool(request.form.get("vegan"))
    gluten_free = bool(request.form.get("gluten_free"))
    nuts = bool(request.form.get("nuts"))
    dairy = bool(request.form.get("dairy"))
    seafood = bool(request.form.get("seafood"))

    if not dish_name:
        abort(400, "Dish name is required.")

    dish_row = query_one("SELECT accomm_id FROM Dish WHERE dish_id = %s", (dish_id,))
    if not dish_row:
        abort(404)

    with transaction() as cursor:
        accomm_id = dish_row["accomm_id"]
        if accomm_id is None:
            cursor.execute(
                """
                INSERT INTO Accommodations (vegan, gluten_free, nuts, dairy, seafood)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (vegan, gluten_free, nuts, dairy, seafood),
            )
            accomm_id = cursor.lastrowid
        else:
            cursor.execute(
                """
                UPDATE Accommodations
                SET vegan = %s, gluten_free = %s, nuts = %s, dairy = %s, seafood = %s
                WHERE accomm_id = %s
                """,
                (vegan, gluten_free, nuts, dairy, seafood, accomm_id),
            )

        cursor.execute(
            """
            UPDATE Dish
            SET dish_name = %s, location_id = %s, accomm_id = %s
            WHERE dish_id = %s
            """,
            (dish_name, location_id, accomm_id, dish_id),
        )

    flash("Dish updated.", "success")
    return redirect(url_for("dishes.dish_detail", dish_id=dish_id))


@bp.post("/<int:dish_id>/delete")
@login_required
@admin_required
def delete_dish(dish_id):
    execute("DELETE FROM Dish WHERE dish_id = %s", (dish_id,))
    flash("Dish deleted.", "info")
    return redirect(url_for("dishes.list_dishes"))


@bp.post("/locations")
@login_required
@admin_required
def create_location():
    location_name = request.form.get("location_name", "").strip()
    if not location_name:
        abort(400, "Location name is required.")
    execute("INSERT INTO Location (location_name) VALUES (%s)", (location_name,))
    flash("Location added.", "success")
    return redirect(url_for("dishes.list_dishes"))


@bp.post("/locations/<int:location_id>/edit")
@login_required
@admin_required
def edit_location(location_id):
    location_name = request.form.get("location_name", "").strip()
    if not location_name:
        abort(400, "Location name is required.")
    execute(
        "UPDATE Location SET location_name = %s WHERE location_id = %s",
        (location_name, location_id),
    )
    flash("Location updated.", "success")
    return redirect(url_for("dishes.list_dishes"))


@bp.post("/locations/<int:location_id>/delete")
@login_required
@admin_required
def delete_location(location_id):
    execute("DELETE FROM Location WHERE location_id = %s", (location_id,))
    flash("Location deleted.", "info")
    return redirect(url_for("dishes.list_dishes"))


@bp.post("/accommodations/<int:accomm_id>/delete")
@login_required
@admin_required
def delete_accommodation(accomm_id):
    execute("DELETE FROM Accommodations WHERE accomm_id = %s", (accomm_id,))
    flash("Accommodation deleted.", "info")
    return redirect(url_for("dishes.list_dishes"))
