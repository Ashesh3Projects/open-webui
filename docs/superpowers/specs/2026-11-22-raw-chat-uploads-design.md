# Raw chat uploads

The user wants chat attachments available as original files in the existing browser Python filesystem, without text extraction or embeddings. A 32,490,652-byte CSV currently expands to 86 MB and triggers thousands of embedding requests.

Use the existing authenticated file storage and Python attachment transfer. Document uploads in chats with Python available will use `process=false`, carry `context: raw`, and enable Python. Raw attachments bypass retrieval and full-context injection. Knowledge uploads and media transcription keep their current behavior. Original bytes reach `/mnt/uploads/<filename>` when Python executes.

Alternatives: tuning embeddings does not satisfy the request; adding a server terminal was declined. The existing browser Python path was explicitly selected by the user.

Validate upload completion without status polling, original-byte transfer, no retrieval for raw files, frontend build, and the 31 MB file through the deployed upload and Python paths. Retain the previous container for rollback.
