#!/usr/bin/env python3
"""Local build helper for the `local` branch.

Steps (each usable on its own):
  assemble DIST [SRC OUT]  copy the tsp output (out/@ebusd/ebus-typespec) to DIST/en and resolve the src symlinks
  overlay  DIST       apply the tables in overlay/ to DIST/en/vaillant
  check    DIST       fail on duplicate bus IDs inside one file
  compare  A B        write a per-message difference report of two DIST dirs (en/vaillant) to stdout

See LOCAL.md for the table formats.
"""
import csv
import io
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TSP_OUT = os.path.join(ROOT, 'out', '@ebusd', 'ebus-typespec')
BRAND = 'vaillant'
COND_RE = re.compile(r'^((?:\[[^\]]*\])*)(.*)$')


def read_rows(path):
    """returns a list of csv rows, keeping comment and default rows too"""
    with open(path, encoding='utf-8', newline='') as f:
        return list(csv.reader(f))


def write_rows(path, rows):
    buf = io.StringIO()
    csv.writer(buf, lineterminator='\n').writerows(rows)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(buf.getvalue())


def split_type(field0):
    m = COND_RE.match(field0)
    return m.group(1), m.group(2)


def is_message(row):
    return bool(row) and not row[0].startswith(('#', '*')) and row[0] != 'type' and len(row) > 8


def read_table(name, ncols):
    path = os.path.join(HERE, name)
    entries = []
    with open(path, encoding='utf-8', newline='') as f:
        for row in csv.reader(line for line in f if line.strip() and not line.startswith('#')):
            if row[0] == 'file':
                continue
            if len(row) != ncols:
                raise SystemExit(f'{name}: expected {ncols} columns: {row}')
            entries.append(row)
    return entries


def assemble(dist, src=None, tspout=None):
    en = os.path.join(dist, 'en')
    shutil.rmtree(dist, ignore_errors=True)
    shutil.copytree(tspout or TSP_OUT, en)
    src = src or os.path.join(ROOT, 'src')
    n = 0
    for dirpath, _, files in os.walk(src):
        for fn in files:
            p = os.path.join(dirpath, fn)
            if not os.path.islink(p):
                continue
            rel = os.path.relpath(p, src).replace('.tsp', '.csv')
            target = os.path.relpath(os.path.realpath(p), src).replace('.tsp', '.csv')
            shutil.copyfile(os.path.join(en, target), os.path.join(en, rel))
            n += 1
    print(f'assembled {dist}/en ({n} symlinked files resolved)')


def messages_by_name(rows):
    res = {}
    for i, row in enumerate(rows):
        if is_message(row):
            res.setdefault(row[3], []).append(i)
    return res


def overlay(dist):
    vdir = os.path.join(dist, 'en', BRAND)
    prios = read_table('priorities.csv', 3)
    readonly = read_table('readonly_copies.csv', 2)
    remove = read_table('remove.csv', 2)
    files = {}
    errors = []

    def rows_of(fn):
        if fn not in files:
            files[fn] = read_rows(os.path.join(vdir, fn))
        return files[fn]

    removed = {}
    for fn, name in remove:
        rows = rows_of(fn)
        idx = messages_by_name(rows).get(name, [])
        if not idx:
            print(f'warning: remove {fn} {name}: message not present (already gone upstream)')
        for i in idx:
            removed[(fn, i)] = True
    for fn, name, prio in prios:
        if not re.fullmatch(r'[1-9]', prio):
            errors.append(f'priorities.csv: bad priority {prio!r} for {fn} {name}')
            continue
        rows = rows_of(fn)
        hit = 0
        for i in messages_by_name(rows).get(name, []):
            cond, typ = split_type(rows[i][0])
            if typ == 'r':
                rows[i][0] = f'{cond}r{prio}'
                hit += 1
        if not hit:
            errors.append(f'priorities.csv: no read line for {fn} {name}')
    for fn, name in readonly:
        rows = rows_of(fn)
        hit = 0
        for i in messages_by_name(rows).get(name, []):
            cond, typ = split_type(rows[i][0])
            if typ.startswith('r') and rows[i][2] == 'install':
                rows[i][2] = ''
                hit += 1
        if not hit:
            errors.append(f'readonly_copies.csv: no read line with level install for {fn} {name}')
    for fn, rows in files.items():
        keep = [r for i, r in enumerate(rows) if (fn, i) not in removed]
        write_rows(os.path.join(vdir, fn), keep)
    if errors:
        raise SystemExit('overlay FAILED:\n  ' + '\n  '.join(errors))
    print(f'overlay applied: {len(prios)} priorities, {len(readonly)} read-only copies, {len(remove)} removals')


def bus_key(row):
    cond, typ = split_type(row[0])
    kind = 'r' if re.fullmatch(r'r[1-9]?', typ) else typ
    return (cond, kind, row[1], row[5], row[6], row[7], row[8])


def check(dist):
    vdir = os.path.join(dist, 'en', BRAND)
    bad = 0
    for fn in sorted(os.listdir(vdir)):
        if not fn.endswith('.csv'):
            continue
        seen = {}
        for row in read_rows(os.path.join(vdir, fn)):
            if not is_message(row):
                continue
            k = bus_key(row)
            if k in seen and seen[k] != row[3]:
                print(f'DUPLICATE ID in {fn}: {row[3]} and {seen[k]} share {k[2:]}')
                bad += 1
            seen.setdefault(k, row[3])
    if bad:
        raise SystemExit(f'check FAILED: {bad} duplicate bus IDs')
    print('check OK: no duplicate bus IDs')


def message_map(path):
    res = {}
    for row in read_rows(path):
        if is_message(row):
            cond, typ = split_type(row[0])
            key = (row[3], 'r' if re.fullmatch(r'r[1-9]?', typ) else typ, cond)
            prio = typ[1:] if re.fullmatch(r'r[1-9]', typ) else ''
            res[key] = (prio, row)
    return res


def compare(a, b, files=None, label_a='A', label_b='B'):
    """per message differences; priority and level differences are reported separately from ID/type ones"""
    out = []
    adir = os.path.join(a, 'en', BRAND) if os.path.isdir(os.path.join(a, 'en')) else a
    bdir = os.path.join(b, 'en', BRAND) if os.path.isdir(os.path.join(b, 'en')) else b
    names = files or sorted(set(f for f in os.listdir(adir) if f.endswith('.csv')) | set(f for f in os.listdir(bdir) if f.endswith('.csv')))
    for fn in names:
        pa, pb = os.path.join(adir, fn), os.path.join(bdir, fn)
        if not (os.path.exists(pa) and os.path.exists(pb)):
            out.append(f'===== {fn}: only in {label_a if os.path.exists(pa) else label_b}')
            continue
        ma, mb = message_map(pa), message_map(pb)
        lines = []
        for k in sorted(set(ma) | set(mb)):
            name, kind, cond = k
            tag = f'{cond}{kind} {name}'
            if k not in mb:
                lines.append(f'ONLY {label_a}  {tag}  {",".join(ma[k][1][7:9])}')
            elif k not in ma:
                lines.append(f'ONLY {label_b}  {tag}  {",".join(mb[k][1][7:9])}')
            else:
                (qa, ra), (qb, rb) = ma[k], mb[k]
                ra, rb = list(ra), list(rb)
                notes = []
                if qa != qb:
                    notes.append(f'prio {qa or "-"} -> {qb or "-"}')
                if ra[2] != rb[2]:
                    notes.append(f'level {ra[2] or "-"} -> {rb[2] or "-"}')
                ra[0] = rb[0] = ''
                ra[2] = rb[2] = ''
                if ra != rb:
                    diff = [i for i in range(max(len(ra), len(rb))) if (ra[i] if i < len(ra) else None) != (rb[i] if i < len(rb) else None)]
                    notes.append(f'definition differs (columns {diff})')
                if notes:
                    lines.append(f'CHANGED  {tag}: ' + '; '.join(notes))
        if lines:
            out.append(f'===== {fn} ({label_a} vs {label_b})')
            out.extend(lines)
    return '\n'.join(out) + '\n'


def main(argv):
    if len(argv) >= 3 and argv[1] == 'assemble':
        assemble(*argv[2:5])
    elif len(argv) >= 3 and argv[1] == 'overlay':
        overlay(argv[2])
    elif len(argv) >= 3 and argv[1] == 'check':
        check(argv[2])
    elif len(argv) >= 4 and argv[1] == 'compare':
        sys.stdout.write(compare(argv[2], argv[3], argv[4:] or None, 'first', 'second'))
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main(sys.argv)
