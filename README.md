# Quiz App (DevOps Project)

A simple quiz web app used to demonstrate a full DevOps workflow with **Git, GitHub, Jenkins and Docker**.

**Features**

- **Login page**: username and password, with hashed passwords
- **Subjects**: DSA, DevOps, Linux, Java, Math (5 questions each)
- **Quiz per subject**: multiple-choice questions, a score, and a review showing the correct answers

**Demo accounts**

| Username  | Password     |
|-----------|--------------|
| `student` | `student123` |
| `admin`   | `admin123`   |

## How the pipeline works

```
 Developer ──git push──▶ GitHub ──(poll / webhook)──▶ Jenkins
                                                        │
                ┌───────────────────────────────────────┘
                ▼
   1. Checkout     pull the latest code from GitHub
   2. Test         run unit tests (pytest) inside Docker
   3. Build Image  docker build → quiz-app:<build number>
   4. Deploy       replace the running container (port 5000)
   5. Smoke Test   call /health to make sure the app is up
   6. Push (opt.)  push the image to Docker Hub
```

The page footer shows the **Jenkins build number**, so after every push you can see the new version is live.

## Tech stack

| Tool    | Used for                                   |
|---------|--------------------------------------------|
| Python / Flask | The quiz web application            |
| pytest  | Unit tests                                 |
| Git     | Version control                            |
| GitHub  | Hosting the code, team collaboration (PRs) |
| Docker  | Packaging and running the app              |
| Jenkins | CI/CD pipeline (`Jenkinsfile`)             |

## Project structure

```
├── app.py                 # Flask app (login, subjects, quiz, /health, /api/subjects)
├── data/
│   ├── questions.json     # Subjects and their questions - edit to add/change
│   └── users.json         # Login accounts (username → password hash)
├── templates/             # HTML pages (login, subjects, quiz, result)
├── static/style.css       # Styling
├── tests/test_app.py      # Unit tests
├── requirements.txt       # App dependencies
├── requirements-dev.txt   # Test dependencies
├── Dockerfile             # Multi-stage: base → test → production
├── docker-compose.yml     # Run the app locally with Docker
├── Jenkinsfile            # CI/CD pipeline definition
└── jenkins/               # Jenkins server (runs in Docker, with Docker CLI)
    ├── Dockerfile
    └── docker-compose.yml
```

## Prerequisites

- [Git](https://git-scm.com/downloads)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (running)
- Python 3.10+ (only needed to run without Docker)

## 1. Run the app

**With Docker (recommended):**

```bash
git clone <repo-url>
cd <repo-folder>
docker compose up --build
```

Open http://localhost:5000 and log in with `student` / `student123`. Stop it with `Ctrl+C` (or `docker compose down`).

**Without Docker:**

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
pytest            # run tests
python app.py     # open http://localhost:5000
```

## 2. Set up Jenkins (runs in Docker)

1. Start Jenkins from the project folder:

   ```bash
   docker compose -f jenkins/docker-compose.yml up -d --build
   ```

2. Get the initial admin password:

   ```bash
   docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
   ```

3. Open http://localhost:8080, paste the password, choose **Install suggested plugins**, and create an admin user.

4. Create the pipeline job:
   - **New Item** → name `quiz-app` → **Pipeline** → OK
   - Under **Pipeline**, set **Definition** to `Pipeline script from SCM`
   - **SCM**: `Git`, **Repository URL**: the GitHub repo URL (e.g. `https://github.com/<owner>/<repo>.git`)
   - **Branch Specifier**: `*/main`
   - **Script Path**: `Jenkinsfile`
   - Save

   If the repo is **private**, add credentials: **Add → Jenkins**, kind *Username with password*, username = GitHub username, password = a GitHub [personal access token](https://github.com/settings/tokens) with `repo` scope.

5. Click **Build Now**. When it is green, open http://localhost:5000. The footer shows the build number.

### Automatic builds on every push

The `Jenkinsfile` polls GitHub every ~2 minutes (`pollSCM`). This starts after the **first** manual build. After that, every `git push` to `main` triggers a new build automatically.

Optional, for instant builds: use a GitHub webhook. Jenkins on `localhost` can't be reached from GitHub, so expose it with a tool like [ngrok](https://ngrok.com/) (`ngrok http 8080`), then in GitHub go to **Settings → Webhooks → Add webhook**, use `https://<ngrok-url>/github-webhook/` with content type `application/json`, and in the Jenkins job tick **GitHub hook trigger for GITScm polling**.

### Optional: push the image to Docker Hub

1. In Jenkins: **Manage Jenkins → Credentials → (global) → Add Credentials**, kind *Username with password*, ID `dockerhub-creds`, using your Docker Hub username and an [access token](https://hub.docker.com/settings/security).
2. Run **Build with Parameters** and tick `PUSH_TO_DOCKERHUB`.

## 3. Team workflow with Git & GitHub

```bash
git checkout main
git pull                                  # get latest code
git checkout -b feature/add-questions     # make a branch for your work
# ... make changes, e.g. edit data/questions.json ...
pytest                                    # make sure tests pass
git add .
git commit -m "Add 5 new Docker questions"
git push -u origin feature/add-questions
```

Then open a **Pull Request** on GitHub, have a teammate review it, and **merge into `main`**. Jenkins picks up the change and deploys the new version.

**Easy first task for each team member:** add a question or a whole new subject (see below).

## 4. Customising

**Add a question or subject:** edit `data/questions.json`. Each subject has an `id` (used in the URL, e.g. `/quiz/docker`), a `name`, a `description` and a list of `questions`. Question `id`s must be unique within a subject, and the `answer` must exactly match one of the `options`. The tests check both.

**Add a login account:** generate a password hash:

```bash
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('your-password'))"
```

Then add `"username": "<the hash>"` to `data/users.json`. Never put plain-text passwords in the file.

**Secret key:** login sessions are signed with `SECRET_KEY`. The app has a default for demos. For a real deployment, set your own, e.g. add `-e SECRET_KEY=<random string>` to the `docker run` command in the `Jenkinsfile`.

## Useful commands

| Command | What it does |
|---------|--------------|
| `docker ps` | List running containers |
| `docker logs quiz-app` | See app logs (container deployed by Jenkins) |
| `docker images quiz-app` | List built image versions |
| `docker compose -f jenkins/docker-compose.yml down` | Stop Jenkins (data is kept in a volume) |
| `curl http://localhost:5000/health` | Check the app is healthy |

## Troubleshooting

- **`port is already allocated`**: something else uses port 5000. Stop the other container (`docker compose down` if you ran it locally, since the Jenkins deploy also uses 5000) or change `APP_PORT` in the `Jenkinsfile`.
- **Jenkins: `docker: not found` or `permission denied on docker.sock`**: make sure Jenkins was started with `jenkins/docker-compose.yml` (it installs the Docker CLI and mounts the Docker socket) and that Docker Desktop is running.
- **Build fails at the Test stage**: a unit test failed. Read the pytest output in the Jenkins console log.
