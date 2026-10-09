# Free hosting: Render + Aiven MySQL

Use only free plans. No credit card or paid subscription is required for this setup. Do not add payment details if you want services to stop rather than charge for exceeding free usage.

## 1. Create a free MySQL service

Sign in at https://console.aiven.io and create **MySQL / Free**. Wait until Running. Copy the connection hostname, port, username, password and database name from its overview. Use its CA certificate from the connection details.

The Aiven database is separate from your computer. Do not use localhost, 127.0.0.1 or your local root password. The app verifies both the server certificate and hostname.

## 2. Deploy the app

Open https://render.com/deploy?repo=https://github.com/indhu1002/talent-forge-ai and approve the Blueprint for this repository. It explicitly selects the Free web-service plan.

Enter these private environment values in Render:

| Variable | Value |
| --- | --- |
| MYSQL_DATABASE | Aiven database name, often defaultdb |
| MYSQL_USER | Aiven application user, often avnadmin |
| MYSQL_PASSWORD | Aiven-generated password |
| MYSQL_HOST | Aiven hostname |
| MYSQL_PORT | Aiven connection port |
| MYSQL_SSL_CA | Entire Aiven CA PEM certificate; actual newlines or literal \n separators |
| OPENAI_API_KEY | A new private OpenAI API key; leave blank to disable paid AI reports |

The Blueprint generates SECRET_KEY. RENDER_EXTERNAL_HOSTNAME supplies the allowed domain and trusted CSRF origin. DEBUG is disabled. The Docker image serves the React assets and API on one origin. Migrations and the cache table are applied on startup. No local data is copied to the cloud.

If setting up a Web Service manually, select Docker, repository root, Free, and health path /health/. Set the variables above plus DB_ENGINE=mysql, DEBUG=0 and a long random SECRET_KEY.

## 3. Verify

Wait for Render to show Live. Visit the displayed HTTPS URL and /health/. Register a candidate and recruiter, sign in, upload a text PDF, download it and confirm another candidate cannot access it. Restart the service and verify the upload still downloads. Try JD coaching only after setting a valid API key with available credit and an API-accessible model.

The requested model names are kept as configuration, but availability depends on your OpenAI project. A Codex model name alone does not establish OpenAI API availability.

## Free-plan limits

Render sleeps after 15 minutes idle and may take about a minute to wake. Aiven's free MySQL has 1 GB disk, 1 GB RAM and may power off after inactivity. PDF storage is capped at 128 MB by default to leave room for database records. The quota is an application budget, not a substitute for provider usage monitoring. AI reports are durable queued records; a request interrupted during provider execution becomes failed and can be retried, with another API call.

OpenAI usage is not included in free hosting. Keep ENABLE_AI_FEEDBACK=0 to avoid optional AI calls during every resume upload. Explicit JD report requests still call OpenAI when a key is configured.

## Administrative access

Public registration cannot create an administrator. Use a private management session or a controlled one-time bootstrap to create an admin. Never deploy the local seed_demo accounts.

## References

- https://render.com/docs/free
- https://render.com/docs/blueprint-spec
- https://aiven.io/docs/products/mysql/concepts/mysql-free-tier
