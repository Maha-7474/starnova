\# StarNova — Codex Project Instructions



\## 1. Project Overview



StarNova is a full-stack web platform for discovering and managing

auditions and competitions.



There are two main user roles:



\- `user` — participant/applicant

\- `organizer` — creates and manages opportunities and reviews applications



The project is being developed as a portfolio/interview project for a

DeltaX Associate Product Engineer / Full Stack Developer role.



The project should remain practical, understandable, and interview-defensible.



Do not add unnecessary complexity just to increase the technology list.



\---



\# 2. Technology Stack



\## Frontend



\- HTML

\- CSS

\- Vanilla JavaScript



Do not migrate to React, Vue, Angular, or another frontend framework unless

explicitly requested.



\## Backend



\- Python

\- Flask

\- REST APIs



\## Database



\- MySQL 8

\- MySQL Workbench

\- mysql-connector-python



\## Testing



\- pytest



\## Environment Configuration



\- python-dotenv

\- `.env` for local secrets

\- `.env.example` for placeholders



\## Planned Infrastructure



\- Docker

\- Docker Compose

\- GitHub Actions CI/CD



\---



\# 3. Architecture



The intended architecture is:



Browser

&#x20;   ↓

HTML / CSS / Vanilla JavaScript

&#x20;   ↓

Flask REST API

&#x20;   ↓

Authentication / Authorization

&#x20;   ↓

MySQL

