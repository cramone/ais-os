# AIS-OS Control Tower — runtime image.
#
# App code + data are NOT baked in. The Cortex compose service bind-mounts
# the host's /opt/ais-os clone to /app, so this image is purely the Python
# runtime + system deps Tower shells out to (git, gh). Code changes land via
# `git pull` + container restart — no rebuild needed. Rebuild only when
# tower/requirements.txt changes.

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
# repo is bind-mounted at /app — no override needed.
CMD ["python", "-m", "uvicorn", "tower.server:app", "--host", "0.0.0.0", "--port", "8765"]
