"""Local-only launcher for NSA. Reads .env without extra dependencies."""
import os
from pathlib import Path

root = Path(__file__).resolve().parent
env = root / '.env'
if env.exists():
    for line in env.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

if __name__ == '__main__':
    import uvicorn
    print('NorthByte Space Agency — local preview: http://127.0.0.1:8080')
    print('Staff dashboard: http://127.0.0.1:8080/admin')
    uvicorn.run('app:app', host='127.0.0.1', port=8080, reload=False)
