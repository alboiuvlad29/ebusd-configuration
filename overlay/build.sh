#!/bin/bash -e
# Builds the local definitions: TypeSpec compile, overlay, check, comparison with upstream, release zip.
# Usage: overlay/build.sh            (output in dist/)
# Needs node >= 20 and python3. Compares against upstream/master when that remote exists (or UPSTREAM_REF).
cd "$(dirname "$0")/.."
UPSTREAM_REF="${UPSTREAM_REF:-upstream/master}"
rm -rf dist out
npm ci --no-audit --no-fund 2>/dev/null || npm install --no-audit --no-fund
npx tsp compile --emit @ebusd/ebus-typespec src/main.tsp --output-dir out
python3 overlay/localbuild.py assemble dist/base
cp -r dist/base dist/local
python3 overlay/localbuild.py overlay dist/local
python3 overlay/localbuild.py check dist/local
# pure upstream build for the comparison report
if git rev-parse --verify -q "$UPSTREAM_REF" >/dev/null; then
  rm -rf .upstream && mkdir .upstream
  git archive "$UPSTREAM_REF" src | tar -x -C .upstream
  ln -s ../node_modules .upstream/node_modules
  (cd .upstream && npx tsp compile --emit @ebusd/ebus-typespec src/main.tsp --output-dir out)
  python3 overlay/localbuild.py assemble dist/upstream .upstream/src .upstream/out/@ebusd/ebus-typespec
  {
    echo "# local build vs $UPSTREAM_REF ($(git rev-parse --short "$UPSTREAM_REF")), generated $(date -u +%Y-%m-%d)"
    echo "# 'first' = local build (incl. overlay), 'second' = upstream"
    python3 overlay/localbuild.py compare dist/local dist/upstream
  } > dist/local_vs_upstream.txt
  rm -rf .upstream
fi
(cd dist/local && zip -qr ../ebusd-config-local.zip en && tar -czf ../ebusd-config-local.tar.gz en)
echo "built dist/ebusd-config-local.zip ($(ls dist/local/en/vaillant | wc -l) files in en/vaillant)"
