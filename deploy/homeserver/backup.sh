#!/usr/bin/env bash
#
# Nightly backup of AdmitFlow on the homeserver: a database dump plus a snapshot of the uploaded files.
# Installed by install.sh as /usr/local/sbin/admitflow-backup (root-owned, so the app user cannot change
# what runs as root) and run every night by admitflow-backup.timer. Run it by hand any time:
#
#   sudo admitflow-backup
#
# Layout under BACKUP_DIR (root-only, 0700: the dumps contain applicants' personal data):
#   db/admitflow-YYYYMMDD-HHMMSS.dump    pg_dump custom format; restore with pg_restore (see README)
#   files/YYYYMMDD-HHMMSS/               the MinIO data directory; unchanged files are hard links to the
#                                        previous snapshot, so each night only costs what changed
# Snapshots older than KEEP_DAYS are removed; the newest one is always kept.
#
# Note: BACKUP_DIR is on /srv, a different partition from the database (/), but the same disk. It
# protects against mistakes and a damaged system partition, not against the disk failing: copy the
# newest dump somewhere else from time to time.
set -euo pipefail

BACKUP_DIR=${BACKUP_DIR:-/srv/nas/admitflow-backups}
DB_NAME=${DB_NAME:-admitflow}
MINIO_DATA=${MINIO_DATA:-/srv/nas/admitflow/minio}
KEEP_DAYS=${KEEP_DAYS:-14}

[ "$(id -u)" -eq 0 ] || { echo "run this as root (sudo admitflow-backup)" >&2; exit 1; }

# One backup at a time (a manual run while the timer fires would otherwise interleave).
exec 9>/run/admitflow-backup.lock
flock -n 9 || { echo "another backup is already running" >&2; exit 1; }

stamp=$(date -u +%Y%m%d-%H%M%S)
umask 077
install -d -m 0700 "$BACKUP_DIR" "$BACKUP_DIR/db" "$BACKUP_DIR/files"

# ---- database: dump to a temporary name, prove it is readable, then give it its real name
partial="$BACKUP_DIR/db/.admitflow-$stamp.dump.partial"
trap 'rm -f "$partial"' EXIT
runuser -u postgres -- pg_dump --format=custom --dbname="$DB_NAME" > "$partial"
pg_restore --list "$partial" > /dev/null
mv "$partial" "$BACKUP_DIR/db/admitflow-$stamp.dump"
trap - EXIT
echo "database: $BACKUP_DIR/db/admitflow-$stamp.dump ($(du -h "$BACKUP_DIR/db/admitflow-$stamp.dump" | cut -f1))"

# ---- uploaded files: a hard-linked snapshot of the MinIO data directory
if [ -d "$MINIO_DATA" ]; then
    previous=$(find "$BACKUP_DIR/files" -mindepth 1 -maxdepth 1 -type d -name '20*' | sort | tail -n 1)
    link=()
    [ -n "$previous" ] && link=(--link-dest="$previous")
    rsync -a --delete "${link[@]}" "$MINIO_DATA/" "$BACKUP_DIR/files/$stamp.partial/"
    mv "$BACKUP_DIR/files/$stamp.partial" "$BACKUP_DIR/files/$stamp"
    echo "files:    $BACKUP_DIR/files/$stamp ($(du -sh "$BACKUP_DIR/files/$stamp" | cut -f1) on disk incl. shared links)"
else
    echo "files:    $MINIO_DATA not found, skipped" >&2
fi

# ---- retention: drop snapshots older than KEEP_DAYS, but never the newest of each kind
newest_db=$(find "$BACKUP_DIR/db" -maxdepth 1 -name 'admitflow-*.dump' | sort | tail -n 1)
find "$BACKUP_DIR/db" -maxdepth 1 -name 'admitflow-*.dump' -mtime +"$KEEP_DAYS" ! -path "$newest_db" -delete
newest_files=$(find "$BACKUP_DIR/files" -mindepth 1 -maxdepth 1 -type d -name '20*' | sort | tail -n 1)
find "$BACKUP_DIR/files" -mindepth 1 -maxdepth 1 -type d -name '20*' -mtime +"$KEEP_DAYS" ! -path "$newest_files" -exec rm -rf {} +
# leftovers from an interrupted run
find "$BACKUP_DIR/db" -maxdepth 1 -name '.*.partial' -mmin +60 -delete
find "$BACKUP_DIR/files" -mindepth 1 -maxdepth 1 -type d -name '*.partial' -mmin +60 -exec rm -rf {} +

echo "backup done ($(find "$BACKUP_DIR/db" -maxdepth 1 -name 'admitflow-*.dump' | wc -l) database dumps kept)"
