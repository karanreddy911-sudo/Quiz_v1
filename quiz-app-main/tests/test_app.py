import pytest

from app import app, load_subjects, load_users


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def logged_in(client):
    client.post("/login", data={"username": "student", "password": "student123"})
    return client


# ---------- Login ----------

def test_login_page(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Log in" in response.data


def test_home_redirects_to_login_when_logged_out(client):
    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


@pytest.mark.parametrize("path", ["/subjects", "/quiz/devops"])
def test_pages_require_login(client, path):
    response = client.get(path)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_wrong_password_is_rejected(client):
    response = client.post("/login", data={"username": "student", "password": "wrong"})
    assert b"Invalid username or password" in response.data
    assert client.get("/subjects").status_code == 302


def test_unknown_user_is_rejected(client):
    response = client.post("/login", data={"username": "nobody", "password": "student123"})
    assert b"Invalid username or password" in response.data


def test_login_success_redirects_to_subjects(client):
    response = client.post("/login", data={"username": "student", "password": "student123"})
    assert response.status_code == 302
    assert "/subjects" in response.headers["Location"]


def test_logout(logged_in):
    logged_in.get("/logout")
    assert logged_in.get("/subjects").status_code == 302


# ---------- Subjects & quiz ----------

def test_subjects_page_lists_all_subjects(logged_in):
    response = logged_in.get("/subjects")
    assert response.status_code == 200
    assert b"student" in response.data
    for subject in load_subjects():
        assert subject["name"].replace("&", "&amp;").encode() in response.data


def test_quiz_page_shows_subject_questions(logged_in):
    subject = load_subjects()[0]
    response = logged_in.get(f"/quiz/{subject['id']}")
    assert response.status_code == 200
    for q in subject["questions"]:
        assert f'name="q{q["id"]}"'.encode() in response.data


def test_unknown_subject_returns_404(logged_in):
    assert logged_in.get("/quiz/does-not-exist").status_code == 404


def test_all_correct_answers_give_full_score(logged_in):
    subject = load_subjects()[1]
    total = len(subject["questions"])
    form = {f"q{q['id']}": q["answer"] for q in subject["questions"]}
    response = logged_in.post(f"/quiz/{subject['id']}/submit", data=form)
    assert response.status_code == 200
    assert f"{total} / {total}".encode() in response.data
    assert b"100%" in response.data


def test_no_answers_give_zero_score(logged_in):
    subject = load_subjects()[0]
    total = len(subject["questions"])
    response = logged_in.post(f"/quiz/{subject['id']}/submit", data={})
    assert response.status_code == 200
    assert f"0 / {total}".encode() in response.data
    assert b"Not answered" in response.data


# ---------- Health & API ----------

def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_api_hides_answers(client):
    data = client.get("/api/subjects").get_json()
    assert len(data) == len(load_subjects())
    for subject in data:
        assert all("answer" not in q for q in subject["questions"])


# ---------- Data files ----------

def test_questions_file_is_valid():
    subjects = load_subjects()
    subject_ids = [s["id"] for s in subjects]
    assert len(subject_ids) == len(set(subject_ids)), "subject ids must be unique"
    for s in subjects:
        assert s["questions"], f"subject {s['id']} has no questions"
        ids = [q["id"] for q in s["questions"]]
        assert len(ids) == len(set(ids)), f"question ids must be unique in subject {s['id']}"
        for q in s["questions"]:
            assert q["answer"] in q["options"], f"answer missing from options: {s['id']} question {q['id']}"


def test_users_file_has_hashed_passwords():
    for username, password_hash in load_users().items():
        assert password_hash.startswith(("scrypt:", "pbkdf2:")), f"password for {username} is not hashed"
