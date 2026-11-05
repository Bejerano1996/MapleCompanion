"""Build a staged app without deleting state/cache in an existing output."""
from pathlib import Path
import argparse,sys,subprocess,shutil,tempfile,ssl
def main():
    root=Path(__file__).resolve().parent
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=root/'dist/Umbrale Companion')
    args=parser.parse_args();output=args.output.resolve()
    if output==root or output in root.parents:raise ValueError('Choose a separate output folder')
    builds=root/'.build';builds.mkdir(exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='release-',dir=builds))
    command=[sys.executable,'-m','PyInstaller','--noconfirm','--windowed','--onedir','--name','Umbrale Companion','--icon',str(root/'icon.ico'),'--add-data',str(root/'icon.ico')+';.','--add-data',str(root/'icon.png')+';.','--add-data',str(root/'assets')+';assets','--collect-submodules','winrt','--hidden-import','screen_ocr','--hidden-import','webview.platforms.winforms','--collect-all','rapidocr_onnxruntime','--collect-binaries','onnxruntime','--distpath',str(stage/'dist'),'--workpath',str(stage/'work'),'--specpath',str(stage),str(root/'app.py')]
    # This Python runtime's ssl module loads a supplemental certificate policy
    # beside ssl.py. Frozen apps must carry the same file; TLS verification stays on.
    certificate_policy=Path(ssl.__file__).parent/'codex-rejected-cas.pem'
    if certificate_policy.is_file():
        command[-1:-1]=['--add-data',str(certificate_policy)+';.']
    subprocess.run(command,cwd=root,check=True)
    built=stage/'dist/Umbrale Companion';output.mkdir(parents=True,exist_ok=True)
    for file in built.rglob('*'):
        if file.is_file():
            target=output/file.relative_to(built);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,target)
    print(output)
if __name__=='__main__':main()
