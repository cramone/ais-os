# IIS Sites via Traefik File Provider

**Date:** 2026-08-07  
**Status:** Implemented

---

## Problem

IIS sites running on a separate Windows machine (`ramonehome`, Tailscale IP `100.80.221.90`) need to be publicly accessible via Traefik on cortex. Traefik's Docker provider only discovers containers — it has no awareness of external, non-Docker backends. A file provider is required to define static router + service config for these backends.

---

## Architecture

```
Public internet
    → Cloudflare (orange-cloud proxy, WAF)
        → cortex LAN NIC 192.168.0.253:443 (websecure entrypoint)
            → Traefik (network_mode: host)
                → file provider: cortex/traefik-dynamic/iis-tenants.yml
                    → http://100.80.221.90:80 (IIS on ramonehome via Tailscale)
                        → IIS host header binding routes to correct site
```

Cloudflare DDNS (`cloudflare-ddns` container) keeps A records for both tenant hostnames pointed at cortex's WAN IP. Traefik's DNS-01 resolver (Cloudflare token) mints LE certs on first request for each hostname.

---

## How It Works

### Host header passthrough

Traefik passes the original `Host` header to the backend by default (`passHostHeader: true`). IIS receives `tenant1.ramonedevelopment.com` or `tenant2.ramonedevelopment.com` and routes to the correct site via its own host bindings — no port differentiation needed.

### File provider hot-reload

`--providers.file.watch=true` means Traefik watches the dynamic config directory and reloads on change. Adding, removing, or modifying a router/service takes effect immediately — no Traefik restart required.

### Cert acquisition

Each router's `tls.certResolver: public` tells Traefik to mint a cert the first time a TLS handshake arrives for that hostname. DNS-01 challenge runs against Cloudflare — no public :80 needed.

---

## Components

### `cortex/traefik-dynamic/iis-tenants.yml`

Defines two routers sharing one backend service:

```yaml
http:
  routers:
    tenant1:
      rule: "Host(`tenant1.ramonedevelopment.com`)"
      entrypoints: [websecure, tailnet]
      tls:
        certResolver: public
      service: iis-windows

    tenant2:
      rule: "Host(`tenant2.ramonedevelopment.com`)"
      entrypoints: [websecure, tailnet]
      tls:
        certResolver: public
      service: iis-windows

  services:
    iis-windows:
      loadBalancer:
        passHostHeader: true
        servers:
          - url: "http://100.80.221.90:80"
```

### `cortex/docker-compose.yml` — traefik service

Added to `command`:
```yaml
- "--providers.file.directory=/etc/traefik/dynamic"
- "--providers.file.watch=true"
```

Added to `volumes`:
```yaml
- "/mnt/shared/claudia/magiq/cortex/traefik-dynamic:/etc/traefik/dynamic:ro"
```

### `cortex/docker-compose.yml` — cloudflare-ddns service

`tenant1.ramonedevelopment.com` and `tenant2.ramonedevelopment.com` added to `DOMAINS`. `PROXIED: "true"` — orange cloud, WAF, WAN IP hidden.

---

## IIS Requirements

Each IIS site must have a host binding matching its public hostname:

| Site | IIS binding |
|------|------------|
| tenant1 | `tenant1.ramonedevelopment.com` |
| tenant2 | `tenant2.ramonedevelopment.com` |

Remove any wildcard `*` binding that would catch-all — it breaks host-based routing.

---

## Cloudflare Requirements

No manual setup needed beyond what is already configured:

- **DNS records:** created automatically by `cloudflare-ddns` container on deploy
- **SSL/TLS mode:** zone-wide Full or Full (Strict) — already correct for tower/login
- **Always Use HTTPS:** zone-wide — already active
- **LE certs:** Traefik DNS-01 uses the existing `CF_DNS_API_TOKEN`

Verify SSL/TLS mode at: Cloudflare dashboard → ramonedevelopment.com → SSL/TLS → Overview. Must be Full or Full (Strict), not Flexible.

---

## Adding a New Site

### New IIS site on the same Windows machine

1. Add IIS host binding for the new hostname
2. Add a new router block in `cortex/traefik-dynamic/iis-tenants.yml` pointing to the existing `iis-windows` service
3. Add the hostname to `cloudflare-ddns` DOMAINS in `docker-compose.yml`
4. Traefik hot-reloads; cert mints on first request

### New site on a different machine

1. Add a new `services` entry in `iis-tenants.yml` with the new machine's Tailscale IP
2. Add a router pointing to that service
3. Add hostname to `cloudflare-ddns` DOMAINS

### Tailnet-only (not public)

Change `entrypoints: [websecure, tailnet]` to `entrypoints: [tailnet]` in the router. Do NOT add to `cloudflare-ddns` DOMAINS — the `dns-internal` dnsmasq wildcard already resolves `*.ramonedevelopment.com` to cortex's Tailscale IP for tailnet clients.

---

## Applying Changes

```bash
# On cortex, from ~/stack
docker compose up -d --no-deps traefik cloudflare-ddns
```

File provider changes (iis-tenants.yml edits) take effect immediately via hot-reload — no compose command needed.
