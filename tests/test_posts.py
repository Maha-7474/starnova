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


def set_session_user(client, user_id=8, role="organizer"):
    """Set the same minimal identity that the login route stores."""
    with client.session_transaction() as saved_session:
        saved_session["user_id"] = user_id
        saved_session["role"] = role


def post_record(post_id=3, organizer_id=8):
    return {
        "id": post_id,
        "organizer_id": organizer_id,
        "title": "Campus Film Audition",
        "opportunity_type": "audition",
        "category": "acting",
        "event_date": "2026-10-15",
        "start_time": "10:00:00",
        "end_time": "13:00:00",
        "venue": "College Auditorium",
        "description": "Prepare a short monologue.",
        "image_path": None,
        "created_at": None,
        "updated_at": None,
    }


def post_payload(**overrides):
    payload = {
        "title": "Campus Film Audition",
        "opportunity_type": "audition",
        "category": "acting",
        "event_date": "2026-10-15",
        "start_time": "10:00",
        "end_time": "13:00",
        "venue": "College Auditorium",
        "description": "Prepare a short monologue.",
    }
    payload.update(overrides)
    return payload


def test_list_posts_returns_public_opportunities(client):
    connection, _ = make_connection(fetchall_values=[post_record()])

    with patch("app.get_connection", return_value=connection):
        response = client.get("/api/posts")

    assert response.status_code == 200
    assert response.get_json()["posts"][0]["title"] == "Campus Film Audition"
    assert "password_hash" not in response.get_json()["posts"][0]


def test_list_posts_filters_by_type(client):
    connection, cursor = make_connection()

    with patch("app.get_connection", return_value=connection):
        response = client.get("/api/posts?type=audition")

    assert response.status_code == 200
    assert "opportunity_type = %s" in cursor.execute.call_args.args[0]
    assert cursor.execute.call_args.args[1] == ("audition",)


def test_list_posts_filters_by_category(client):
    connection, cursor = make_connection()

    with patch("app.get_connection", return_value=connection):
        response = client.get("/api/posts?category=acting")

    assert response.status_code == 200
    assert "category = %s" in cursor.execute.call_args.args[0]
    assert cursor.execute.call_args.args[1] == ("acting",)


def test_list_posts_searches_text_fields(client):
    connection, cursor = make_connection()

    with patch("app.get_connection", return_value=connection):
        response = client.get("/api/posts?q=film")

    assert response.status_code == 200
    assert "title LIKE %s" in cursor.execute.call_args.args[0]
    assert cursor.execute.call_args.args[1] == ("%film%",) * 4


@pytest.mark.parametrize("query", ["type=concert", "category=painting"])
def test_list_posts_rejects_invalid_filter_values(client, query):
    with patch("app.get_connection") as mock_get_connection:
        response = client.get(f"/api/posts?{query}")

    assert response.status_code == 400
    mock_get_connection.assert_not_called()


def test_get_post_returns_an_existing_opportunity(client):
    connection, cursor = make_connection(fetchone_values=[post_record()])

    with patch("app.get_connection", return_value=connection):
        response = client.get("/api/posts/3")

    assert response.status_code == 200
    assert response.get_json()["post"]["id"] == 3
    assert cursor.execute.call_args.args[1] == (3,)


def test_get_post_returns_404_for_a_missing_opportunity(client):
    connection, _ = make_connection(fetchone_values=[None])

    with patch("app.get_connection", return_value=connection):
        response = client.get("/api/posts/999")

    assert response.status_code == 404
    assert response.get_json() == {"message": "Opportunity not found."}


def test_create_post_rejects_an_unauthenticated_request(client):
    with patch("app.get_connection") as mock_get_connection:
        response = client.post("/api/posts", json=post_payload())

    assert response.status_code == 401
    mock_get_connection.assert_not_called()


def test_create_post_rejects_a_normal_user(client):
    set_session_user(client, role="user")

    with patch("app.get_connection") as mock_get_connection:
        response = client.post("/api/posts", json=post_payload())

    assert response.status_code == 403
    mock_get_connection.assert_not_called()


def test_organizer_can_create_post_using_the_session_owner_id(client):
    set_session_user(client, user_id=8)
    connection, cursor = make_connection(lastrowid=25)
    payload = post_payload(organizer_id=999)

    with patch("app.get_connection", return_value=connection):
        response = client.post("/api/posts", json=payload)

    assert response.status_code == 201
    assert response.get_json()["post"]["organizer_id"] == 8
    insert_values = cursor.execute.call_args.args[1]
    assert insert_values[0] == 8
    assert 999 not in insert_values
    connection.commit.assert_called_once()


@pytest.mark.parametrize(
    "payload",
    [
        post_payload(title=""),
        post_payload(opportunity_type="concert"),
        post_payload(category="painting"),
        post_payload(event_date="15-10-2026"),
        post_payload(start_time="14:00", end_time="13:00"),
    ],
)
def test_create_post_rejects_invalid_input(client, payload):
    set_session_user(client)

    with patch("app.get_connection") as mock_get_connection:
        response = client.post("/api/posts", json=payload)

    assert response.status_code == 400
    mock_get_connection.assert_not_called()


def test_organizer_can_update_own_post(client):
    set_session_user(client, user_id=8)
    connection, cursor = make_connection(fetchone_values=[{"id": 3, "organizer_id": 8}])
    payload = post_payload(title="Updated Film Audition", organizer_id=999)

    with patch("app.get_connection", return_value=connection):
        response = client.put("/api/posts/3", json=payload)

    assert response.status_code == 200
    assert response.get_json()["post"]["title"] == "Updated Film Audition"
    update_values = cursor.execute.call_args_list[1].args[1]
    assert update_values[-1] == 3
    assert 999 not in update_values
    connection.commit.assert_called_once()


def test_organizer_cannot_update_another_organizers_post(client):
    set_session_user(client, user_id=8)
    connection, _ = make_connection(fetchone_values=[{"id": 3, "organizer_id": 9}])

    with patch("app.get_connection", return_value=connection):
        response = client.put("/api/posts/3", json=post_payload())

    assert response.status_code == 403


def test_normal_user_cannot_update_a_post(client):
    set_session_user(client, role="user")

    with patch("app.get_connection") as mock_get_connection:
        response = client.put("/api/posts/3", json=post_payload())

    assert response.status_code == 403
    mock_get_connection.assert_not_called()


def test_update_returns_404_for_a_missing_post(client):
    set_session_user(client)
    connection, _ = make_connection(fetchone_values=[None])

    with patch("app.get_connection", return_value=connection):
        response = client.put("/api/posts/999", json=post_payload())

    assert response.status_code == 404


def test_organizer_can_delete_own_post(client):
    set_session_user(client, user_id=8)
    connection, cursor = make_connection(fetchone_values=[{"id": 3, "organizer_id": 8}])

    with patch("app.get_connection", return_value=connection):
        response = client.delete("/api/posts/3")

    assert response.status_code == 200
    assert response.get_json() == {"message": "Opportunity deleted."}
    assert cursor.execute.call_args_list[1].args == ("DELETE FROM posts WHERE id = %s", (3,))
    connection.commit.assert_called_once()


def test_organizer_cannot_delete_another_organizers_post(client):
    set_session_user(client, user_id=8)
    connection, _ = make_connection(fetchone_values=[{"id": 3, "organizer_id": 9}])

    with patch("app.get_connection", return_value=connection):
        response = client.delete("/api/posts/3")

    assert response.status_code == 403


def test_normal_user_cannot_delete_a_post(client):
    set_session_user(client, role="user")

    with patch("app.get_connection") as mock_get_connection:
        response = client.delete("/api/posts/3")

    assert response.status_code == 403
    mock_get_connection.assert_not_called()


def test_delete_returns_404_for_a_missing_post(client):
    set_session_user(client)
    connection, _ = make_connection(fetchone_values=[None])

    with patch("app.get_connection", return_value=connection):
        response = client.delete("/api/posts/999")

    assert response.status_code == 404
