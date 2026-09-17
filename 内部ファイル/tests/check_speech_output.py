"""Explicit hardware regression: local Korean speech, live volume and cancellation."""
import json,os,sys,threading,time,queue,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from scipy.signal import resample_poly
from accuracy import DirectTranslator,load_recognizer,recognize
from speech import Speaker,LocalVoice,output_devices
from process_audio import ProcessCapture


def main():
    model,_=load_recognizer()
    text=DirectTranslator().translate('こんにちは。','ja','ko')
    samples,rate=LocalVoice().generate(text,'ko')
    speaker=Speaker(queue.Queue())
    output=output_devices()[0][0]
    results=[]
    try:
        for volume in [0,20,40]:
            ready=threading.Event();blocks=[];errors=[]
            def capture():
                try:
                    with ProcessCapture(os.getpid()) as stream:
                        ready.set()
                        until=time.monotonic()+len(samples)/rate+.8
                        while time.monotonic()<until:
                            block=stream.read()
                            if len(block):blocks.append(block)
                except Exception as exc:errors.append(exc);ready.set()
            thread=threading.Thread(target=capture);thread.start();assert ready.wait(10)
            assert not errors,errors
            speaker.volume=volume
            speaker.play_audio(samples,rate,output,speaker.generation)
            thread.join(10);assert not thread.is_alive() and not errors,errors
            audio=np.concatenate(blocks) if blocks else np.zeros(1,np.float32)
            rms=float(np.sqrt(np.mean(audio*audio)));peak=float(np.max(np.abs(audio)))
            results.append(dict(volume=volume,rms=rms,peak=peak))
            if volume==0:assert peak<.0001
            else:
                assert peak>.001
                divisor=math.gcd(48000,16000)
                recognized,info=recognize(model,resample_poly(audio,16000//divisor,48000//divisor))
                assert info.language=='ko' and '안녕' in recognized,(recognized,info)
                results[-1]['recognized']=recognized
        assert 1.7<results[2]['peak']/results[1]['peak']<2.3,results
        speaker.cancel();started=time.monotonic()
        speaker.play_audio(samples,rate,output,speaker.generation-1)
        assert time.monotonic()-started<1,'Cancelled playback did not return promptly'
        Path(__file__).with_name('speech-output-v5.json').write_text(json.dumps(dict(ok=True,text=text,results=results),ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(results,ensure_ascii=False))
    finally:
        speaker.shutdown.set();speaker.thread.join(3)

if __name__=='__main__':main()
