from flask_login import UserMixin

from app.db import query_one


class AppUser(UserMixin):
    def __init__(self, user_id, username, email, admin=False, profile_picture=None):
        self.id = str(user_id)
        self.user_id = user_id
        self.username = username
        self.email = email
        self.admin = bool(admin)
        self.profile_picture = profile_picture

    @staticmethod
    def from_row(row):
        if not row:
            return None
        return AppUser(
            user_id=row["user_id"],
            username=row["username"],
            email=row["email"],
            admin=row["admin"],
            profile_picture=row.get("profile_picture"),
        )


def load_user_from_db(user_id):
    row = query_one(
        """
        SELECT user_id, username, email, admin, profile_picture
        FROM `User`
        WHERE user_id = %s
        """,
        (user_id,),
    )
    return AppUser.from_row(row)
