# Product Operations ERP

A Django MVP for Sales Order fulfillment tracking across four inventory trackers:

- A — Finish Good
- B — Not Finish
- C — In Process
- D — Raw Material

`repeat_no` is the business key that links orders, inventory detail, shortage data, and remarks. Order allocation values are taken from the Sales Order snapshot in the workbook. Coil rows provide traceability and are not added to the order-level allocation totals.

## Requirements

- Python 3.11 or newer
- Packages listed in `requirements.txt`
- The provided `Data/Training Web.xlsx` workbook for the initial import

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py import_training_data
python manage.py runserver
```

Open `http://127.0.0.1:8000/`. Django Admin is at `http://127.0.0.1:8000/admin/`.

To import a different workbook, pass its path:

```bash
python manage.py import_training_data "/path/to/workbook.xlsx"
```

The importer replaces the current imported snapshot for the seven supported source sheets in one database transaction. Make a database backup before importing into a database that contains operational edits. The workbook data is synthetic and intended for training/demo use.

## Railway deployment

The project includes a Dockerfile for Railway. It collects static assets during the image build, applies Django migrations when the web service starts, then serves the app with Gunicorn on Railway's `PORT`.

1. Push this project to a GitHub repository and create a Railway project from it. Railway detects the Dockerfile.
2. Add a PostgreSQL service to the same Railway project.
3. In the Django service variables, add:

   | Variable | Value |
   | --- | --- |
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (use the actual PostgreSQL service name) |
   | `DJANGO_DEBUG` | `0` |
   | `DJANGO_SECRET_KEY` | A newly generated secret, for example `python -c 'import secrets; print(secrets.token_urlsafe(50))'` |
   | `DJANGO_ALLOWED_HOSTS` | `.up.railway.app` and any custom domain, comma-separated |
   | `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://${{RAILWAY_PUBLIC_DOMAIN}}` and any custom HTTPS domain, comma-separated |

4. Generate a public domain for the Django service in Railway's Networking settings. Deploy with one web replica while the container applies migrations at startup.
5. Create the first administrator and import the training workbook once, after the first deployment:

   ```bash
   railway ssh --service <django-service-name> -- python manage.py createsuperuser
   railway ssh --service <django-service-name> -- python manage.py import_training_data
   ```

   The Docker image includes `Data/Training Web.xlsx`. The import command replaces the current imported snapshot, so run it only for initial setup or an intentional full refresh. Enable PostgreSQL backups before using real operational data.

The local default remains SQLite (`db.sqlite3`). Outside Railway, PostgreSQL can be configured with `DATABASE_URL`, or with `DB_ENGINE=postgresql` plus `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT`.

## Product notes

- Product requirements: [PRD.md](PRD.md)
- Interface and interaction design: [Design.md](Design.md)
- Source workbook: `Data/Training Web.xlsx`

The initial project implements the dashboard, Sales Order search/filter/detail, tracker lists, shortage monitor, remark capture, CSV exports, and Django Admin. XLSX import is currently available as a management command.
