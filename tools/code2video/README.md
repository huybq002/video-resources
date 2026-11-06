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
