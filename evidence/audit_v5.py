"""Read-only completion gates. A missing gate is not treated as successful."""
from pathlib import Path
import hashlib, json, zipfile

root = Path(__file__).resolve().parent.parent
release = root/'outputs'/'Maple Companion 5'
source = release/'source'
def report(name):
    path = source/name
    return json.loads(path.read_text(encoding='utf8')) if path.exists() else {}

checks = {}
for filename, expected in [('regression-results.json',45),('live-regression-results.json',37),('utility-results.json',33)]:
    result = report(filename)
    checks[filename] = result.get('ok') is True and result.get('count') == expected
manifest = report('build-manifest.json')
checks['executable_matches_manifest'] = manifest.get('output_sha256') == hashlib.sha256((release/'Maple Companion.exe').read_bytes()).hexdigest()
portable = report('portable-smoke-results.json')
checks['independent_directory_smoke_test'] = portable.get('ok') is True and portable.get('state_unchanged') is True and portable.get('copied_runtime_files') == 1007 and portable.get('executable_sha256') == manifest.get('output_sha256')
integrity = report('integrity-results.json')
checks['engine_and_runtime_preserved'] = integrity.get('ok') is True and integrity.get('runtime_files_identical') == 1007 and integrity.get('engine_entries_unchanged') == 12 and integrity.get('original_main_embedded_unchanged') is True
checks['embedded_extension_matches_editable_source'] = integrity.get('embedded_extension_matches_editable_source') is True
build = report('build-results.json')
checks['pure_model_tests_and_state_preservation'] = build.get('ok') is True and build.get('pure_model_checks') == 16 and build.get('state_preserved_on_rebuild_and_tests') is True
packaging_tests = report('release-state-results.json')
checks['packaging_preserves_existing_state'] = packaging_tests.get('ok') is True and packaging_tests.get('count') == 4
for filename, seconds, cycles in [('v5-stability-results.json',900,290),('five-hour-stability-results.json',18000,6000)]:
    result = report(filename)
    checks[filename] = result.get('ok') is True and result.get('elapsed_seconds',0) >= seconds and result.get('cycles',0) >= cycles and result.get('callback_errors') == []
checks['instructions_and_scope_present'] = (release/'README-he.md').exists() and (source/'VERIFICATION.md').exists()
migration = report('migration-results.json')
checks['imported_state_backed_up'] = migration.get('ok') is True and (release/'backups'/'state-packaged.json').exists() and hashlib.sha256((release/'backups'/'state-packaged.json').read_bytes()).hexdigest() == migration.get('snapshot_sha256')
target = root/'outputs'/'Maple Companion 5.zip'
checks['portable_zip_crc_and_contents'] = False
checks['zip_sha256_verified'] = False
if target.exists():
    with zipfile.ZipFile(target) as zipped:
        checks['portable_zip_crc_and_contents'] = zipped.testzip() is None and all('Maple Companion 5/'+name in zipped.namelist() for name in ('Maple Companion.exe','state.json','README-he.md','source/VERIFICATION.md','_internal/python312.dll'))
    checksum = target.with_suffix('.sha256.txt')
    checks['zip_sha256_verified'] = checksum.exists() and checksum.read_text().split()[0] == hashlib.sha256(target.read_bytes()).hexdigest()
result = {'complete':all(checks.values()),'checks':checks,'remaining':[name for name,passed in checks.items() if not passed]}
(root/'work'/'v5-completion-audit.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result,indent=2))
