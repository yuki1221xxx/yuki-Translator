"""Explicit hardware integration check: two quiet tones from separate processes."""
import json
from pathlib import Path
import subprocess
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from process_audio import ProcessCapture

PLAYER = '''
import sys
import numpy as np
import pyaudiowpatch as pa
with pa.PyAudio() as p:
    host = p.get_host_api_info_by_type(pa.paWASAPI)
    d = p.get_device_info_by_index(host['defaultOutputDevice'])
    rate = int(d['defaultSampleRate'])
    stream = p.open(format=pa.paFloat32, channels=2, rate=rate, output=True, output_device_index=d['index'])
    print('READY', flush=True)
    sys.stdin.readline()
    signal = (.015 * np.sin(2*np.pi*float(sys.argv[1])*np.arange(rate*4)/rate)).astype(np.float32)
    for offset in range(0, len(signal), 960):
        stream.write(np.repeat(signal[offset:offset+960, None], 2, axis=1).tobytes())
    stream.close()
'''


def main():
    players = []
    result = {}
    errors = []
    try:
        for freq in (440, 880):
            proc = subprocess.Popen([sys.executable, '-c', PLAYER, str(freq)], stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                    creationflags=subprocess.CREATE_NO_WINDOW)
            players.append(proc)
            assert proc.stdout.readline().strip() == 'READY'

        def capture():
            try:
                with ProcessCapture(players[0].pid) as stream:
                    players[1].stdin.write('GO\n')
                    players[1].stdin.flush()
                    baseline = []
                    end = time.monotonic() + .6
                    while time.monotonic() < end:
                        baseline.extend(stream.read())
                    result['other_process_only_peak'] = float(np.max(np.abs(baseline))) if baseline else 0
                    players[0].stdin.write('GO\n')
                    players[0].stdin.flush()
                    samples = []
                    end = time.monotonic() + 1.5
                    while time.monotonic() < end:
                        samples.extend(stream.read())
                    values = np.asarray(samples)
                    assert len(values) > 24000, 'No captured audio'
                    frequencies = np.fft.rfftfreq(len(values), 1/48000)
                    spectrum = np.abs(np.fft.rfft(values * np.hanning(len(values))))
                    first = float(spectrum[np.abs(frequencies - 440) < 3].max())
                    second = float(spectrum[np.abs(frequencies - 880) < 3].max())
                    result.update(frames=len(values), selected_tone=first, excluded_tone=second)
                    assert result['other_process_only_peak'] < .0001, result
                    assert first > 1 and second < first * .02, result
                result['ok'] = True
            except BaseException as exc:
                errors.append(exc)
        worker = threading.Thread(target=capture)
        worker.start()
        worker.join(20)
        assert not worker.is_alive(), 'Capture did not stop'
        if errors:
            raise errors[0]
        print(json.dumps(result, indent=2))
    finally:
        for proc in players:
            if proc.poll() is None:
                proc.terminate()
            proc.wait(timeout=5)


if __name__ == '__main__':
    main()
