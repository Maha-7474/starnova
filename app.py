"""Flask application entry point for StarNova."""

import os
import re
from datetime import date, datetime, time, timedelta
from urllib.parse import urlparse

from flask import Flask, jsonify, render_template, request, session
from mysql.connector import Error
from werkzeug.security import check_password_hash, generate_password_hash

from database import get_connection

ALLOWED_ROLES = {"user", "organizer"}
ALLOWED_OPPORTUNITY_TYPES = {"audition", "competition"}
ALLOWED_CATEGORIES = {"acting", "music", "dance"}
ALLOWED_APPLICATION_STATUSES = {
    "Pending",
    "Under Review",
    "Shortlisted",
    "Selected",
    "Rejected",
}
MINIMUM_PASSWORD_LENGTH = 8
MAXIMUM_EXPERIENCE_LENGTH = 5000
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(email):
    """Return a consistent email value, or an empty string for invalid input."""
    if not isinstance(email, str):
        return ""
    return email.strip().lower()


def is_valid_email(email):
    """Perform a small, practical email-format check."""
    return bool(EMAIL_PATTERN.fullmatch(email)) and len(email) <= 150


def get_json_object():
    """Return JSON request data only when it is an object."""
    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else None


def safe_user(user):
    """Return only fields that may be sent to a browser."""
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
    }


def close_database_resources(cursor, connection):
    """Close MySQL resources after a request, even when an error occurs."""
    if cursor is not None:
        cursor.close()
    if connection is not None:
        connection.close()


def rollback_connection(connection):
    """Roll back a failed write without masking the original database error."""
    if connection is not None:
        try:
            connection.rollback()
        except Error:
            pass


def format_date(value):
    """Convert a database date into an API-friendly string."""
    if isinstance(value, (date, datetime)):
        return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
    return value


def format_time(value):
    """Convert a database time into an API-friendly string."""
    if isinstance(value, time):
        return value.strftime("%H:%M:%S")

    if isinstance(value, timedelta):
        total_seconds = int(value.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    return value


def safe_post(post):
    """Return fields that are safe and useful in an opportunity response."""
    return {
        "id": post["id"],
        "organizer_id": post["organizer_id"],
        "title": post["title"],
        "opportunity_type": post["opportunity_type"],
        "category": post["category"],
        "event_date": format_date(post["event_date"]),
        "start_time": format_time(post["start_time"]),
        "end_time": format_time(post["end_time"]),
        "venue": post["venue"],
        "description": post["description"],
        "image_path": post["image_path"],
        "created_at": (
    post["created_at"].isoformat()
    if isinstance(post.get("created_at"), datetime)
    else post.get("created_at")
),
"updated_at": (
    post["updated_at"].isoformat()
    if isinstance(post.get("updated_at"), datetime)
    else post.get("updated_at")
),
    }


def parse_post_id(post_id):
    """Return a positive integer post ID, or None for an invalid route value."""
    try:
        parsed_id = int(post_id)
    except (TypeError, ValueError):
        return None
    return parsed_id if parsed_id > 0 else None


def parse_time_value(value):
    """Accept common API time formats and return a Python time value."""
    if not isinstance(value, str):
        return None
    for time_format in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(value, time_format).time()
        except ValueError:
            continue
    return None


def validate_post_payload(payload):
    """Validate a complete create/update post JSON body."""
    if payload is None:
        return None, "A JSON request body is required."

    title = payload.get("title")
    opportunity_type = payload.get("opportunity_type")
    category = payload.get("category")
    event_date = payload.get("event_date")
    start_time = payload.get("start_time")
    end_time = payload.get("end_time")
    venue = payload.get("venue")
    description = payload.get("description")

    if not isinstance(title, str) or not title.strip():
        return None, "Title is required."
    title = title.strip()
    if len(title) > 200:
        return None, "Title must be 200 characters or fewer."

    if opportunity_type not in ALLOWED_OPPORTUNITY_TYPES:
        return None, "Opportunity type must be 'audition' or 'competition'."
    if category not in ALLOWED_CATEGORIES:
        return None, "Category must be 'acting', 'music', or 'dance'."

    if not isinstance(event_date, str):
        return None, "Event date must use YYYY-MM-DD format."
    try:
        parsed_event_date = datetime.strptime(event_date, "%Y-%m-%d").date()
    except ValueError:
        return None, "Event date must use YYYY-MM-DD format."

    if (start_time is None) != (end_time is None):
        return None, "Start time and end time must be provided together."
    parsed_start_time = None
    parsed_end_time = None
    if start_time is not None:
        parsed_start_time = parse_time_value(start_time)
        parsed_end_time = parse_time_value(end_time)
        if parsed_start_time is None or parsed_end_time is None:
            return None, "Times must use HH:MM or HH:MM:SS format."
        if parsed_end_time <= parsed_start_time:
            return None, "End time must be later than start time."

    if not isinstance(venue, str) or not venue.strip():
        return None, "Venue is required."
    venue = venue.strip()
    if len(venue) > 255:
        return None, "Venue must be 255 characters or fewer."

    if description is not None and not isinstance(description, str):
        return None, "Description must be text."

    return {
        "title": title,
        "opportunity_type": opportunity_type,
        "category": category,
        "event_date": parsed_event_date,
        "start_time": parsed_start_time,
        "end_time": parsed_end_time,
        "venue": venue,
        "description": description.strip() if isinstance(description, str) else None,
    }, None


def require_organizer():
    """Return the session organizer ID or a safe authorization response."""
    user_id = session.get("user_id")
    if not isinstance(user_id, int):
        return None, (jsonify({"message": "Authentication is required."}), 401)
    if session.get("role") != "organizer":
        return None, (jsonify({"message": "Organizer access is required."}), 403)
    return user_id, None


def require_user():
    """Return the session user ID or a safe authorization response."""
    user_id = session.get("user_id")
    if not isinstance(user_id, int):
        return None, (jsonify({"message": "Authentication is required."}), 401)
    if session.get("role") != "user":
        return None, (jsonify({"message": "User access is required."}), 403)
    return user_id, None


def is_valid_portfolio_url(portfolio_url):
    """Allow only reasonably-sized HTTP(S) portfolio URLs."""
    if not isinstance(portfolio_url, str) or len(portfolio_url) > 500:
        return False
    parsed_url = urlparse(portfolio_url)
    return parsed_url.scheme in {"http", "https"} and bool(parsed_url.netloc)


def validate_application_payload(payload):
    """Validate data supplied by a user when applying to an opportunity."""
    if payload is None:
        return None, "A JSON request body is required."

    experience = payload.get("experience")
    portfolio_url = payload.get("portfolio_url")
    if not isinstance(experience, str) or not experience.strip():
        return None, "Experience is required."
    experience = experience.strip()
    if len(experience) > MAXIMUM_EXPERIENCE_LENGTH:
        return None, "Experience must be 5000 characters or fewer."

    if portfolio_url is not None:
        if not is_valid_portfolio_url(portfolio_url):
            return None, "Portfolio URL must be a valid HTTP or HTTPS URL."
        portfolio_url = portfolio_url.strip()

    return {"experience": experience, "portfolio_url": portfolio_url}, None


def safe_application(application):
    """Return non-sensitive application fields."""
    return {
        "id": application["id"],
        "post_id": application["post_id"],
        "applicant_id": application["applicant_id"],
        "experience": application["experience"],
        "portfolio_url": application["portfolio_url"],
        "status": application["status"],
        "applied_at": application.get("applied_at"),
        "updated_at": application.get("updated_at"),
    }


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        # False keeps cookie sessions usable on local http://localhost development.
        SESSION_COOKIE_SECURE=False,
    )

    @app.get("/")
    def home():
        """Show a temporary home page for the backend foundation."""
        return render_template("home.html")

    @app.get("/api/health")
    def health_check():
        """Report that the web application is running."""
        return jsonify({"status": "ok"}), 200

    @app.get("/api/db-health")
    def database_health_check():
        """Check that the application can connect to MySQL."""
        connection = None
        cursor = None

        try:
            connection = get_connection()
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            return jsonify({"status": "ok", "database": "reachable"}), 200
        except Error:
            app.logger.warning("Database health check failed.")
            return jsonify({"status": "error", "message": "Database unavailable"}), 503
        except (TypeError, ValueError):
            app.logger.warning("Database health check configuration is invalid.")
            return jsonify({"status": "error", "message": "Database unavailable"}), 503
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None:
                connection.close()

    @app.post("/api/auth/register")
    def register():
        """Create a user account with a securely hashed password."""
        payload = get_json_object()
        if payload is None:
            return jsonify({"message": "A JSON request body is required."}), 400

        name = payload.get("name")
        email = normalize_email(payload.get("email"))
        password = payload.get("password")
        role = payload.get("role")

        if not isinstance(name, str) or not name.strip():
            return jsonify({"message": "Name is required."}), 400
        name = name.strip()
        if len(name) > 100:
            return jsonify({"message": "Name must be 100 characters or fewer."}), 400
        if not is_valid_email(email):
            return jsonify({"message": "A valid email is required."}), 400
        if not isinstance(password, str) or len(password) < MINIMUM_PASSWORD_LENGTH:
            return jsonify({
                "message": f"Password must be at least {MINIMUM_PASSWORD_LENGTH} characters long."
            }), 400
        if role not in ALLOWED_ROLES:
            return jsonify({"message": "Role must be either 'user' or 'organizer'."}), 400

        connection = None
        cursor = None
        try:
            connection = get_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))

            if cursor.fetchone() is not None:
                return jsonify({"message": "An account with this email already exists."}), 409

            password_hash = generate_password_hash(password)
            cursor.execute(
                """
                INSERT INTO users (name, email, password_hash, role)
                VALUES (%s, %s, %s, %s)
                """,
                (name, email, password_hash, role),
            )
            connection.commit()

            user = {"id": cursor.lastrowid, "name": name, "email": email, "role": role}
            return jsonify({"message": "Registration successful.", "user": user}), 201
        except Error as error:
            if getattr(error, "errno", None) == 1062:
                return jsonify({"message": "An account with this email already exists."}), 409
            app.logger.warning("Registration database operation failed.")
            return jsonify({"message": "Registration is temporarily unavailable."}), 503
        finally:
            close_database_resources(cursor, connection)

    @app.post("/api/auth/login")
    def login():
        """Verify credentials and store the minimum identity in the session."""
        payload = get_json_object()
        if payload is None:
            return jsonify({"message": "A JSON request body is required."}), 400

        email = normalize_email(payload.get("email"))
        password = payload.get("password")
        if not is_valid_email(email) or not isinstance(password, str) or not password:
            return jsonify({"message": "A valid email and password are required."}), 400

        connection = None
        cursor = None
        try:
            connection = get_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT id, name, email, password_hash, role
                FROM users
                WHERE email = %s
                """,
                (email,),
            )
            user = cursor.fetchone()

            try:
                password_is_valid = user is not None and check_password_hash(
                    user["password_hash"], password
                )
            except (TypeError, ValueError):
                password_is_valid = False

            if not password_is_valid:
                return jsonify({"message": "Invalid email or password."}), 401

            session.clear()
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            return jsonify({"message": "Login successful.", "user": safe_user(user)}), 200
        except Error:
            app.logger.warning("Login database operation failed.")
            return jsonify({"message": "Login is temporarily unavailable."}), 503
        finally:
            close_database_resources(cursor, connection)

    @app.post("/api/auth/logout")
    def logout():
        """Clear the session whether or not a user is currently logged in."""
        session.clear()
        return jsonify({"message": "Logged out successfully."}), 200

    @app.get("/api/me")
    def current_user():
        """Return the logged-in user's current safe profile."""
        user_id = session.get("user_id")
        if not isinstance(user_id, int):
            return jsonify({"message": "Authentication is required."}), 401

        connection = None
        cursor = None
        try:
            connection = get_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT id, name, email, role
                FROM users
                WHERE id = %s
                """,
                (user_id,),
            )
            user = cursor.fetchone()
            if user is None:
                session.clear()
                return jsonify({"message": "Authentication is required."}), 401

            return jsonify({"user": safe_user(user)}), 200
        except Error:
            app.logger.warning("Current-user database operation failed.")
            return jsonify({"message": "User information is temporarily unavailable."}), 503
        finally:
            close_database_resources(cursor, connection)

    @app.get("/api/posts")
    def list_posts():
        """Return public opportunities, with optional safe filters."""
        opportunity_type = request.args.get("type")
        category = request.args.get("category")
        search_query = request.args.get("q")

        where_clauses = []
        parameters = []
        if opportunity_type is not None:
            opportunity_type = opportunity_type.strip().lower()
            if opportunity_type not in ALLOWED_OPPORTUNITY_TYPES:
                return jsonify({"message": "Invalid opportunity type filter."}), 400
            where_clauses.append("opportunity_type = %s")
            parameters.append(opportunity_type)
        if category is not None:
            category = category.strip().lower()
            if category not in ALLOWED_CATEGORIES:
                return jsonify({"message": "Invalid category filter."}), 400
            where_clauses.append("category = %s")
            parameters.append(category)
        if search_query is not None and search_query.strip():
            like_query = f"%{search_query.strip()}%"
            where_clauses.append(
                "(title LIKE %s OR category LIKE %s OR venue LIKE %s OR description LIKE %s)"
            )
            parameters.extend([like_query, like_query, like_query, like_query])

        query = """
            SELECT id, organizer_id, title, opportunity_type, category, event_date,
                   start_time, end_time, venue, description, image_path,
                   created_at, updated_at
            FROM posts
        """
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        query += " ORDER BY event_date ASC, id ASC"

        connection = None
        cursor = None
        try:
            connection = get_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, tuple(parameters))
            return jsonify({"posts": [safe_post(post) for post in cursor.fetchall()]}), 200
        except Error:
            app.logger.warning("Post listing database operation failed.")
            return jsonify({"message": "Opportunities are temporarily unavailable."}), 503
        finally:
            close_database_resources(cursor, connection)

    @app.get("/api/posts/<post_id>")
    def get_post(post_id):
        """Return one public opportunity by its ID."""
        parsed_post_id = parse_post_id(post_id)
        if parsed_post_id is None:
            return jsonify({"message": "Post ID must be a positive integer."}), 400

        connection = None
        cursor = None
        try:
            connection = get_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT id, organizer_id, title, opportunity_type, category, event_date,
                       start_time, end_time, venue, description, image_path,
                       created_at, updated_at
                FROM posts
                WHERE id = %s
                """,
                (parsed_post_id,),
            )
            post = cursor.fetchone()
            if post is None:
                return jsonify({"message": "Opportunity not found."}), 404
            return jsonify({"post": safe_post(post)}), 200
        except Error:
            app.logger.warning("Post detail database operation failed.")
            return jsonify({"message": "Opportunity is temporarily unavailable."}), 503
        finally:
            close_database_resources(cursor, connection)

    @app.post("/api/posts")
    def create_post():
        """Create an opportunity owned by the logged-in organizer."""
        organizer_id, authorization_error = require_organizer()
        if authorization_error is not None:
            return authorization_error
        post_data, validation_error = validate_post_payload(get_json_object())
        if validation_error is not None:
            return jsonify({"message": validation_error}), 400

        connection = None
        cursor = None
        try:
            connection = get_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                """
                INSERT INTO posts (
                    organizer_id, title, opportunity_type, category, event_date,
                    start_time, end_time, venue, description, image_path
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    organizer_id,
                    post_data["title"],
                    post_data["opportunity_type"],
                    post_data["category"],
                    post_data["event_date"],
                    post_data["start_time"],
                    post_data["end_time"],
                    post_data["venue"],
                    post_data["description"],
                    None,
                ),
            )
            connection.commit()
            created_post = {"id": cursor.lastrowid, "organizer_id": organizer_id, **post_data,
                            "image_path": None, "created_at": None, "updated_at": None}
            return jsonify({"message": "Opportunity created.", "post": safe_post(created_post)}), 201
        except Error:
            rollback_connection(connection)
            app.logger.warning("Post creation database operation failed.")
            return jsonify({"message": "Opportunity creation is temporarily unavailable."}), 503
        finally:
            close_database_resources(cursor, connection)

    @app.put("/api/posts/<post_id>")
    def update_post(post_id):
        """Update a post only when it belongs to the logged-in organizer."""
        organizer_id, authorization_error = require_organizer()
        if authorization_error is not None:
            return authorization_error
        parsed_post_id = parse_post_id(post_id)
        if parsed_post_id is None:
            return jsonify({"message": "Post ID must be a positive integer."}), 400
        post_data, validation_error = validate_post_payload(get_json_object())
        if validation_error is not None:
            return jsonify({"message": validation_error}), 400

        connection = None
        cursor = None
        try:
            connection = get_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT id, organizer_id FROM posts WHERE id = %s", (parsed_post_id,))
            existing_post = cursor.fetchone()
            if existing_post is None:
                return jsonify({"message": "Opportunity not found."}), 404
            if existing_post["organizer_id"] != organizer_id:
                return jsonify({"message": "You do not own this opportunity."}), 403

            cursor.execute(
                """
                UPDATE posts
                SET title = %s, opportunity_type = %s, category = %s, event_date = %s,
                    start_time = %s, end_time = %s, venue = %s, description = %s
                WHERE id = %s
                """,
                (
                    post_data["title"],
                    post_data["opportunity_type"],
                    post_data["category"],
                    post_data["event_date"],
                    post_data["start_time"],
                    post_data["end_time"],
                    post_data["venue"],
                    post_data["description"],
                    parsed_post_id,
                ),
            )
            connection.commit()
            updated_post = {"id": parsed_post_id, "organizer_id": organizer_id, **post_data,
                            "image_path": None, "created_at": None, "updated_at": None}
            return jsonify({"message": "Opportunity updated.", "post": safe_post(updated_post)}), 200
        except Error:
            rollback_connection(connection)
            app.logger.warning("Post update database operation failed.")
            return jsonify({"message": "Opportunity update is temporarily unavailable."}), 503
        finally:
            close_database_resources(cursor, connection)

    @app.delete("/api/posts/<post_id>")
    def delete_post(post_id):
        """Delete a post only when it belongs to the logged-in organizer."""
        organizer_id, authorization_error = require_organizer()
        if authorization_error is not None:
            return authorization_error
        parsed_post_id = parse_post_id(post_id)
        if parsed_post_id is None:
            return jsonify({"message": "Post ID must be a positive integer."}), 400

        connection = None
        cursor = None
        try:
            connection = get_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT id, organizer_id FROM posts WHERE id = %s", (parsed_post_id,))
            existing_post = cursor.fetchone()
            if existing_post is None:
                return jsonify({"message": "Opportunity not found."}), 404
            if existing_post["organizer_id"] != organizer_id:
                return jsonify({"message": "You do not own this opportunity."}), 403

            cursor.execute("DELETE FROM posts WHERE id = %s", (parsed_post_id,))
            connection.commit()
            return jsonify({"message": "Opportunity deleted."}), 200
        except Error:
            rollback_connection(connection)
            app.logger.warning("Post deletion database operation failed.")
            return jsonify({"message": "Opportunity deletion is temporarily unavailable."}), 503
        finally:
            close_database_resources(cursor, connection)

    @app.post("/api/posts/<post_id>/apply")
    def apply_to_post(post_id):
        """Allow an authenticated normal user to apply to an opportunity."""
        applicant_id, authorization_error = require_user()
        if authorization_error is not None:
            return authorization_error
        parsed_post_id = parse_post_id(post_id)
        if parsed_post_id is None:
            return jsonify({"message": "Post ID must be a positive integer."}), 400
        application_data, validation_error = validate_application_payload(get_json_object())
        if validation_error is not None:
            return jsonify({"message": validation_error}), 400

        connection = None
        cursor = None
        try:
            connection = get_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT id FROM posts WHERE id = %s", (parsed_post_id,))
            if cursor.fetchone() is None:
                return jsonify({"message": "Opportunity not found."}), 404

            cursor.execute(
                "SELECT id FROM applications WHERE post_id = %s AND applicant_id = %s",
                (parsed_post_id, applicant_id),
            )
            if cursor.fetchone() is not None:
                return jsonify({"message": "You have already applied to this opportunity."}), 409

            cursor.execute(
                """
                INSERT INTO applications (post_id, applicant_id, experience, portfolio_url, status)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    parsed_post_id,
                    applicant_id,
                    application_data["experience"],
                    application_data["portfolio_url"],
                    "Pending",
                ),
            )
            connection.commit()
            application = {
                "id": cursor.lastrowid,
                "post_id": parsed_post_id,
                "applicant_id": applicant_id,
                "experience": application_data["experience"],
                "portfolio_url": application_data["portfolio_url"],
                "status": "Pending",
                "applied_at": None,
                "updated_at": None,
            }
            return jsonify({"message": "Application submitted.", "application": safe_application(application)}), 201
        except Error as error:
            rollback_connection(connection)
            if getattr(error, "errno", None) == 1062:
                return jsonify({"message": "You have already applied to this opportunity."}), 409
            app.logger.warning("Application creation database operation failed.")
            return jsonify({"message": "Application submission is temporarily unavailable."}), 503
        finally:
            close_database_resources(cursor, connection)

    @app.get("/api/my-applications")
    def my_applications():
        """Return applications belonging only to the logged-in normal user."""
        applicant_id, authorization_error = require_user()
        if authorization_error is not None:
            return authorization_error

        connection = None
        cursor = None
        try:
            connection = get_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT a.id AS application_id, a.post_id, p.title, p.opportunity_type,
                       p.category, p.event_date, p.venue, a.status,
                       a.applied_at, a.updated_at
                FROM applications AS a
                INNER JOIN posts AS p ON p.id = a.post_id
                WHERE a.applicant_id = %s
                ORDER BY a.applied_at DESC, a.id DESC
                """,
                (applicant_id,),
            )
            applications = []
            for application in cursor.fetchall():
                applications.append(
                    {
                        "id": application["application_id"],
                        "post_id": application["post_id"],
                        "title": application["title"],
                        "opportunity_type": application["opportunity_type"],
                        "category": application["category"],
                        "event_date": format_date(application["event_date"]),
                        "venue": application["venue"],
                        "status": application["status"],
                        "applied_at": application["applied_at"],
                        "updated_at": application["updated_at"],
                    }
                )
            return jsonify({"applications": applications}), 200
        except Error:
            app.logger.warning("My-applications database operation failed.")
            return jsonify({"message": "Applications are temporarily unavailable."}), 503
        finally:
            close_database_resources(cursor, connection)

    @app.get("/api/posts/<post_id>/applications")
    def post_applications(post_id):
        """Allow a post owner to view applicants for that one opportunity."""
        organizer_id, authorization_error = require_organizer()
        if authorization_error is not None:
            return authorization_error
        parsed_post_id = parse_post_id(post_id)
        if parsed_post_id is None:
            return jsonify({"message": "Post ID must be a positive integer."}), 400

        connection = None
        cursor = None
        try:
            connection = get_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT id, organizer_id FROM posts WHERE id = %s", (parsed_post_id,))
            post = cursor.fetchone()
            if post is None:
                return jsonify({"message": "Opportunity not found."}), 404
            if post["organizer_id"] != organizer_id:
                return jsonify({"message": "You do not own this opportunity."}), 403

            cursor.execute(
                """
                SELECT a.id AS application_id, a.applicant_id, u.name AS applicant_name,
                       u.email AS applicant_email, a.experience, a.portfolio_url,
                       a.status, a.applied_at, a.updated_at
                FROM applications AS a
                INNER JOIN users AS u ON u.id = a.applicant_id
                WHERE a.post_id = %s
                ORDER BY a.applied_at DESC, a.id DESC
                """,
                (parsed_post_id,),
            )
            applications = []
            for application in cursor.fetchall():
                applications.append(
                    {
                        "id": application["application_id"],
                        "applicant_id": application["applicant_id"],
                        "applicant_name": application["applicant_name"],
                        "applicant_email": application["applicant_email"],
                        "experience": application["experience"],
                        "portfolio_url": application["portfolio_url"],
                        "status": application["status"],
                        "applied_at": application["applied_at"],
                        "updated_at": application["updated_at"],
                    }
                )
            return jsonify({"applications": applications}), 200
        except Error:
            app.logger.warning("Post-applications database operation failed.")
            return jsonify({"message": "Applications are temporarily unavailable."}), 503
        finally:
            close_database_resources(cursor, connection)

    @app.put("/api/applications/<application_id>/status")
    def update_application_status(application_id):
        """Allow an opportunity owner to choose an allowed application status."""
        organizer_id, authorization_error = require_organizer()
        if authorization_error is not None:
            return authorization_error
        parsed_application_id = parse_post_id(application_id)
        if parsed_application_id is None:
            return jsonify({"message": "Application ID must be a positive integer."}), 400
        payload = get_json_object()
        if payload is None or payload.get("status") not in ALLOWED_APPLICATION_STATUSES:
            return jsonify({"message": "A valid application status is required."}), 400
        status = payload["status"]

        connection = None
        cursor = None
        try:
            connection = get_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT a.id, a.post_id, a.applicant_id, a.experience, a.portfolio_url,
                       a.status, a.applied_at, a.updated_at, p.organizer_id
                FROM applications AS a
                INNER JOIN posts AS p ON p.id = a.post_id
                WHERE a.id = %s
                """,
                (parsed_application_id,),
            )
            application = cursor.fetchone()
            if application is None:
                return jsonify({"message": "Application not found."}), 404
            if application["organizer_id"] != organizer_id:
                return jsonify({"message": "You do not own this opportunity."}), 403

            cursor.execute(
                "UPDATE applications SET status = %s WHERE id = %s",
                (status, parsed_application_id),
            )
            connection.commit()
            application["status"] = status
            return jsonify({"message": "Application status updated.", "application": safe_application(application)}), 200
        except Error:
            rollback_connection(connection)
            app.logger.warning("Application status database operation failed.")
            return jsonify({"message": "Application status update is temporarily unavailable."}), 503
        finally:
            close_database_resources(cursor, connection)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
