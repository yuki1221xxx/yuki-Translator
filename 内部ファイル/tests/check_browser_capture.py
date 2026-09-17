"""Launch an isolated Chrome test profile and capture only its process tree."""
import base64,json,queue,subprocess,sys,threading,time
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import psutil,numpy as np
from scipy.signal import resample_poly
from engine import Session
from process_audio import application_processes
from accuracy import load_recognizer,recognize,DirectTranslator

root=Path(__file__).resolve().parent
chrome=Path('C:/Program Files/Google/Chrome/Application/chrome.exe')
fixture=base64.b64encode((root/'fixtures/ko_hello_m.mp3').read_bytes()).decode()
page=root/'browser-capture-test.html'
page.write_text('<title>Translator audio test</title><audio id="a" src="data:audio/mpeg;base64,'+fixture+'"></audio><script>const a=document.getElementById("a");a.volume=.2;setInterval(()=>{a.currentTime=0;a.play().catch(()=>{});},3000);</script>')
model,_=load_recognizer()
proc=subprocess.Popen([str(chrome),'--headless=new','--no-first-run','--no-default-browser-check','--disable-background-networking','--disable-sync','--autoplay-policy=no-user-gesture-required','--user-data-dir='+str(root/'browser-test-profile'),page.as_uri()],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
session=None
try:
    owner=psutil.Process(proc.pid)
    config=dict(input_kind='process',process_pid=proc.pid,process_created=owner.create_time(),threshold=.002)
    session=Session(config,queue.Queue(),Mock())
    worker=threading.Thread(target=session.capture);worker.start()
    audio,rate=session.audio.get(timeout=22)
    session.stop.set();worker.join(3)
    apps=application_processes()
    assert any(a['pid']==proc.pid for a in apps),'Chrome was missing from the app selector'
    text,info=recognize(model,resample_poly(audio,1,3))
    assert rate==48000 and info.language=='ko' and '안녕' in text,(rate,text,info)
    translated=DirectTranslator().translate(text,'ko','ja')
    assert 'こんにちは' in translated,translated
    result=dict(ok=True,application='Chrome (isolated headless profile)',captured_frames=len(audio),peak=float(np.max(np.abs(audio))),recognized=text,translated=translated)
    (root/'browser-capture-v6.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))
finally:
    if session:session.stop.set()
    if proc.poll() is None:
        children=psutil.Process(proc.pid).children(recursive=True)
        proc.terminate()
        for child in children:
            try:child.terminate()
            except psutil.NoSuchProcess:pass
        proc.wait(timeout=5)
