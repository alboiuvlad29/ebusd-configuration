#!/bin/sh
# Installs the local ebusd definitions into the eBUSd add-on config folder (run from the HA terminal).
#   sh ebusd_install.sh           download the latest release of alboiuvlad29/ebusd-configuration (default)
#   sh ebusd_install.sh share     fallback: copy the files from /share/ebusd-config/en (old mode)
# The previous files are kept as ebusd-config-backup/en.<timestamp> (last 3). Restart the add-on afterwards.
REPO=alboiuvlad29/ebusd-configuration
ASSET=ebusd-config-local.tar.gz
URL="${ASSET_URL:-https://github.com/$REPO/releases/latest/download/$ASSET}"   # ASSET_URL / ADDON_DIR: for testing
SRC=/share/ebusd-config/en
MODE="${1:-download}"

fail() { echo "FAILED: $*"; exit 1; }

for d in "${ADDON_DIR:-/addon_configs/b4d7ad18_ebusd}" /addon_configs/b4d7ad18-ebusd; do
  [ -d "$d" ] && DEST="$d" && break
done
[ -n "$DEST" ] || { echo "FAILED: eBUSd add-on config folder not found. Folders here:"; ls / /addon_configs 2>/dev/null; exit 1; }

TMP="$DEST/.ebusd-config-new"
rm -rf "$TMP" && mkdir -p "$TMP" || fail "cannot create $TMP"

if [ "$MODE" = "share" ]; then
  [ -d "$SRC" ] || fail "$SRC not found (is /share mapped?)"
  cp -r "$SRC" "$TMP/en" || fail "copy error"
  FROM="$SRC"
else
  echo "downloading $URL"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL -o "$TMP/$ASSET" "$URL" || fail "download error (no release yet, or no internet?). Try: sh $0 share"
  elif command -v wget >/dev/null 2>&1; then
    wget -q -O "$TMP/$ASSET" "$URL" || fail "download error (no release yet, or no internet?). Try: sh $0 share"
  else
    fail "neither curl nor wget available"
  fi
  tar -xzf "$TMP/$ASSET" -C "$TMP" || fail "cannot unpack $ASSET"
  rm -f "$TMP/$ASSET"
  FROM="$URL"
fi

# sanity check before touching the live files
for f in 08.hmu.HW5103.csv 15.ctlv3.csv 26.vr_71.csv 76.vwzio.csv; do
  [ -f "$TMP/en/vaillant/$f" ] || { rm -rf "$TMP"; fail "$f missing in new files, nothing changed"; }
done
N=$(ls "$TMP/en/vaillant" | wc -l | tr -d " ")

mkdir -p "$DEST/ebusd-config" "$DEST/ebusd-config-backup" || fail "cannot create folders"
if [ -d "$DEST/ebusd-config/en" ]; then
  B="$DEST/ebusd-config-backup/en.$(date +%Y%m%d-%H%M%S)"
  mv "$DEST/ebusd-config/en" "$B" || { rm -rf "$TMP"; fail "cannot back up the old files"; }
  echo "backup: $B"
fi
mv "$TMP/en" "$DEST/ebusd-config/en" || fail "cannot move new files into place (restore from ebusd-config-backup)"
rm -rf "$TMP"
# keep only the 3 newest backups
ls -d "$DEST"/ebusd-config-backup/en.* 2>/dev/null | sort -r | tail -n +4 | while read -r old; do rm -rf "$old"; done

if [ "$N" -ge 100 ] && [ -f "$DEST/mqtt-hassio.cfg" ]; then
  echo "OK: installed $N files in $DEST/ebusd-config/en (from $FROM). Restart the eBUSd add-on."
else
  echo "CHECK: installed $N files (expected >= 100) from $FROM; mqtt-hassio.cfg present: $([ -f "$DEST/mqtt-hassio.cfg" ] && echo yes || echo no). Restart the eBUSd add-on."
fi
