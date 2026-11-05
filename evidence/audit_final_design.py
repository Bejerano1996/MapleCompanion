"""Read-only completion gates. A missing gate is not treated as successful."""
from pathlib import Path
import hashlib, json, zipfile

root = Path(__file__).resolve().parent.parent
release = root/'outputs'/'Maple Companion 5.1'
source = release/'source'
def report(name):
    path = source/name
    return json.loads(path.read_text(encoding='utf8')) if path.exists() else {}

checks = {}
for filename, expected in [('regression-results.json',45),('live-regression-results.json',37),('utility-results.json',33),('design-results.json',28)]:
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
checks['final_candidate_build_count'] = build.get('source_candidate')=='D' and build.get('packaged_checks')==143
checks['pure_model_tests_and_state_preservation'] = build.get('ok') is True and build.get('pure_model_checks') == 22 and build.get('state_preserved_on_rebuild_and_tests') is True
models=report('model-results.json')
checks['actual_model_count_and_input_hashes'] = models.get('ok') is True and models.get('count')==22 and bool(models.get('input_sha256')) and all((source/name).exists() and hashlib.sha256((source/name).read_bytes()).hexdigest()==digest for name,digest in models.get('input_sha256',{}).items())
packaging_tests = report('release-state-results.json')
checks['packaging_preserves_existing_state'] = packaging_tests.get('ok') is True and packaging_tests.get('count') == 4
for filename, seconds, cycles in [('design-stability-results.json',900,300),('reminder-refinement-stability-results.json',900,300),('quest-refinement-stability-results.json',900,300),('graphics-baseline-two-hour-results.json',7200,2400),('engine-baseline-five-hour-results.json',18000,6000)]:
    result = report(filename)
    checks[filename] = result.get('ok') is True and result.get('elapsed_seconds',0) >= seconds and result.get('cycles',0) >= cycles and result.get('callback_errors') == []
gps=report('design-stability-results.json')
checks['gps_lifecycle_exercised']=gps.get('gps_render_cycles',0)>=50 and gps.get('gps_close_cycles',0)>=25
resources = report('graphics-resource-results.json')
checks['bounded_graphics_resources'] = resources.get('ok') is True and all(resources.get('runs',{}).get(key,{}).get('ok') is True for key in ('graphics_baseline','quest_refinement','reminder_refinement','final_design'))
checks['instructions_and_scope_present'] = (release/'README-he.md').exists() and (source/'VERIFICATION.md').exists()
migration = report('migration-results.json')
verification=report('release-verification.json')
checks['published_check_totals_match'] = verification.get('automatic_checks')==169 and verification.get('packaged_checks')==143 and verification.get('pure_model_checks')==22 and verification.get('packaging_state_checks')==4
checks['imported_state_backed_up'] = migration.get('ok') is True and (release/'backups'/'state-packaged.json').exists() and hashlib.sha256((release/'backups'/'state-packaged.json').read_bytes()).hexdigest() == migration.get('snapshot_sha256')
target = root/'outputs'/'Maple Companion 5.1.zip'
checks['portable_zip_crc_and_contents'] = False
checks['zip_sha256_verified'] = False
checks['archived_build_and_state_match'] = False
checks['archive_has_no_development_files'] = False
if target.exists():
    with zipfile.ZipFile(target) as zipped:
        checks['portable_zip_crc_and_contents'] = zipped.testzip() is None and all('Maple Companion 5.1/'+name in zipped.namelist() for name in ('Maple Companion.exe','state.json','README-he.md','source/VERIFICATION.md','_internal/python312.dll'))
        prefix = release.name+'/'
        checks['archived_build_and_state_match'] = (
            hashlib.sha256(zipped.read(prefix+'Maple Companion.exe')).hexdigest() == manifest.get('output_sha256')
            and hashlib.sha256(zipped.read(prefix+'state.json')).hexdigest() == migration.get('snapshot_sha256')
            and zipped.read(prefix+'source/companion_ui.py') == (source/'companion_ui.py').read_bytes()
            and zipped.read(prefix+'source/placement_model.py') == (source/'placement_model.py').read_bytes())
        allowed = {'_internal','cache','source','backups','Maple Companion.exe','state.json','README-he.md'}
        checks['archive_has_no_development_files'] = all(
            name.startswith(prefix) and name[len(prefix):].split('/')[0] in allowed
            and '__pycache__' not in name.split('/') and not name.endswith('.log')
            and not name.endswith('-progress.json')
            and not ('diagnostic' in name.split('/')[-1] and name.endswith('.json'))
            and name.split('/')[-1] not in ('design-leak-probe.json','design-corner-cleanup-results.json')
            and '..' not in name.split('/') for name in zipped.namelist())
    checksum = target.with_suffix('.sha256.txt')
    checks['zip_sha256_verified'] = checksum.exists() and checksum.read_text().split()[0] == hashlib.sha256(target.read_bytes()).hexdigest()
result = {'release_ready':all(checks.values()),'checks':checks,'remaining':[name for name,passed in checks.items() if not passed]}
(root/'work'/'final-design-release-audit.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result,indent=2))
