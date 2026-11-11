# DataGuard
[![DataGuard CI](https://github.com/2025csjanakiabhayakumarc-ux/CDD_Project/actions/workflows/ci.yml/badge.svg)](https://github.com/2025csjanakiabhayakumarc-ux/CDD_Project/actions/workflows/ci.yml)
A CSV data-validation engine built for **1BCS303 — Collaborative Development and DevOps** (Mini Project, Lab 14).

## Team

| # | Role | CDD Focus |
|---|------|-----------|
| 1 | Git & Collaboration | Gitflow, branch protection, issue board |
| 2 | CI/CD Engineer | GitHub Actions, test pipeline |
| 3 | Container & IaC Engineer | Dockerfile, Docker Compose |
| 4 | UX Researcher | Design Thinking, range/format rules |
| 5 | UI/Interaction Designer | Flask app, HTML report |

## Branch strategy

- `main` — protected; merge only via reviewed PR from `develop`
- `develop` — integration branch; all feature PRs target here
- `feature/<member>/<short-desc>` — one branch per task

## Running locally

```bash
pip install -r requirements.txt
python -m src.cli sample_data/input.csv
```
