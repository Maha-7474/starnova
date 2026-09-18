from app import create_app


def test_health_check_returns_ok():
    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
