# Code2Video pipeline

Pipeline tích hợp:

- VieNeu-TTS tạo voice tiếng Việt.
- faster-whisper lấy word-level timestamps từ audio đã tạo.
- Logic SRT của `srt-whiteboard-animation` parse cue và chia scene.
- HyperFrames render composition HTML thành MP4.

## Kiến trúc

```text
script.txt / script.srt
        |
        v
  VieNeu-TTS -> voiceover.wav
        |
        v
 faster-whisper -> word timestamps
        |
        v
 timeline.json + index.html
        |
        v
 npx hyperframes render -> output.mp4
```

`timeline.json` là contract chung. Timestamp luôn là milliseconds; HyperFrames nhận các giá trị tương ứng ở giây.

## Cài đặt

Yêu cầu Python 3.10+, Node.js/npm và HyperFrames CLI.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[tts,alignment,dev]'
```

VieNeu tự tải model khi khởi tạo lần đầu. faster-whisper cũng tải Whisper model ở lần chạy đầu.

## FFmpeg và ffprobe

HyperFrames và Studio dùng FFmpeg để đọc/ghi media. Trên Ubuntu/Debian, cài bản hệ thống:

```bash
sudo apt update
sudo apt install -y ffmpeg
ffmpeg -version
ffprobe -version
```

Nếu máy đã có bản Snap nhưng thiếu lệnh `ffprobe` trong `PATH`, kiểm tra:

```bash
command -v ffmpeg
command -v ffprobe
```

## Chạy nhanh (start.sh / start.bat)

```bash
cp .env.example .env   # sửa WHITEBOARD_ROOT, WHITEBOARD_PYTHON, STUDIO_PORT... theo máy bạn
./start.sh             # Windows: double-click start.bat
```

`start.sh` nạp `.env` (không ghi đè biến đã export trong shell), tự tìm `.venv`, rồi mở trình duyệt.
API key AI không nằm trong `.env`: nhập ở Studio → Settings (lưu tại `.studio-data/settings/ai.json`, đã gitignore).

## Ứng dụng desktop (cửa sổ riêng)

Cùng một giao diện và server với bản web, nhưng mở thành cửa sổ riêng như một phần mềm (dùng WebView2 của Windows),
không cần mở trình duyệt hay gõ lệnh. Bản web vẫn chạy bình thường và có thể chạy song song (desktop dùng cổng 7870, web dùng 7863).

```bash
pip install -e ".[desktop]"                                   # cài thêm pywebview (một lần)
powershell -ExecutionPolicy Bypass -File scripts\make-desktop-shortcut.ps1   # tạo shortcut "Code2Video Studio" ngoài Desktop
```

Sau đó chỉ cần bấm shortcut trên Desktop. Các cách mở khác: `desktop.pyw` (double-click, không hiện console), `desktop.bat`,
`./start.sh --desktop`, hoặc `python -m code2video.desktop` (thêm `--check` để kiểm tra môi trường mà không mở cửa sổ).

- **Phần mềm đi kèm dùng bằng đường dẫn:** vào **Settings → Đường dẫn công cụ**, nhập thư mục `srt-whiteboard-animation` (và Python của nó nếu có).
  Đường dẫn được kiểm tra, lưu local và có hiệu lực ngay. ffmpeg, node, npx lấy từ `PATH` của máy (Settings hiện ✓/✗ cho từng cái).
  File `.env` (nếu có) vẫn được nạp, nhưng giá trị lưu trong Settings được ưu tiên.
- **Đóng cửa sổ là tắt luôn server.** Mở bằng shortcut thì log nằm ở `.studio-data/desktop.log`.
- **Dữ liệu** (settings, skill, flow, kết quả) dùng chung thư mục `.studio-data` với bản web.
- Dành cho một máy: cần máy đã có Python, ffmpeg, node và các model như bản web, chưa đóng gói thành file `.exe`.
- Shortcut trỏ tới thư mục code chứa script; nếu bạn chuyển thư mục code, chạy lại script tạo shortcut.

## Chạy Studio (giao diện web)

Tạo virtualenv và cài ứng dụng cùng các adapter:

```bash
cd /data/Project_HCM/Personal/tool/code2video
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[tts,alignment]'
```

Khởi động giao diện web:

```bash
code2video-studio
```

Hoặc:

```bash
PYTHONPATH=src python3 -m code2video.studio.app
```

Mở trình duyệt tại `http://127.0.0.1:7860`. Nếu cần cho thiết bị khác trong mạng truy cập:

```bash
STUDIO_HOST=0.0.0.0 STUDIO_PORT=7860 code2video-studio
```

Nếu không có quyền `sudo`, dùng launcher đã cấu hình FFmpeg/ffprobe local:

```bash
./scripts/run-studio.sh
```

Studio dùng hàng đợi job chạy tuần tự (một worker thread), tái dùng model TTS/Whisper giữa các
job và báo tiến trình qua SSE.

### Chạy hàng loạt bằng CLI

`code2video` nhận nhiều file hoặc một thư mục (đệ quy) để render hàng loạt, nạp model một lần:

```bash
code2video examples/ --output-dir build/batch --dry-run --skip-alignment
code2video a.srt b.srt c.srt --voice 'Hải Đăng' --render
```

Launcher CLI tương ứng:

```bash
./scripts/run-cli.sh examples/sample.srt --output-dir build/dry-run --dry-run --skip-alignment
```

Trên máy này FFmpeg 4.3.1 đã có qua Snap nhưng Snap bị sandbox khi đọc file trong workspace. Vì vậy project có thể dùng bản Ubuntu local trong `.tools/ffmpeg-local`; thư mục này đã được thêm vào `.gitignore`. Cách cài chuẩn cho máy khác vẫn là `sudo apt install -y ffmpeg`.

Studio có các chức năng:

- Nhập script từng dòng hoặc upload `.srt`/`.txt`.
- Chọn VieNeu mode, preset voice hoặc audio tham chiếu để clone giọng.
- Chọn Whisper model/device/compute type.
- Xếp nhiều job vào hàng đợi, chạy tuần tự và tái dùng model giữa các job.
- Theo dõi tiến trình từng job qua SSE (stage + %).
- Chạy dry-run để kiểm tra timing mà không tải model.
- Preview voiceover/video, tải `timeline.json`, composition HTML và MP4.

### Whiteboard animation

Studio có thể render project bằng `srt-whiteboard-animation` thay cho HyperFrames. Cài repo
whiteboard và môi trường riêng theo README của repo đó, sau đó cấu hình trên máy chạy Studio:

```bash
export WHITEBOARD_ROOT=/path/to/srt-whiteboard-animation
export WHITEBOARD_PYTHON=/path/to/srt-whiteboard-animation/.venv/bin/python
./scripts/run-studio.sh
```

Chọn engine **Whiteboard animation**. Mỗi hàng scene nhận một file script/SRT, một ảnh PNG và
annotation JSON tương ứng; dùng **Thêm scene** để nhập nhiều cảnh trong một lần gửi. Mỗi hàng tạo
một job/video cảnh riêng. Khi các cảnh đã xong, chọn chúng trong hàng đợi và bấm **Ghép cảnh** để
tạo video cuối theo thứ tự gửi. Studio dùng cùng VieNeu TTS, voice preset/reference audio, speaker
mapping và dry-run hiện có, sau đó mux voiceover vào từng cảnh và ghép cả video lẫn audio.
Whiteboard project không cần `index.html`; annotation JSON cần có `elements` và khớp ảnh PNG.

### AI Kịch bản (whiteboard)

Tab **AI Kịch bản** (engine Whiteboard): nhập ý tưởng → AI sinh kịch bản SRT + chọn doodle cho
từng câu → duyệt/sửa → app dựng resource (PNG + annotation + SRT) rồi chạy pipeline TTS + render
song song + auto-merge (video từng scene vẫn được giữ để tải về). Các tab **Folder** và **Thủ công**
vẫn hoạt động như cũ cho tài nguyên upload thủ công.

- Provider mặc định: **Google Gemini** / **Groq** / **OpenRouter** (free tier) + **Other** cho mọi
  API chuẩn OpenAI-compatible (nhập baseUrl + model + API key). Key lưu tại `.studio-data/settings/ai.json`
  (đã gitignore). Lấy key miễn phí: aistudio.google.com, console.groq.com, openrouter.ai.
- Provider **Demo** chạy offline không cần key — dùng để thử luồng.
- **Skills**: các system prompt tự thêm (id + nội dung), chọn khi sinh kịch bản.
- **Kiểm tra AI chạy được chưa**: Settings → mỗi provider có nút **⟳ Tải danh sách model** (chọn model chat/ảnh
  từ danh sách thay vì gõ tay) và **Kiểm tra kết nối** (gọi thử 1 câu, hiện ✓ + độ trễ hoặc lỗi cụ thể).
- **Upload skill**: Settings → **Tải skill lên** (`.md/.txt`, ≤200 KB), lưu local tại `.studio-data/settings/uploads/skills`.
  Tối đa 4 file upload; bước Skill trong Workflow chọn được tối đa 4 skill cùng lúc (gộp thành một system prompt). Mục **Tệp đã tải lên** liệt kê dung lượng, skill đang dùng và cho xóa (skill gắn với file cũng bị gỡ).

### Workflow (theo step)

Màn Workflow đi theo các bước cố định, có đủ từ prompt tới video hoàn chỉnh (nút **Hướng dẫn** có giải thích):

- **Whiteboard**: Ý tưởng → Skill (tùy chọn) → AI kịch bản → Hình ảnh (AI tự vẽ hoặc doodle của app) → Giọng đọc → Render → Ghép cảnh.
- **HyperFrames**: Ý tưởng → Skill (tùy chọn) → AI kịch bản → Giọng đọc → AI dựng HTML → Render. Giọng đọc chạy trước nên AI nhận
  thời lượng thật của từng câu và dựng hình khớp tiếng; video render xong được ghép giọng đọc vào.

**Nhiều nhân vật:** ở bước AI kịch bản nhập mỗi dòng một tên (2 đến 4 nhân vật), AI viết lời thoại đối đáp luân phiên;
ở bước Giọng đọc gán giọng VieNeu riêng cho từng nhân vật (người chưa gán dùng giọng mặc định). Dùng được cho cả Whiteboard và HyperFrames.

Bước thiếu thông tin có dấu ⚠ và chặn lúc bấm **Chạy**. Khi chạy, cột trái cho biết đang ở bước nào. Bấm bước đã xong để xem
kết quả (ô nhập bị khóa, **Mở khóa để sửa** nếu muốn chỉnh). Card AI lỗi được thử lại theo số lần cài ở bước đó.

### Dữ liệu lưu ở đâu

Settings, skill upload, flow đã lưu và kết quả lần chạy gần nhất nằm trong `.studio-data/` ở thư mục repo chính
(tự gitignore, dùng chung cho mọi git worktree và mọi nhánh). Đổi vị trí bằng biến `STUDIO_DATA_DIR`.

## Chạy dry-run

Dry-run không tải TTS/Whisper model, dùng silent audio giả lập để kiểm tra timing và HTML:

```bash
PYTHONPATH=src python3 -m code2video.cli \
  examples/sample.srt \
  --output-dir build/dry-run \
  --dry-run \
  --skip-alignment
```

Kết quả:

- `build/dry-run/voiceover.wav`
- `build/dry-run/timeline.json`
- `build/dry-run/index.html`

## Chạy thật bằng VieNeu

Với preset voice:

```bash
PYTHONPATH=src python3 -m code2video.cli \
  examples/sample.srt \
  --output-dir build/video \
  --voice 'Hải Đăng' \
  --whisper-model small \
  --whisper-device cpu \
  --whisper-compute-type int8
```

Hoặc clone giọng từ file tham chiếu:

```bash
PYTHONPATH=src python3 -m code2video.cli \
  script.txt \
  --output-dir build/video \
  --ref-audio /absolute/path/reference.wav
```

File `.srt` giữ mốc bắt đầu của từng cue. Nếu audio một cue dài hơn khoảng trống được cấp, cue tiếp theo được đẩy về sau thay vì time-stretch giọng nói.

## Render HyperFrames

Sau khi build composition:

```bash
npx hyperframes render --output build/video/output.mp4 build/video
```

Hoặc chạy luôn từ pipeline:

```bash
PYTHONPATH=src python3 -m code2video.cli \
  examples/sample.srt \
  --output-dir build/video \
  --render \
  --video-output build/video/output.mp4
```

Nếu bản HyperFrames CLI yêu cầu cú pháp khác, chạy `npx hyperframes render --help`; pipeline giữ lệnh render ở một adapter riêng trong `src/code2video/pipeline.py`.

## Kiểm tra

```bash
PYTHONPATH=src python3 -m compileall -q src tests
PYTHONPATH=src python3 -m pytest -q
```

## Ghi chú timing

- VieNeu trả waveform, không trả word timestamps chuẩn hóa.
- faster-whisper được chạy trên chính `voiceover.wav` nên timing phản ánh audio thật.
- Alignment là bước tùy chọn trong dry-run, nhưng nên bật trong production.
- Scene grouping giữ logic mục tiêu 25–35 giây của `srt-whiteboard-animation`.
- HyperFrames không cần biết VieNeu hay Whisper; nó chỉ đọc audio và timing trong composition.
# code2video
