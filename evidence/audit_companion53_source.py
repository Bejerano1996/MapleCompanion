from pathlib import Path
import json,marshal,types,importlib.util,hashlib
root=Path(__file__).resolve().parent.parent
source=root/'work/companion-next'
candidate=root/'work/companion53-fixed-build'
spec=importlib.util.spec_from_file_location('builder',source/'build_upgrade.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
packed=builder.unpack((candidate/'Maple Companion.exe').read_bytes())
app=marshal.loads(next(raw for name,kind,raw,flag in packed[1] if name=='app'))
def constants(code):
    for value in code.co_consts:
        yield value
        if isinstance(value,types.CodeType):yield from constants(value)
embedded=list(constants(app))
modules=('companion_ui.py','live_sync.py','placement_model.py','feature_model.py','planner_model.py','utility_ui.py','market_ui.py')
expected='\n'.join((source/name).read_text(encoding='utf-8-sig') for name in modules)
assert expected in embedded,'Embedded production source mismatch'
copies={path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in source.glob('*.py')}
assert all((candidate/'source'/name).is_file() and hashlib.sha256((candidate/'source'/name).read_bytes()).hexdigest()==digest for name,digest in copies.items()),'Editable source copy mismatch'
digest=hashlib.sha256((candidate/'Maple Companion.exe').read_bytes()).hexdigest()
report={'ok':True,'executable_sha256':digest,'embedded_modules':list(modules),'editable_files':copies}
(root/'work/companion53-source-integrity.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'ok':True,'embedded_modules':len(modules),'editable_files':len(copies),'exe':digest}))
