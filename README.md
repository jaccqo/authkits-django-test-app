# Authkits Django Example App

This repository is the public reference and integration sandbox for **Authkits Django**.

It intentionally behaves like a normal customer-owned Django application rather than part of the Authkits package itself.

## What belongs here

- minimal Authkits installation examples
- signup, login, verification, recovery, and MFA examples
- host-project settings and URL configuration
- template and styling overrides
- custom user-model examples
- django-allauth examples
- API/headless examples when those integrations ship
- regression checks for the real wheel-install experience

The paid Authkits package source does **not** live in this repository.

## Local setup

Create a virtual environment, install Django, then install the Authkits wheel you are testing.

```bash
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install django
python -m pip install /path/to/authkits_django-<version>-py3-none-any.whl
python manage.py migrate
python manage.py runserver
```

Then open `http://localhost:8000/`.

## Safety

Do not commit real credentials, production secrets, databases, license keys, or wheel files to this repository.
