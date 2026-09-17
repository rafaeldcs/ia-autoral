"""Read only first-access readiness. Never prints a credential, salt or hash."""
import json
import os
from pathlib import Path
import sqlite3
path=Path(os.environ['LOCALAPPDATA'])/'LocalAuthor/lan/publication-auth.sqlite3'
database=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
try:
    configured=database.execute('SELECT COUNT(*) FROM publication_password').fetchone()[0]>0
finally:
    database.close()
result={'passwordConfigured':configured,'readyForFirstAccess':not configured}
(Path(__file__).resolve().parents[1]/'reports/publication-password-state.json').write_text(json.dumps(result),encoding='utf-8')
print(json.dumps(result))
