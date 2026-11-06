# Hợp đồng tài nguyên HyperFrames engine (dành cho AI tạo file)

Tài liệu này liệt kê **đúng các file, cấu trúc thư mục và khuôn mẫu** mà Code2Video Studio cần để render video bằng engine HyperFrames. Khuôn mẫu được trích từ `src/code2video/composition.py` và các project đã render thật (`examples/demo-multi`, `build/ui-runs/10b14d730f86`).

**Cách dùng:** đưa toàn bộ file này (hoặc khối "Prompt rút gọn" ở cuối) cho AI cùng yêu cầu video; AI chỉ được tạo file theo đúng cấu trúc dưới đây.

**Đã kiểm chứng:** khuôn mẫu ở mục 3–4 được dựng thành project thật → `npx hyperframes check` trả `ok: true` (0 lỗi, 0 cảnh báo ngoại trừ wav im lặng dùng để test) và `npx hyperframes render` ra video 12.0s thật.

---

## 1. Cấu trúc thư mục

Tối thiểu để render:

```
<project>/
├── index.html                # BẮT BUỘC — root composition
├── script.srt                # BẮT BUỘC nếu muốn app tự sinh voiceover + timeline
└── assets/
    ├── bg.svg                # bối cảnh (vector/PNG)
    ├── an.svg                # nhân vật 1 — TÁCH riêng từng nhân vật
    ├── minh.svg              # nhân vật 2
    └── audio/voiceover.wav   # do app sinh, AI KHÔNG cần tạo
```

Đầy đủ (project nhiều scene / có metadata):

```
<project>/
├── index.html
├── script.srt
├── timeline.json             # tùy chọn: có thì app bỏ qua TTS-alignment, render thẳng
├── hyperframes.json          # tùy chọn: khai báo paths cho CLI/Studio
├── package.json              # tùy chọn
├── meta.json                 # tùy chọn
├── assets/
│   ├── *.svg|png|jpg         # bối cảnh, nhân vật, đạo cụ
│   ├── fonts/*.woff2         # chỉ khi dùng font ngoài bundled (kèm @font-face)
│   └── audio/voiceover.wav
└── compositions/
    ├── scene_1.html          # mỗi file = 1 cảnh, mọi thứ trong <template>
    └── scene_2.html
```

### Chức năng từng file

| File | Bắt buộc | Chức năng | Ai tạo |
|---|---|---|---|
| `index.html` | ✔ | Root composition: khai báo `#root`, `data-composition-id`, `data-duration` = tổng thời lượng video (giây); mount scene host; chứa `<audio>` voiceover | AI |
| `script.srt` | ✔* | Lời thoại + timestamp từng câu; là nguồn sinh timeline + voiceover | AI |
| `compositions/scene_N.html` | khi nhiều cảnh | Một cảnh: style + markup + script GSAP đặt trong `<template>` | AI |
| `assets/*.svg` | ✔ | Bối cảnh và **từng nhân vật riêng biệt** để animate độc lập (tay, chân, head-tilt, đi lại) | AI |
| `assets/fonts/*` | khi cần font lạ | Font tự nhúng, bắt buộc `@font-face` trỏ file trong assets | AI |
| `assets/audio/voiceover.wav` | | Audio ghép vào video | App (TTS) |
| `timeline.json` | | Timeline ms + word-level; có thì app bỏ qua bước alignment | App hoặc AI |
| `hyperframes.json` / `package.json` / `meta.json` | | Metadata cho CLI/Studio; app tự thêm khi sinh project | App |

\* bắt buộc khi muốn có giọng đọc; video không lời thì bỏ.

---

## 2. Bảng thuộc tính (đơn vị là bắt buộc)

| Thuộc tính | Đơn vị | Đặt ở | Ý nghĩa |
|---|---|---|---|
| `class="clip"` | | mọi phần tử có thời gian | đánh dấu phần tử được timeline quản lý |
| `data-start` | **giây** | `.clip` | thời điểm hiện |
| `data-duration` | **giây** | `.clip`, root, scene | độ dài hiện; root `data-duration` = độ dài video |
| `data-composition-id` | | root + mỗi scene | id timeline, phải khớp key trong `window.__timelines` |
| `data-composition-src` | | scene host trong root | đường dẫn file scene, dạng `compositions/scene_1.html` |
| `data-width` / `data-height` | px | root + scene | 1920 / 1080 mặc định |
| `data-track-index` | số | `.clip` | lane trong Studio (không quyết định thứ tự vẽ — thứ tự vẽ là `z-index`) |
| `data-track-kind` | | scene host / overlay / caption host | `graphics` \| `captions` |
| `data-var-text` / `data-var-src` | | element/asset | biến để Studio sửa chữ/ảnh không đụng code |
| `data-has-audio` | | `<video>` | `"true"` nếu giữ tiếng, ngược lại phải `muted` |
| `data-layout-allow-overflow` / `-overlap` | | element cố tình tràn/đè | suppression có chủ đích |

**Quy đổi:** SRT và `timeline.json` dùng **ms**; HTML dùng **giây** (`12.345`).

---

## 3. Khuôn mẫu `index.html`

```html
<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=1920, height=1080">
  <title>Tiêu đề video</title>
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js"></script>
  <style>
    html, body { margin: 0; width: 1920px; height: 1080px; overflow: hidden; background: #0d1211; }
    #root { position: relative; width: 1920px; height: 1080px; overflow: hidden; }
    #voice { position: absolute; width: 1px; height: 1px; opacity: 0; }
    .scene-host { position: absolute; inset: 0; z-index: 2; }
    .stage { position: absolute; inset: 0; z-index: 1; background: #0d1211; }
  </style>
</head>
<body>
  <div id="root" data-composition-id="story" data-width="1920" data-height="1080"
       data-start="0" data-duration="12">

    <div id="stage" class="clip stage" data-start="0" data-duration="12" data-track-index="0"></div>

    <audio id="voice" src="assets/audio/voiceover.wav"
           data-start="0" data-duration="12" data-track-index="0"></audio>

    <div id="scene-1-host" class="clip scene-host"
         data-composition-id="scene-1" data-composition-src="compositions/scene_1.html"
         data-start="0" data-duration="6" data-track-index="1" data-track-kind="graphics"></div>

    <div id="scene-2-host" class="clip scene-host"
         data-composition-id="scene-2" data-composition-src="compositions/scene_2.html"
         data-start="6" data-duration="6" data-track-index="1" data-track-kind="graphics"></div>

    <script>
      const tl = gsap.timeline({ paused: true });
      window.__timelines = window.__timelines || {};
      window.__timelines['story'] = tl;
    </script>
  </div>
</body>
</html>
```

Root chỉ chứa: scene host, media, audio — không nhét nội dung cảnh vào root.

---

## 4. Khuôn mẫu `compositions/scene_1.html`

```html
<template id="scene-1-template">
  <div data-composition-id="scene-1" data-width="1920" data-height="1080" data-duration="6">
    <div class="background"></div>
    <div class="title clip" id="title" data-start="0" data-duration="6">Video nhỏ, chuyện thật</div>
    <div class="horizon"></div>

    <img class="character" id="an" src="assets/an.svg" alt=""
         style="left: 22%" data-start="0" data-duration="6">
    <img class="character" id="minh" src="assets/minh.svg" alt=""
         style="left: 62%" data-start="0" data-duration="6">

    <div class="caption clip" id="cap-1" data-start="0" data-duration="3"><span>Chào Minh, hôm nay mình quay một video nhỏ.</span></div>
    <div class="caption clip" id="cap-2" data-start="2.8" data-duration="3.2"><span>Ừ, có nhân vật, có bối cảnh, và giọng nói riêng.</span></div>

    <style>
      #root { position: absolute; inset: 0; overflow: hidden; }
      .background { position: absolute; inset: -8%; z-index: 1; background: url(assets/bg.svg) center/cover; }
      .horizon { position: absolute; left: 0; right:0; top: 62%; height: 2px; z-index: 2; background: rgba(255,255,255,.08); }
      .character { position: absolute; bottom: 16%; width: 16%; height: 52%; z-index: 3; }
      .title { position: absolute; left: 8%; top: 9%; z-index: 5; color: #f4f1e6; font: 700 54px/1.2 system-ui; }
      .caption { position: absolute; left: 8%; right: 8%; bottom: 11%; z-index: 4; opacity: 0; }
      .caption span { display: inline-block; padding: 18px 34px; border-radius: 14px;
                      background: rgba(10,14,13,.72); color: #f4f1e6; font: 600 34px/1.35 system-ui; }
    </style>

    <script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js"></script>
    <script>
      (function () {
        const tl = gsap.timeline({ paused: true });

        tl.fromTo('.background', { scale: 1.04 }, { scale: 1, duration: 6, ease: 'none' }, 0);
        tl.fromTo('#an',   { y: 18 }, { y: 0, duration: 0.3, ease: 'power2.out' }, 0);
        tl.fromTo('#minh', { y: 18 }, { y: 0, duration: 0.45, ease: 'power2.out' }, 0.2);
        tl.to('#an', { y: -10, duration: 0.9, ease: 'sine.inOut', yoyo: true, repeat: 3 }, 0.6);
        tl.fromTo('#cap-1', { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.25 }, 0.15);
        tl.to('#cap-1 span', { opacity: 0, duration: 0.2 }, 2.8);
        tl.fromTo('#cap-2', { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.25 }, 2.8);

        window.__timelines = window.__timelines || {};
        window.__timelines['scene-1'] = tl;
      })();
    </script>
  </div>
</template>
```

Điểm phải đúng: mọi thứ nằm trong `<template>`; root của template style bằng `#root`; timeline `paused: true`; **đăng ký `window.__timelines['<id>']` SAU khi tạo xong tweens**; id khớp `data-composition-id`.

---

## 5. `script.srt`

Đa nhân vật (app đọc ra giọng riêng từng vai):

```
[An][00:00:00,000 --> 00:00:03,500]: Chào Minh, hôm nay mình quay một video nhỏ.

[Minh][00:00:03,500 --> 00:00:07,000]: Ừ, có nhân vật, có bối cảnh, và giọng nói riêng.

[An][00:00:07,000 --> 00:00:11,000]: Vậy là đủ để thành một câu chuyện rồi.
```

Một nhân vật: SRT chuẩn (`1`, `00:00:00,000 --> 00:00:03,500`, dòng lời thoại, cách một dòng trống).

Ràng buộc:
- Không để cue vượt quá cảnh của nó: `cue.startMs`/`cue.endMs` nằm trong `[scene.startMs, scene.endMs]`.
- Tổng thời lượng SRT khớp `data-duration` của root (lệch nhỏ hơn 0.5s để tránh hở frame cuối).
- App sẽ co giãn giọng thật vào từng cửa sổ (`atempo`), nên timestamp trong SRT là **dự kiến**, không cần chính xác tuyệt đối.

---

## 6. Rule cứng (vi phạm là render sai hoặc `check` báo lỗi)

1. Mọi phần tử có thời gian: `class="clip"` + `data-start` + `data-duration` bằng **giây**; kết thúc phải "đáp" trạng thái cuối ngay trước `start + duration`.
2. Độ dài video = `data-duration` của root; tràn bị cắt, kết thúc sớm thì giữ frame cuối.
3. Mỗi composition đúng **một** timeline `gsap.timeline({paused:true})`, đăng ký sau khi tạo tweens.
4. **Cấm**: `Date.now()`, `Math.random()` không seed, `fetch`, `setTimeout/setInterval/requestAnimationFrame` tự chạy, `repeat: -1`. Mọi thứ phải là hàm của timeline time.
5. Không tween `display` / `visibility` / `autoAlpha` trên `.clip` → animate phần tử con bên trong.
6. Không đặt CSS `transform` lên element GSAP đang transform; animate `transform`/`x`/`y`, không animate `left`/`top`/`width`/`height`.
7. Không gọi `play()` / `pause()` / seek trên media; `<video>` giữ tiếng thì `data-has-audio="true"`, không thì `muted`; nhạc/voiceover là `<audio>` riêng.
8. Mỗi `<audio>` phải có `id`; media không dùng thuộc tính `crossorigin`; chỉ tính thời gian trên `<video>` **hoặc** wrapper, không cả hai.
9. Font: chỉ font bundled resolve theo tên; font khác bắt buộc `@font-face` trỏ `assets/fonts/`.
10. Đường dẫn asset: `assets/...`, **không** bắt đầu bằng `/`, kể cả trong sub-composition.
11. Filter (grade, grain, blur, vignette) lên footage phải qua `npx hyperframes media-treatment`, không dùng CSS filter.
12. Nội dung trong action-safe 90%, chữ chính + caption trong title-safe 80%; không tự vẽ guide line.
13. Một scene = một sub-composition, id ngắn gọn dễ đọc; mỗi track một kind (`graphics`, `captions`); caption gộp vào **một** host duy nhất.
14. Chữ, màu thương hiệu, ảnh có thể thay → đưa vào biến (`data-var-text`, `data-var-src`, `var(--id)`).
15. **Không được ra dạng slide thuyết trình**: phải có nhân vật + bối cảnh + chuyển động; mỗi cảnh có hành động riêng (đi, quay đầu, chỉ tay, breathing) đồng bộ lời thoại.
16. **Frame đầu phải đã có nội dung** (chữ đề hoặc hình chủ chốt hiện sẵn ở 0s, không fade-from-nothing) vì frame 0 là thumbnail trên social player; `check` báo `first_frame_empty`.
17. **Giữ chữ đủ lâu để đọc**: một dòng caption phải hiển thị ≥ `0.5s + 0.3s × số từ` và còn trên màn hình ≥ 2s trước khi cảnh kết; **không fade dòng caption cuối** của cảnh (kéo `data-duration` tới hết cảnh). `check` sẽ báo `line_unread` nếu vi phạm.

---

## 7. Kiểm tra trước khi giao

```bash
npx hyperframes check --json            # vi phạm hợp đồng + dòng "Fix:"
npx hyperframes lint --json             # style/attribute
npx hyperframes snapshot --at 3.5       # xem frame thật tại 3.5s
npx hyperframes snapshot --range 0-6 --composition scene-1
```

Trong Studio: engine **HyperFrames** → tab **File lẻ** (tải `index.html` + assets + script) hoặc **Folder** (nguyên cây thư mục) → Render.

---

## 8. Prompt rút gọn (dán cho AI)

```
Tạo bộ tài nguyên video HyperFrames theo hợp đồng docs/hyperframes-asset-contract.md.
Chủ đề: <...>. Ngôn ngữ: <vi|en|ja|zh|ko>. Thời lượng: <N> giây. Khung hình: 1920x1080.
Bắt buộc:
- Cây file: index.html, script.srt, assets/*.svg (bối cảnh + TỪNG nhân vật riêng),
  compositions/scene_N.html cho mỗi cảnh.
- HTML dùng data-start/data-duration bằng GIÂY; root data-duration = tổng thời lượng.
- Mỗi composition: gsap.timeline({paused:true}) rồi window.__timelines['<id>'] = tl.
- Cấm Date.now/random không seed/fetch/setTimeout/repeat:-1; không tween display/visibility/autoAlpha trên .clip.
- Asset path dạng assets/..., không có / đầu.
- script.srt đa nhân vật: [Tên][00:00:00,000 --> 00:00:03,500]: lời, block cách nhau 1 dòng trống.
- Video phải có nhân vật + bối cảnh + chuyển động, KHÔNG phải slide.
- Dòng caption cuối của mỗi cảnh giữ tới hết cảnh (không fade sớm) để đủ thời gian đọc.
Xuất đủ file, tự chạy `npx hyperframes check --json` và sửa hết lỗi trước khi giao.
```
