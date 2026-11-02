#!/bin/bash
set -e

echo "=========================================="
echo "🚀 UPDATING NAMMAL ON PYTHONANYWHERE"
echo "=========================================="

# 1. Verify remote origin is configured
CURRENT_REMOTE=$(git remote get-url origin 2>/dev/null || echo "")
if [[ -z "$CURRENT_REMOTE" ]]; then
    git remote add origin https://github.com/sonamolcm/nammal.git
fi

# 2. Fetch and pull latest code
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
echo "[2/5] Pulling latest code from $CURRENT_BRANCH..."
git pull origin "$CURRENT_BRANCH"

# 3. Install/update python packages
echo "[3/5] Installing dependencies..."
pip install -r requirements.txt

# 4. Apply database migrations
echo "[4/5] Running migrations..."
python manage.py migrate

# 5. Collect static files
echo "[5/5] Collecting static files..."
python manage.py collectstatic --noinput

# 6. Touch WSGI to trigger auto-reload
touch /var/www/*_wsgi.py 2>/dev/null || true

echo "=========================================="
echo "✅ DEPLOYMENT SUCCEEDED!"
echo "Visit your Web tab and click 'Reload' if needed."
echo "=========================================="
