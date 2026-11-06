# Workflow Automation (kéo-thả card, ý tưởng → video) — Thiết kế

**Ngày:** 2026-11-04
**Trạng thái:** Đã duyệt thiết kế (các phần 1–6), UI điều chỉnh: chức năng tổ chức bằng **sidebar** dọc thay vì hàng tab.

## Mục tiêu

Thêm chế độ **Workflow Automation** vào Code2Video Studio: người dùng kéo-thả các **card** (step) để dựng một flow tự động hóa việc tạo video từ ý tưởng đến video hoàn chỉnh. Mỗi card AI cho phép nhập **prompt**, chọn **model** (provider từ Settings) và gắn **skill**; một flow có thể dùng **nhiều model khác nhau**. Flow hỗ trợ **loop và rẽ nhánh hoàn toàn tự động** (điều kiện trên dữ liệu, không chặn thủ công) vì tương lai flow sẽ được kích hoạt headless từ nguồn ý tưởng crawl/phân tích internet và job nền. Có sẵn **2 template** đề xuất cho 2 engine kèm model gợi ý theo từng bước.

**Ràng buộc bắt buộc:**
- Các chế độ hiện tại giữ nguyên: upload thủ công (File lẻ, Folder, whiteboard Folder/Thủ công) và AI Kịch bản — automation chỉ là chế độ thêm vào.
- Tool chạy local/offline: canvas tự dựng (HTML5 drag + SVG), **không dùng thư viện qua CDN**.
- API key không nằm trong file flow — key vẫn ở `settings/ai.json`.

## Kiến trúc

Flow được lưu thành **file JSON** tại `flows/<tên>.flow.json` (tracked trong git). Toàn bộ logic chạy nằm ở **executor Python headless** (`src/code2video/flow/`) — UI chỉ là trình soạn thảo; điều này chừa sẵn chỗ cho trigger/job nền ở tương lai.

### Flow JSON schema (ví dụ)

```json
{
  "id": "wb-story",
  "name": "Whiteboard Kể chuyện",
  "engine": "whiteboard",
  "start": "idea",
  "nodes": {
    "idea":     {"type": "idea", "label": "Ý tưởng", "config": {"text": "Vụ án phòng kín bất khả thi", "language": "vi", "minutes": 3}},
    "script":   {"type": "ai-script", "label": "AI kịch bản", "config": {"provider": "gemini", "skill": "whiteboard", "prompt": ""}},
    "scenes":   {"type": "build-scenes", "label": "Dựng scene", "config": {}},
    "tts":      {"type": "tts", "label": "Voiceover", "config": {"voice": "", "ttsMode": "v3turbo", "dryRun": false}},
    "render":   {"type": "render", "label": "Render", "config": {"fps": 60, "format": "16:9", "formatMode": "fit"}},
    "merge":    {"type": "merge", "label": "Ghép cảnh", "config": {}}
  },
  "edges": [
    {"from": "idea",   "to": "script"},
    {"from": "script", "to": "script", "condition": {"field": "script.error", "op": "exists"}, "maxLoop": 3},
    {"from": "script", "to": "scenes", "condition": {"field": "script.scenes", "op": "exists"}},
    {"from": "scenes", "to": "tts"},
    {"from": "tts",    "to": "render"},
    {"from": "render", "to": "merge"}
  ]
}
```

Quy ước:
- `nodes` là object map id → node; `edges` là danh sách; `start` là id node đầu tiên.
- `condition` dạng `{"field": "a.b.c", "op": "eq|ne|gt|lt|in|exists|missing", "value": ...}`; thiếu `condition` = luôn đi được. Field thiếu trong state → điều kiện `false` (trừ `missing`).
- `maxLoop` (mặc định 3): số lần tối đa đi qua cùng một dây nối trong một lần chạy.
- Output của node **ghi đè toàn bộ** `state[id]` — một node chạy lại sẽ xóa `*.error` cũ (ví dụ trên: `script` chạy lại thành công thì `script.error` biến mất, dây retry không còn khớp).

### State

Một `dict` JSON tích lũy xuyên suốt flow. Node đọc state đầu vào, ghi output (ghi đè toàn bộ) dưới key = id node; các key chuẩn: `topic`, `scenes`, `resources` (danh sách thư mục scene), `project` (thư mục HyperFrames), `video` (đường dẫn mp4), `<id>.error` (thông báo lỗi để điều kiện/loop bắt). Node `idea` ghi `state.idea = {topic, language, minutes}` và đồng thời `state.topic`.

### Executor (`src/code2video/flow/`)

- `flow.py` — `run_flow(flow: dict, state: dict, on_step) -> dict`:
  1. Bắt đầu từ `start`; lặp: chạy node hiện tại (gọi registry), ghi output vào state.
  2. Xét các dây nối ra từ node hiện tại **theo thứ tự khai báo**, lọc dây có `condition` thỏa mãn; chọn dây đầu tiên khớp. Không dây nào khớp → flow kết thúc bình thường (nhánh chết được phép).
  3. Đếm số lần đi qua mỗi dây; vượt `maxLoop` → lỗi `Flow lặp quá N lần tại dây X → Y`.
  4. Node ném lỗi → ghi `state["<id>.error"]`, flow dừng và lỗi kèm id node.
  5. `on_step(node_id, kind, message)` để UI cập nhật tiến trình (stage).
- `conditions.py` — `evaluate(condition: dict, state: dict) -> bool`; hỗ trợ field lồng nhau (tách theo dấu `.`), các toán tử: `eq, ne, gt, lt, in, exists, missing`.
- `nodes.py` — registry `NODES: dict[str, callable]`, mỗi hàm `(state, config, ctx) -> dict` (output ghi vào state). Tái dùng module hiện có.

## Bộ card v1

Mỗi card AI có `config.provider` (id trong `settings/ai.json`), `config.skill` (id skill), `config.prompt` (bổ sung/ghi đè system prompt) → một flow dùng được nhiều model.

| Card | Engine | Đầu vào (state) | Hành động | Output (state) |
|---|---|---|---|---|
| `idea` | cả hai | — | lấy topic/language/minutes từ config | `topic` |
| `ai-script` | cả hai | `topic` | LLM (provider+skill+prompt) sinh kịch bản; validate `parse_script_payload` | `script.scenes` (hoặc `script.error`) |
| `build-scenes` | whiteboard | `script.scenes` | `build_scene_folder` cho từng scene vào thư mục chạy | `resources = [thư mục scene]` |
| `ai-html` | hyperframes | `script.scenes` | LLM sinh index.html + assets (system prompt = `docs/claude-code-skill-brief.md`) | `project = thư mục` |
| `tts` | cả hai | `resources` / `project` | `build_whiteboard_from_script` (từng scene) / `prepare_composition_audio` | voiceover + timeline trong từng thư mục |
| `render` | cả hai | các thư mục đã có voiceover | `render_whiteboard` / `render_hyperframes` | `output.mp4` từng phần |
| `merge` | whiteboard | các scene video | `merge_whiteboard_scenes` + `apply_format` | `video` |

HyperFrames không có card `merge` (render ra 1 video). Provider `demo` (offline) được phép ở mọi card AI.

## Templates (`flows/templates/`)

1. **Whiteboard Kể chuyện** — `idea → ai-script (gemini, skill whiteboard) → build-scenes → tts → render → merge`; loop `script → script` khi `script.error` tồn tại (maxLoop 3). Model gợi ý: `gemini-2.0-flash`.
2. **HyperFrames Kịch bản cảnh** — `idea → ai-script (gemini) → ai-html (openrouter, model `deepseek/deepseek-chat-v3-0324:free`) → tts → render`. 

Template chỉ gợi ý model — khi chạy, provider phải có key trong Settings; thiếu key → lỗi rõ ràng ở card đó.

## UI — sidebar + canvas

- **Sidebar dọc (trái)** thay hàng tab hiện tại, các mục chức năng:
  - **File lẻ** (HyperFrames upload lẻ), **Folder** (HyperFrames folder), **AI Kịch bản** (whiteboard AI, giữ nguyên panel hiện có), **Workflow** (mới), và mục **Settings** (AI provider & skills — chuyển panel settings AI từ tab whiteboard lên đây, dùng chung cho cả AI Kịch bản và Workflow).
  - Chọn engine Whiteboard → các mục whiteboard hiển thị (Folder/Thủ công/AI Kịch bản như wtab cũ); engine HyperFrames → File lẻ/Folder. Workflow luôn hiển thị (engine do từng flow quyết định).
- **Vùng nội dung (phải)**: thanh cài đặt chung (engine, ngôn ngữ, khung hình, fps, workers) + panel của chức năng đang chọn.
- **Màn hình Workflow**:
  - Trái trong: thư viện card (kéo vào canvas; card không hợp lệ với engine flow đang mở bị mờ).
  - Giữa: canvas — card là khối có cổng vào/ra, kéo cổng ra → cổng vào để nối dây (SVG); click dây → panel đặt `condition` + `maxLoop`; click card → panel phải cấu hình (label, provider, skill, prompt, tham số riêng).
  - Nút: *Tạo từ template*, *Lưu*, *Mở*, *Xóa*, *Chạy*. Chạy → job mode `flow` trong JobQueue, tiến trình qua SSE như hiện tại; card đang chạy được tô sáng, card lỗi tô đỏ.
- Canvas tự dựng bằng HTML5 drag events + SVG, không thư viện ngoài.

## API mới

- `GET /api/flow` — danh sách flow (id, tên, engine).
- `POST /api/flow/from-template` — body `{template: "wb-story" | "hf-scenes", name}` → tạo file flow mới từ template, trả flow.
- `GET /api/flow/{flow_id}` — đọc flow.
- `PUT /api/flow/{flow_id}` — ghi flow (validate schema: node type hợp lệ, dây nối trỏ đúng node, có `start`).
- `DELETE /api/flow/{flow_id}` — xóa file flow.
- `POST /api/flow/run` — body `{flowId, topic?}` → chạy headless, trả jobId (mode `flow`).

## Xử lý lỗi

- Node lỗi → flow dừng, job `error` kèm id node + message; UI tô đỏ card lỗi.
- Loop vượt `maxLoop` → lỗi `Flow lặp quá N lần tại dây X → Y`.
- Nhiều dây ra khớp điều kiện → ưu tiên dây khai báo trước; không dây khớp → kết thúc bình thường.
- Chạy lại luôn chạy từ đầu (v1 không cache bước giữa chừng).
- Job flow chạy trong worker thread (tuân thủ khóa TTS tuần tự của JobQueue).

## Testing (TDD)

- `conditions.py`: từng toán tử, field lồng, field thiếu, `missing`.
- `flow.py`: đồ thị nhỏ với node fake — chuỗi thẳng; rẽ nhánh theo điều kiện; loop đến `maxLoop` thì lỗi; lỗi giữa chừng dừng đúng node và ghi `*.error`.
- Từng node thật: `ai-script` (provider demo), `build-scenes` (sinh đủ PNG+annotation+SRT), `tts` (dry-run), `merge`.
- API: lưu/mở/xóa flow, validate schema, chạy flow tạo job đúng params.
- E2E: chạy template Whiteboard với Demo provider + dry-run TTS → ra video merge thật (chứng minh bằng file).

## Ngoài phạm vi v1 (định hướng)

- Node `http`/`crawl` (ý tưởng từ internet), scheduler chạy flow định kỳ, cache kết quả node để resume — executor headless đã chừa sẵn chỗ, sẽ có kế hoạch riêng.
