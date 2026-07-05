# AIS-OS Control Tower — runtime image.
#
# App code + data are NOT baked in. The Cortex compose service bind-mounts
# the shared DS923 mount (/mnt/shared/claudia/magiq — the same live copy
# Windows edits over SMB, see decisions/log.md 2026-07-05) to /app, so this
# image is purely the Python runtime + system deps Tower shells out to (git,
# gh). Code changes land the instant they're saved from Windows — just
# restart the container to pick them up, no rebuild, no git pull. Rebuild
# only when tower/requirements.txt changes.

FROM python:3.12-slim

# git    — repo present at runtime via bind mount; kept for parity/debugging.
# gh CLI — tower/readers/github.py shells out to `gh` for PR data.
RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl ca-certificates \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update && apt-get install -y --no-install-recommends gh \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Installed at build time so a plain `git pull` doesn't require a rebuild.
COPY tower/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

EXPOSE 8765

# AIOS_ROOT self-locates to /app (tower/config.py -> parent.parent) once the
# repo is bind-mounted at /app — no override needed. Do NOT set AIOS_ROOT in
# .env: a hardcoded value breaks self-location the moment Tower runs in any
# environment where the mount path differs (confirmed 2026-07-05 — a stray
# AIOS_ROOT=/mnt/shared/claudia/magiq in .env broke startup everywhere except
# Cortex itself, since that's the only place the path is literally correct).
CMD ["python", "-m", "uvicorn", "tower.server:app", "--host", "0.0.0.0", "--port", "8765"]
