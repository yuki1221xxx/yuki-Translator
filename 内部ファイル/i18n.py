"""UI messages use stable keys; changing the UI never changes translation direction."""
from dataclasses import dataclass, field

UI_LANGUAGES = {'ja': '日本語', 'ko': '한국어', 'en': 'English'}
TEXT = {
    'title': ('yuki Translator', 'yuki Translator', 'yuki Translator'),
    'ui_language': ('表示言語', '화면 언어', 'App language'),
    'tab_voice': ('通話・翻訳', '통화 · 번역', 'Voice & translation'),
    'tab_subtitles': ('字幕・表示位置', '자막 · 표시 위치', 'Subtitles & position'),
    'input': ('音声入力', '음성 입력', 'Audio input'),
    'source': ('対象言語', '입력 언어', 'Source language'),
    'target': ('翻訳先の言語', '번역 언어', 'Translate into'),
    'output': ('読み上げ出力', '음성 출력 장치', 'Speech output'),
    'model': ('音声認識モデル', '음성 인식 모델', 'Speech recognition model'),
    'model_light': ('Qwen3-ASR 0.6B — 軽量', 'Qwen3-ASR 0.6B — 가벼움', 'Qwen3-ASR 0.6B — Light'),
    'model_heavy': ('Qwen3-ASR 1.7B — 少し重め', 'Qwen3-ASR 1.7B — 조금 무거움', 'Qwen3-ASR 1.7B — Somewhat heavier'),
    'model_hint': ('両モデルともCPU動作。1.7Bはメモリ使用量と待ち時間が増えます。', '두 모델 모두 CPU에서 실행됩니다. 1.7B는 메모리와 처리 시간이 더 필요합니다.', 'Both models run on CPU. 1.7B uses more memory and takes longer.'),
    'backend': ('読み上げ方式', '음성 합성 방식', 'Speech synthesis'),
    'local': ('ローカルAI（日・韓・英）', '로컬 AI (일본어 · 한국어 · 영어)', 'Local AI (Japanese / Korean / English)'),
    'online': ('オンライン（翻訳文を送信）', '온라인 (번역문 전송)', 'Online (sends translated text)'),
    'auto': ('自動判定（日・韓・英）', '자동 감지 (일본어 · 한국어 · 영어)', 'Auto-detect (Japanese / Korean / English)'),
    'ja': ('日本語', '일본어', 'Japanese'),
    'ko': ('韓国語', '한국어', 'Korean'),
    'en': ('英語', '영어', 'English'),
    'speak': ('翻訳を読み上げる', '번역문 읽어주기', 'Read translations aloud'),
    'volume': ('音量', '음량', 'Volume'),
    'test_speech': ('読み上げテスト', '음성 출력 테스트', 'Test speech'),
    'guard': ('読み上げ中はマイク入力を一時停止', '음성 출력 중 마이크 입력 일시 중지', 'Pause microphone input during speech output'),
    'threshold': ('音声検出しきい値', '음성 감지 기준값', 'Speech detection threshold'),
    'threshold_hint': ('小声 ← → 雑音を除く', '작은 목소리 ← → 잡음 제외', 'Quiet voices ← → Reject noise'),
    'start': ('▶ 翻訳開始', '▶ 번역 시작', '▶ Start translation'),
    'stop': ('■ 停止', '■ 중지', '■ Stop'),
    'install': ('モデル導入', '모델 설치', 'Install models'),
    'refresh': ('デバイス再取得', '장치 새로고침', 'Refresh devices'),
    'guide': ('接続ガイド', '연결 안내', 'Connection guide'),
    'show_subtitles': ('字幕を表示', '자막 표시', 'Show subtitles'),
    'hide_subtitles': ('字幕を隠す', '자막 숨기기', 'Hide subtitles'),
    'font_size': ('字幕の文字サイズ', '자막 글자 크기', 'Subtitle font size'),
    'opacity': ('文字の不透明度', '글자 불투명도', 'Text opacity'),
    'monitor': ('表示する画面', '표시할 화면', 'Display'),
    'display_name': ('画面 {number}（{width} × {height}）', '화면 {number} ({width} × {height})', 'Display {number} ({width} × {height})'),
    'position': ('字幕の表示位置', '자막 위치', 'Subtitle position'),
    'top_left': ('左上', '왼쪽 위', 'Top left'), 'top_center': ('上中央', '위 중앙', 'Top center'), 'top_right': ('右上', '오른쪽 위', 'Top right'),
    'center_left': ('左中央', '왼쪽 중앙', 'Center left'), 'center_center': ('中央', '중앙', 'Center'), 'center_right': ('右中央', '오른쪽 중앙', 'Center right'),
    'bottom_left': ('左下', '왼쪽 아래', 'Bottom left'), 'bottom_center': ('下中央', '아래 중앙', 'Bottom center'), 'bottom_right': ('右下', '오른쪽 아래', 'Bottom right'),
    'custom': ('自由配置', '자유 배치', 'Custom position'),
    'offset_x': ('左右の調整（px）', '좌우 조정 (px)', 'Horizontal offset (px)'),
    'offset_y': ('上下の調整（px）', '상하 조정 (px)', 'Vertical offset (px)'),
    'move_subtitles': ('字幕をドラッグで移動する', '자막을 드래그하여 이동', 'Drag subtitles to move'),
    'show_original': ('字幕に認識原文も表示', '인식된 원문도 표시', 'Also show recognized text'),
    'subtitle_hint': ('背景・枠は透明です。通常はクリックが背後のアプリへ通ります。移動をONにすると文字をドラッグできます。位置は自動保存します。', '배경과 테두리는 투명합니다. 기본적으로 클릭은 뒤의 앱으로 전달됩니다. 이동을 켜면 글자를 드래그할 수 있습니다. 위치는 자동 저장됩니다.', 'The background and frame are transparent. Clicks normally pass through to the app behind. Enable dragging to move the text. Position is saved automatically.'),
    'subtitle_preview': ('翻訳した字幕がここに表示されます', '번역된 자막이 여기에 표시됩니다', 'Your translated subtitles appear here'),
    'idle': ('待機中 • 入力と翻訳方向を選んでください', '대기 중 · 입력과 번역 언어를 선택하세요', 'Ready · Choose an input and translation direction'),
    'level': ('入力音量', '입력 음량', 'Input level'),
    'waiting': ('発話待ち', '발화 대기 중', 'Waiting for speech'),
    'backend_pending': ('ローカル認識・直接翻訳 • モデルの準備待ち', '로컬 인식 · 직접 번역 · 모델 준비 대기', 'Local recognition & direct translation · Models not loaded'),
    'backend_status': ('認識: {model} / CPU • 日韓直接翻訳', '인식: {model} / CPU · 일한 직접 번역', 'Recognition: {model} / CPU · Direct Japanese–Korean translation'),
    'discord_device': ('{name} 専用（PID {pid}）', '{name} 전용 (PID {pid})', '{name} only (PID {pid})'),
    'discord_missing': ('Discord専用（起動後に再取得）', 'Discord 전용 (실행 후 새로고침)', 'Discord only (launch Discord, then refresh)'),
    'loopback': ('再生音・全アプリ', '재생 오디오 · 모든 앱', 'Playback · All apps'), 'mic': ('マイク', '마이크', 'Microphone'),
    'device_error': ('デバイス取得失敗: {detail}', '장치를 불러오지 못했습니다: {detail}', 'Cannot load devices: {detail}'),
    'device_required': ('音声入力と読み上げ出力を選択してください。', '음성 입력과 출력 장치를 선택하세요.', 'Choose an audio input and speech output.'),
    'output_missing': ('読み上げ出力が見つかりません。デバイスを再取得してください。', '음성 출력 장치를 찾을 수 없습니다. 장치를 새로고침하세요.', 'Speech output not found. Refresh the devices.'),
    'speech_loading': ('読み上げ音声を準備中…', '음성 합성 준비 중…', 'Preparing speech…'),
    'speech_test': ('選択した翻訳先の言語でテスト音声を再生します。', '선택한 번역 언어로 테스트 음성을 재생합니다.', 'Playing a test in the selected target language.'),
    'speech_disabled': ('読み上げをONにし、音量を上げてください。', '음성 출력을 켜고 음량을 높여 주세요.', 'Enable speech output and turn up the volume.'),
    'speech_failed': ('読み上げ失敗: {detail}', '음성 출력 실패: {detail}', 'Speech output failed: {detail}'),
    'tts_missing': ('読み上げモデルがありません。「モデル導入」を実行してください。', '음성 합성 모델이 없습니다. 모델 설치를 실행하세요.', 'Speech model is missing. Use Install models.'),
    'tts_empty': ('読み上げ音声を生成できませんでした。', '음성을 생성하지 못했습니다.', 'No speech audio was generated.'),
    'asr_missing': ('認識モデルがありません。「モデル導入」を実行してください。', '인식 모델이 없습니다. 모델 설치를 실행하세요.', 'Recognition model is missing. Use Install models.'),
    'translation_missing': ('翻訳モデルがありません。「モデル導入」を実行してください。', '번역 모델이 없습니다. 모델 설치를 실행하세요.', 'Translation model is missing. Use Install models.'),
    'stopping': ('停止処理中…', '중지하는 중…', 'Stopping…'), 'stopped': ('停止しました', '중지되었습니다', 'Stopped'),
    'install_failed': ('導入失敗: {detail}', '설치 실패: {detail}', 'Installation failed: {detail}'),
    'install_asr': ('認識モデル {model} を確認・導入中…', '인식 모델 {model} 확인 및 설치 중…', 'Checking / installing recognition model {model}…'),
    'install_translation': ('直接翻訳モデルを確認・導入中…', '직접 번역 모델 확인 및 설치 중…', 'Checking / installing the direct translation model…'),
    'install_tts': ('ローカル読み上げモデルを確認・導入中…', '로컬 음성 합성 모델 확인 및 설치 중…', 'Checking / installing the local speech model…'),
    'installed': ('モデルの準備が完了しました', '모델 준비가 완료되었습니다', 'Models are ready'),
    'setup_title': ('初回セットアップ', '첫 실행 설정', 'First-time setup'),
    'setup_intro': (
        '高精度な音声認識・翻訳・読み上げに必要なローカルAIをダウンロードします。完了後はオフラインで利用できます。',
        '고정밀 음성 인식, 번역, 음성 출력에 필요한 로컬 AI를 다운로드합니다. 완료 후에는 오프라인으로 사용할 수 있습니다.',
        'Downloading the local AI models required for accurate recognition, translation, and speech. After this finishes, the app can work offline.'),
    'setup_progress': ('モデルの確認を開始しています…', '모델 확인을 시작하는 중…', 'Starting model check…'),
    'setup_failed': ('初回セットアップに失敗しました: {detail}', '첫 실행 설정 실패: {detail}', 'First-time setup failed: {detail}'),
    'update_downloading': ('更新 v{version} をダウンロード中…', '업데이트 v{version} 다운로드 중…', 'Downloading update v{version}…'),
    'update_download_progress': ('更新 v{version} をダウンロード中… {percent}%', '업데이트 v{version} 다운로드 중… {percent}%', 'Downloading update v{version}… {percent}%'),
    'update_ready_title': ('更新の準備ができました', '업데이트 준비 완료', 'Update ready'),
    'update_ready_body': (
        'v{version} をインストールします。アプリを再起動して更新してよろしいですか？',
        'v{version}을 설치합니다. 앱을 다시 시작하여 업데이트할까요?',
        'Version {version} is ready. Restart the app and install it now?'),
    'update_failed': ('自動更新に失敗しました: {detail}', '자동 업데이트 실패: {detail}', 'Automatic update failed: {detail}'),
    'original': ('認識原文', '인식 원문', 'Recognized text'),
    'loading': ('ローカルモデルを読み込み中…', '로컬 모델을 불러오는 중…', 'Loading local models…'),
    'unclear': ('明瞭な発話を認識できなかったため表示を保留しました。', '명확한 발화를 인식하지 못해 표시를 보류했습니다.', 'No clear speech was recognized; subtitles were withheld.'),
    'unknown_language': ('言語を確定できません。少し長めに話してください。', '언어를 확인할 수 없습니다. 조금 더 길게 말해 주세요.', 'Language could not be determined. Try a longer phrase.'),
    'filtered_language': ('{language}を検出 • 対象言語と異なるため除外', '{language} 감지 · 선택한 입력 언어와 달라 제외됨', '{language} detected · Excluded by source language filter'),
    'same_language': ('{language}を検出 • 翻訳先と同じため原文表示', '{language} 감지 · 번역 언어와 같아 원문 표시', '{language} detected · Showing original text'),
    'translation_direction': ('{language} → {target}', '{language} → {target}', '{language} → {target}'),
    'language_info': ('{reason}（認識文から判定）', '{reason} (인식된 텍스트로 판단)', '{reason} (determined from recognized text)'),
    'session_error': ('翻訳処理エラー: {detail}', '번역 처리 오류: {detail}', 'Translation error: {detail}'),
    'input_active': ('入力中: {name}', '입력 중: {name}', 'Listening: {name}'),
    'backlog': ('処理が追いつかないため古い音声をスキップしました。0.6Bモデルも利用できます。', '처리 지연으로 오래된 음성을 건너뛰었습니다. 0.6B 모델도 사용할 수 있습니다.', 'Older audio was skipped because processing is behind. Try the 0.6B model.'),
    'capture_error': ('音声入力エラー: {detail}', '음성 입력 오류: {detail}', 'Audio input error: {detail}'),
    'discord_select': ('Discordを起動し、デバイス再取得で対象を選んでください。', 'Discord를 실행하고 장치를 새로고침한 후 선택하세요.', 'Launch Discord, refresh devices, then select it.'),
    'discord_restarted': ('Discordが再起動しています。デバイスを再取得してください。', 'Discord가 다시 시작되었습니다. 장치를 새로고침하세요.', 'Discord restarted. Refresh the devices.'),
    'discord_connected': ('Discord専用入力に接続 • {name} / PID {pid} • 発話待ち', 'Discord 전용 입력 연결 · {name} / PID {pid} · 발화 대기', 'Connected to Discord audio · {name} / PID {pid} · Waiting for speech'),
    'discord_closed': ('Discordが終了しました。再起動後に入力を選び直してください。', 'Discord가 종료되었습니다. 다시 실행한 후 입력을 선택하세요.', 'Discord closed. Restart it and select the input again.'),
    'capture_windows': ('アプリ別の音声取得にはWindowsビルド20348以降が必要です。', '앱별 오디오 입력에는 Windows 빌드 20348 이상이 필요합니다.', 'Per-app audio capture requires Windows build 20348 or later.'),
    'capture_timeout': ('アプリ音声の初期化がタイムアウトしました。', '앱 오디오 초기화 시간이 초과되었습니다.', 'App audio initialization timed out.'),
    'error': ('エラー', '오류', 'Error'),
    'guide_text': (
        '相手の声を翻訳: Discord専用入力 → 対象言語は自動 → 翻訳先を選択。\n\n自分の声を送信: マイク入力 → 日本語から韓国語。仮想ケーブルを別途導入し、読み上げ出力を CABLE Input、Discord入力を CABLE Output に設定してください。\n\nローカルAI音声は日韓英に対応し、Windows追加音声やネット接続は不要です。「読み上げテスト」で出力を確認できます。\n\n字幕は「字幕・表示位置」で設定できます。背景は透明で、通常はクリックが背後に通ります。ゲームはボーダーレス表示を推奨します。\n\nDiscord専用入力はDiscordの再生音だけを取得します。マイクや他アプリは含みません。一度に1方向の翻訳です。',
        '상대방 음성 번역: Discord 전용 입력 → 입력 언어 자동 → 번역 언어 선택.\n\n내 음성 전송: 마이크 입력 → 일본어에서 한국어. 가상 오디오 케이블을 별도로 설치하고 음성 출력은 CABLE Input, Discord 입력은 CABLE Output으로 설정하세요.\n\n로컬 AI 음성은 일본어·한국어·영어를 지원합니다. Windows 추가 음성이나 인터넷이 필요하지 않습니다. 음성 출력 테스트로 확인하세요.\n\n자막 위치는 자막 탭에서 설정합니다. 배경은 투명하며 클릭은 뒤로 전달됩니다. 게임은 테두리 없는 창 모드를 권장합니다.\n\nDiscord 전용 입력은 Discord 재생음만 가져옵니다. 마이크와 다른 앱은 포함하지 않습니다. 한 번에 한 방향으로 번역합니다.',
        'Translate your friend: Discord-only input → Auto-detect → Choose a target language.\n\nSend your voice: Microphone → Japanese to Korean. Install a virtual audio cable separately. Set speech output to CABLE Input and Discord input to CABLE Output.\n\nLocal AI speech supports Japanese, Korean and English without extra Windows voices or an internet connection. Use Test speech to check your output.\n\nSet subtitle position on the Subtitles tab. The background is transparent and clicks pass through. Use borderless window mode for games.\n\nDiscord-only input captures Discord playback, excluding microphones and other apps. Translation runs in one direction at a time.'),
}


TEXT.update({
    'tab_voice': ('翻訳', '번역', 'Translate'),
    'tab_subtitles': ('字幕レイアウト', '자막 레이아웃', 'Subtitle layout'),
    'tab_settings': ('設定', '설정', 'Settings'),
    'app_select': ('取得するアプリを起動し、一覧を更新して選択してください。', '앱을 실행하고 목록을 새로고침한 후 선택하세요.', 'Launch the app, refresh the list, and select it.'),
    'app_restarted': ('選択したアプリが終了・再起動しました。一覧を更新してください。', '선택한 앱이 종료되거나 다시 시작되었습니다. 목록을 새로고침하세요.', 'The selected app closed or restarted. Refresh the list.'),
    'app_closed': ('選択したアプリが終了しました。', '선택한 앱이 종료되었습니다.', 'The selected app has closed.'),
    'app_connected': ('音声を取得中 · {name}', '오디오 수신 중 · {name}', 'Listening to {name}'),
    'app_missing': ('{name}（起動後に一覧を更新）', '{name} (실행 후 새로고침)', '{name} (launch, then refresh)'),
    'input': ('音声を取得するアプリ / マイク', '오디오를 가져올 앱 / 마이크', 'Capture audio from'),
    'capture_hint': ('ブラウザは他タブの音声、ゲームはBGM・効果音も含みます。', '브라우저는 다른 탭의 소리, 게임은 배경음과 효과음도 포함합니다.', 'Browser audio includes other tabs. Game audio includes music and effects.'),
    'background_apps': ('バックグラウンドのプロセスも一覧に表示', '백그라운드 프로세스도 표시', 'Also list background processes'),
    'speak': ('音声読み上げ', '음성 출력', 'Speech output'),
    'subtitles_on': ('字幕', '자막', 'Subtitles'),
    'speech_hint': ('翻訳を選択した出力先に読み上げ', '선택한 장치로 번역 음성 재생', 'Read translations on your chosen output'),
    'subtitle_output_hint': ('画面に透明な字幕を表示', '화면에 투명한 자막 표시', 'Show transparent captions on your screen'),
    'preview_hint': ('プレビュー内をクリック、または字幕をドラッグして配置', '미리보기를 클릭하거나 자막을 드래그하여 배치', 'Click in the preview or drag the caption to position it'),
    'preview_sample': ('ここに字幕が表示されます', '여기에 자막이 표시됩니다', 'Your subtitles appear here'),
    'move_subtitles': ('画面上で直接移動', '화면에서 직접 이동', 'Move directly on screen'),
    'subtitle_off_hint': ('字幕はOFFです。位置の調整はプレビュー内で行えます。', '자막이 꺼져 있습니다. 미리보기에서 위치를 조정할 수 있습니다.', 'Subtitles are off. You can still adjust the position in the preview.'),
    'subtitle_hint': ('プレビューで配置 → 自動保存。直接移動をONにすると、画面上の枠をつかんで動かせます。', '미리보기에서 배치하면 자동 저장됩니다. 직접 이동을 켜면 화면의 상자를 드래그할 수 있습니다.', 'Position in the preview; changes save automatically. Enable direct movement to drag the frame on screen.'),
    'recent': ('翻訳ログ', '번역 기록', 'Transcript'),
    'empty_history': ('翻訳した会話がここに表示されます', '번역된 대화가 여기에 표시됩니다', 'Your translated conversation appears here'),
    'on': ('ON', 'ON', 'ON'), 'off': ('OFF', 'OFF', 'OFF'),
    'subtitle_disabled': ('字幕はOFFです', '자막이 꺼져 있습니다', 'Subtitles are off'),
    'guide_text': (
        '音声を取得するアプリからDiscord・Chrome・ゲームなどを選択してください。見つからなければアプリを起動して一覧を更新します。バックグラウンドのVCアプリは設定から一覧に追加できます。選択したアプリと子プロセスの再生音を取得します。ブラウザは他タブ、ゲームはBGM・効果音も含みます。\n\n音声読み上げと字幕は独立したスイッチです。両方OFFでも翻訳ログは残ります。設定変更のために翻訳を止める必要はありません。\n\n字幕レイアウトのプレビューをクリック・ドラッグして配置できます。画面上で直接移動をONにすると枠全体をつかめます。OFFに戻すと文字だけの透明字幕になり、クリックが背後に通ります。ゲームはボーダーレス表示を使用してください。\n\n自分の声を送るにはマイクを選び、仮想ケーブルを別途導入して読み上げ出力をCABLE Input、Discord等の入力をCABLE Outputに設定します。',
        'Discord, Chrome, 게임 등 오디오를 가져올 앱을 선택하세요. 앱이 없으면 실행 후 목록을 새로고침하세요. 설정에서 백그라운드 프로세스도 표시할 수 있습니다. 선택한 앱과 하위 프로세스의 소리를 가져옵니다. 브라우저는 다른 탭, 게임은 음악과 효과음도 포함합니다.\n\n음성 출력과 자막은 독립적으로 켜고 끌 수 있습니다. 둘 다 꺼도 번역 기록은 표시됩니다.\n\n자막 레이아웃 미리보기를 클릭하거나 드래그해 배치하세요. 화면에서 직접 이동을 켜면 상자를 드래그할 수 있습니다. 끄면 글자만 남고 클릭이 뒤로 전달됩니다. 게임은 테두리 없는 창 모드를 사용하세요.\n\n내 음성을 전송하려면 마이크를 선택하고 가상 오디오 케이블을 별도로 설치하세요. 음성 출력은 CABLE Input, 통화 앱 입력은 CABLE Output으로 설정하세요.',
        'Choose Discord, Chrome, a game, or another app as the audio source. Launch the app and refresh if it is missing. Settings can also list background processes. Capture includes the selected app and its child processes. Browsers include other tabs; games include music and effects.\n\nSpeech and subtitles have independent switches and can change while translation runs. With both off, the transcript still updates.\n\nClick or drag in the subtitle preview to place your captions. Enable direct movement to drag the frame on screen. Turn it off for transparent, click-through text. Use borderless window mode in games.\n\nTo send your own translated voice, select a microphone and install a virtual audio cable separately. Set speech output to CABLE Input and your call app input to CABLE Output.'),
})


@dataclass(frozen=True)
class Message:
    key: str
    params: dict = field(default_factory=dict)

    def __str__(self):
        return render(self, 'ja')


class UserMessageError(RuntimeError):
    def __init__(self, key, **params):
        self.message = Message(key, params)
        super().__init__(str(self.message))


def message(key, **params):
    return Message(key, params)


def render(value, language='ja'):
    if isinstance(value, UserMessageError):
        value = value.message
    if not isinstance(value, Message):
        return str(value)
    template = TEXT[value.key][{'ja': 0, 'ko': 1, 'en': 2}.get(language, 0)]
    return template.format(**{k: render(v, language) for k, v in value.params.items()})


def tr(key, language='ja', **params):
    return render(message(key, **params), language)
