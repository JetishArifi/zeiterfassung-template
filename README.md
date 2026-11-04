# Zeiterfassung – Startprojekt

Lauffähiges Grundgerüst mit **Flask**, **SQLite**, **Pico.css** und **pytest**.
Alle Bibliotheken sind eingebunden; die Use Cases baut ihr selbst.

## Installation

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1              # Windows PowerShell
# source .venv/bin/activate             # macOS / Linux

pip install -r requirements.txt
flask --app app init-db                 # Datenbank anlegen (löscht alte Daten)
flask --app app run --debug
```

Hauptbenutzer Jetish nach `init-db`: Benutzername `jetish`, Passwort `Beis2015`.
Weitere Mitarbeitende können sich über den Link **Mitarbeiterkonto erstellen**
auf der Anmeldeseite mit Name, Benutzername und Passwort registrieren.
Nach der Anmeldung können sie **Projekt wählen und einstempeln**. Die Startseite
zeigt danach das Projekt und die live laufende Zeit; über **Ausstempeln** wird
die Stempelung beendet.
Jetish kann über **Mitarbeitende kontrollieren** die Stempelungen aller
Mitarbeitenden ansehen, filtern und korrigieren. Das Konto `chefin` hat ebenfalls
Kontrollrechte.
Einem bestehenden Konto kannst du Adminrechte ohne Datenverlust geben:
`flask --app app grant-admin jetish`.

Dann <http://127.0.0.1:5000> öffnen. Mit `--debug` lädt der Server bei jeder
Änderung am Code neu.

PowerShell meldet "Ausführung von Skripts deaktiviert"? Einmalig ausführen:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

## Tests

```bash
pytest
```

Bei jedem Push führt GitHub die Tests automatisch aus
(`.github/workflows/tests.yml`). Das Ergebnis steht beim Commit als grüner
Haken oder rotes Kreuz, Details im Reiter **Actions**.

## Aufbau

| Datei | Inhalt |
|---|---|
| `app.py` | Die Seiten (Routen) der App |
| `db.py` | Alle SQL-Befehle |
| `schema.sql` | Die Tabellen (`CREATE TABLE ...`) |
| `templates/` | HTML-Seiten; alle erweitern `base.html` |
| `static/` | Pico.css und eigenes CSS in `style.css` |
| `tests/` | Tests; `conftest.py` liefert `client` und eine frische Datenbank |

## So baut ihr einen Use Case

Am Beispiel "Liste anzeigen und neuen Eintrag erfassen":

**1. Tabelle** in `schema.sql`, dann `flask --app app init-db`:

```sql
DROP TABLE IF EXISTS beispiel;
CREATE TABLE beispiel (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
);
```

**2. SQL-Funktionen** in `db.py`:

```python
def beispiele():
    return verbindung().execute("SELECT * FROM beispiel ORDER BY name").fetchall()


def beispiel_anlegen(name: str):
    db = verbindung()
    db.execute("INSERT INTO beispiel (name) VALUES (?)", (name,))
    db.commit()
```

**3. Route** in `app.py` (Imports oben ergänzen: `flash, redirect, request, url_for`):

```python
@app.route("/beispiele", methods=["GET", "POST"])
def beispiele():
    if request.method == "POST":
        db.beispiel_anlegen(request.form["name"])
        flash("Gespeichert.", "ok")
        return redirect(url_for("beispiele"))
    return render_template("beispiele.html", beispiele=db.beispiele())
```

**4. Template** `templates/beispiele.html`:

```html
{% extends "base.html" %}
{% block titel %}Beispiele{% endblock %}
{% block inhalt %}
<h1>Beispiele</h1>
<ul>
  {% for b in beispiele %}<li>{{ b.name }}</li>{% endfor %}
</ul>
<form method="post">
  <input name="name" placeholder="Name" required>
  <button type="submit">Speichern</button>
</form>
{% endblock %}
```

Den Link im Menü in `base.html` ergänzen:
`<li><a href="{{ url_for('beispiele') }}">Beispiele</a></li>`

**5. Test** `tests/test_beispiele.py`:

```python
def test_beispiel_erfassen(client):
    client.post("/beispiele", data={"name": "Erstes"})
    assert "Erstes" in client.get("/beispiele").get_data(as_text=True)
```

## Regeln, die Ärger ersparen

- **SQL immer mit `?`** und Werten als Tupel, nie mit f-Strings
  zusammensetzen (sonst SQL-Injection).
- **Nach jedem POST weiterleiten** (`redirect`), sonst schickt "Neu laden"
  das Formular nochmals ab.
- **Nach Änderungen `commit()`**, sonst ist nichts gespeichert.
- **Passwörter nie im Klartext speichern:** `generate_password_hash` und
  `check_password_hash` aus `werkzeug.security` (wird mit Flask installiert).
- Eingeloggte Person merken: `session["mitarbeiter_id"] = ...` (Flask-Session).

## Zusammenarbeit mit Git

1. Vor dem Arbeiten: `git pull`
2. Pro Use Case einen Branch
3. Oft committen
4. Auf GitHub einen Pull Request öffnen; mergen, wenn die Tests grün sind
   und jemand aus dem Team den Code angeschaut hat.

Jede Person im Team schreibt zu ihrem Use Case mindestens einen Test.

## Dokumentation

- Flask: <https://flask.palletsprojects.com/en/stable/tutorial/>
- Jinja-Templates: <https://jinja.palletsprojects.com/en/stable/templates/>
- SQLite in Python: <https://docs.python.org/3/library/sqlite3.html>
- Pico.css: <https://picocss.com/docs>
- pytest: <https://docs.pytest.org/en/stable/getting-started.html>
