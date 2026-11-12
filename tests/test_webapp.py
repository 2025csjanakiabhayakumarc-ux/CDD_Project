"""Tests for the DataGuard web app (Member 5)."""
import importlib
import io
import pathlib
import sys

import pytest

# Make "src" importable no matter where pytest is started from.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

create_app = importlib.import_module("src.webapp.app").create_app
service = importlib.import_module("src.webapp.service")

CLEAN = b"id,name,attendance\n1,Asha,90\n2,Ravi,85\n"
BAD = b"id,name,attendance\n1,Asha,90\n2,,85\n1,Asha,90\n"


@pytest.fixture
def client(monkeypatch):
    # Use the built-in demo checker so these tests do not depend on teammates' code.
    monkeypatch.setenv("DATAGUARD_UI_DEMO", "1")
    app = create_app()
    app.testing = True
    return app.test_client()


def upload(client, content, name="data.csv", **extra):
    data = {"file": (io.BytesIO(content), name), **extra}
    return client.post("/validate", data=data, content_type="multipart/form-data")


def test_home_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Check my file" in response.data


def test_health_route(client):
    assert client.get("/health").get_json() == {"status": "ok"}


def test_no_file_gives_friendly_error(client):
    response = client.post("/validate", data={}, content_type="multipart/form-data")
    assert response.status_code == 400
    assert b"choose a CSV file" in response.data


def test_wrong_file_type_is_rejected(client):
    response = upload(client, b"hello", name="notes.pdf")
    assert response.status_code == 400
    assert b"not supported" in response.data


def test_empty_file_shows_error_page(client):
    response = upload(client, b"   \n")
    assert response.status_code == 422
    assert b"could not read" in response.data


def test_clean_file_shows_all_clear(client):
    response = upload(client, CLEAN)
    assert response.status_code == 200
    assert b"All clear" in response.data
    assert b'data-total="0"' in response.data


def test_bad_file_lists_problems_with_hints(client):
    response = upload(client, BAD)
    assert response.status_code == 200
    assert b"missing_values" in response.data
    assert b"duplicates" in response.data
    assert b"How to fix it" in response.data


def test_required_columns_are_checked(client):
    response = upload(client, CLEAN, required="id, email")
    assert b"required_columns" in response.data
    assert b"email" in response.data


def test_file_contents_are_escaped(client):
    response = upload(client, b"id,<script>alert(1)</script>\n1,\n")
    assert b"<script>alert(1)</script>" not in response.data


def test_score_drops_when_problems_exist(monkeypatch):
    monkeypatch.setenv("DATAGUARD_UI_DEMO", "1")
    clean = service.analyze_upload("a.csv", CLEAN)
    bad = service.analyze_upload("b.csv", BAD)
    assert clean.score == 100
    assert bad.score < clean.score


def test_real_engine_smoke(monkeypatch):
    """Runs only once the team's src/loader.py exists. It must not crash on a normal file."""
    pytest.importorskip("src.loader")
    monkeypatch.delenv("DATAGUARD_UI_DEMO", raising=False)
    report = service.analyze_upload("good.csv", CLEAN)
    assert report.error == ""
    assert report.engine == "dataguard"


@pytest.fixture
def real_engine(monkeypatch, tmp_path):
    """Use the team's real code with a small rules file that this test controls."""
    pytest.importorskip("src.loader")
    pytest.importorskip("yaml")
    monkeypatch.delenv("DATAGUARD_UI_DEMO", raising=False)
    rules = tmp_path / "rules.yaml"
    rules.write_text("missing_values:\n  columns:\n    - name\n    - age\n", encoding="utf-8")
    monkeypatch.setenv("DATAGUARD_RULES", str(rules))
    return rules


def test_real_engine_uses_rules_yaml_settings(real_engine):
    report = service.analyze_upload("t.csv", b"name,age\nBob,\n,25\n")
    found = [f for f in report.findings if f.rule == "missing_values"]
    assert len(found) == 2
    assert sorted(f.row for f in found) == ["2", "3"]  # spreadsheet rows, not counted from 0
    assert {f.column for f in found} == {"name", "age"}


def test_real_engine_says_when_a_rule_has_no_settings(real_engine):
    report = service.analyze_upload("t.csv", b"name,age\nBob,1\n")
    assert any("required_columns" in note for note in report.notes)
    assert "required_columns" not in report.rules_run


def test_real_engine_full_rules_on_develop(monkeypatch):
    """With the team's real rules.yaml, every rule shows up and bad data is caught."""
    pytest.importorskip("src.engine")
    pytest.importorskip("yaml")
    monkeypatch.delenv("DATAGUARD_UI_DEMO", raising=False)
    monkeypatch.delenv("DATAGUARD_RULES", raising=False)
    csv = (
        b"name,student_id,attendance,email,dob\n"
        b"Asha,1,150,not-an-email,2004-13-45\n"
        b",2,80,b@x.com,2004-01-01\n"
    )
    report = service.analyze_upload("t.csv", csv)
    assert report.engine == "dataguard"
    assert {"missing_values", "range_and_format"} <= {f.rule for f in report.findings}
    assert all(f.row == "" or int(f.row) >= 2 for f in report.findings)  # spreadsheet rows
    assert all(f.hint for f in report.findings)


def test_a_missing_column_does_not_crash_the_report(monkeypatch):
    """The team's rules.yaml names student_id for duplicates; a file without it must still get a report."""
    pytest.importorskip("src.engine")
    monkeypatch.delenv("DATAGUARD_UI_DEMO", raising=False)
    monkeypatch.delenv("DATAGUARD_RULES", raising=False)
    report = service.analyze_upload("t.csv", b"name,age\nAnu,20\nAnu,20\n")
    assert report.error == ""
    assert any(f.rule == "required_columns" for f in report.findings)
