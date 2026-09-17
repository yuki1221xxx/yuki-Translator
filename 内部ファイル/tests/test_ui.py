import unittest,tempfile,json,tkinter as tk
from pathlib import Path
from unittest.mock import patch
from app import App
from accuracy import HEAVY_MODEL

class UiTests(unittest.TestCase):
    def test_language_and_position_survive_restart_without_changing_direction(self):
        with tempfile.TemporaryDirectory() as folder,patch('app.DATA_DIR',Path(folder)):
            root=tk.Tk();app=App(root)
            try:
                app.source.set('ja');app.target.set('ko');app.model.set(HEAVY_MODEL)
                app.ui_language.set('ko');app.change_language()
                app.position.set('top_right');app.offset_x.set(-80);app.offset_y.set(40)
                app.update_overlay();root.update();app.save_settings()
                data=json.loads(app.settings_path.read_text(encoding='utf-8'))
                self.assertEqual((data['source'],data['target']),('ja','ko'))
                self.assertEqual(data['ui_language'],'ko')
                self.assertEqual(data['position'],'top_right')
            finally:app.close()
            root=tk.Tk();app=App(root,persist=False)
            try:
                self.assertEqual(app.model.get(),HEAVY_MODEL)
                self.assertEqual(app.ui_language.get(),'ko')
                self.assertEqual((app.source.get(),app.target.get()),('ja','ko'))
                self.assertEqual(app.offset_x.get(),-80)
                self.assertEqual(app.position.get(),'top_right')
                app.ui_language.set('en');app.change_language()
                self.assertEqual(app.start_button.cget('text'),'▶ Start translation')
                self.assertEqual((app.source.get(),app.target.get()),('ja','ko'))
            finally:app.close()

    def test_output_switches_are_independent_and_subtitles_stay_off(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as folder,patch('app.DATA_DIR',Path(folder)):
            root=tk.Tk();app=App(root,persist=False)
            try:
                app.speak.set(False);app.update_speech()
                app.subtitle_enabled.set(True);app.update_subtitle_output();root.update()
                self.assertFalse(app.speaker.enabled)
                self.assertEqual(app.overlay.state(),'normal')
                app.subtitle_enabled.set(False);app.update_subtitle_output()
                app.events.put(('result',('hello','こんにちは')));app.poll();root.update()
                self.assertEqual(app.overlay.state(),'withdrawn')
                self.assertIn('こんにちは',app.history.get('1.0','end'))
                app.movable.set(True);app.update_overlay();root.update()
                self.assertEqual(app.overlay.state(),'withdrawn')
                app.speak.set(True);app.update_speech()
                self.assertTrue(app.speaker.enabled)
                self.assertFalse(app.subtitle_enabled.get())
                app.tabs.select(1);root.update()
                app.preview_move(SimpleNamespace(x=app.preview.winfo_width()/2,y=app.preview.winfo_height()/2))
                self.assertEqual(app.position.get(),'custom')
                self.assertIsNotNone(app.custom_position)
                self.assertEqual(app.overlay.state(),'withdrawn')
            finally:app.close()

    def test_caption_only_start_does_not_require_audio_output(self):
        with tempfile.TemporaryDirectory() as folder,patch('app.DATA_DIR',Path(folder)),patch('app.Session') as session:
            root=tk.Tk();app=App(root,persist=False)
            try:
                app.devices=[dict(kind='process',index=None,name='game.exe',pid=123,created=42)]
                app.input_box['values']=['Game'];app.input_box.current(0)
                app.outputs=[];app.output_box['values']=[];app.output_box.set('')
                app.speak.set(False);app.update_speech();app.subtitle_enabled.set(False)
                app.start();root.update()
                config=session.call_args.args[0]
                self.assertEqual(config['process_pid'],123)
                self.assertIsNone(config['output'])
                session.return_value.thread.start.assert_called_once()
                self.assertEqual(app.overlay.state(),'withdrawn')
            finally:app.close()

    def test_legacy_windows_speech_migrates_to_local_ai(self):
        with tempfile.TemporaryDirectory() as folder,patch('app.DATA_DIR',Path(folder)):
            Path(folder,'settings.json').write_text(json.dumps({'source':'日本語','target':'한국어 / 韓国語','backend':'Windows（ローカル）','schema_version':4}),encoding='utf-8')
            root=tk.Tk();app=App(root,persist=False)
            try:
                self.assertEqual((app.source.get(),app.target.get()),('ja','ko'))
                self.assertEqual(app.backend.get(),'local')
                self.assertEqual(app.speaker.backend,'local')
            finally:app.close()

if __name__=='__main__':unittest.main()
