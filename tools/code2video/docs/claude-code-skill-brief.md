# Brief: skill Claude Code sinh tài nguyên cho Code2Video Studio

Tài liệu này mô tả **đầu vào/đầu ra và cấu trúc** để Claude Code viết một **Agent Skill** có tên
`code2video-resource-generator`. Skill đó nhận một kịch bản tiếng Việt và sinh ra **bộ tài nguyên
render được** cho app Code2Video Studio.

Mục tiêu cuối: người dùng chạy skill → có một thư mục project → kéo vào Studio (chế độ "Upload file lẻ"
hoặc "Chọn folder project") → bấm render → ra `output.mp4` **có nhân vật, bối cảnh, chuyển động**,
không phải slide chữ.

---

## 1. App nhận gì (hợp đồng bắt buộc)

App render bằng `npx hyperframes render` chạy trong thư mục project, đọc `index.html`, xuất
`output.mp4`. Vì vậy skill phải xuất đúng cấu trúc:

```
<project>/
  index.html              # BẮT BUỘC — root composition
  compositions/           # cảnh con (sub-composition), mỗi cảnh 1 file
    scene_1.html
    scene_2.html
  assets/                 # ảnh, font, (media) — path luôn là assets/...
    scene_1_bg.png
    char_a.png
  voiceover.wav           # audio root index.html tham chiếu (nếu có lời)
  timeline.json           # contract timing (xem mục 3) — nên có
  hyperframes.json        # (tùy chọn nhưng nên có) cấu hình paths
  package.json            # (tùy chọn) script render
```

Ánh xạ khi upload vào Studio:
- **"Upload file lẻ (html + timeline + assets)"**: `index.html` → gốc; `timeline.json` → gốc;
  mọi file chọn ở ô assets → ghi vào `assets/<tên>`; `voiceover.wav` → gốc.
- **"Chọn folder project"**: upload cả cây; app tự tìm thư mục chứa `index.html` làm project root.
- Tên artifact app phục vụ: `output.mp4`, `index.html`, `timeline.json`, `voiceover.wav`.

## 2. Hợp đồng HyperFrames (bắt buộc để render đúng)

Đọc chuẩn đầy đủ: skill `hyperframes`, và `npx hyperframes docs <topic>`. Tóm tắt điều kiện sống còn:

1. **Root**: `<div id="root" data-composition-id="<id>" data-width="1920" data-height="1080"
   data-start="0" data-duration="<tổng_s>">` (hoặc đặt trên `#root`).
2. **Timed element**: mọi phần tử có thời lượng phải có `class="clip"` + `data-start` +
   `data-duration` — đơn vị **giây**. `data-track-index` chỉ là lane Studio, **không** quyết định
   thứ tự vẽ (dùng `z-index`).
3. **Độ dài video** = `data-duration` của root; tràn bị cắt, thiếu thì giữ frame cuối.
4. **GSAP**: mỗi composition tạo `gsap.timeline({ paused: true })` rồi đăng ký **sau khi thêm tween**:
   `window.__timelines["<data-composition-id>"] = tl;`. Chỉ dùng `set/to/from/fromTo`.
5. **Không** dùng `Date.now()`, `Math.random()` chưa seed, `fetch`, `setTimeout`, `repeat: -1`.
   Mọi thứ phải là hàm của thời gian timeline.
6. **Không** tween `display/visibility/autoAlpha` trên chính phần tử `.clip` — animate phần tử con.
7. **Không** đặt CSS `transform` lên phần tử GSAP đang transform; animate transform, không
   `left/top/width/height`.
8. **Không** `play()/pause()` media. `<video>` giữ tiếng bằng `data-has-audio="true"`, còn lại `muted`.
   Mọi `<audio>` phải có `id`.
9. **Font**: chỉ font bundle mới resolve theo tên; font khác cần `@font-face` trỏ file trong `assets/fonts/`.
10. **Asset path**: `assets/...` (không có `/` đầu), kể cả trong sub-composition.
11. **Scene file**: đặt style/markup/script trong `<template>`; style root qua `#root` hoặc
    `[data-composition-id="..."]`.
12. Một cảnh = một sub-composition; root chỉ chứa scene host, media, audio.

### Scene host trong root
```html
<div class="clip" data-composition-id="scene_1"
     data-composition-src="compositions/scene_1.html"
     data-start="0.000" data-duration="8.710" data-track-index="1"></div>
```

### Scene file mẫu (compositions/scene_1.html)
```html
<template id="scene_1-template">
  <div data-composition-id="scene_1" data-width="1920" data-height="1080" data-duration="8.71">
    <div class="bg"></div>
    <img id="char-a" class="char" src="assets/char_a.png">
    <div id="cap-1" class="caption"><span>Lời thoại...</span></div>
    <style>
      [data-composition-id="scene_1"] .bg { position:absolute; inset:0; z-index:1;
        background:url("assets/scene_1_bg.png") center/cover; }
      [data-composition-id="scene_1"] .char { position:absolute; bottom:14%; left:12%; width:22%; z-index:3; opacity:0; }
      [data-composition-id="scene_1"] .caption { position:absolute; left:8%; right:8%; bottom:10%; z-index:4;
        text-align:center; opacity:0; }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js"></script>
    <script>
      (function () {
        const tl = gsap.timeline({ paused: true });
        tl.fromTo("[data-composition-id='scene_1'] .bg", { scale: 1.05 }, { scale: 1.12, duration: 8.71, ease: "none" }, 0);
        tl.fromTo("#char-a", { opacity: 0, x: -80 }, { opacity: 1, x: 0, duration: 0.6, ease: "power2.out" }, 0.2);
        tl.fromTo("#cap-1", { opacity: 0, y: 24 }, { opacity: 1, y: 0, duration: 0.3 }, 0.4);
        tl.to("#cap-1", { opacity: 0, duration: 0.2 }, 3.0);
        window.__timelines = window.__timelines || {};
        window.__timelines["scene_1"] = tl;
      })();
    </script>
  </div>
</template>
```

> Timing **trong scene là relative** (0..duration của scene). Root đặt scene tại `data-start` tuyệt đối.

## 3. `timeline.json` — schema khớp app (milliseconds)

App tự sinh theo `Timeline.to_dict()`. Skill phải xuất đúng key (dùng để đồng bộ scene/cue):

```json
{
  "audio": "voiceover.wav",
  "durationMs": 9210,
  "sampleRate": 48000,
  "language": "vi",
  "cues": [
    { "index": 1, "text": "...", "startMs": 0, "endMs": 2990,
      "durMs": 2990, "requestedStartMs": 0,
      "words": [{ "text": "...", "startMs": 0, "endMs": 320 }] }
  ],
  "scenes": [
    { "sceneIndex": 1, "startMs": 0, "endMs": 8710,
      "sceneDurationMs": 8710, "cueRange": [1, 3], "text": "..." }
  ],
  "metadata": {}
}
```

Quy ước:
- Mọi timestamp **ms**. Đổi sang giây (`/1000`, 3 chữ số thập phân) khi ghi vào HTML.
- Scene 25–35s (app gom vậy); video ngắn < 25s = 1 scene.
- `cueRange` = [index đầu, index cuối] của cue thuộc scene. Cue không vượt scene.
- Cue timestamp **liền mạch**, không overlap.

## 4. Tài nguyên hình ảnh & audio

- **Bắt buộc** có yếu tố "video", không phải slide:
  - ≥1 lớp **background** mỗi scene (ảnh `assets/sceneN_bg.png` HOẶC gradient có chiều sâu).
  - ≥1 **nhân vật** hiện diện bằng hình (sprite PNG nền trong suốt, hoặc SVG nhân vật).
  - ≥1 **chuyển động thật** (nhân vật/virtual camera di chuyển qua GSAP).
  - Phụ đề ở **1/3 dưới**, không chiếm toàn khung.
- Ảnh nền/sprite 1920×1080 (hoặc 16:9) đặt trong `assets/`; tái dùng sprite xuyên cảnh.
- Audio: nếu có lời, skill phải cung cấp `voiceover.wav` ở gốc và root `<audio id="voice"
  src="voiceover.wav" ...>`. Nếu cố ý im lặng, bỏ `<audio>` để tránh lint `audio_src_not_found`.

## 5. Cấu trúc skill cần viết

```
code2video-resource-generator/
  SKILL.md
  references/
    hyperframes-contract.md      # copy mục 2 (rule render)
    timeline-schema.md           # copy mục 3
    scene-template.html          # mẫu scene chuẩn (mục 2)
  scripts/
    scaffold_project.py          # sinh khung project từ danh sách scene
    validate.py                  # chạy hyperframes check/lint + kiểm tra schema
  assets/
    (sprite/placeholder mặc định nếu cần)
```

`SKILL.md` frontmatter gợi ý:
```markdown
---
name: code2video-resource-generator
description: Generate a renderable Code2Video project (index.html + compositions/*.html + assets/ + timeline.json + voiceover.wav) from a Vietnamese script, with characters, backgrounds and motion (never slides). Use when asked to create/author Code2Video video resources, build a HyperFrames composition with scenes/characters, or produce index.html + timeline.json for the Code2Video Studio app.
---
```

Nội dung SKILL.md nên có: mục tiêu, **quy trình** (mục 6), trỏ tới references, cách chạy scripts,
và **checklist nghiệm thu** (mục 8).

## 6. Quy trình skill thực hiện

1. Nhận input: chủ đề hoặc script/SRT + (tùy chọn) số cảnh, giọng, phong cách.
2. Viết **Script/SRT** (mỗi cue ≤ ~14 từ), kèm comment mỗi scene:
   `# SCENE | setting | nhân vật | action | camera`.
3. Lập **Scene Brief** mỗi cảnh: background, characters (blocking), motion, caption, palette.
4. Sinh **assets**: ảnh nền mỗi scene + sprite nhân vật (ImageGen hoặc placeholder SVG) → `assets/`.
5. Tạo **timeline.json** theo schema mục 3 (ms, scene 25–35s).
6. Dựng **index.html** (root: audio + scene hosts + root timeline) và
   **compositions/scene_N.html** (template + #root + timeline relative) bám đúng mục 2.
7. Ghi `hyperframes.json` + `package.json`.
8. Chạy `scripts/validate.py` → `npx hyperframes check --json` + `lint`; sửa tới khi 0 error.
9. (Tùy chọn) `npx hyperframes render` thử → xác nhận `output.mp4`.
10. Trả về đường dẫn thư mục project để người dùng kéo vào Studio.

## 7. Cách app render (để skill không lệch)

- App chạy `npx hyperframes render --output <project>/output.mp4` với **cwd = project dir**.
- App đọc artifact theo tên cố định: `output.mp4`, `index.html`, `timeline.json`, `voiceover.wav`.
- App **không** đọc timeline để dựng hình — hình do `index.html` quyết định. `timeline.json` chỉ để
  đồng bộ/tham chiếu và hiển thị. ⇒ Skill phải đặt timing thật trong GSAP của HTML, khớp với
  `timeline.json`.

## 8. Checklist nghiệm thu (skill tự kiểm)

- [ ] Thư mục có `index.html` + `compositions/*.html` + `assets/` + `timeline.json` (+ `voiceover.wav`).
- [ ] `npx hyperframes check --json` → `ok: true`, **0 error** (warning cần cân nhắc).
- [ ] Mỗi scene có background + ≥1 nhân vật + ≥1 chuyển động GSAP; có `class="clip"` + `data-start/duration` (giây).
- [ ] Mỗi composition có `window.__timelines["<id>"]`.
- [ ] `timeline.json` ms liền mạch, scene 25–35s, `cueRange` khớp cue.
- [ ] Không có cảnh chỉ là chữ giữa nền trơn (= slide).
- [ ] Render thử ra `output.mp4` có **video (+ audio nếu có lời)**.
- [ ] Upload vào Studio ("files" hoặc "folder") render thành công.

## 9. Prompt sẵn để đưa Claude Code

> "Viết một Agent Skill tên `code2video-resource-generator` (format SKILL.md + references/ + scripts/).
> Nó nhận một kịch bản tiếng Việt và sinh ra một thư mục project render được bởi app Code2Video
> Studio: `index.html` (root mount từng scene), `compositions/scene_N.html` (mỗi cảnh một
> sub-composition, timing tương đối), `assets/` (ảnh nền + sprite nhân vật), `timeline.json`
> đúng schema ms, và `voiceover.wav` nếu có lời. Bắt buộc tuân thủ hợp đồng HyperFrames: root
> `data-composition-id/width/height/duration`, phần tử timed có `class="clip"` + `data-start/duration`
> giây, GSAP `paused:true` đăng ký `window.__timelines[id]`, không network/timer/random, asset path
> `assets/...`, scene file bọc `<template>`. Video phải có nhân vật + bối cảnh + chuyển động, không
> phải slide. Kèm script `scaffold_project.py` dựng khung và `validate.py` chạy `npx hyperframes
> check --json`. Đọc chi tiết trong `docs/claude-code-skill-brief.md` và `docs/ai-video-assets-spec.md`."

## 10. Tham chiếu nội bộ repo

- Hợp đồng sinh hiện tại: `src/code2video/composition.py` (ví dụ project đa file chuẩn).
- Schema: `src/code2video/models.py` (`Timeline.to_dict`).
- App nhận upload: `src/code2video/studio/app.py` (mode `files` / `upload`); render:
  `src/code2video/pipeline.py:render_hyperframes`.
- Spec nội dung: `docs/ai-video-assets-spec.md`.
