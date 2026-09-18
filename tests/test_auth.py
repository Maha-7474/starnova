from unittest.mock import MagicMock, patch

import pytest
from mysql.connector import Error
from werkzeug.security import check_password_hash, generate_password_hash

from app import create_app


@pytest.fixture
def app():
    application = create_app()
    application.config.update(TESTING=True, SECRET_KEY="test-secret-key")
    return application


@pytest.fixture
def client(app):
    return app.test_client()


def make_connection(fetchone_values=None, lastrowid=1):
    """Create mocked MySQL connection and dictionary cursor objects."""
    cursor = MagicMock()
    cursor.fetchone.side_effect = fetchone_values or []
    cursor.lastrowid = lastrowid
    connection = MagicMock()
    connection.cursor.return_value = cursor
    return connection, cursor


def registration_payload(**overrides):
    payload = {
        "name": "Test User",
        "email": "test@example.com",
        "password": "password123",
        "role": "user",
    }
    payload.update(overrides)
    return payload


def test_registers_user_with_normalized_email_and_hashed_password(client):
    connection, cursor = make_connection([None], lastrowid=17)

    with patch("app.get_connection", return_value=connection):
        response = client.post(
            "/api/auth/register",
            json=registration_payload(email=" Test@Example.COM "),
        )

    assert response.status_code == 201
    assert response.get_json() == {
        "message": "Registration successful.",
        "user": {
            "id": 17,
            "name": "Test User",
            "email": "test@example.com",
            "role": "user",
        },
    }
    inserted_values = cursor.execute.call_args_list[1].args[1]
    assert inserted_values[1] == "test@example.com"
    assert inserted_values[2] != "password123"
    assert check_password_hash(inserted_values[2], "password123")
    connection.commit.assert_called_once()


def test_registration_rejects_duplicate_email(client):
    existing_user = {"id": 4}
    connection, _ = make_connection([existing_user])

    with patch("app.get_connection", return_value=connection):
        response = client.post("/api/auth/register", json=registration_payload())

    assert response.status_code == 409
    assert response.get_json() == {"message": "An account with this email already exists."}


@pytest.mark.parametrize(
    "payload",
    [
        registration_payload(name=""),
        registration_payload(email="not-an-email"),
        registration_payload(password="short"),
        {},
    ],
)
def test_registration_rejects_missing_or_invalid_input(client, payload):
    with patch("app.get_connection") as mock_get_connection:
        response = client.post("/api/auth/register", json=payload)

    assert response.status_code == 400
    mock_get_connection.assert_not_called()


def test_registration_rejects_an_invalid_role(client):
    with patch("app.get_connection") as mock_get_connection:
        response = client.post(
            "/api/auth/register",
            json=registration_payload(role="admin"),
        )

    assert response.status_code == 400
    assert response.get_json() == {"message": "Role must be either 'user' or 'organizer'."}
    mock_get_connection.assert_not_called()


def test_registration_returns_safe_error_for_database_failure(client):
    with patch("app.get_connection", side_effect=Error("Database unavailable")):
        response = client.post("/api/auth/register", json=registration_payload())

    assert response.status_code == 503
    assert response.get_json() == {"message": "Registration is temporarily unavailable."}


def test_login_creates_session_and_returns_safe_user(client):
    password_hash = generate_password_hash("password123")
    user = {
        "id": 8,
        "name": "Test User",
        "email": "test@example.com",
        "password_hash": password_hash,
        "role": "user",
    }
    connection, _ = make_connection([user])

    with patch("app.get_connection", return_value=connection):
        response = client.post(
            "/api/auth/login",
            json={"email": " TEST@EXAMPLE.COM ", "password": "password123"},
        )

    assert response.status_code == 200
    assert response.get_json() == {
        "message": "Login successful.",
        "user": {"id": 8, "name": "Test User", "email": "test@example.com", "role": "user"},
    }
    assert "password_hash" not in response.get_json()["user"]
    with client.session_transaction() as saved_session:
        assert saved_session["user_id"] == 8
        assert saved_session["role"] == "user"


def test_login_rejects_incorrect_password(client):
    user = {
        "id": 8,
        "name": "Test User",
        "email": "test@example.com",
        "password_hash": generate_password_hash("correct-password"),
        "role": "user",
    }
    connection, _ = make_connection([user])

    with patch("app.get_connection", return_value=connection):
        response = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "incorrect-password"},
        )

    assert response.status_code == 401
    assert response.get_json() == {"message": "Invalid email or password."}


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"email": "test@example.com"},
        {"password": "password123"},
        {"email": "not-an-email", "password": "password123"},
    ],
)
def test_login_rejects_missing_input(client, payload):
    with patch("app.get_connection") as mock_get_connection:
        response = client.post("/api/auth/login", json=payload)

    assert response.status_code == 400
    mock_get_connection.assert_not_called()


def test_logout_clears_the_session(client):
    with client.session_transaction() as saved_session:
        saved_session["user_id"] = 8
        saved_session["role"] = "user"

    response = client.post("/api/auth/logout")

    assert response.status_code == 200
    assert response.get_json() == {"message": "Logged out successfully."}
    with client.session_transaction() as saved_session:
        assert "user_id" not in saved_session
        assert "role" not in saved_session


def test_current_user_requires_authentication(client):
    response = client.get("/api/me")

    assert response.status_code == 401
    assert response.get_json() == {"message": "Authentication is required."}


def test_current_user_returns_safe_user_data(client):
    user = {
        "id": 8,
        "name": "Test User",
        "email": "test@example.com",
        "role": "user",
        "password_hash": "must-not-be-returned",
    }
    connection, cursor = make_connection([user])
    with client.session_transaction() as saved_session:
        saved_session["user_id"] = 8
        saved_session["role"] = "user"

    with patch("app.get_connection", return_value=connection):
        response = client.get("/api/me")

    assert response.status_code == 200
    assert response.get_json() == {
        "user": {"id": 8, "name": "Test User", "email": "test@example.com", "role": "user"}
    }
    assert "password_hash" not in response.get_json()["user"]
    assert "password_hash" not in cursor.execute.call_args.args[0]


def test_current_user_handles_database_failure_safely(client):
    with client.session_transaction() as saved_session:
        saved_session["user_id"] = 8
        saved_session["role"] = "user"

    with patch("app.get_connection", side_effect=Error("Database unavailable")):
        response = client.get("/api/me")

    assert response.status_code == 503
    assert response.get_json() == {"message": "User information is temporarily unavailable."}
