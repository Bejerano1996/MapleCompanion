"""Open a user-requested item search in the real MesoWatch website.

Only fills the visible search control; never downloads or extracts price tables.
No Python API is exposed to the website.
"""
import json
import os
import subprocess
import sys
from urllib.parse import urlsplit

ORIGIN='https://meso.watch/'

def search_script(name):
    value=json.dumps(str(name).strip()[:120],ensure_ascii=True)
    return '''(() => {
      if (location.origin !== 'https://meso.watch') return false;
      const name=NAME;
      const started=Date.now();
      const deadline=started+45000;
      const timer=setInterval(() => {
        if (location.origin !== 'https://meso.watch' || Date.now()>deadline) {clearInterval(timer);return;}
        const input=document.getElementById('search');
        const rows=document.getElementById('rows');
        if (Date.now()-started<2500 || !input || input.disabled || !rows || !rows.children.length) return;
        clearInterval(timer);
        Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(input,name);
        input.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:name}));
        input.dispatchEvent(new KeyboardEvent('keyup',{key:'Unidentified',bubbles:true}));
        input.dispatchEvent(new Event('change',{bubbles:true}));
        input.focus();
        setTimeout(() => {
          const match=Array.from(rows.querySelectorAll('button')).find(b => (b.title || b.textContent).trim().toLowerCase()===name.toLowerCase());
          if(match)match.click();
        },400);
      },200);
      return true;
    })()'''.replace('NAME',value)

def launch_search(name):
    name=str(name).strip()[:120]
    if not name:raise ValueError('Enter an item name.')
    command=([sys.executable] if getattr(sys,'frozen',False) else [sys.executable,os.path.join(os.path.dirname(__file__),'app.py')])
    startup=None
    if sys.platform=='win32':
        startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=1
    return subprocess.Popen(command+['--mesowatch-search',name],startupinfo=startup,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))

def run_browser(name):
    import webview
    webview.settings['ALLOW_FILE_URLS']=False
    webview.settings['ALLOW_DOWNLOADS']=False
    webview.settings['IGNORE_SSL_ERRORS']=False
    window=webview.create_window('MesoWatch · '+name[:120],ORIGIN,width=1080,height=760,min_size=(620,480),text_select=True)
    def loaded():
        if urlsplit(window.get_current_url() or '').netloc=='meso.watch':
            window.evaluate_js(search_script(name))
    window.events.loaded+=loaded
    webview.start(gui='edgechromium',private_mode=True)
