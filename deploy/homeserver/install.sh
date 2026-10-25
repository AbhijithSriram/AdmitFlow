#!/usr/bin/env bash
#
# Install (or update) AdmitFlow on homeserver.
#
#   cd /home/abhijith/admitflow && git pull && sudo bash deploy/homeserver/install.sh
#
# Idempotent: safe to re-run, and re-running IS the update path (it rebuilds the venv and the
# website from the checked-out code and restarts the services). What it touches:
#
#   packages              nginx and postgresql, only if missing (apt)
#   PostgreSQL            one role and one database, both called admitflow
#   /etc/admitflow.env             backend secrets   created once, then only updated from the secrets file
#   /etc/admitflow-minio.env       file-storage keys created once, never overwritten
#   /etc/systemd/system/admitflow.service and admitflow-minio.service
#   /usr/local/bin/minio           the file-storage server (staged beforehand, see below)
#   /etc/nginx/sites-available/admitflow   (+ symlink in sites-enabled)
#   /etc/cloudflared/config.yml    ONE ingress rule appended, backed up first
#   /srv/nas/admitflow             uploaded files
#   /var/www/admitflow             the built website (nginx cannot read /home/abhijith)
#
# It does not touch cockpit, chat, ammas-codex, locomotion-transitops, voicelab, 8086-emulator,
# ieee-eds, drishtitrust or pwiews, and it uses ports none of them use:
#   5001 API, 8088 nginx, 9000 + 9001 file storage, 5432 database. All loopback-only.
#
# Optional input, prepared beforehand by whoever runs this (see deploy/homeserver/secrets.env.example):
#   /home/abhijith/.admitflow-secrets.env     Razorpay, Gmail and reCAPTCHA keys
#   /home/abhijith/.admitflow-stage/minio     the MinIO server binary (it is not available as a
#                                             package or a download any more; this one was built
#                                             from source, see docker/minio/Dockerfile)

set -euo pipefail

APP_USER=abhijith
APP_DIR=/home/abhijith/admitflow
DATA_DIR=/srv/nas/admitflow
WEB_ROOT=/var/www/admitflow/frontend/dist
ENV_FILE=/etc/admitflow.env
MINIO_ENV_FILE=/etc/admitflow-minio.env
SECRETS_FILE=/home/abhijith/.admitflow-secrets.env
STAGED_MINIO=/home/abhijith/.admitflow-stage/minio
HOSTNAME_FQDN=admitflow.abhijith-sriram.in
API_PORT=5001
WEB_PORT=8088
MINIO_PORT=9000
MINIO_CONSOLE_PORT=9001
DB_NAME=admitflow
DB_USER=admitflow
BUCKET=admitflow
CF_CONFIG=/etc/cloudflared/config.yml
HERE="$APP_DIR/deploy/homeserver"

say()  { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33mWARNING: %s\033[0m\n' "$*"; }
die()  { printf '\n\033[1;31mFAILED: %s\033[0m\n' "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || die "run this with sudo"
[ -d "$APP_DIR/backend" ] && [ -d "$APP_DIR/frontend" ] || die "$APP_DIR is not the AdmitFlow checkout -- clone the repo there first"

# Generated values never leave this machine and never go through the repo or a chat log.
rand_hex() { python3 -c "import secrets; print(secrets.token_hex($1))"; }
rand_url() { python3 -c "import secrets; print(secrets.token_urlsafe($1))"; }

port_busy() { ss -ltnH "( sport = :$1 )" 2>/dev/null | grep -q .; }
# A port in use is fine if it is ours (re-run); anything else holding it is a conflict, and the
# install stops rather than fight a neighbour for it.
need_port() { # port unit
    if port_busy "$1" && ! systemctl is-active --quiet "$2"; then
        die "port $1 is already in use by something that is not $2 -- pick another port at the top of this script"
    fi
}

# ------------------------------------------------------------ 0. pre-flight
say "Pre-flight"
need_port "$API_PORT" admitflow
need_port "$WEB_PORT" nginx
need_port "$MINIO_PORT" admitflow-minio
need_port "$MINIO_CONSOLE_PORT" admitflow-minio
[ -x /usr/local/bin/minio ] || [ -f "$STAGED_MINIO" ] || die "no MinIO binary: expected $STAGED_MINIO (or an installed /usr/local/bin/minio)"
python3 -m venv --help >/dev/null 2>&1 || die "python3 venv support is missing (apt install python3-venv)"
command -v node >/dev/null && command -v npm >/dev/null || die "node/npm are needed to build the website"
[ -f "$SECRETS_FILE" ] || warn "$SECRETS_FILE not found: payments, email and signup (reCAPTCHA) will not work until it exists. Create it from deploy/homeserver/secrets.env.example and re-run."
# Some steps run as other users (postgres, abhijith) who cannot see whatever directory this was
# started from; every path in this script is absolute.
cd /

# ------------------------------------------------------------ 1. packages
say "Packages"
NGINX_NEW=0
MISSING=""
command -v nginx >/dev/null || { MISSING="$MISSING nginx"; NGINX_NEW=1; }
command -v psql  >/dev/null || MISSING="$MISSING postgresql"
if [ -n "$MISSING" ]; then
    say "Installing:$MISSING"
    apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y $MISSING
else
    echo "nginx and postgresql already installed"
fi
if [ "$NGINX_NEW" = "1" ]; then
    # A fresh nginx ships a welcome site on port 80 that would start answering on the LAN. Nothing
    # was listening on 80 before, so keep it that way.
    rm -f /etc/nginx/sites-enabled/default
fi
systemctl enable --now postgresql >/dev/null
for i in $(seq 1 20); do runuser -u postgres -- pg_isready -q && break; sleep 1; done
runuser -u postgres -- pg_isready -q || die "PostgreSQL is not accepting connections"

# ------------------------------------------------------------ 2. secrets
say "Secrets"
install -d -m 0755 "$DATA_DIR" "$DATA_DIR/minio"
chown -R "$APP_USER:$APP_USER" "$DATA_DIR"

if [ ! -f "$MINIO_ENV_FILE" ]; then
    say "Creating $MINIO_ENV_FILE"
    cat > "$MINIO_ENV_FILE" <<ENV
# AdmitFlow file-storage credentials. Read by systemd, which is not a shell:
# do not quote values, do not use \$substitution.
MINIO_ROOT_USER=af$(rand_hex 6)
MINIO_ROOT_PASSWORD=$(rand_hex 24)
ENV
    chown root:root "$MINIO_ENV_FILE"; chmod 600 "$MINIO_ENV_FILE"
fi
minio_val() { grep -E "^$1=" "$MINIO_ENV_FILE" | head -1 | cut -d= -f2-; }

NEW_ENV=0
if [ ! -f "$ENV_FILE" ]; then
    say "Creating $ENV_FILE"
    printf '%s\n' \
        "# AdmitFlow runtime secrets. Read by systemd, which is not a shell:" \
        "# do not quote values, do not use \$substitution." > "$ENV_FILE"
    chown root:root "$ENV_FILE"; chmod 600 "$ENV_FILE"
    NEW_ENV=1
fi
env_val() { grep -E "^$1=" "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- || true; }
set_env() { # KEY VALUE: replace the line, or append it
    local tmp; tmp=$(mktemp)
    grep -v -E "^$1=" "$ENV_FILE" > "$tmp" || true
    printf '%s=%s\n' "$1" "$2" >> "$tmp"
    install -m 600 -o root -g root "$tmp" "$ENV_FILE"; rm -f "$tmp"
}
set_env_once() { [ -n "$(env_val "$1")" ] || set_env "$1" "$2"; }

DB_PASSWORD=$(env_val DATABASE_URL | sed -n 's#^postgresql://[^:]*:\([^@]*\)@.*#\1#p')
[ -n "$DB_PASSWORD" ] || DB_PASSWORD=$(rand_hex 20)

set_env_once FLASK_SECRET_KEY "$(rand_hex 32)"
set_env FLASK_ENV production
set_env DATABASE_URL "postgresql://$DB_USER:$DB_PASSWORD@127.0.0.1:5432/$DB_NAME"
set_env SESSION_TIMEOUT_SECONDS 1800
set_env CORS_ORIGINS "https://$HOSTNAME_FQDN"
set_env MINIO_ENDPOINT "127.0.0.1:$MINIO_PORT"
set_env MINIO_ACCESS_KEY "$(minio_val MINIO_ROOT_USER)"
set_env MINIO_SECRET_KEY "$(minio_val MINIO_ROOT_PASSWORD)"
set_env MINIO_BUCKET "$BUCKET"
# Signed file links must name a host the visitor's browser can open (see admitflow.nginx.conf).
set_env MINIO_PUBLIC_ENDPOINT "$HOSTNAME_FQDN"
set_env MINIO_PUBLIC_SECURE 1

# Third-party keys: copied from the optional secrets file on every run, so rotating a key is
# "edit the file, re-run". Only these names are ever copied.
secret() { [ -f "$SECRETS_FILE" ] && grep -E "^$1=" "$SECRETS_FILE" | head -1 | cut -d= -f2- || true; }
for key in RAZORPAY_KEY_ID RAZORPAY_KEY_SECRET SMTP_HOST SMTP_PORT SMTP_USERNAME SMTP_PASSWORD RECAPTCHA_SECRET_KEY; do
    value=$(secret "$key")
    [ -n "$value" ] && set_env "$key" "$value"
done
for key in RAZORPAY_KEY_ID RAZORPAY_KEY_SECRET SMTP_USERNAME SMTP_PASSWORD RECAPTCHA_SECRET_KEY; do
    [ -n "$(env_val "$key")" ] || warn "$key is not set in $ENV_FILE"
done

# ------------------------------------------------------------ 3. database
say "Database"
db() { runuser -u postgres -- psql -v ON_ERROR_STOP=1 -qtAX "$@"; }
if [ "$(db -c "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'")" = "1" ]; then
    db -c "ALTER ROLE $DB_USER WITH LOGIN PASSWORD '$DB_PASSWORD'"
else
    db -c "CREATE ROLE $DB_USER WITH LOGIN PASSWORD '$DB_PASSWORD'"
fi
[ "$(db -c "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'")" = "1" ] || db -c "CREATE DATABASE $DB_NAME OWNER $DB_USER"

# Run as the application role over TCP, so the tables belong to it.
app_psql() { PGPASSWORD="$DB_PASSWORD" psql -h 127.0.0.1 -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -qtAX "$@"; }
if [ -z "$(app_psql -c "SELECT to_regclass('public.students')")" ]; then
    say "Creating the tables (schema.sql)"
    app_psql -f "$APP_DIR/backend/migrations/schema.sql"
fi
# Numbered migrations (002_*.sql, 003_*.sql, ...), applied in order on every run. Each one must be
# idempotent (IF NOT EXISTS, ON CONFLICT DO NOTHING, ...): a no-op on a fresh install, the upgrade
# path on an older database. A new migration is picked up just by adding the file; nothing here
# needs editing. The glob sorts, so the three-digit prefix is the order.
shopt -s nullglob
for migration in "$APP_DIR"/backend/migrations/[0-9][0-9][0-9]_*.sql; do
    echo "migration: $(basename "$migration")"
    app_psql -f "$migration" >/dev/null
done
shopt -u nullglob
echo "database ready"

# ------------------------------------------------------------ 4. file storage
say "File storage (MinIO)"
if [ -f "$STAGED_MINIO" ] && ! cmp -s "$STAGED_MINIO" /usr/local/bin/minio 2>/dev/null; then
    install -m 0755 -o root -g root "$STAGED_MINIO" /usr/local/bin/minio
    echo "installed /usr/local/bin/minio"
fi
install -m 0644 "$HERE/admitflow-minio.service" /etc/systemd/system/admitflow-minio.service
systemctl daemon-reload
systemctl enable admitflow-minio >/dev/null
systemctl restart admitflow-minio
for i in $(seq 1 20); do curl -fsS -o /dev/null "http://127.0.0.1:$MINIO_PORT/minio/health/live" 2>/dev/null && break; sleep 1; done
curl -fsS -o /dev/null "http://127.0.0.1:$MINIO_PORT/minio/health/live" || { journalctl -u admitflow-minio -n 30 --no-pager; die "file storage did not come up (log above)"; }
echo "file storage is up on 127.0.0.1:$MINIO_PORT"

# ------------------------------------------------------------ 5. backend venv
say "Backend: virtualenv (as $APP_USER)"
# Built as the app user: a root-owned venv inside abhijith's home is a trap. Wheels only: the
# pinned versions all have Python 3.14 wheels, and a silent compile on this shared box is worse
# than a clear failure.
runuser -u "$APP_USER" -- bash -c "
    set -e
    cd '$APP_DIR/backend'
    [ -d .venv ] || python3 -m venv .venv
    .venv/bin/pip install --quiet --upgrade pip
    .venv/bin/pip install --quiet --only-binary=:all: -r requirements.txt
    .venv/bin/python -c 'import flask, sqlalchemy, psycopg2, minio, razorpay, weasyprint, gunicorn; print(\"backend deps OK\")'
"

# ------------------------------------------------------------ 6. website build
say "Website: build (as $APP_USER)"
VITE_RAZORPAY_KEY_ID=$(secret VITE_RAZORPAY_KEY_ID)
VITE_RECAPTCHA_SITE_KEY=$(secret VITE_RECAPTCHA_SITE_KEY)
[ -n "$VITE_RAZORPAY_KEY_ID" ] || warn "VITE_RAZORPAY_KEY_ID is empty: the payment window will not open"
[ -n "$VITE_RECAPTCHA_SITE_KEY" ] || warn "VITE_RECAPTCHA_SITE_KEY is empty: the signup form will have no reCAPTCHA and the server will refuse every signup"
# VITE_API_BASE_URL is deliberately EMPTY: the browser then calls /api on the same host, which is
# exactly what nginx serves. (frontend/src/api/client.js uses ?? so an empty value is respected.)
runuser -u "$APP_USER" -- env \
    VITE_API_BASE_URL= \
    VITE_RAZORPAY_KEY_ID="$VITE_RAZORPAY_KEY_ID" \
    VITE_RECAPTCHA_SITE_KEY="$VITE_RECAPTCHA_SITE_KEY" \
    bash -c "cd '$APP_DIR/frontend' && (npm ci --no-audit --no-fund --loglevel=error || npm install --no-audit --no-fund --loglevel=error) && npm run build"
[ -f "$APP_DIR/frontend/dist/index.html" ] || die "the website build produced no dist/index.html"
rm -rf "$WEB_ROOT"
install -d -m 0755 "$WEB_ROOT"
cp -a "$APP_DIR/frontend/dist/." "$WEB_ROOT/"
chown -R root:root /var/www/admitflow
chmod -R a+rX /var/www/admitflow
echo "website copied to $WEB_ROOT"

# ------------------------------------------------------------ 7. backend service
say "Backend service"
install -m 0644 "$HERE/admitflow.service" /etc/systemd/system/admitflow.service
systemctl daemon-reload
systemctl enable admitflow >/dev/null
systemctl restart admitflow
sleep 4
systemctl is-active --quiet admitflow || { journalctl -u admitflow -n 40 --no-pager; die "admitflow did not stay up (log above)"; }
# 401 is the right answer for "who am I?" without a session: it proves Flask, PostgreSQL and the
# session table are all working.
CODE=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$API_PORT/api/auth/me" || true)
[ "$CODE" = "401" ] || { journalctl -u admitflow -n 40 --no-pager; die "the API answered $CODE on /api/auth/me, expected 401 (log above)"; }
echo "API is up on 127.0.0.1:$API_PORT"

# ------------------------------------------------------------ 8. admin accounts (first install only)
ADMIN_REPORT=""
if [ "$(app_psql -c 'SELECT count(*) FROM admins')" = "0" ]; then
    say "Creating the four admin accounts"
    ADMIN_ENV=()
    for i in 1 2 3 4; do
        pw=$(rand_url 12)
        ADMIN_ENV+=("ADMIN${i}_NAME=Admin $i" "ADMIN${i}_EMAIL=admin${i}@${HOSTNAME_FQDN}" "ADMIN${i}_PASSWORD=$pw")
        ADMIN_REPORT+="      admin${i}@${HOSTNAME_FQDN}   $pw"$'\n'
    done
    runuser -u "$APP_USER" -- env \
        FLASK_ENV=production \
        "$(grep -E '^FLASK_SECRET_KEY=' "$ENV_FILE")" \
        "$(grep -E '^DATABASE_URL=' "$ENV_FILE")" \
        "${ADMIN_ENV[@]}" \
        bash -c "cd '$APP_DIR/backend' && .venv/bin/python -m scripts.seed_admins" | grep -E 'created|skip|Done' || true
fi

# ------------------------------------------------------------ 9. nginx
say "nginx"
SITE=/etc/nginx/sites-available/admitflow
[ -f "$SITE" ] && cp -a "$SITE" "$SITE.bak.$(date +%Y%m%d-%H%M%S)" || true
install -m 0644 "$HERE/admitflow.nginx.conf" "$SITE"
ln -sf "$SITE" /etc/nginx/sites-enabled/admitflow
if ! nginx -t; then
    rm -f /etc/nginx/sites-enabled/admitflow
    die "nginx rejected the config -- the new site was disabled, nothing else changed"
fi
systemctl enable nginx >/dev/null
systemctl reload nginx || systemctl restart nginx
sleep 1
HOSTHDR="Host: $HOSTNAME_FQDN"
curl -fsS -o /dev/null -H "$HOSTHDR" "http://127.0.0.1:$WEB_PORT/" || die "nginx is not serving the website on 127.0.0.1:$WEB_PORT"
CODE=$(curl -s -o /dev/null -w '%{http_code}' -H "$HOSTHDR" "http://127.0.0.1:$WEB_PORT/api/auth/me" || true)
[ "$CODE" = "401" ] || die "nginx -> API answered $CODE, expected 401"
echo "nginx is serving the website and the API on 127.0.0.1:$WEB_PORT"

# ------------------------------------------------------------ 10. cloudflared
if grep -q "$HOSTNAME_FQDN" "$CF_CONFIG"; then
    say "Tunnel already routes $HOSTNAME_FQDN -- config left untouched"
else
    say "Adding one ingress rule to the existing tunnel"
    BACKUP="$CF_CONFIG.bak.$(date +%Y%m%d-%H%M%S)"
    cp -a "$CF_CONFIG" "$BACKUP"
    echo "    backup: $BACKUP"

    # Insert immediately before the catch-all: rules match top to bottom and http_status:404
    # matches everything, so a rule after it would never fire. Every existing hostname keeps its
    # order and precedence.
    awk -v host="$HOSTNAME_FQDN" -v port="$WEB_PORT" '
        !done && /^[[:space:]]*-[[:space:]]*service:[[:space:]]*http_status:404/ {
            print "  - hostname: " host
            print "    service: http://localhost:" port
            print "    originRequest:"
            print "      # payment confirmation renders a PDF and sends an email inside the request"
            print "      connectTimeout: 30s"
            done = 1
        }
        { print }
        END { if (!done) exit 3 }
    ' "$BACKUP" > "$CF_CONFIG" || { cp -a "$BACKUP" "$CF_CONFIG"; die "no catch-all rule found -- $CF_CONFIG restored from $BACKUP"; }

    # `--config` is a flag on `tunnel`, not on `ingress validate`: in the wrong place cloudflared
    # prints "Incorrect Usage" and still exits 0, so the check would pass without validating.
    if ! cloudflared tunnel --config "$CF_CONFIG" ingress validate; then
        cp -a "$BACKUP" "$CF_CONFIG"
        die "ingress validation failed -- $CF_CONFIG rolled back, tunnel untouched"
    fi

    say "Reloading cloudflared (the other apps' tunnel drops for a few seconds)"
    systemctl restart cloudflared
    sleep 3
    systemctl is-active --quiet cloudflared || {
        cp -a "$BACKUP" "$CF_CONFIG"
        systemctl restart cloudflared
        die "cloudflared would not start -- config rolled back and restarted"
    }
fi

say "Done"
echo
echo "  https://$HOSTNAME_FQDN"
echo
echo "  The hostname needs ONE DNS record, once (this script cannot create it):"
echo "      Cloudflare dashboard -> DNS -> add a CNAME"
echo "          name    admitflow"
echo "          target  6d4003bd-0238-4a7b-bce4-96b9e51174a0.cfargotunnel.com"
echo "          proxy   on (orange cloud)"
echo
if [ -n "$ADMIN_REPORT" ]; then
    echo "  Admin accounts (sign in at https://$HOSTNAME_FQDN/admin/auth). Shown ONCE: only"
    echo "  bcrypt hashes are stored. Copy them now."
    echo
    printf '%s' "$ADMIN_REPORT"
    echo
fi
echo "  Logs:     journalctl -u admitflow -f        journalctl -u admitflow-minio -f"
echo "  Restart:  sudo systemctl restart admitflow"
echo "  Update:   cd $APP_DIR && git pull && sudo bash deploy/homeserver/install.sh"
echo
