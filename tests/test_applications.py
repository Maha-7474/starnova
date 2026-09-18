from unittest.mock import MagicMock, patch

import pytest

from app import create_app


@pytest.fixture
def app():
    application = create_app()
    application.config.update(TESTING=True, SECRET_KEY="test-secret-key")
    return application


@pytest.fixture
def client(app):
    return app.test_client()


def make_connection(fetchone_values=None, fetchall_values=None, lastrowid=1):
    """Create mocked MySQL connection and dictionary cursor objects."""
    cursor = MagicMock()
    cursor.fetchone.side_effect = fetchone_values or []
    cursor.fetchall.return_value = fetchall_values or []
    cursor.lastrowid = lastrowid
    connection = MagicMock()
    connection.cursor.return_value = cursor
    return connection, cursor


def set_session_user(client, user_id=11, role="user"):
    """Set the same minimal identity written by the login route."""
    with client.session_transaction() as saved_session:
        saved_session["user_id"] = user_id
        saved_session["role"] = role


def application_payload(**overrides):
    payload = {
        "experience": "Two years of college theatre experience.",
        "portfolio_url": "https://portfolio.example.test/test-user",
    }
    payload.update(overrides)
    return payload


def application_record(application_id=7, post_id=3, applicant_id=11, organizer_id=8):
    return {
        "id": application_id,
        "post_id": post_id,
        "applicant_id": applicant_id,
        "experience": "Two years of college theatre experience.",
        "portfolio_url": "https://portfolio.example.test/test-user",
        "status": "Pending",
        "applied_at": None,
        "updated_at": None,
        "organizer_id": organizer_id,
    }


def test_apply_requires_authentication(client):
    with patch("app.get_connection") as mock_get_connection:
        response = client.post("/api/posts/3/apply", json=application_payload())

    assert response.status_code == 401
    mock_get_connection.assert_not_called()


def test_organizer_cannot_apply(client):
    set_session_user(client, role="organizer")

    with patch("app.get_connection") as mock_get_connection:
        response = client.post("/api/posts/3/apply", json=application_payload())

    assert response.status_code == 403
    mock_get_connection.assert_not_called()


def test_normal_user_can_apply_with_session_identity_and_pending_status(client):
    set_session_user(client, user_id=11)
    connection, cursor = make_connection(fetchone_values=[{"id": 3}, None], lastrowid=14)
    payload = application_payload(applicant_id=999, status="Selected")

    with patch("app.get_connection", return_value=connection):
        response = client.post("/api/posts/3/apply", json=payload)

    assert response.status_code == 201
    application = response.get_json()["application"]
    assert application["applicant_id"] == 11
    assert application["status"] == "Pending"
    assert "password_hash" not in application
    insert_values = cursor.execute.call_args_list[2].args[1]
    assert insert_values == (
        3,
        11,
        "Two years of college theatre experience.",
        "https://portfolio.example.test/test-user",
        "Pending",
    )
    connection.commit.assert_called_once()


def test_apply_returns_404_for_a_missing_post(client):
    set_session_user(client)
    connection, _ = make_connection(fetchone_values=[None])

    with patch("app.get_connection", return_value=connection):
        response = client.post("/api/posts/999/apply", json=application_payload())

    assert response.status_code == 404
    assert response.get_json() == {"message": "Opportunity not found."}


def test_apply_rejects_a_duplicate_application(client):
    set_session_user(client)
    connection, _ = make_connection(fetchone_values=[{"id": 3}, {"id": 7}])

    with patch("app.get_connection", return_value=connection):
        response = client.post("/api/posts/3/apply", json=application_payload())

    assert response.status_code == 409
    assert response.get_json() == {"message": "You have already applied to this opportunity."}


@pytest.mark.parametrize(
    "payload",
    [
        {},
        application_payload(experience=""),
        application_payload(portfolio_url="not-a-url"),
    ],
)
def test_apply_rejects_invalid_or_missing_input(client, payload):
    set_session_user(client)

    with patch("app.get_connection") as mock_get_connection:
        response = client.post("/api/posts/3/apply", json=payload)

    assert response.status_code == 400
    mock_get_connection.assert_not_called()


def test_my_applications_requires_authentication(client):
    response = client.get("/api/my-applications")

    assert response.status_code == 401


def test_organizer_cannot_view_my_applications(client):
    set_session_user(client, role="organizer")

    with patch("app.get_connection") as mock_get_connection:
        response = client.get("/api/my-applications")

    assert response.status_code == 403
    mock_get_connection.assert_not_called()


def test_normal_user_can_view_only_their_own_applications(client):
    set_session_user(client, user_id=11)
    application = {
        "application_id": 7,
        "post_id": 3,
        "title": "Campus Film Audition",
        "opportunity_type": "audition",
        "category": "acting",
        "event_date": "2026-10-15",
        "venue": "College Auditorium",
        "status": "Pending",
        "applied_at": None,
        "updated_at": None,
        "password_hash": "must-not-be-returned",
    }
    connection, cursor = make_connection(fetchall_values=[application])

    with patch("app.get_connection", return_value=connection):
        response = client.get("/api/my-applications?applicant_id=999")

    assert response.status_code == 200
    returned_application = response.get_json()["applications"][0]
    assert returned_application["id"] == 7
    assert "password_hash" not in returned_application
    assert cursor.execute.call_args.args[1] == (11,)
    assert "password_hash" not in cursor.execute.call_args.args[0]


def test_my_applications_returns_an_empty_list(client):
    set_session_user(client)
    connection, _ = make_connection(fetchall_values=[])

    with patch("app.get_connection", return_value=connection):
        response = client.get("/api/my-applications")

    assert response.status_code == 200
    assert response.get_json() == {"applications": []}


def test_post_applications_requires_authentication(client):
    response = client.get("/api/posts/3/applications")

    assert response.status_code == 401


def test_normal_user_cannot_view_post_applications(client):
    set_session_user(client, role="user")

    with patch("app.get_connection") as mock_get_connection:
        response = client.get("/api/posts/3/applications")

    assert response.status_code == 403
    mock_get_connection.assert_not_called()


def test_organizer_can_view_applicants_for_their_own_post(client):
    set_session_user(client, user_id=8, role="organizer")
    applicant = {
        "application_id": 7,
        "applicant_id": 11,
        "applicant_name": "Test User",
        "applicant_email": "test@example.com",
        "experience": "Two years of college theatre experience.",
        "portfolio_url": "https://portfolio.example.test/test-user",
        "status": "Pending",
        "applied_at": None,
        "updated_at": None,
        "password_hash": "must-not-be-returned",
    }
    connection, cursor = make_connection(
        fetchone_values=[{"id": 3, "organizer_id": 8}],
        fetchall_values=[applicant],
    )

    with patch("app.get_connection", return_value=connection):
        response = client.get("/api/posts/3/applications")

    assert response.status_code == 200
    returned_application = response.get_json()["applications"][0]
    assert returned_application["applicant_email"] == "test@example.com"
    assert "password_hash" not in returned_application
    assert "password_hash" not in cursor.execute.call_args_list[1].args[0]


def test_organizer_cannot_view_another_organizers_applicants(client):
    set_session_user(client, user_id=8, role="organizer")
    connection, _ = make_connection(fetchone_values=[{"id": 3, "organizer_id": 9}])

    with patch("app.get_connection", return_value=connection):
        response = client.get("/api/posts/3/applications")

    assert response.status_code == 403


def test_post_applications_returns_404_for_a_missing_post(client):
    set_session_user(client, user_id=8, role="organizer")
    connection, _ = make_connection(fetchone_values=[None])

    with patch("app.get_connection", return_value=connection):
        response = client.get("/api/posts/999/applications")

    assert response.status_code == 404


def test_status_update_requires_authentication(client):
    response = client.put("/api/applications/7/status", json={"status": "Shortlisted"})

    assert response.status_code == 401


def test_normal_user_cannot_update_application_status(client):
    set_session_user(client, role="user")

    with patch("app.get_connection") as mock_get_connection:
        response = client.put("/api/applications/7/status", json={"status": "Shortlisted"})

    assert response.status_code == 403
    mock_get_connection.assert_not_called()


def test_organizer_can_update_their_own_post_application_status(client):
    set_session_user(client, user_id=8, role="organizer")
    connection, cursor = make_connection(fetchone_values=[application_record(organizer_id=8)])

    with patch("app.get_connection", return_value=connection):
        response = client.put(
            "/api/applications/7/status",
            json={"status": "Shortlisted", "organizer_id": 999},
        )

    assert response.status_code == 200
    assert response.get_json()["application"]["status"] == "Shortlisted"
    assert cursor.execute.call_args_list[1].args == (
        "UPDATE applications SET status = %s WHERE id = %s",
        ("Shortlisted", 7),
    )
    connection.commit.assert_called_once()


def test_organizer_cannot_update_another_organizers_application(client):
    set_session_user(client, user_id=8, role="organizer")
    connection, _ = make_connection(fetchone_values=[application_record(organizer_id=9)])

    with patch("app.get_connection", return_value=connection):
        response = client.put("/api/applications/7/status", json={"status": "Selected"})

    assert response.status_code == 403


def test_status_update_returns_404_for_a_missing_application(client):
    set_session_user(client, user_id=8, role="organizer")
    connection, _ = make_connection(fetchone_values=[None])

    with patch("app.get_connection", return_value=connection):
        response = client.put("/api/applications/999/status", json={"status": "Selected"})

    assert response.status_code == 404


def test_status_update_rejects_invalid_status(client):
    set_session_user(client, user_id=8, role="organizer")

    with patch("app.get_connection") as mock_get_connection:
        response = client.put("/api/applications/7/status", json={"status": "Approved"})

    assert response.status_code == 400
    mock_get_connection.assert_not_called()


@pytest.mark.parametrize("status", ["Pending", "Under Review", "Shortlisted", "Selected", "Rejected"])
def test_status_update_accepts_each_allowed_status(client, status):
    set_session_user(client, user_id=8, role="organizer")
    connection, _ = make_connection(fetchone_values=[application_record(organizer_id=8)])

    with patch("app.get_connection", return_value=connection):
        response = client.put("/api/applications/7/status", json={"status": status})

    assert response.status_code == 200
    assert response.get_json()["application"]["status"] == status
