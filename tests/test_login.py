from datetime import datetime, timedelta

import db


def test_jetish_kann_sich_anmelden(app, client):
    app.test_cli_runner().invoke(args=["init-db"])

    antwort = client.post(
        "/login",
        data={"benutzername": "jetish", "passwort": "Beis2015"},
        follow_redirects=True,
    )

    assert antwort.status_code == 200
    assert "Projekt wählen und einstempeln" in antwort.get_data(as_text=True)


def test_mitarbeiter_kann_sich_mit_namen_registrieren(app, client):
    app.test_cli_runner().invoke(args=["init-db"])

    antwort = client.post(
        "/registrieren",
        data={"name": "Ada Beispiel", "benutzername": "ada", "passwort": "geheim"},
        follow_redirects=True,
    )

    assert antwort.status_code == 200
    assert "Konto erstellt" in antwort.get_data(as_text=True)
    with app.app_context():
        assert db.anmelden("ada", "geheim")["name"] == "Ada Beispiel"


def test_registrierung_verweigert_doppelten_benutzernamen(app, client):
    app.test_cli_runner().invoke(args=["init-db"])
    client.post(
        "/registrieren",
        data={"name": "Erste Person", "benutzername": "ada", "passwort": "geheim"},
    )

    antwort = client.post(
        "/registrieren",
        data={"name": "Zweite Person", "benutzername": "ada", "passwort": "anders"},
    )

    assert "Dieser Benutzername ist bereits vergeben." in antwort.get_data(as_text=True)


def test_chefin_kann_mitarbeitende_ansehen_und_kontrollieren(app, client):
    app.test_cli_runner().invoke(args=["init-db"])
    client.post(
        "/login",
        data={"benutzername": "chefin", "passwort": "chefin123"},
    )

    startseite = client.get("/")
    kontrolle = client.get("/korrektur")

    assert startseite.status_code == 200
    assert "Mitarbeitende kontrollieren" in startseite.get_data(as_text=True)
    assert kontrolle.status_code == 200
    assert "Jetish" in kontrolle.get_data(as_text=True)
    assert "Joel" in kontrolle.get_data(as_text=True)


def test_jetish_kann_mitarbeitende_ansehen_und_kontrollieren(app, client):
    app.test_cli_runner().invoke(args=["init-db"])
    client.post(
        "/login",
        data={"benutzername": "jetish", "passwort": "Beis2015"},
    )

    startseite = client.get("/")
    kontrolle = client.get("/korrektur")

    assert startseite.status_code == 200
    assert "Mitarbeitende kontrollieren" in startseite.get_data(as_text=True)
    assert kontrolle.status_code == 200
    assert "Joel" in kontrolle.get_data(as_text=True)


def test_adminrechte_koennen_ueber_cli_vergeben_werden(app):
    app.test_cli_runner().invoke(args=["init-db"])
    with app.app_context():
        db.verbindung().execute(
            "UPDATE mitarbeiter SET ist_chefin = 0 WHERE benutzername = ?",
            ("jetish",),
        )
        db.verbindung().commit()

    ergebnis = app.test_cli_runner().invoke(args=["grant-admin", "jetish"])

    assert ergebnis.exit_code == 0
    with app.app_context():
        assert db.anmelden("jetish", "Beis2015")["ist_chefin"] == 1


def test_jetish_kann_stempelzeit_eines_mitarbeiters_aendern(app, client):
    app.test_cli_runner().invoke(args=["init-db"])
    with app.app_context():
        db.projekt_erfassen("P1", "Beispielprojekt")
        joel = db.verbindung().execute(
            "SELECT id FROM mitarbeiter WHERE benutzername = ?", ("joel",)
        ).fetchone()
        db.einstempeln(joel["id"], "P1")
        stempelung = db.verbindung().execute(
            "SELECT id FROM stempelung WHERE mitarbeiter_id = ?", (joel["id"],)
        ).fetchone()

    client.post(
        "/login",
        data={"benutzername": "jetish", "passwort": "Beis2015"},
    )
    formular = client.get(f"/korrektur/{stempelung['id']}")
    assert formular.status_code == 200
    assert "Stempelung korrigieren" in formular.get_data(as_text=True)

    antwort = client.post(
        f"/korrektur/{stempelung['id']}",
        data={"beginn": "2026-11-04T08:00", "ende": "2026-11-04T09:00"},
    )

    assert antwort.status_code == 302
    with app.app_context():
        geaendert = db.verbindung().execute(
            "SELECT beginn, ende FROM stempelung WHERE id = ?", (stempelung["id"],)
        ).fetchone()
        assert geaendert["beginn"] == "2026-11-04T08:00:00"
        assert geaendert["ende"] == "2026-11-04T09:00:00"


def test_mitarbeiter_kann_mitarbeiterkontrolle_nicht_oeffnen(app, client):
    app.test_cli_runner().invoke(args=["init-db"])
    client.post(
        "/login",
        data={"benutzername": "joel", "passwort": "joel123"},
    )

    antwort = client.get("/korrektur")

    assert antwort.status_code == 302
    assert antwort.headers["Location"].endswith("/")


def test_mitarbeiter_kann_einstempeln_laufzeit_sehen_und_ausstempeln(app, client):
    app.test_cli_runner().invoke(args=["init-db"])
    with app.app_context():
        db.projekt_erfassen("P1", "Beispielprojekt")
    client.post(
        "/login",
        data={"benutzername": "joel", "passwort": "joel123"},
    )

    start = client.post("/stempeln", data={"projekt": "P1"})
    laufend = client.get("/")

    assert start.status_code == 302
    assert "Du bist eingestempelt" in laufend.get_data(as_text=True)
    assert "Beispielprojekt" in laufend.get_data(as_text=True)
    assert 'id="laufzeit"' in laufend.get_data(as_text=True)

    ende = client.post("/ausstempeln")

    assert ende.status_code == 302
    with app.app_context():
        eintrag = db.verbindung().execute(
            "SELECT ende FROM stempelung WHERE mitarbeiter_id = "
            "(SELECT id FROM mitarbeiter WHERE benutzername = ?)",
            ("joel",),
        ).fetchone()
        assert eintrag["ende"] is not None


def test_projektverwaltung_zeigt_gespeicherte_projektnummer(app, client):
    app.test_cli_runner().invoke(args=["init-db"])
    client.post(
        "/login",
        data={"benutzername": "jetish", "passwort": "Beis2015"},
    )
    client.post(
        "/projekt",
        data={"projektnummer": "P2", "name": "Neues Projekt"},
    )

    antwort = client.get("/projekt")

    assert "P2. Neues Projekt" in antwort.get_data(as_text=True)


def test_mitarbeiter_arbeitet_bis_jetish_laufende_zeit_beendet(app):
    app.test_cli_runner().invoke(args=["init-db"])
    mitarbeiter_app = app.test_client()
    hauptbenutzer_app = app.test_client()

    hauptbenutzer_app.post(
        "/login",
        data={"benutzername": "jetish", "passwort": "Beis2015"},
    )
    hauptbenutzer_app.post(
        "/projekt",
        data={"projektnummer": "P3", "name": "Testprojekt"},
    )
    mitarbeiter_app.post(
        "/login",
        data={"benutzername": "joel", "passwort": "joel123"},
    )
    einstempeln = mitarbeiter_app.post("/stempeln", data={"projekt": "P3"})

    assert einstempeln.status_code == 302
    laufende_seite = mitarbeiter_app.get("/")
    assert "Du bist eingestempelt" in laufende_seite.get_data(as_text=True)
    assert "Testprojekt" in laufende_seite.get_data(as_text=True)
    assert 'id="laufzeit"' in laufende_seite.get_data(as_text=True)

    with app.app_context():
        stempelung = db.verbindung().execute(
            """SELECT s.id, s.beginn, m.name AS mitarbeiter
               FROM stempelung s
               JOIN mitarbeiter m ON m.id = s.mitarbeiter_id
               WHERE m.benutzername = ? AND s.ende IS NULL""",
            ("joel",),
        ).fetchone()
        assert stempelung is not None
        assert stempelung["mitarbeiter"] == "Joel"
        beginn = (datetime.now() - timedelta(minutes=5)).isoformat(timespec="seconds")
        db.verbindung().execute(
            "UPDATE stempelung SET beginn = ? WHERE id = ?",
            (beginn, stempelung["id"]),
        )
        db.verbindung().commit()

    admin_liste = hauptbenutzer_app.get("/korrektur")
    assert "Joel" in admin_liste.get_data(as_text=True)
    ende = datetime.now().isoformat(timespec="seconds")
    beenden = hauptbenutzer_app.post(
        f"/korrektur/{stempelung['id']}",
        data={"beginn": beginn[:16], "ende": ende[:16]},
    )

    assert beenden.status_code == 302
    with app.app_context():
        gespeicherte_stempelung = db.verbindung().execute(
            "SELECT ende FROM stempelung WHERE id = ?", (stempelung["id"],)
        ).fetchone()
        assert gespeicherte_stempelung["ende"] is not None

    beendete_seite = mitarbeiter_app.get("/")
    assert "Du bist momentan nicht eingestempelt." in beendete_seite.get_data(as_text=True)
    assert 'id="laufzeit"' not in beendete_seite.get_data(as_text=True)
