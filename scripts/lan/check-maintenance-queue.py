"""Local Windows operator probe, read-only; never exposes jobs or credentials."""
from pathlib import Path
import sqlite3
import sys

database=Path(sys.argv[1]).resolve(strict=True)
with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True) as connection:
    busy=connection.execute('SELECT count(*) FROM jobs WHERE state IN (?,?)',('queued','running')).fetchone()[0]
if busy:
    print('Finish or cancel queued/running work before maintenance.',file=sys.stderr)
    raise SystemExit(2)
