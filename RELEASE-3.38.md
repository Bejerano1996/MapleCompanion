# Umbrale Companion 3.38

NiaDB explicitly refused the old client and withdrew its former permission. This release does not claim to have downloaded the new database or to bypass the refusal. Live data access is paused until the operator renews authorization. Current policy: https://meowdb.com/reuse#tool-rules (updated November 9, 2026).

Existing local cached indexes remain usable. A local check loaded 401 quests, 453 maps/routes and 199 monsters with zero outbound calls. This is cached-data validation, not live new-content verification.

The shared provider limiter now permits only one serial request per ten seconds after renewed permission. A 403 or 429 stops all further requests, including portraits and guide jobs. Index refresh validates the whole new catalog before replacing existing data. Invalid or incomplete refreshes preserve the prior indexes. The NiaDB data/refresh menu shows loaded counts, cache age and the access-pause reason. Original character saves and caches are never bundled or uploaded.

Preserves the 3.37 background-error reason and details dialog. The proposed contact-bearing User-Agent uses the public project issues URL. Changing that identifier does not enable access; the permission gate stays closed.

Renewal recipient: contact@meowdb.com. Subject: Permission request: Umbrale Companion. The user must authorize any message; no email has been sent by this task.
