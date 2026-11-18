USERS = {
    1: {"first_name": "Văn", "last_name": "Nguyễn", "email": "a@vnu.vn"},
    2: {"first_name": "Trang", "last_name": "Trần", "email": "b@vnu.vn"},
}


def get_user(uid):
    return USERS.get(uid)


def add_user(first_name, last_name, email):
    uid = max(USERS) + 1 if USERS else 1
    USERS[uid] = {"first_name": first_name, "last_name": last_name, "email": email}
    return uid