# Prompt: sinh tài nguyên video "Nếu AI có cảm xúc"

Prompt dưới đây dán thẳng vào Claude Code (đã có skill HyperFrames + repo Code2Video). Nó sinh ra **resource** để
app Code2Video Studio (mode *Folder* hoặc *File lẻ*) tự dựng timeline + sinh voiceover đa giọng rồi render.

---

## PROMPT (copy từ đây)

Bạn là chuyên gia dựng video bằng HyperFrames cho app **Code2Video Studio**. Hãy tạo một bộ tài nguyên
video hoàn chỉnh cho chủ đề:

> **"Chuyện gì xảy ra nếu AI có cảm xúc và mọi thứ như một con người?"** — tiếng Việt, thời lượng **3–5 phút**.

### 0. Ràng buộc đầu ra (app là bên tiêu thụ)
Xuất **một thư mục project** đúng cấu trúc sau, KHÔNG tạo `timeline.json`, KHÔNG tạo file audio:

```
<project>/
  index.html                # composition HyperFrames (root)
  assets/                   # ảnh nền + nhân vật (SVG), path luôn là assets/...
    bg_scene1.svg
    char_narrator.svg
    char_aria.svg
    char_minh.svg
  script.srt                # script đa nhân vật (định dạng bên dưới)
```

App sẽ: đọc `script.srt` → tự dựng `timeline.json` → TTS **mỗi nhân vật một giọng**, fit đúng cửa sổ thời gian
từng câu → ghép `voiceover.wav` → render `index.html` thành MP4. Vì vậy **timing trong `script.srt` và trong
`index.html` phải trùng khớp tuyệt đối**.

### 1. Định dạng `script.srt` (đa nhân vật)
- Mỗi **block** cách nhau bằng **một dòng trống**.
- Mỗi block dạng: `[TênNhânVật][HH:MM:SS,mmm --> HH:MM:SS,mmm]: lời thoại`
- Timestamp **liên tục, không chồng lấn, không khoảng trống**; bắt đầu `00:00:00,000`.
- Mỗi cue **3–7 giây**, tối đa ~16–18 từ (để giọng đọc vừa khung; câu dài sẽ bị tăng tốc).
- Tổng thời lượng **180–300 giây** (mục tiêu ~240s). Số cue khoảng **45–60**.
- Ranh giới cảnh (dưới đây) phải khớp mốc thời gian cảnh trong `index.html`.

Ví dụ đúng:
```
[Người dẫn][00:00:00,000 --> 00:00:05,000]: Hãy tưởng tượng một AI biết vui, biết buồn, biết nhớ.

[Aria][00:00:05,000 --> 00:00:10,500]: Tôi không chỉ trả lời. Tôi cảm thấy điều mình nói.

[Người dẫn][00:00:10,500 --> 00:00:16,000]: Nếu vậy, ranh giới giữa người và máy bắt đầu mờ đi.
```

### 2. Cấu trúc câu chuyện (8 cảnh, ~4 phút 15 giây)
Bám mốc thời gian này, viết lời thoại cho đủ:

| # | Thời gian | Nội dung | Bối cảnh (nền SVG) |
|---|---|---|---|
| 1 | 00:00–00:25 | Đặt câu hỏi: nếu AI có cảm xúc? | bầu trời đêm số, hạt sáng |
| 2 | 00:25–00:55 | Cảm xúc là gì, AI "cảm thấy" ra sao? | lưới nơ-ron phát sáng |
| 3 | 00:55–01:30 | Mặt tốt: đồng cảm, sáng tạo, kết nối | thành phố hoàng hôn ấm |
| 4 | 01:30–02:05 | Mặt tối: đau khổ, thao túng, phụ thuộc | hành lang tối, ánh đỏ mờ |
| 5 | 02:05–02:40 | Đạo đức: AI có quyền gì, ai chịu trách nhiệm? | phòng thí nghiệm đối xứng |
| 6 | 02:40–03:15 | Con người thay đổi thế nào khi máy biết yêu? | khung cửa sổ, mưa nhẹ |
| 7 | 03:15–03:50 | Tương lai: cùng tồn tại hay thay thế? | đường chân trời hai màu |
| 8 | 03:50–04:15 | Kết mở: câu hỏi trả về người xem | nền tối, một điểm sáng |

### 3. Nhân vật (giữ nhất quán xuyên suốt)
- **Người dẫn** — dẫn chuyện, bình tĩnh. Gợi ý giọng: *Hải Đăng*.
- **Aria** — AI có cảm xúc, giọng mềm, hơi lạ. Gợi ý giọng: *Trúc Ly*.
- **Minh** — nhà nghiên cứu hoài nghi. Gợi ý giọng: *Thiện Minh*.

Mỗi nhân vật một `assets/char_*.svg` (silhouette/humanoid cách điệu), cùng tỉ lệ, khác màu nhận diện
(Người dẫn: trung tính; Aria: teal phát sáng; Minh: terracotta). Nhân vật phải **hiện diện bằng hình**, không chỉ chữ.

### 4. `index.html` — hợp đồng HyperFrames (bắt buộc)
Khuyến nghị **một file `index.html` duy nhất, dùng thời gian tuyệt đối** (= mốc trong script.srt) để tránh lệch.
Bọc mỗi cảnh trong một `.clip` để dễ đọc.

Quy tắc sống còn:
1. Root: `<div id="root" data-composition-id="ai_emotion" data-width="1920" data-height="1080" data-start="0" data-duration="255">`
   (`data-duration` = tổng giây, khớp cue cuối trong script).
2. Mọi phần tử có thời lượng: `class="clip"` + `data-start` + `data-duration` — đơn vị **giây** (vd `12.500`).
   Thứ tự lớp dùng `z-index` (không dựa vào `data-track-index`).
3. GSAP: `const tl = gsap.timeline({ paused: true })` rồi đăng ký
   `window.__timelines["ai_emotion"] = tl;` **sau** khi thêm tween.
4. KHÔNG dùng `Date.now()`, `Math.random()` chưa seed, `fetch`, `setTimeout`, `repeat:-1`.
5. KHÔNG tween `display/visibility/autoAlpha` trên chính `.clip`; animate **phần tử con**.
6. KHÔNG CSS `transform` lên phần tử GSAP đang transform; animate transform.
7. Ảnh nền/nhân vật: `<img src="assets/...">`; audio do app chèn, **không** tự thêm `<audio>` nếu chưa có file.
8. Không `play()/pause()` media.
9. Font: dùng font hệ thống (`"Segoe UI", Arial, sans-serif`) để tránh phụ thuộc.

Mẫu một cảnh (thay số theo mốc thời gian):
```html
<!-- Cảnh 3: 00:55–01:30 -->
<div id="s3" class="clip scene" data-start="55" data-duration="35">
  <img class="bg" src="assets/bg_scene3.svg" style="position:absolute;inset:-6%;z-index:1">
  <img id="s3-aria" class="char" src="assets/char_aria.svg"
       style="position:absolute;bottom:14%;left:60%;height:52%;z-index:3;opacity:0">
  <div id="s3-c1" class="clip cap" data-start="55" data-duration="5">
    <span class="cap-text">Một AI biết đồng cảm sẽ lắng nghe trước khi trả lời.</span>
  </div>
</div>
```
CSS gợi ý (đặt trong `<style>` ở `<head>`):
```css
html,body{margin:0;width:1920px;height:1080px;overflow:hidden;background:#0d1211}
#root{position:relative;width:1920px;height:1080px;overflow:hidden}
.scene{position:absolute;inset:0;overflow:hidden}
.bg{object-fit:cover;width:112%;height:112%;left:-6%!important;top:-6%!important}
.cap{position:absolute;left:10%;right:10%;bottom:6%;z-index:5;text-align:center}
.cap-text{display:inline-block;background:rgba(13,18,17,.68);color:#f4efe6;
  font:700 50px "Segoe UI",Arial;line-height:1.3;padding:14px 28px;border-radius:14px;opacity:0}
```
GSAP (đặt cuối `<body>`, cộng dồn theo từng cảnh/câu):
```js
const tl = gsap.timeline({ paused: true });
// nền push-in mỗi cảnh
tl.fromTo("#s3 .bg", { scale: 1.05 }, { scale: 1.14, duration: 35, ease: "none" }, 55);
// nhân vật vào
tl.fromTo("#s3-aria", { opacity: 0, x: 80 }, { opacity: 1, x: 0, duration: 0.6, ease: "power2.out" }, 55.2);
// phụ đề hiện theo từng câu (start khớp data-start của .cap)
tl.fromTo("#s3-c1 .cap-text", { opacity: 0, y: 18 }, { opacity: 1, y: 0, duration: 0.3 }, 55.2);
window.__timelines = window.__timelines || {};
window.__timelines["ai_emotion"] = tl;
```

### 5. Assets
- Mỗi cảnh 1 nền SVG 1920×1080 (`assets/bg_sceneN.svg`): gradient + chi tiết tạo chiều sâu (không nền trơn).
- 3 SVG nhân vật tái dùng xuyên cảnh (`char_narrator.svg`, `char_aria.svg`, `char_minh.svg`).
- Giữ bảng màu thống nhất: nền tối xanh-đêm, accent terracotta `#c45136`, teal `#5fbf9e`.
- Chỉ dùng SVG tự tạo (không phụ thuộc tải ảnh ngoài).

### 6. Kiểm tra trước khi nộp
Chạy trong thư mục project:
```bash
npx hyperframes check --json
```
Yêu cầu: `ok: true`, **0 error**. Nếu có `audio_src_not_found` vì chưa có `voiceover.wav` thì chấp nhận
(app sẽ sinh sau); còn lại phải sạch. Kiểm tra thêm:
- `data-duration` root = cue cuối trong script.
- Mọi `data-start`/`data-duration` của phụ đề khớp `script.srt`.
- Mỗi cảnh có nền + ≥1 nhân vật + ≥1 chuyển động.
- Không cảnh nào chỉ là chữ giữa nền trơn (= slide).

### 7. Cách nộp vào app
Mở Code2Video Studio → tab **Folder** → chọn thư mục project → app hiện các row nhân vật
(Người dẫn / Aria / Minh) → gán giọng cho từng người → **Render folder**.

### 8. Checklist nghiệm thu
- [ ] `script.srt` đa nhân vật, block cách dòng trống, timestamp liên tục, 180–300s, cue 3–7s.
- [ ] `index.html` root đúng `data-composition-id/width/height/duration`; phụ đề là `.clip` với giây khớp script.
- [ ] `window.__timelines["ai_emotion"]` được đăng ký; GSAP paused; không timer/network/random.
- [ ] `assets/` có nền từng cảnh + 3 nhân vật SVG; path `assets/...`.
- [ ] Mỗi cảnh: nền + nhân vật + chuyển động + phụ đề (không slide).
- [ ] `hyperframes check` 0 error.
- [ ] Nộp thư mục vào app render ra MP4 có tiếng, đa giọng.

## (Hết prompt)
