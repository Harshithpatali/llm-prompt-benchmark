# Database migrations

The consolidated platform targets PostgreSQL on Neon.

- `migrations/001_initial_schema.sql` defines the initial relational schema for dataset versions, models, prompts, rubrics, runs, results, traces, metrics, annotations, adjudication, calibration, review queues, and audit events.
- `backend/db.py` provides a minimal lazy psycopg connection boundary. It requires TLS and does not connect during module import.
- Set `DATABASE_URL` in a deployment secret or local untracked `.env` file. Never commit credentials.

## Apply procedure

1. Confirm the Neon project and branch intended for this application.
2. Take or verify a recoverable backup/snapshot.
3. Review the SQL migration and compare it with the target branch schema.
4. Apply `migrations/001_initial_schema.sql` to the intended branch using the Neon SQL editor or a controlled migration tool.
5. Verify the tables and indexes, then configure `DATABASE_URL` in Render.

The migration has been syntax-tested on a temporary Neon branch and that temporary branch was discarded. **It has not been applied to the production/default branch.** The existing API and Streamlit app do not yet persist runs through this database adapter.
