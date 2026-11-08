# Releases and downloads

- [Latest Windows program and source](https://github.com/Bejerano1996/MapleCompanion/releases/latest)
- [All historical versions](https://github.com/Bejerano1996/MapleCompanion/releases)
- [Machine-readable archive index](release-index.json)

Download the program ZIP, extract it, and run `Umbrale Companion.exe` on Windows. Your character data stays on each computer; it is not stored in GitHub. When updating an existing installation, preserve its `state.json` and `cache` folder.

The archive contains 60 retained versions and 112 original or privacy-filtered source/program ZIPs. Original archives are preserved locally. Seven legacy Maple releases have only program archives; their tags do not claim a matching source snapshot. The separate legacy UI source archive is also preserved. Import dates do not claim original release dates.

Each release includes SHA256SUMS.txt and a release manifest. For privacy-filtered archives the manifest records the original and published hashes plus the number of excluded entries. Required software certificate-policy files are retained.

## Future versions

1. Make a meaningful, verified change and update the version in companion_integration.py.
2. Run focused regression checks, build and validate program/source archives.
3. Publish with the validated package manifest:

```powershell
python tools/publish_release.py --version 3.37 --source-dir C:/path/to/source --repo-dir C:/path/to/MapleCompanion --program-zip "C:/path/to/Umbrale Companion 3.37.zip" --source-zip "C:/path/to/Umbrale Companion 3.37 Source.zip" --release-manifest C:/path/to/training-3.37-release-ready.json
```

The local publisher requires a clean release checkout, verifies archive hashes/CRC and privacy exclusions, commits source, pushes main plus an immutable tag, uploads assets and verifies remote SHA-256 digests. It uses the existing Git credential helper without storing credentials in this repository.

As a fallback, pushing a new version to main without its tag starts the Windows GitHub Actions workflow. Checks must pass before packaging and publishing. Existing tags are not overwritten. A manual workflow run builds and verifies artifacts only.

Large program ZIPs belong in GitHub Releases, not the Git file history. Source snapshots are available through tags and the source ZIP attached to each retained source release.
