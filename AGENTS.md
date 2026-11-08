# Publishing releases

Every new verified version must be committed, tagged and published to `Bejerano1996/MapleCompanion` with program/source ZIPs, manifest and SHA-256 checksums. The user authorized this as the default release workflow. Never rewrite published versions or include state.json, caches, .env files, credentials or local character backups. Do not remove required bundled certificate-policy files.

Use `tools/publish_release.py` for a validated local package. Read RELEASES.md for the command. GitHub Actions builds and publishes an untagged new version pushed to main. A manual workflow run only verifies a build and does not replace an existing release. A local build alone is not publication.
