def test_startseite_wird_angezeigt(app, client):
    app.test_cli_runner().invoke(args=["init-db"])
    client.post(
        "/login",
        data={"benutzername": "jetish", "passwort": "Beis2015"},
    )

    antwort = client.get("/")
    assert antwort.status_code == 200
    assert "Projekt wählen und einstempeln" in antwort.get_data(as_text=True)
