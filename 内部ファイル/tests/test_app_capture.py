import queue
import unittest
from unittest.mock import Mock, patch
from process_audio import select_application_roots
from engine import Session


class AppCaptureTests(unittest.TestCase):
    def test_browsers_collapse_to_root_and_game_keeps_its_own_process(self):
        def row(pid, parent, name, created=1):
            return dict(pid=pid, ppid=parent, name=name, create_time=created, username='user')
        rows = {1:row(1,0,'chrome.exe'), 2:row(2,1,'chrome.exe',2),
                3:row(3,2,'chrome.exe',3), 4:row(4,0,'steam.exe'),
                5:row(5,4,'game.exe',2), 6:row(6,0,'YukiTranslator.exe'),
                7:row(7,0,'voice-helper.exe'), 8:row(8,0,'service.exe')}
        rows[8]['username']='SYSTEM'
        result = select_application_roots(rows,{3,5,6},6,False,'user')
        self.assertEqual({r['pid'] for r in result},{1,5})
        result = select_application_roots(rows,{3,5,6},6,True,'user')
        self.assertIn(7,{r['pid'] for r in result})
        self.assertNotIn(8,{r['pid'] for r in result})

    def test_pid_reuse_is_rejected_before_capture(self):
        events=queue.Queue();speaker=Mock()
        session=Session({'process_pid':123,'process_created':1},events,speaker)
        with patch('psutil.Process') as process,patch('engine.ProcessCapture') as capture:
            process.return_value.create_time.return_value=2
            session.capture_process()
            capture.assert_not_called()
        self.assertTrue(session.stop.is_set())
        kind,msg=events.get_nowait()
        self.assertEqual(kind,'error')


if __name__=='__main__':unittest.main()
