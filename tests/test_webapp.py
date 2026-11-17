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
    assert b'href="/check"' in response.data  # the landing page leads to the upload page


def test_upload_page_loads(client):
    response = client.get("/check")
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
    assert b"File could not be read" in response.data


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
    assert "required_columns" in report.skipped  # greyed out on the page, not a warning banner
    assert not any("required_columns" in note for note in report.notes)
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


def test_cleaned_csv_keeps_whole_numbers_as_integers():
    """A blank salary makes pandas read the column as float; the download must not add '.0'."""
    pytest.importorskip("src.autofix")
    data = b"emp_id,salary\nE1,55000\nE2,\n"
    cleaned, _, _log = service.get_cleaned_csv(data)
    lines = cleaned.decode("utf-8").splitlines()
    assert lines[0] == "emp_id,salary"
    assert lines[1] == "E1,55000"


def test_employees_clean_sample_scores_100_with_employees_template(monkeypatch):
    """Demo file: samples/employees_clean.csv must pass every rule in the employees template."""
    pytest.importorskip("src.engine")
    pytest.importorskip("yaml")
    monkeypatch.delenv("DATAGUARD_UI_DEMO", raising=False)
    root = pathlib.Path(__file__).resolve().parents[1]
    data = (root / "samples" / "employees_clean.csv").read_bytes()
    report = service.analyze_upload(
        "employees_clean.csv", data, config_path=str(root / "templates_rules" / "employees.yaml")
    )
    assert report.engine == "dataguard"
    assert "india_formats" in report.rules_run  # the employees template is really in use
    assert report.findings == []
    assert report.score == 100


def test_upload_page_lists_rule_templates_without_server_paths(client):
    response = client.get("/check")
    assert b'value="employees"' in response.data
    assert b'value="auto"' in response.data
    assert b"templates_rules" not in response.data  # file paths stay on the server


def test_employees_template_runs_its_own_rules(monkeypatch):
    """The employees template must run its own rules (incl. india_formats) when picked."""
    pytest.importorskip("src.engine")
    monkeypatch.delenv("DATAGUARD_UI_DEMO", raising=False)
    app = create_app()
    root = pathlib.Path(__file__).resolve().parents[1]
    data = (root / "samples" / "employees.csv").read_bytes()
    response = app.test_client().post(
        "/validate", data={"file": (io.BytesIO(data), "employees.csv"), "template": "employees"},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    assert b"5876543215" in response.data  # the India phone check ran
    assert b"Validation Summary" in response.data


def test_unreadable_file_message_hides_server_paths(monkeypatch):
    pytest.importorskip("src.engine")
    monkeypatch.delenv("DATAGUARD_UI_DEMO", raising=False)
    report = service.analyze_upload("mine.csv", b"\x00\x01\x02 not a csv")
    assert report.error
    assert "mine.csv" in report.error
    assert "dataguard_" not in report.error and "Temp" not in report.error


def test_grid_marks_each_problem_on_its_own_cell(monkeypatch):
    """The data X-ray grid puts each finding on the cell it is about, in spreadsheet rows."""
    pytest.importorskip("src.engine")
    monkeypatch.delenv("DATAGUARD_UI_DEMO", raising=False)
    root = pathlib.Path(__file__).resolve().parents[1]
    report = service.analyze_upload(
        "employees.csv", (root / "samples" / "employees.csv").read_bytes(),
        config_path=str(root / "templates_rules" / "employees.yaml"),
    )
    grid = report.grid
    marked = {
        (row["num"], report.columns[i]): cell["sev"]
        for row in grid["rows"] for i, cell in enumerate(row["cells"]) if cell.get("sev")
    }
    assert marked == {("4", "email"): "error", ("5", "name"): "error",
                      ("6", "join_date"): "error", ("7", "phone"): "error"}
    duplicate = next(row for row in grid["rows"] if row["num"] == "13")
    assert duplicate["sev"] == "warning" and duplicate["removed"]  # auto-fix drops it
    assert [f.row for f in report.findings] == sorted((f.row for f in report.findings), key=int)
    assert "%Y" not in " ".join(f.hint for f in report.findings)  # dates shown as YYYY-MM-DD


def test_sample_links_open_a_report(monkeypatch):
    pytest.importorskip("src.engine")
    monkeypatch.delenv("DATAGUARD_UI_DEMO", raising=False)
    client = create_app().test_client()
    messy = client.get("/try/employees")
    assert messy.status_code == 200 and b"5876543215" in messy.data
    clean = client.get("/try/employees_clean")
    assert clean.status_code == 200 and b'data-total="0"' in clean.data
    assert client.get("/try/not-a-sample").status_code == 404


def test_download_works_for_a_file_too_big_for_a_cookie(client, tmp_path, monkeypatch):
    """The upload used to live in the session cookie; browsers drop cookies over ~4 KB."""
    pytest.importorskip("src.autofix")
    monkeypatch.setattr(importlib.import_module("src.webapp.app"), "UPLOAD_DIR", tmp_path)
    rows = b"".join(b"%d,Person %d,%d\n" % (i, i, 50 + i % 50) for i in range(2000))
    big = b"id,name,attendance\n" + rows
    assert len(big) > 20_000
    assert upload(client, big).status_code == 200
    cookie = client.get_cookie("session")
    assert cookie is not None and len(cookie.value) < 1000  # only an id, not the file
    response = client.get("/download-cleaned")
    assert response.status_code == 200
    assert response.data.startswith(b"id,name,attendance")
    assert client.get("/download-changes").status_code == 200


def test_download_refuses_a_made_up_upload_id(client):
    with client.session_transaction() as sess:
        sess["upload_id"] = "../../etc/passwd"
    assert client.get("/download-cleaned").status_code == 400


def test_upload_limit_is_shown_on_the_page(client):
    limit = importlib.import_module("src.webapp.app").MAX_UPLOAD_MB
    assert f"Up to {limit} MB".encode() in client.get("/check").data


def test_upload_page_offers_three_ways_to_pick_rules(client):
    page = client.get("/check").get_data(as_text=True)
    for mode in ("auto", "set", "ai"):
        assert f'name="rule_mode" value="{mode}"' in page
    assert 'value="auto" checked' in page  # choosing for you is the default


def test_ai_mode_falls_back_to_choosing_rules_from_the_columns(client):
    response = upload(client, b"name,email\nAsha,asha@example.com\n", rule_mode="ai", template="employees")
    assert response.status_code == 200
    assert "Let DataGuard choose" in response.get_data(as_text=True)


def test_rule_set_mode_uses_the_picked_template(client):
    response = upload(client, b"name,email\nAsha,asha@example.com\n", rule_mode="set", template="employees")
    assert "Employees" in response.get_data(as_text=True)


def test_checks_that_cannot_run_are_one_quiet_line_not_banners():
    from src.webapp.app import create_app
    client = create_app().test_client()  # the real engine, as on a laptop
    sample = pathlib.Path(__file__).resolve().parent.parent / "samples" / "event_registrations.csv"
    page = upload(client, sample.read_bytes(), name="event_registrations.csv",
                  rule_mode="set", template="default").get_data(as_text=True)
    assert "banner-warning" not in page
    assert "Duplicate rows didn&#39;t run" in page or "Duplicate rows didn't run" in page
    assert 'marked "Not run" have no settings' in page or "marked &#34;Not run&#34; have no settings" in page


def test_downloads_apply_the_email_and_date_fixes_the_rules_name(client, tmp_path, monkeypatch):
    """Auto-fix used to run with no settings, so emails and dates were never fixed."""
    pytest.importorskip("src.autofix")
    monkeypatch.delenv("DATAGUARD_UI_DEMO", raising=False)
    monkeypatch.setattr(importlib.import_module("src.webapp.app"), "UPLOAD_DIR", tmp_path)
    data = (b"emp_id,name,email,phone,join_date,salary\n"
            b"E1,Priya Sharma,Priya@Company.COM,9876543210,15/01/2022,55000\n"
            b"E2,Rahul Verma,rahul@company.com,9876543211,2022-03-20,\n"
            b"E3,Anita Desai,anita@company.com,9876543212,2022-06-01,59000\n")
    page = upload(client, data, template="employees")
    assert page.status_code == 200
    assert b"priya@company.com" in page.data  # shown in "What auto-fix changes"
    cleaned = client.get("/download-cleaned").data.decode()
    assert "E1,Priya Sharma,priya@company.com,9876543210,2022-01-15,55000" in cleaned
    assert ".0" not in cleaned
    changes = client.get("/download-changes").data.decode()
    assert "lowercase" in changes and "normalize date" in changes
