# Raw Chat Uploads Implementation Plan

**Goal:** Upload documents for browser Python without indexing.

**Architecture:** Keep original bytes in authenticated file storage. Mark chat documents as raw, enable Python, and use the existing transfer into `/mnt/uploads`.

**Tech Stack:** Svelte/TypeScript, FastAPI/Python, Docker.

**Spec:** `docs/superpowers/specs/2026-11-22-raw-chat-uploads-design.md`

## Constraints and review focus

- Respect Python/model permissions and existing terminal uploads.
- Preserve image, audio/video, and Knowledge behavior.
- Raw files must skip retrieval even if the user's default context is full.
- Fetch Python attachment bytes with bearer authentication.
- Keep uploads and configuration intact during deployment.

### Task 1: Route and test raw uploads

- [ ] Add failing tests for document routing, explicit unprocessed uploads without polling, and raw attachments bypassing retrieval.
- [ ] Add a small upload-policy helper; apply it to the chat composer and skip processing-status polling for `process=false`.
- [ ] Skip raw attachments in retrieval; use authenticated file download for Python transfer.
- [ ] Run focused tests and frontend suite/build, then review the diff.

### Task 2: Deploy and verify

- [ ] Build a new image and preserve the current container as rollback.
- [ ] Deploy with the existing mounts, environment, OAuth and port bindings.
- [ ] Verify raw upload of the existing 31 MB CSV, hash equality, no embedding requests, and Python filesystem access.
- [ ] Record findings and remaining limitations.
