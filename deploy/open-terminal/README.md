# General machine

One shared Open Terminal machine for Open WebUI users and agents. The pinned image is
the standard full-toolkit `latest` variant, Open Terminal 0.18.6. Models use their
existing WebUI inference connections; no Codex or Claude Code CLI login is required.

The container has a persistent `/home/user`, a 2 CPU / 4 GiB memory budget, and no
published host port. Its workspace is shared by the users allowed to use the General
connection. It has no production data, host project folders, or Docker socket mounted.

## Deploy

Create the `open-webui-machines` Docker network and connect the WebUI container to it.
Create a private environment file containing `OPEN_TERMINAL_API_KEY` (a randomly
generated key), then run:

```sh
docker compose --env-file /path/to/private.env -f deploy/open-terminal/compose.yaml up -d
```

Keep the environment file outside Git and readable only by its owner. In WebUI's
admin machine integrations, add `General` with URL `http://open-terminal-general:8000`,
Bearer authentication and that key. Set chat uploads to **Filesystem** and grant
public read access to make this shared machine available to all approved users.
Keep existing connections when adding it. Preserve the machines network attachment
whenever recreating the WebUI container.

## File transport

Files larger than 64 MiB use the same bounded browser transport as regular WebUI
uploads. The machine proxy stages parts under `.machine-chunks`, bound to the user,
machine and chat/model context. After rechecking access, it streams the original
bytes to the selected machine. These uploads create no indexed WebUI file record.
Failed uploads are canceled; interrupted sessions expire after 24 hours and are
cleaned hourly. Completed sessions retain only retry metadata until expiry.

Validate through the public WebUI URL: upload a file over the proxy's request limit,
check its exact size and SHA-256 from the machine, use a WebUI model to process it,
and download an output. Also verify access from a non-admin account and persistence
across a General container restart. The browser Python workflow remains available
when no machine is selected.
