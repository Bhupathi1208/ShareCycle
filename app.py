from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    send_from_directory
)

from database import create_tables, get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash
from matching import calculate_match

import os
import uuid

from dotenv import load_dotenv
from werkzeug.utils import secure_filename


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# FLASK APPLICATION
# ============================================================

app = Flask(__name__)

# Secret key for login sessions
app.secret_key = os.getenv("SECRET_KEY")


# ============================================================
# UPLOAD SETTINGS
# ============================================================

UPLOAD_FOLDER = "uploads"

ALLOWED_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp"
}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Maximum image size = 5 MB
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)


# ============================================================
# IMAGE VALIDATION
# ============================================================

def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(
            ".",
            1
        )[1].lower()
        in ALLOWED_EXTENSIONS
    )


# ============================================================
# CREATE DATABASE TABLES
# ============================================================

create_tables()


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    connection = get_db_connection()

    total_users = connection.execute("""
        SELECT COUNT(*) AS total
        FROM users
    """).fetchone()["total"]

    total_items = connection.execute("""
        SELECT COUNT(*) AS total
        FROM items
    """).fetchone()["total"]

    available_items = connection.execute("""
        SELECT COUNT(*) AS total
        FROM items
        WHERE status = 'Available'
    """).fetchone()["total"]

    completed_donations = connection.execute("""
        SELECT COUNT(*) AS total
        FROM requests
        WHERE status IN ('Completed', 'Confirmed')
    """).fetchone()["total"]

    connection.close()

    return render_template(
        "index.html",
        total_users=total_users,
        total_items=total_items,
        available_items=available_items,
        completed_donations=completed_donations
    )


# ============================================================
# REGISTER
# ============================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        phone = request.form["phone"]
        location = request.form["location"]

        hashed_password = generate_password_hash(
            password
        )

        connection = get_db_connection()

        try:

            INSERT_QUERY = """
                INSERT INTO users
                (
                    name,
                    email,
                    password,
                    phone,
                    location
                )
                VALUES (?, ?, ?, ?, ?)
            """

            connection.execute(
                INSERT_QUERY,
                (
                    name,
                    email,
                    hashed_password,
                    phone,
                    location
                )
            )

            connection.commit()

        except Exception:

            connection.close()

            return "This email is already registered."

        connection.close()

        return redirect(
            url_for("login")
        )

    return render_template(
        "register.html"
    )


# ============================================================
# LOGIN
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        connection = get_db_connection()

        user = connection.execute("""
            SELECT *
            FROM users
            WHERE email = ?
        """, (
            email,
        )).fetchone()

        connection.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["id"]

            session["user_name"] = user["name"]

            session["role"] = user["role"]

            # Start with fresh mode selection
            session.pop(
                "current_mode",
                None
            )

            # Admin dashboard
            if user["role"] == "admin":

                return redirect(
                    url_for("admin_dashboard")
                )

            # Normal user chooses mode
            return redirect(
                url_for("choose_mode")
            )

        return "Invalid email or password."

    return render_template(
        "login.html"
    )


# ============================================================
# CHOOSE MODE
# ============================================================

@app.route("/choose-mode")
def choose_mode():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    if session.get("role") == "admin":

        return redirect(
            url_for("admin_dashboard")
        )

    return render_template(
        "choose_mode.html"
    )


# ============================================================
# SWITCH TO DONOR
# ============================================================

@app.route("/switch-to-donor")
def switch_to_donor():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    if session.get("role") == "admin":

        return redirect(
            url_for("admin_dashboard")
        )

    session["current_mode"] = "donor"

    return redirect(
        url_for("donor_dashboard")
    )


# ============================================================
# SWITCH TO RECIPIENT
# ============================================================

@app.route("/switch-to-recipient")
def switch_to_recipient():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    if session.get("role") == "admin":

        return redirect(
            url_for("admin_dashboard")
        )

    session["current_mode"] = "recipient"

    return redirect(
        url_for("recipient_dashboard")
    )


# ============================================================
# DONOR DASHBOARD
# ============================================================

@app.route("/donor/dashboard")
def donor_dashboard():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    if session.get("role") == "admin":

        return redirect(
            url_for("admin_dashboard")
        )

    if session.get("current_mode") != "donor":

        return redirect(
            url_for("choose_mode")
        )

    return render_template(
        "donor_dashboard.html"
    )


# ============================================================
# RECIPIENT DASHBOARD
# ============================================================

@app.route("/recipient/dashboard")
def recipient_dashboard():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    if session.get("role") == "admin":

        return redirect(
            url_for("admin_dashboard")
        )

    if session.get("current_mode") != "recipient":

        return redirect(
            url_for("choose_mode")
        )

    return render_template(
        "recipient_dashboard.html"
    )


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@app.route("/admin/dashboard")
def admin_dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return "Access denied."

    connection = get_db_connection()

    total_users = connection.execute("""
        SELECT COUNT(*) AS count
        FROM users
        WHERE role != 'admin'
    """).fetchone()["count"]

    total_donors = connection.execute("""
        SELECT COUNT(DISTINCT donor_id) AS count
        FROM items
    """).fetchone()["count"]

    total_recipients = connection.execute("""
        SELECT COUNT(DISTINCT recipient_id) AS count
        FROM requests
    """).fetchone()["count"]

    total_items = connection.execute("""
        SELECT COUNT(*) AS count
        FROM items
    """).fetchone()["count"]

    available_items = connection.execute("""
        SELECT COUNT(*) AS count
        FROM items
        WHERE status = 'Available'
    """).fetchone()["count"]

    completed_donations = connection.execute("""
        SELECT COUNT(*) AS count
        FROM requests
        WHERE status = 'Completed'
    """).fetchone()["count"]

    connection.close()

    return render_template(
        "admin_dashboard.html",
        total_users=total_users,
        total_donors=total_donors,
        total_recipients=total_recipients,
        total_items=total_items,
        available_items=available_items,
        completed_donations=completed_donations
    )

# ============================================================
# ADMIN USERS
# ============================================================

@app.route("/admin/users")
def admin_users():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return "Access denied."

    connection = get_db_connection()

    users = connection.execute("""
        SELECT
            users.id,
            users.name,
            users.email,
            users.phone,
            users.location,
            users.role,
            users.created_at,

            COUNT(DISTINCT items.id) AS donated_items,

            COUNT(DISTINCT requests.id) AS requested_items

        FROM users

        LEFT JOIN items
            ON users.id = items.donor_id

        LEFT JOIN requests
            ON users.id = requests.recipient_id

        GROUP BY
            users.id

        ORDER BY
            users.created_at DESC
    """).fetchall()

    connection.close()

    return render_template(
        "admin_users.html",
        users=users
    )

# ============================================================
# ADMIN ITEMS
# ============================================================

@app.route("/admin/items")
def admin_items():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return "Access denied."

    connection = get_db_connection()

    items = connection.execute("""
        SELECT
            items.id,
            items.title,
            items.category,
            items.description,
            items.image,
            items.condition,
            items.quantity,
            items.location,
            items.status,
            items.created_at,
            users.name AS donor_name,
            users.email AS donor_email
        FROM items
        JOIN users
            ON items.donor_id = users.id
        ORDER BY items.created_at DESC
    """).fetchall()

    connection.close()

    return render_template(
        "admin_items.html",
        items=items
    )


# ============================================================
# ADMIN DELETE ITEM
# ============================================================

@app.route(
    "/admin/items/<int:item_id>/delete",
    methods=["POST"]
)
def admin_delete_item(item_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    if session["role"] != "admin":

        return "Access denied."

    connection = get_db_connection()

    item = connection.execute("""
        SELECT id, title
        FROM items
        WHERE id = ?
    """, (
        item_id,
    )).fetchone()

    if item is None:

        connection.close()

        return "Item not found."

    connection.execute("""
        DELETE FROM requests
        WHERE item_id = ?
    """, (
        item_id,
    ))

    connection.execute("""
        DELETE FROM matches
        WHERE item_id = ?
    """, (
        item_id,
    ))

    connection.execute("""
        DELETE FROM items
        WHERE id = ?
    """, (
        item_id,
    ))

    connection.commit()

    connection.close()

    return redirect(
        url_for("admin_items")
    )


# ============================================================
# ADMIN ANALYTICS
# ============================================================

@app.route("/admin/analytics")
def admin_analytics():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    if session["role"] != "admin":

        return "Access denied."

    connection = get_db_connection()

    total_users = connection.execute("""
        SELECT COUNT(*) AS count
        FROM users
    """).fetchone()["count"]

    total_donors = connection.execute("""
        SELECT COUNT(*) AS count
        FROM users
        WHERE role = 'donor'
    """).fetchone()["count"]

    total_recipients = connection.execute("""
        SELECT COUNT(*) AS count
        FROM users
        WHERE role = 'recipient'
    """).fetchone()["count"]

    total_items = connection.execute("""
        SELECT COUNT(*) AS count
        FROM items
    """).fetchone()["count"]

    available_items = connection.execute("""
        SELECT COUNT(*) AS count
        FROM items
        WHERE status = 'Available'
    """).fetchone()["count"]

    reserved_items = connection.execute("""
        SELECT COUNT(*) AS count
        FROM items
        WHERE status = 'Reserved'
    """).fetchone()["count"]

    donated_items = connection.execute("""
        SELECT COUNT(*) AS count
        FROM items
        WHERE status = 'Donated'
    """).fetchone()["count"]

    total_requests = connection.execute("""
        SELECT COUNT(*) AS count
        FROM requests
    """).fetchone()["count"]

    pending_requests = connection.execute("""
        SELECT COUNT(*) AS count
        FROM requests
        WHERE status = 'Pending'
    """).fetchone()["count"]

    accepted_requests = connection.execute("""
        SELECT COUNT(*) AS count
        FROM requests
        WHERE status = 'Accepted'
    """).fetchone()["count"]

    rejected_requests = connection.execute("""
        SELECT COUNT(*) AS count
        FROM requests
        WHERE status = 'Rejected'
    """).fetchone()["count"]

    completed_donations = connection.execute("""
        SELECT COUNT(*) AS count
        FROM requests
        WHERE status = 'Completed'
    """).fetchone()["count"]

    connection.close()

    return render_template(
        "admin_analytics.html",
        total_users=total_users,
        total_donors=total_donors,
        total_recipients=total_recipients,
        total_items=total_items,
        available_items=available_items,
        reserved_items=reserved_items,
        donated_items=donated_items,
        total_requests=total_requests,
        pending_requests=pending_requests,
        accepted_requests=accepted_requests,
        rejected_requests=rejected_requests,
        completed_donations=completed_donations
    )


# ============================================================
# BROWSE ITEMS
# ============================================================

@app.route("/items")
def items():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    search = request.args.get(
        "search",
        ""
    ).strip()

    category = request.args.get(
        "category",
        ""
    ).strip()

    location = request.args.get(
        "location",
        ""
    ).strip()

    condition = request.args.get(
        "condition",
        ""
    ).strip()

    if category.lower() in [
        "all categories",
        ""
    ]:

        category = ""

    if condition.lower() in [
        "any condition",
        ""
    ]:

        condition = ""

    connection = get_db_connection()

    query = """
        SELECT
            items.*,
            users.name AS donor_name
        FROM items
        JOIN users
            ON items.donor_id = users.id
        WHERE items.status = 'Available'
    """

    parameters = []

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    if search:

        search_words = search.lower().split()

        for word in search_words:

            query += """
                AND (
                    LOWER(items.title) LIKE ?
                    OR LOWER(items.description) LIKE ?
                    OR LOWER(items.category) LIKE ?
                )
            """

            search_value = "%" + word + "%"

            parameters.append(
                search_value
            )

            parameters.append(
                search_value
            )

            parameters.append(
                search_value
            )

    # --------------------------------------------------------
    # CATEGORY
    # --------------------------------------------------------

    if category:

        query += """
            AND LOWER(items.category) = LOWER(?)
        """

        parameters.append(
            category
        )

    # --------------------------------------------------------
    # LOCATION
    # --------------------------------------------------------

    if location:

        query += """
            AND LOWER(items.location) LIKE ?
        """

        parameters.append(
            "%" + location.lower() + "%"
        )

    # --------------------------------------------------------
    # CONDITION
    # --------------------------------------------------------

    if condition:

        query += """
            AND LOWER(items.condition) = LOWER(?)
        """

        parameters.append(
            condition
        )

    # --------------------------------------------------------
    # ORDER
    # --------------------------------------------------------

    query += """
        ORDER BY items.created_at DESC
    """

    items_list = connection.execute(
        query,
        parameters
    ).fetchall()

    connection.close()

    return render_template(
        "items.html",
        items=items_list,
        search=search,
        category=category,
        location=location,
        condition=condition
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("home")
    )


# ============================================================
# UPLOAD FILE
# ============================================================

@app.route("/uploads/<filename>")
def uploaded_file(filename):

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )


# ============================================================
# ADD ITEM
# ============================================================

@app.route(
    "/add-item",
    methods=["GET", "POST"]
)
def add_item():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    if session.get("role") == "admin":

        return redirect(
            url_for("admin_dashboard")
        )

    if session.get("current_mode") != "donor":

        return redirect(
            url_for("choose_mode")
        )

    if request.method == "POST":

        title = request.form["title"]

        description = request.form[
            "description"
        ]

        category = request.form[
            "category"
        ]

        condition = request.form[
            "condition"
        ]

        quantity = request.form[
            "quantity"
        ]

        location = request.form[
            "location"
        ]

        image = request.files.get(
            "image"
        )

        image_filename = None

        if image and image.filename:

            if not allowed_file(
                image.filename
            ):

                return (
                    "Invalid image format. "
                    "Please upload JPG, JPEG, PNG, or WEBP."
                )

            original_filename = secure_filename(
                image.filename
            )

            extension = original_filename.rsplit(
                ".",
                1
            )[1].lower()

            unique_filename = (
                f"{uuid.uuid4().hex}.{extension}"
            )

            image_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                unique_filename
            )

            image.save(
                image_path
            )

            image_filename = unique_filename

        connection = get_db_connection()

        connection.execute("""
            INSERT INTO items
            (
                donor_id,
                title,
                description,
                category,
                condition,
                quantity,
                location,
                image
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            title,
            description,
            category,
            condition,
            quantity,
            location,
            image_filename
        ))

        connection.commit()

        connection.close()

        return redirect(
            url_for("my_items")
        )

    return render_template(
        "add_item.html"
    )


# ============================================================
# MY ITEMS
# ============================================================

@app.route("/my-items")
def my_items():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    if session.get("role") == "admin":

        return redirect(
            url_for("admin_dashboard")
        )

    if session.get("current_mode") != "donor":

        return redirect(
            url_for("choose_mode")
        )

    connection = get_db_connection()

    items = connection.execute("""
        SELECT *
        FROM items
        WHERE donor_id = ?
        ORDER BY created_at DESC
    """, (
        session["user_id"],
    )).fetchall()

    connection.close()

    return render_template(
        "my_items.html",
        items=items
    )


# ============================================================
# ITEM DETAILS
# ============================================================

@app.route("/item/<int:item_id>")
def item_details(item_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    connection = get_db_connection()

    item = connection.execute("""
        SELECT *
        FROM items
        WHERE id = ?
    """, (
        item_id,
    )).fetchone()

    if not item:

        connection.close()

        return redirect(
            url_for("items")
        )

    donor = connection.execute("""
        SELECT *
        FROM users
        WHERE id = ?
    """, (
        item["donor_id"],
    )).fetchone()

    connection.close()

    return render_template(
        "item_details.html",
        item=item,
        donor=donor
    )


# ============================================================
# REQUEST ITEM
# ============================================================

@app.route(
    "/request/<int:item_id>",
    methods=["POST"]
)
def request_item(item_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    if session.get("role") == "admin":

        return redirect(
            url_for("admin_dashboard")
        )

    if session.get("current_mode") != "recipient":

        return redirect(
            url_for("choose_mode")
        )

    message = request.form[
        "message"
    ]

    connection = get_db_connection()

    item = connection.execute("""
        SELECT *
        FROM items
        WHERE id = ?
        AND status = 'Available'
    """, (
        item_id,
    )).fetchone()

    if item is None:

        connection.close()

        return "This item is no longer available."

    existing_request = connection.execute("""
        SELECT *
        FROM requests
        WHERE item_id = ?
        AND recipient_id = ?
        AND status = 'Pending'
    """, (
        item_id,
        session["user_id"]
    )).fetchone()

    if existing_request:

        connection.close()

        return "You have already requested this item."

    connection.execute("""
        INSERT INTO requests
        (
            item_id,
            recipient_id,
            message
        )
        VALUES (?, ?, ?)
    """, (
        item_id,
        session["user_id"],
        message
    ))

    connection.execute("""
        INSERT INTO notifications
        (
            user_id,
            message
        )
        VALUES (?, ?)
    """, (
        item["donor_id"],
        "You received a new donation request."
    ))

    connection.commit()

    connection.close()

    return redirect(
        url_for("recipient_dashboard")
    )


# ============================================================
# DONOR REQUESTS
# ============================================================

@app.route("/donor/requests")
def donor_requests():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    if session.get("role") == "admin":

        return redirect(
            url_for("admin_dashboard")
        )

    if session.get("current_mode") != "donor":

        return redirect(
            url_for("choose_mode")
        )

    connection = get_db_connection()

    requests_list = connection.execute("""
        SELECT
            requests.*,
            items.title AS item_title,
            users.name AS recipient_name,
            users.email AS recipient_email,
            users.phone AS recipient_phone
        FROM requests
        JOIN items
            ON requests.item_id = items.id
        JOIN users
            ON requests.recipient_id = users.id
        WHERE items.donor_id = ?
        ORDER BY requests.requested_at DESC
    """, (
        session["user_id"],
    )).fetchall()

    connection.close()

    return render_template(
        "donor_requests.html",
        requests=requests_list
    )


# ============================================================
# ACCEPT REQUEST
# ============================================================

@app.route(
    "/request/<int:request_id>/accept",
    methods=["POST"]
)
def accept_request(request_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    if session.get("role") == "admin":

        return redirect(
            url_for("admin_dashboard")
        )

    if session.get("current_mode") != "donor":

        return redirect(
            url_for("choose_mode")
        )

    connection = get_db_connection()

    request_data = connection.execute("""
        SELECT
            requests.id,
            requests.item_id,
            requests.recipient_id,
            requests.status,
            items.title,
            items.donor_id
        FROM requests
        JOIN items
            ON requests.item_id = items.id
        WHERE requests.id = ?
        AND items.donor_id = ?
    """, (
        request_id,
        session["user_id"]
    )).fetchone()

    if request_data is None:

        connection.close()

        return "Request not found."

    if request_data["status"] != "Pending":

        connection.close()

        return "This request has already been processed."

    item_id = request_data[
        "item_id"
    ]

    recipient_id = request_data[
        "recipient_id"
    ]

    item_title = request_data[
        "title"
    ]

    connection.execute("""
        UPDATE requests
        SET status = 'Accepted'
        WHERE id = ?
    """, (
        request_id,
    ))

    connection.execute("""
        UPDATE items
        SET status = 'Reserved'
        WHERE id = ?
    """, (
        item_id,
    ))

    connection.execute("""
        INSERT INTO notifications
        (
            user_id,
            message
        )
        VALUES (?, ?)
    """, (
        recipient_id,
        f"Your request for '{item_title}' has been accepted."
    ))

    other_requests = connection.execute("""
        SELECT
            id,
            recipient_id
        FROM requests
        WHERE item_id = ?
        AND id != ?
        AND status = 'Pending'
    """, (
        item_id,
        request_id
    )).fetchall()

    for other in other_requests:

        connection.execute("""
            UPDATE requests
            SET status = 'Rejected'
            WHERE id = ?
        """, (
            other["id"],
        ))

        connection.execute("""
            INSERT INTO notifications
            (
                user_id,
                message
            )
            VALUES (?, ?)
        """, (
            other["recipient_id"],
            f"Your request for '{item_title}' was not accepted because the item was given to another recipient."
        ))

    connection.commit()

    connection.close()

    return redirect(
        url_for("donor_requests")
    )


# ============================================================
# REJECT REQUEST
# ============================================================

@app.route(
    "/request/<int:request_id>/reject",
    methods=["POST"]
)
def reject_request(request_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    if session.get("role") == "admin":

        return redirect(
            url_for("admin_dashboard")
        )

    if session.get("current_mode") != "donor":

        return redirect(
            url_for("choose_mode")
        )

    connection = get_db_connection()

    req = connection.execute("""
        SELECT
            requests.*,
            items.title AS item_title,
            items.donor_id
        FROM requests
        JOIN items
            ON requests.item_id = items.id
        WHERE requests.id = ?
        AND items.donor_id = ?
    """, (
        request_id,
        session["user_id"]
    )).fetchone()

    if req is None:

        connection.close()

        return "Request not found."

    if req["status"] != "Pending":

        connection.close()

        return "This request has already been processed."

    connection.execute("""
        UPDATE requests
        SET status = 'Rejected'
        WHERE id = ?
    """, (
        request_id,
    ))

    connection.execute("""
        INSERT INTO notifications
        (
            user_id,
            message
        )
        VALUES (?, ?)
    """, (
        req["recipient_id"],
        "Your request for '"
        + req["item_title"]
        + "' has been rejected."
    ))

    connection.commit()

    connection.close()

    return redirect(
        url_for("donor_requests")
    )


# ============================================================
# RECIPIENT REQUESTS
# ============================================================

@app.route("/recipient/requests")
def recipient_requests():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    if session.get("role") == "admin":

        return redirect(
            url_for("admin_dashboard")
        )

    if session.get("current_mode") != "recipient":

        return redirect(
            url_for("choose_mode")
        )

    connection = get_db_connection()

    requests_list = connection.execute("""
        SELECT
            requests.*,
            items.title AS item_title,
            items.description AS item_description,
            items.category,
            items.condition,
            items.location,
            users.name AS donor_name
        FROM requests
        JOIN items
            ON requests.item_id = items.id
        JOIN users
            ON items.donor_id = users.id
        WHERE requests.recipient_id = ?
        ORDER BY requests.requested_at DESC
    """, (
        session["user_id"],
    )).fetchall()

    connection.close()

    return render_template(
        "my_requests.html",
        requests=requests_list
    )


# ============================================================
# COMPLETE REQUEST
# ============================================================

@app.route(
    "/request/<int:request_id>/complete",
    methods=["POST"]
)
def complete_request(request_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    if session.get("role") == "admin":

        return redirect(
            url_for("admin_dashboard")
        )

    if session.get("current_mode") != "donor":

        return redirect(
            url_for("choose_mode")
        )

    connection = get_db_connection()

    req = connection.execute("""
        SELECT
            requests.*,
            items.title AS item_title,
            items.donor_id
        FROM requests
        JOIN items
            ON requests.item_id = items.id
        WHERE requests.id = ?
        AND items.donor_id = ?
    """, (
        request_id,
        session["user_id"]
    )).fetchone()

    if req is None:

        connection.close()

        return "Request not found."

    if req["status"] != "Accepted":

        connection.close()

        return "Only accepted requests can be completed."

    connection.execute("""
        UPDATE requests
        SET status = 'Completed'
        WHERE id = ?
    """, (
        request_id,
    ))

    connection.execute("""
        UPDATE items
        SET status = 'Donated'
        WHERE id = ?
    """, (
        req["item_id"],
    ))

    connection.execute("""
        INSERT INTO notifications
        (
            user_id,
            message
        )
        VALUES (?, ?)
    """, (
        req["recipient_id"],
        f"Donation completed for '{req['item_title']}'."
    ))

    connection.commit()

    connection.close()

    return redirect(
        url_for("donor_requests")
    )


# ============================================================
# NOTIFICATIONS
# ============================================================

@app.route("/notifications")
def notifications():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    connection = get_db_connection()

    notifications = connection.execute("""
        SELECT *
        FROM notifications
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (
        session["user_id"],
    )).fetchall()

    connection.close()

    return render_template(
        "notifications.html",
        notifications=notifications
    )


# ============================================================
# NOTIFICATION COUNT
# ============================================================

@app.context_processor
def notification_count():

    if "user_id" not in session:

        return {
            "unread_notifications": 0
        }

    connection = get_db_connection()

    count = connection.execute("""
        SELECT COUNT(*) AS total
        FROM notifications
        WHERE user_id = ?
        AND is_read = 0
    """, (
        session["user_id"],
    )).fetchone()["total"]

    connection.close()

    return {
        "unread_notifications": count
    }


# ============================================================
# MARK ALL NOTIFICATIONS AS READ
# ============================================================

@app.route(
    "/notifications/read-all",
    methods=["POST"]
)
def mark_all_notifications_read():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    connection = get_db_connection()

    connection.execute("""
        UPDATE notifications
        SET is_read = 1
        WHERE user_id = ?
    """, (
        session["user_id"],
    ))

    connection.commit()

    connection.close()

    return redirect(
        url_for("notifications")
    )


# ============================================================
# MATCHING
# ============================================================

@app.route("/recipient/matches")
def recipient_matches():

    # --------------------------------------------------------
    # LOGIN CHECK
    # --------------------------------------------------------

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    # --------------------------------------------------------
    # ADMIN CHECK
    # --------------------------------------------------------

    if session.get("role") == "admin":

        return redirect(
            url_for("admin_dashboard")
        )

    # --------------------------------------------------------
    # RECIPIENT MODE CHECK
    # --------------------------------------------------------

    if session.get("current_mode") != "recipient":

        return redirect(
            url_for("choose_mode")
        )

    connection = get_db_connection()

    # --------------------------------------------------------
    # GET CURRENT RECIPIENT
    # --------------------------------------------------------

    recipient = connection.execute("""
        SELECT
            id,
            name,
            location,
            category,
            requirement
        FROM users
        WHERE id = ?
    """, (
        session["user_id"],
    )).fetchone()

    if recipient is None:

        connection.close()

        return "Recipient profile not found."

    # --------------------------------------------------------
    # GET AVAILABLE ITEMS
    #
    # The recipient's own donated items are excluded.
    # Only Available items can be matched.
    # --------------------------------------------------------

    available_items = connection.execute("""
        SELECT
            items.*,
            users.name AS donor_name
        FROM items
        JOIN users
            ON items.donor_id = users.id
        WHERE items.status = 'Available'
        AND items.donor_id != ?
        ORDER BY items.created_at DESC
    """, (
        session["user_id"],
    )).fetchall()

    connection.close()

    # --------------------------------------------------------
    # CALCULATE MATCHES
    # --------------------------------------------------------

    matched_items = []

    for item in available_items:

        score, reasons = calculate_match(
            item,
            recipient
        )

        # Show items that have at least
        # one matching factor.
        if score > 0:

            matched_items.append({
                "item": item,
                "score": score,
                "reasons": reasons
            })

    # --------------------------------------------------------
    # SORT BY SCORE
    # --------------------------------------------------------

    matched_items.sort(
        key=lambda match: match["score"],
        reverse=True
    )

    # --------------------------------------------------------
    # ASSIGN MATCH LEVEL
    # --------------------------------------------------------

    for match in matched_items:

        score = match["score"]

        if score >= 80:

            match["match_level"] = (
                "Excellent Match"
            )

        elif score >= 60:

            match["match_level"] = (
                "Strong Match"
            )

        elif score >= 40:

            match["match_level"] = (
                "Good Match"
            )

        else:

            match["match_level"] = (
                "Possible Match"
            )

    # --------------------------------------------------------
    # DISPLAY MATCHES
    # --------------------------------------------------------

    return render_template(
        "matches.html",
        matched_items=matched_items,
        matches=matched_items,
        recipient=recipient
    )


# ============================================================
# EDIT ITEM
# ============================================================

@app.route(
    "/edit-item/<int:item_id>",
    methods=["GET", "POST"]
)
def edit_item(item_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    if session.get("role") == "admin":

        return redirect(
            url_for("admin_dashboard")
        )

    if session.get("current_mode") != "donor":

        return redirect(
            url_for("choose_mode")
        )

    connection = get_db_connection()

    item = connection.execute("""
        SELECT *
        FROM items
        WHERE id = ?
        AND donor_id = ?
    """, (
        item_id,
        session["user_id"]
    )).fetchone()

    if not item:

        connection.close()

        return redirect(
            url_for("my_items")
        )

    if item["status"] != "Available":

        connection.close()

        return redirect(
            url_for("my_items")
        )

    if request.method == "POST":

        title = request.form["title"]

        description = request.form[
            "description"
        ]

        category = request.form[
            "category"
        ]

        condition = request.form[
            "condition"
        ]

        quantity = request.form[
            "quantity"
        ]

        location = request.form[
            "location"
        ]

        image_filename = item["image"]

        image = request.files.get(
            "image"
        )

        if image and image.filename:

            if not allowed_file(
                image.filename
            ):

                connection.close()

                return """
                <h2>Invalid image format</h2>
                <p>
                    Please upload JPG, JPEG, PNG, or WEBP.
                </p>
                <a href="/edit-item/{}">
                    Go Back
                </a>
                """.format(
                    item_id
                )

            original_filename = secure_filename(
                image.filename
            )

            extension = original_filename.rsplit(
                ".",
                1
            )[1].lower()

            unique_filename = (
                f"{uuid.uuid4().hex}.{extension}"
            )

            image_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                unique_filename
            )

            image.save(
                image_path
            )

            image_filename = unique_filename

        connection.execute("""
            UPDATE items
            SET
                title = ?,
                description = ?,
                category = ?,
                condition = ?,
                quantity = ?,
                location = ?,
                image = ?
            WHERE id = ?
            AND donor_id = ?
        """, (
            title,
            description,
            category,
            condition,
            quantity,
            location,
            image_filename,
            item_id,
            session["user_id"]
        ))

        connection.commit()

        connection.close()

        return redirect(
            url_for("my_items")
        )

    connection.close()

    return render_template(
        "edit_item.html",
        item=item
    )


# ============================================================
# DELETE ITEM
# ============================================================

@app.route(
    "/delete-item/<int:item_id>",
    methods=["POST"]
)
def delete_item(item_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    if session.get("role") == "admin":

        return redirect(
            url_for("admin_dashboard")
        )

    if session.get("current_mode") != "donor":

        return redirect(
            url_for("choose_mode")
        )

    connection = get_db_connection()

    item = connection.execute("""
        SELECT *
        FROM items
        WHERE id = ?
        AND donor_id = ?
    """, (
        item_id,
        session["user_id"]
    )).fetchone()

    if not item:

        connection.close()

        return redirect(
            url_for("my_items")
        )

    if item["status"] != "Available":

        connection.close()

        return redirect(
            url_for("my_items")
        )

    # --------------------------------------------------------
    # DELETE IMAGE
    # --------------------------------------------------------

    if item["image"]:

        image_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            item["image"]
        )

        if os.path.exists(
            image_path
        ):

            os.remove(
                image_path
            )

    # --------------------------------------------------------
    # DELETE REQUESTS
    # --------------------------------------------------------

    connection.execute("""
        DELETE FROM requests
        WHERE item_id = ?
    """, (
        item_id,
    ))

    # --------------------------------------------------------
    # DELETE MATCHES
    # --------------------------------------------------------

    connection.execute("""
        DELETE FROM matches
        WHERE item_id = ?
    """, (
        item_id,
    ))

    # --------------------------------------------------------
    # DELETE ITEM
    # --------------------------------------------------------

    connection.execute("""
        DELETE FROM items
        WHERE id = ?
        AND donor_id = ?
    """, (
        item_id,
        session["user_id"]
    ))

    connection.commit()

    connection.close()

    return redirect(
        url_for("my_items")
    )


# ============================================================
# PROFILE
# ============================================================

@app.route(
    "/profile",
    methods=["GET", "POST"]
)
def profile():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    connection = get_db_connection()

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        location = request.form.get(
            "location",
            ""
        ).strip()

        category = request.form.get(
            "category",
            ""
        ).strip()

        requirement = request.form.get(
            "requirement",
            ""
        ).strip()

        if not name:

            connection.close()

            return "Name is required."

        connection.execute("""
            UPDATE users
            SET
                name = ?,
                phone = ?,
                location = ?,
                category = ?,
                requirement = ?
            WHERE id = ?
        """, (
            name,
            phone,
            location,
            category,
            requirement,
            session["user_id"]
        ))

        connection.commit()

        session["user_name"] = name

        connection.close()

        return redirect(
            url_for("profile")
        )

    user = connection.execute("""
        SELECT *
        FROM users
        WHERE id = ?
    """, (
        session["user_id"],
    )).fetchone()

    connection.close()

    if user is None:

        return "User not found."

    return render_template(
        "profile.html",
        user=user
    )


# ============================================================
# CANCEL REQUEST
# ============================================================

@app.route(
    "/request/<int:request_id>/cancel",
    methods=["POST"]
)
def cancel_request(request_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    if session.get("role") == "admin":

        return redirect(
            url_for("admin_dashboard")
        )

    if session.get("current_mode") != "recipient":

        return redirect(
            url_for("choose_mode")
        )

    connection = get_db_connection()

    request_data = connection.execute("""
        SELECT
            requests.id,
            requests.item_id,
            requests.recipient_id,
            requests.status,
            items.title,
            items.donor_id
        FROM requests
        JOIN items
            ON requests.item_id = items.id
        WHERE requests.id = ?
    """, (
        request_id,
    )).fetchone()

    if not request_data:

        connection.close()

        return redirect(
            url_for("recipient_requests")
        )

    if request_data["recipient_id"] != session["user_id"]:

        connection.close()

        return redirect(
            url_for("recipient_requests")
        )

    if request_data["status"] != "Pending":

        connection.close()

        return redirect(
            url_for("recipient_requests")
        )

    connection.execute("""
        UPDATE requests
        SET status = 'Cancelled'
        WHERE id = ?
    """, (
        request_id,
    ))

    connection.execute("""
        INSERT INTO notifications
        (
            user_id,
            message
        )
        VALUES (?, ?)
    """, (
        request_data["donor_id"],
        f"Request for '{request_data['title']}' was cancelled by the recipient."
    ))

    connection.commit()

    connection.close()

    return redirect(
        url_for("recipient_requests")
    )


# ============================================================
# CONFIRM RECEIPT
# ============================================================

@app.route(
    "/request/<int:request_id>/confirm-receipt",
    methods=["POST"]
)
def confirm_receipt(request_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    if session.get("role") == "admin":

        return redirect(
            url_for("admin_dashboard")
        )

    if session.get("current_mode") != "recipient":

        return redirect(
            url_for("choose_mode")
        )

    connection = get_db_connection()

    request_data = connection.execute("""
        SELECT
            requests.id,
            requests.recipient_id,
            requests.status,
            items.title,
            items.donor_id
        FROM requests
        JOIN items
            ON requests.item_id = items.id
        WHERE requests.id = ?
    """, (
        request_id,
    )).fetchone()

    if not request_data:

        connection.close()

        return redirect(
            url_for("recipient_requests")
        )

    if request_data["recipient_id"] != session["user_id"]:

        connection.close()

        return redirect(
            url_for("recipient_requests")
        )

    if request_data["status"] != "Completed":

        connection.close()

        return redirect(
            url_for("recipient_requests")
        )

    connection.execute("""
        UPDATE requests
        SET status = 'Confirmed'
        WHERE id = ?
    """, (
        request_id,
    ))

    connection.execute("""
        INSERT INTO notifications
        (
            user_id,
            message
        )
        VALUES (?, ?)
    """, (
        request_data["donor_id"],
        f"Recipient confirmed receiving '{request_data['title']}'. Donation is fully completed."
    ))

    connection.commit()

    connection.close()

    return redirect(
        url_for("recipient_requests")
    )


# ============================================================
# FILE TOO LARGE
# ============================================================

@app.errorhandler(413)
def file_too_large(error):

    return """
    <div style="
        font-family: Arial;
        text-align: center;
        margin-top: 100px;
    ">

        <h1>
            Image Too Large
        </h1>

        <p>
            Please upload an image smaller than 5 MB.
        </p>

        <a href="/add-item">
            Go Back
        </a>

    </div>
    """, 413

#-----------------page not found----------------------------

@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )