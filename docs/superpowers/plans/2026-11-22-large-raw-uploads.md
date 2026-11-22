# Large raw uploads

The public proxy returned HTTP 413 for a 198,180,864-byte request. It never reached Horizon. Preserve the existing raw-file behavior by sending files larger than 64 MiB in authenticated 64 MiB parts, then reassemble and pass the result through the existing upload handler. Keep small uploads unchanged.

- [ ] Prove the existing large-file request and proxy-error handling fail.
- [ ] Add owner-scoped temporary upload sessions, strict chunk sizes, finalization locking, cached completion and abandoned-session cleanup.
- [ ] Add authenticated init/chunk/complete/cancel routes; retain existing storage, limits, processing, permissions and events during completion.
- [ ] Add the browser upload path and readable non-JSON HTTP errors.
- [ ] Run tests, review, build and deploy with rollback.
- [ ] Verify a 189 MiB file through the public endpoint and browser Python, with matching hash and no embeddings.
