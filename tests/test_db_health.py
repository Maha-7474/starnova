from unittest.mock import MagicMock, patch

from mysql.connector import Error

from app import create_app


def make_test_client():
    """Return a Flask test client without starting a server."""
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


@patch("app.get_connection")
def test_db_health_returns_ok_when_database_is_reachable(mock_get_connection):
    mock_cursor = MagicMock()
    mock_connection = MagicMock()
    mock_connection.cursor.return_value = mock_cursor
    mock_connection.is_connected.return_value = True
    mock_get_connection.return_value = mock_connection

    response = make_test_client().get("/api/db-health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "database": "reachable"}
    mock_cursor.execute.assert_called_once_with("SELECT 1")
    mock_cursor.close.assert_called_once()
    mock_connection.close.assert_called_once()


@patch("app.get_connection", side_effect=Error("Connection failed"))
def test_db_health_returns_safe_error_when_database_is_unreachable(mock_get_connection):
    response = make_test_client().get("/api/db-health")

    assert response.status_code == 503
    assert response.get_json() == {
        "status": "error",
        "message": "Database unavailable",
    }
    mock_get_connection.assert_called_once()
