# Mô tả sinh tài nguyên video cho Code2Video

Tài liệu này là **prompt chuẩn** để AI sinh ra hai loại tài nguyên mà app cần để render một video
có **nhân vật + bối cảnh chuyển động**, thay vì dạng slide thuyết trình chữ giữa màn hình.

Hai đầu ra bắt buộc, luôn đi kèm nhau:

1. **Script / SRT** — lời thoại chia theo *cảnh*, có timeline rõ ràng cho từng cảnh.
2. **Scene Brief + composition HTML** — mô tả hình ảnh từng cảnh và file HyperFrames render được.

Pipeline hiện tại (không đổi): `script → VieNeu TTS → voiceover.wav → faster-whisper →
timeline.json (ms) → composition HTML → npx hyperframes render → output.mp4`.
`timeline.json` là contract trung tâm: **mọi timestamp tính bằng milliseconds**, chỉ khi đưa vào
HyperFrames mới đổi sang **seconds**.

---

## 1. Quy ước thời lượng bắt buộc

- `group_scenes()` gom cue thành **scene 25–35 giây** (mục tiêu 30s). Mỗi scene là **một bối cảnh
  hình ảnh liên tục**; trong scene, các cue là **lời thoại** chạy chồng lên hình.
- Một video ngắn (< 25s) thì toàn bộ là **1 scene**.
- Không được để cue vượt quá cảnh của nó: `cue.startMs`/`cue.endMs` phải nằm trong
  `[scene.startMs, scene.endMs]`.

## 2. Định dạng Script / SRT đầu ra

File `.srt`, mỗi cue một câu nói được (mỗi cue ≈ 1–2 mệnh đề, ≤ ~14 từ để TTS tự nhiên).
**Trên mỗi block cue, thêm dòng comment mô tả cảnh** theo cú pháp (bị parser bỏ qua vì không có `-->`):

```srt
# SCENE 1 | setting: quán cà phê sáng, nắng xiên qua cửa kính | nhân vật: An (ngồi), Minh (đối diện)
1
00:00:00,000 --> 00:00:03,200
Sáng hôm đó, An hẹn Minh ra quán cà phê quen.

2
00:00:03,200 --> 00:00:07,000
Cô muốn nói điều mà cả tuần nay cô giữ trong lòng.

# SCENE 2 | setting: công viên chiều, hàng cây vàng | nhân vật: An đi một mình
3
00:00:07,000 --> 00:00:11,000
Nhưng Minh đã từ chối, và An chọn cách rời đi.
```

Quy tắc:
- Timestamp **liền mạch**, không overlap, không có khe trống giữa cue này và cue kế.
- Mỗi `# SCENE` comment khai: `setting` (bối cảnh), `nhân vật` (ai xuất hiện + trạng thái),
  `action` (hành động chính), `camera/motion` (tùy chọn). Đây là dữ liệu để sinh composition.
- Cue đầu tiên luôn bắt đầu `00:00:00,000`.

## 3. Scene Brief (cái tạo nên "video", không phải slide)

Mỗi scene phải có đủ 5 trường. Đây là phần AI **nghĩ ra**, không có trong pipeline cũ:

| Trường | Nội dung | Ví dụ |
|---|---|---|
| `background` | Mô tả bối cảnh + ảnh nền (sinh bằng ImageGen) hoặc scene CSS | "quán cà phê, tone ấm, blur nhẹ phía sau" |
| `characters` | Danh sách nhân vật, vị trí (blocking), biểu cảm | `An: trái 1/3, quay sang phải; Minh: phải 1/3` |
| `motion` | Chuyển động máy quay / nhân vật theo thời gian | "slow push-in 8s", "An nghiêng đầu ở cue 2" |
| `caption` | Lời thoại hiển thị (phụ đề), **không** chiếm toàn khung | font dưới 1/3 màn hình |
| `palette` | Bảng màu kế thừa từ app (terracotta/paper) hoặc theo mood cảnh | `#c45136` accent |

Yêu cầu tối thiểu để **không** bị gọi là slide:
- Có **ít nhất một lớp background** (ảnh hoặc gradient có chiều sâu), không phải nền trắng trơn.
- Có **nhân vật** hiện diện bằng hình (sprite/SVG/ảnh cắt), không chỉ chữ.
- Có **chuyển động thật**: nhân vật hoặc máy quay di chuyển trong scene (qua GSAP).

## 4. Composition HTML — hợp đồng HyperFrames (bắt buộc đúng)

Cấu trúc gốc:

```html
<div id="root" data-composition-id="root" data-width="1920" data-height="1080">
  <audio id="voice" src="voiceover.wav" data-start="0" data-duration="<TỔNG_s>"
         data-track-index="0"></audio>

  <!-- MỖI SCENE là một clip full-frame, timing bằng SECONDS -->
  <div class="clip scene" data-start="<sceneStart_s>" data-duration="<sceneDur_s>"
       data-track-index="1">
    <img class="bg" src="assets/scene1_bg.png">          <!-- lớp nền, z-index thấp -->
    <img class="char an" src="assets/an.png">             <!-- nhân vật, z-index cao hơn -->
    <div class="cap" data-start="<cueStart_s>" data-duration="<cueDur_s>">
      Sáng hôm đó, An hẹn Minh ra quán cà phê quen.       <!-- phụ đề, không full-frame -->
    </div>
  </div>
  <!-- scene tiếp theo ... -->
</div>
```

Quy tắc cứng (đọc từ `hyperframes docs`):
- Timestamp trong HTML dùng **giây** (`startMs/1000`), định dạng `12.345`.
- Element có thời lượng phải mang `class="clip"` + `data-start` + `data-duration`.
- **Thứ tự vẽ dùng CSS `z-index`**, không dùng `data-track-index` (chỉ để hiển thị trong Studio).
- GSAP: luôn `gsap.timeline({ paused: true })`, đăng ký
  `window.__timelines["root"] = tl`. Chỉ dùng property được hỗ trợ:
  `opacity, x, y, scale, scaleX, scaleY, rotation, width, height, visibility`.
- Không tự chạy `play()`; runtime điều khiển.
- `#root` có `data-composition-id` **duy nhất**.

## 5. Tài nguyên hình ảnh cần sinh kèm

Thư mục `assets/` cạnh `index.html`:
- `sceneN_bg.png` — background mỗi cảnh (ImageGen, 1920×1080 hoặc 16:9).
- `char_<name>.png` — sprite nhân vật nền trong suốt, tái sử dụng xuyên cảnh.
- Nếu không có ảnh: **mở rộng `composition.py`** để sinh scene bằng CSS/SVG (gradient có chiều sâu,
  shape nhân vật, parallax) — vẫn phải thỏa mục 3.

## 6. Luồng tạo ra video (AI làm gì theo thứ tự)

1. Đọc chủ đề → viết **Script/SRT** theo mục 2 (kèm comment `# SCENE`).
2. Từ SRT, lập **Scene Brief** cho từng scene theo mục 3.
3. Sinh **assets** theo mục 5 (gọi ImageGen cho background, chuẩn bị sprite nhân vật).
4. Dựng **composition HTML** theo mục 4, bám đúng giây, z-index, GSAP paused.
5. Chạy `npx hyperframes lint`/`validate` để kiểm tra trước khi render.

## 7. Checklist nghiệm thu

- [ ] SRT: timestamp liền mạch, mỗi scene có comment `# SCENE` đủ 5 trường.
- [ ] Mỗi scene có background thật + ≥1 nhân vật + ≥1 chuyển động GSAP.
- [ ] HTML: `data-*` dùng giây; `class="clip"` đủ; `window.__timelines["root"]` tồn tại.
- [ ] Audio track khớp `durationMs` của `timeline.json`.
- [ ] `hyperframes validate` không lỗi JS/thiếu asset.
- [ ] Không còn cảnh nào chỉ là chữ đen giữa nền trắng (= slide).

## 8. Prompt rút gọn (copy vào AI khi cần sinh nhanh)

> "Viết cho tôi một video Code2Video về [CHỦ ĐỀ], [N] cảnh, giọng tiếng Việt.
> Xuất 2 thứ: (1) file `.srt` chia cue theo câu, mỗi câu ≤14 từ, timestamp liền mạch, và trên mỗi
> scene có dòng `# SCENE | setting | nhân vật | action | camera`; (2) composition HTML HyperFrames
> 1920×1080 với mỗi scene là một `div.clip` full-frame có `data-start`/`data-duration` bằng GIÂY,
> bên trong có lớp `background` (ảnh assets/sceneN_bg.png), `characters` (sprite, định vị bằng
> left/top + z-index), phụ đề ở 1/3 dưới, và GSAP `paused:true` đăng ký ở
> `window.__timelines['root']` tạo push-in/di chuyển nhân vật. KHÔNG làm slide chữ giữa nền trắng.
> Kèm Scene Brief 5 trường cho mỗi cảnh và danh sách ảnh cần ImageGen."
