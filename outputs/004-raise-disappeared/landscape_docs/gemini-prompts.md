# Prompt Gemini: nhân vật SVG + background

Mỗi nhân vật: mở một cuộc trò chuyện Gemini mới, dán prompt `front` trước (bắt buộc), rồi các prompt tùy chọn trong cùng cuộc trò chuyện để nhân vật đồng nhất.
Lưu **chỉ phần `<svg>...</svg>`** vào đúng đường dẫn ở tiêu đề mỗi prompt (thư mục `assets/` của project), rồi trong spec đặt `"external": true` cho nhân vật đó và chạy lại `generate.py --keep-srt --skip-bg`.
Nhân vật dùng file ngoài được di chuyển/nghiêng/nhún/đi ngang như một khối (không có khớp riêng); các file `talk`, `happy`, `sad`, `side`, `back` là bộ biến thể tùy chọn để thay khi cần (chưa tự động đổi trong render hiện tại).

Kiểm tra file: nền trong suốt, nhân vật ở giữa canvas 400×800, chân chạm đáy (y≈780), đầu tròn tâm (200,175).

## Nora (id `nora`)

- Vai trò: 
- Trang phục: young woman in a teal blouse and dark skirt, hair in a bun

### assets/nora.svg  ·  FRONT view, neutral

```text
You are an expert vector illustrator. Draw ONE SVG character sprite.
CHARACTER: Nora - character. young woman in a teal blouse and dark skirt, hair in a bun.
STYLE: Playful minimalist 'stickman explainer' cartoon: a big perfectly round WHITE head with a thick dark outline and a very expressive face (large oval black eyes with two small white highlights, thin curved eyebrows, pink blush ellipses on the cheeks, simple smiling mouth), a very short thin black neck, thin black arms and legs drawn as strokes (stroke width 9, round caps), each hand is ONE small solid black dot (no fingers), clothes are simple flat colour shapes with a 4-5 px dark outline and at most one soft shading gradient. No real person, no sports kit, no brand, no logo, no text.
VIEW / EXPRESSION: FRONT view, neutral. Facing the viewer. Eyes open looking straight ahead, relaxed eyebrows, mouth closed in a gentle small smile. Arms hang slightly away from the body, legs slightly apart.
CONSISTENCY: this is part of a set of images of the same character; keep the same proportions, head size, colours, clothes and line weight in all of them (if you already drew this character's neutral front image in this chat, reuse its design exactly).
TECHNICAL: output ONLY valid SVG code, no markdown fences, no explanation. Root element: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 800" width="400" height="800">. TRANSPARENT background (no background rectangle). Character centred at x=200, standing, soles of the feet touching y=780, whole body visible, nothing cropped. Head = circle centred at (200,175) with radius about 100 (top of head at y=75). Allowed elements: path, circle, ellipse, rect, polygon, g, linearGradient, radialGradient. No <image>, <text>, filters, masks, blur, clip-paths or external references; fewer than 150 elements; outline colour #1c1626.
```

### assets/nora_talk.svg  ·  FRONT view, talking  (tùy chọn)

```text
You are an expert vector illustrator. Draw ONE SVG character sprite.
CHARACTER: Nora - character. young woman in a teal blouse and dark skirt, hair in a bun.
STYLE: Playful minimalist 'stickman explainer' cartoon: a big perfectly round WHITE head with a thick dark outline and a very expressive face (large oval black eyes with two small white highlights, thin curved eyebrows, pink blush ellipses on the cheeks, simple smiling mouth), a very short thin black neck, thin black arms and legs drawn as strokes (stroke width 9, round caps), each hand is ONE small solid black dot (no fingers), clothes are simple flat colour shapes with a 4-5 px dark outline and at most one soft shading gradient. No real person, no sports kit, no brand, no logo, no text.
VIEW / EXPRESSION: FRONT view, talking. Same pose, clothes and head as the neutral front image; only the mouth changes: open mid-speech (dark inside, small pink tongue), eyebrows slightly raised.
CONSISTENCY: this is part of a set of images of the same character; keep the same proportions, head size, colours, clothes and line weight in all of them (if you already drew this character's neutral front image in this chat, reuse its design exactly).
TECHNICAL: output ONLY valid SVG code, no markdown fences, no explanation. Root element: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 800" width="400" height="800">. TRANSPARENT background (no background rectangle). Character centred at x=200, standing, soles of the feet touching y=780, whole body visible, nothing cropped. Head = circle centred at (200,175) with radius about 100 (top of head at y=75). Allowed elements: path, circle, ellipse, rect, polygon, g, linearGradient, radialGradient. No <image>, <text>, filters, masks, blur, clip-paths or external references; fewer than 150 elements; outline colour #1c1626.
```

### assets/nora_happy.svg  ·  FRONT view, very happy  (tùy chọn)

```text
You are an expert vector illustrator. Draw ONE SVG character sprite.
CHARACTER: Nora - character. young woman in a teal blouse and dark skirt, hair in a bun.
STYLE: Playful minimalist 'stickman explainer' cartoon: a big perfectly round WHITE head with a thick dark outline and a very expressive face (large oval black eyes with two small white highlights, thin curved eyebrows, pink blush ellipses on the cheeks, simple smiling mouth), a very short thin black neck, thin black arms and legs drawn as strokes (stroke width 9, round caps), each hand is ONE small solid black dot (no fingers), clothes are simple flat colour shapes with a 4-5 px dark outline and at most one soft shading gradient. No real person, no sports kit, no brand, no logo, no text.
VIEW / EXPRESSION: FRONT view, very happy. Same design. Eyes are closed happy arcs, big open laughing smile, extra rosy cheeks, arms raised a little.
CONSISTENCY: this is part of a set of images of the same character; keep the same proportions, head size, colours, clothes and line weight in all of them (if you already drew this character's neutral front image in this chat, reuse its design exactly).
TECHNICAL: output ONLY valid SVG code, no markdown fences, no explanation. Root element: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 800" width="400" height="800">. TRANSPARENT background (no background rectangle). Character centred at x=200, standing, soles of the feet touching y=780, whole body visible, nothing cropped. Head = circle centred at (200,175) with radius about 100 (top of head at y=75). Allowed elements: path, circle, ellipse, rect, polygon, g, linearGradient, radialGradient. No <image>, <text>, filters, masks, blur, clip-paths or external references; fewer than 150 elements; outline colour #1c1626.
```

### assets/nora_sad.svg  ·  FRONT view, sad  (tùy chọn)

```text
You are an expert vector illustrator. Draw ONE SVG character sprite.
CHARACTER: Nora - character. young woman in a teal blouse and dark skirt, hair in a bun.
STYLE: Playful minimalist 'stickman explainer' cartoon: a big perfectly round WHITE head with a thick dark outline and a very expressive face (large oval black eyes with two small white highlights, thin curved eyebrows, pink blush ellipses on the cheeks, simple smiling mouth), a very short thin black neck, thin black arms and legs drawn as strokes (stroke width 9, round caps), each hand is ONE small solid black dot (no fingers), clothes are simple flat colour shapes with a 4-5 px dark outline and at most one soft shading gradient. No real person, no sports kit, no brand, no logo, no text.
VIEW / EXPRESSION: FRONT view, sad. Same design. Eyebrows tilted up toward the middle, mouth a small downward curve, one small blue tear, shoulders lowered.
CONSISTENCY: this is part of a set of images of the same character; keep the same proportions, head size, colours, clothes and line weight in all of them (if you already drew this character's neutral front image in this chat, reuse its design exactly).
TECHNICAL: output ONLY valid SVG code, no markdown fences, no explanation. Root element: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 800" width="400" height="800">. TRANSPARENT background (no background rectangle). Character centred at x=200, standing, soles of the feet touching y=780, whole body visible, nothing cropped. Head = circle centred at (200,175) with radius about 100 (top of head at y=75). Allowed elements: path, circle, ellipse, rect, polygon, g, linearGradient, radialGradient. No <image>, <text>, filters, masks, blur, clip-paths or external references; fewer than 150 elements; outline colour #1c1626.
```

### assets/nora_side.svg  ·  SIDE view facing the viewer's RIGHT  (tùy chọn)

```text
You are an expert vector illustrator. Draw ONE SVG character sprite.
CHARACTER: Nora - character. young woman in a teal blouse and dark skirt, hair in a bun.
STYLE: Playful minimalist 'stickman explainer' cartoon: a big perfectly round WHITE head with a thick dark outline and a very expressive face (large oval black eyes with two small white highlights, thin curved eyebrows, pink blush ellipses on the cheeks, simple smiling mouth), a very short thin black neck, thin black arms and legs drawn as strokes (stroke width 9, round caps), each hand is ONE small solid black dot (no fingers), clothes are simple flat colour shapes with a 4-5 px dark outline and at most one soft shading gradient. No real person, no sports kit, no brand, no logo, no text.
VIEW / EXPRESSION: SIDE view facing the viewer's RIGHT. Full-body profile looking to the right edge of the canvas: head in profile with one eye, one eyebrow, mouth closed; both thin legs side by side, feet pointing right, one arm slightly forward.
CONSISTENCY: this is part of a set of images of the same character; keep the same proportions, head size, colours, clothes and line weight in all of them (if you already drew this character's neutral front image in this chat, reuse its design exactly).
TECHNICAL: output ONLY valid SVG code, no markdown fences, no explanation. Root element: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 800" width="400" height="800">. TRANSPARENT background (no background rectangle). Character centred at x=200, standing, soles of the feet touching y=780, whole body visible, nothing cropped. Head = circle centred at (200,175) with radius about 100 (top of head at y=75). Allowed elements: path, circle, ellipse, rect, polygon, g, linearGradient, radialGradient. No <image>, <text>, filters, masks, blur, clip-paths or external references; fewer than 150 elements; outline colour #1c1626.
```

### assets/nora_back.svg  ·  BACK view  (tùy chọn)

```text
You are an expert vector illustrator. Draw ONE SVG character sprite.
CHARACTER: Nora - character. young woman in a teal blouse and dark skirt, hair in a bun.
STYLE: Playful minimalist 'stickman explainer' cartoon: a big perfectly round WHITE head with a thick dark outline and a very expressive face (large oval black eyes with two small white highlights, thin curved eyebrows, pink blush ellipses on the cheeks, simple smiling mouth), a very short thin black neck, thin black arms and legs drawn as strokes (stroke width 9, round caps), each hand is ONE small solid black dot (no fingers), clothes are simple flat colour shapes with a 4-5 px dark outline and at most one soft shading gradient. No real person, no sports kit, no brand, no logo, no text.
VIEW / EXPRESSION: BACK view. Seen from behind: plain round head (hair or hat from behind if the character has one), no face, clothes seen from the back, arms down, legs slightly apart.
CONSISTENCY: this is part of a set of images of the same character; keep the same proportions, head size, colours, clothes and line weight in all of them (if you already drew this character's neutral front image in this chat, reuse its design exactly).
TECHNICAL: output ONLY valid SVG code, no markdown fences, no explanation. Root element: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 800" width="400" height="800">. TRANSPARENT background (no background rectangle). Character centred at x=200, standing, soles of the feet touching y=780, whole body visible, nothing cropped. Head = circle centred at (200,175) with radius about 100 (top of head at y=75). Allowed elements: path, circle, ellipse, rect, polygon, g, linearGradient, radialGradient. No <image>, <text>, filters, masks, blur, clip-paths or external references; fewer than 150 elements; outline colour #1c1626.
```

## Sam (id `sam`)

- Vai trò: 
- Trang phục: relaxed man in an orange hoodie, short dark hair

### assets/sam.svg  ·  FRONT view, neutral

```text
You are an expert vector illustrator. Draw ONE SVG character sprite.
CHARACTER: Sam - character. relaxed man in an orange hoodie, short dark hair.
STYLE: Playful minimalist 'stickman explainer' cartoon: a big perfectly round WHITE head with a thick dark outline and a very expressive face (large oval black eyes with two small white highlights, thin curved eyebrows, pink blush ellipses on the cheeks, simple smiling mouth), a very short thin black neck, thin black arms and legs drawn as strokes (stroke width 9, round caps), each hand is ONE small solid black dot (no fingers), clothes are simple flat colour shapes with a 4-5 px dark outline and at most one soft shading gradient. No real person, no sports kit, no brand, no logo, no text.
VIEW / EXPRESSION: FRONT view, neutral. Facing the viewer. Eyes open looking straight ahead, relaxed eyebrows, mouth closed in a gentle small smile. Arms hang slightly away from the body, legs slightly apart.
CONSISTENCY: this is part of a set of images of the same character; keep the same proportions, head size, colours, clothes and line weight in all of them (if you already drew this character's neutral front image in this chat, reuse its design exactly).
TECHNICAL: output ONLY valid SVG code, no markdown fences, no explanation. Root element: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 800" width="400" height="800">. TRANSPARENT background (no background rectangle). Character centred at x=200, standing, soles of the feet touching y=780, whole body visible, nothing cropped. Head = circle centred at (200,175) with radius about 100 (top of head at y=75). Allowed elements: path, circle, ellipse, rect, polygon, g, linearGradient, radialGradient. No <image>, <text>, filters, masks, blur, clip-paths or external references; fewer than 150 elements; outline colour #1c1626.
```

### assets/sam_talk.svg  ·  FRONT view, talking  (tùy chọn)

```text
You are an expert vector illustrator. Draw ONE SVG character sprite.
CHARACTER: Sam - character. relaxed man in an orange hoodie, short dark hair.
STYLE: Playful minimalist 'stickman explainer' cartoon: a big perfectly round WHITE head with a thick dark outline and a very expressive face (large oval black eyes with two small white highlights, thin curved eyebrows, pink blush ellipses on the cheeks, simple smiling mouth), a very short thin black neck, thin black arms and legs drawn as strokes (stroke width 9, round caps), each hand is ONE small solid black dot (no fingers), clothes are simple flat colour shapes with a 4-5 px dark outline and at most one soft shading gradient. No real person, no sports kit, no brand, no logo, no text.
VIEW / EXPRESSION: FRONT view, talking. Same pose, clothes and head as the neutral front image; only the mouth changes: open mid-speech (dark inside, small pink tongue), eyebrows slightly raised.
CONSISTENCY: this is part of a set of images of the same character; keep the same proportions, head size, colours, clothes and line weight in all of them (if you already drew this character's neutral front image in this chat, reuse its design exactly).
TECHNICAL: output ONLY valid SVG code, no markdown fences, no explanation. Root element: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 800" width="400" height="800">. TRANSPARENT background (no background rectangle). Character centred at x=200, standing, soles of the feet touching y=780, whole body visible, nothing cropped. Head = circle centred at (200,175) with radius about 100 (top of head at y=75). Allowed elements: path, circle, ellipse, rect, polygon, g, linearGradient, radialGradient. No <image>, <text>, filters, masks, blur, clip-paths or external references; fewer than 150 elements; outline colour #1c1626.
```

### assets/sam_happy.svg  ·  FRONT view, very happy  (tùy chọn)

```text
You are an expert vector illustrator. Draw ONE SVG character sprite.
CHARACTER: Sam - character. relaxed man in an orange hoodie, short dark hair.
STYLE: Playful minimalist 'stickman explainer' cartoon: a big perfectly round WHITE head with a thick dark outline and a very expressive face (large oval black eyes with two small white highlights, thin curved eyebrows, pink blush ellipses on the cheeks, simple smiling mouth), a very short thin black neck, thin black arms and legs drawn as strokes (stroke width 9, round caps), each hand is ONE small solid black dot (no fingers), clothes are simple flat colour shapes with a 4-5 px dark outline and at most one soft shading gradient. No real person, no sports kit, no brand, no logo, no text.
VIEW / EXPRESSION: FRONT view, very happy. Same design. Eyes are closed happy arcs, big open laughing smile, extra rosy cheeks, arms raised a little.
CONSISTENCY: this is part of a set of images of the same character; keep the same proportions, head size, colours, clothes and line weight in all of them (if you already drew this character's neutral front image in this chat, reuse its design exactly).
TECHNICAL: output ONLY valid SVG code, no markdown fences, no explanation. Root element: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 800" width="400" height="800">. TRANSPARENT background (no background rectangle). Character centred at x=200, standing, soles of the feet touching y=780, whole body visible, nothing cropped. Head = circle centred at (200,175) with radius about 100 (top of head at y=75). Allowed elements: path, circle, ellipse, rect, polygon, g, linearGradient, radialGradient. No <image>, <text>, filters, masks, blur, clip-paths or external references; fewer than 150 elements; outline colour #1c1626.
```

### assets/sam_sad.svg  ·  FRONT view, sad  (tùy chọn)

```text
You are an expert vector illustrator. Draw ONE SVG character sprite.
CHARACTER: Sam - character. relaxed man in an orange hoodie, short dark hair.
STYLE: Playful minimalist 'stickman explainer' cartoon: a big perfectly round WHITE head with a thick dark outline and a very expressive face (large oval black eyes with two small white highlights, thin curved eyebrows, pink blush ellipses on the cheeks, simple smiling mouth), a very short thin black neck, thin black arms and legs drawn as strokes (stroke width 9, round caps), each hand is ONE small solid black dot (no fingers), clothes are simple flat colour shapes with a 4-5 px dark outline and at most one soft shading gradient. No real person, no sports kit, no brand, no logo, no text.
VIEW / EXPRESSION: FRONT view, sad. Same design. Eyebrows tilted up toward the middle, mouth a small downward curve, one small blue tear, shoulders lowered.
CONSISTENCY: this is part of a set of images of the same character; keep the same proportions, head size, colours, clothes and line weight in all of them (if you already drew this character's neutral front image in this chat, reuse its design exactly).
TECHNICAL: output ONLY valid SVG code, no markdown fences, no explanation. Root element: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 800" width="400" height="800">. TRANSPARENT background (no background rectangle). Character centred at x=200, standing, soles of the feet touching y=780, whole body visible, nothing cropped. Head = circle centred at (200,175) with radius about 100 (top of head at y=75). Allowed elements: path, circle, ellipse, rect, polygon, g, linearGradient, radialGradient. No <image>, <text>, filters, masks, blur, clip-paths or external references; fewer than 150 elements; outline colour #1c1626.
```

### assets/sam_side.svg  ·  SIDE view facing the viewer's RIGHT  (tùy chọn)

```text
You are an expert vector illustrator. Draw ONE SVG character sprite.
CHARACTER: Sam - character. relaxed man in an orange hoodie, short dark hair.
STYLE: Playful minimalist 'stickman explainer' cartoon: a big perfectly round WHITE head with a thick dark outline and a very expressive face (large oval black eyes with two small white highlights, thin curved eyebrows, pink blush ellipses on the cheeks, simple smiling mouth), a very short thin black neck, thin black arms and legs drawn as strokes (stroke width 9, round caps), each hand is ONE small solid black dot (no fingers), clothes are simple flat colour shapes with a 4-5 px dark outline and at most one soft shading gradient. No real person, no sports kit, no brand, no logo, no text.
VIEW / EXPRESSION: SIDE view facing the viewer's RIGHT. Full-body profile looking to the right edge of the canvas: head in profile with one eye, one eyebrow, mouth closed; both thin legs side by side, feet pointing right, one arm slightly forward.
CONSISTENCY: this is part of a set of images of the same character; keep the same proportions, head size, colours, clothes and line weight in all of them (if you already drew this character's neutral front image in this chat, reuse its design exactly).
TECHNICAL: output ONLY valid SVG code, no markdown fences, no explanation. Root element: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 800" width="400" height="800">. TRANSPARENT background (no background rectangle). Character centred at x=200, standing, soles of the feet touching y=780, whole body visible, nothing cropped. Head = circle centred at (200,175) with radius about 100 (top of head at y=75). Allowed elements: path, circle, ellipse, rect, polygon, g, linearGradient, radialGradient. No <image>, <text>, filters, masks, blur, clip-paths or external references; fewer than 150 elements; outline colour #1c1626.
```

### assets/sam_back.svg  ·  BACK view  (tùy chọn)

```text
You are an expert vector illustrator. Draw ONE SVG character sprite.
CHARACTER: Sam - character. relaxed man in an orange hoodie, short dark hair.
STYLE: Playful minimalist 'stickman explainer' cartoon: a big perfectly round WHITE head with a thick dark outline and a very expressive face (large oval black eyes with two small white highlights, thin curved eyebrows, pink blush ellipses on the cheeks, simple smiling mouth), a very short thin black neck, thin black arms and legs drawn as strokes (stroke width 9, round caps), each hand is ONE small solid black dot (no fingers), clothes are simple flat colour shapes with a 4-5 px dark outline and at most one soft shading gradient. No real person, no sports kit, no brand, no logo, no text.
VIEW / EXPRESSION: BACK view. Seen from behind: plain round head (hair or hat from behind if the character has one), no face, clothes seen from the back, arms down, legs slightly apart.
CONSISTENCY: this is part of a set of images of the same character; keep the same proportions, head size, colours, clothes and line weight in all of them (if you already drew this character's neutral front image in this chat, reuse its design exactly).
TECHNICAL: output ONLY valid SVG code, no markdown fences, no explanation. Root element: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 800" width="400" height="800">. TRANSPARENT background (no background rectangle). Character centred at x=200, standing, soles of the feet touching y=780, whole body visible, nothing cropped. Head = circle centred at (200,175) with radius about 100 (top of head at y=75). Allowed elements: path, circle, ellipse, rect, polygon, g, linearGradient, radialGradient. No <image>, <text>, filters, masks, blur, clip-paths or external references; fewer than 150 elements; outline colour #1c1626.
```

## Ines (id `ines`)

- Vai trò: 
- Trang phục: colleague in a purple shirt, long black hair

### assets/ines.svg  ·  FRONT view, neutral

```text
You are an expert vector illustrator. Draw ONE SVG character sprite.
CHARACTER: Ines - character. colleague in a purple shirt, long black hair.
STYLE: Playful minimalist 'stickman explainer' cartoon: a big perfectly round WHITE head with a thick dark outline and a very expressive face (large oval black eyes with two small white highlights, thin curved eyebrows, pink blush ellipses on the cheeks, simple smiling mouth), a very short thin black neck, thin black arms and legs drawn as strokes (stroke width 9, round caps), each hand is ONE small solid black dot (no fingers), clothes are simple flat colour shapes with a 4-5 px dark outline and at most one soft shading gradient. No real person, no sports kit, no brand, no logo, no text.
VIEW / EXPRESSION: FRONT view, neutral. Facing the viewer. Eyes open looking straight ahead, relaxed eyebrows, mouth closed in a gentle small smile. Arms hang slightly away from the body, legs slightly apart.
CONSISTENCY: this is part of a set of images of the same character; keep the same proportions, head size, colours, clothes and line weight in all of them (if you already drew this character's neutral front image in this chat, reuse its design exactly).
TECHNICAL: output ONLY valid SVG code, no markdown fences, no explanation. Root element: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 800" width="400" height="800">. TRANSPARENT background (no background rectangle). Character centred at x=200, standing, soles of the feet touching y=780, whole body visible, nothing cropped. Head = circle centred at (200,175) with radius about 100 (top of head at y=75). Allowed elements: path, circle, ellipse, rect, polygon, g, linearGradient, radialGradient. No <image>, <text>, filters, masks, blur, clip-paths or external references; fewer than 150 elements; outline colour #1c1626.
```

### assets/ines_talk.svg  ·  FRONT view, talking  (tùy chọn)

```text
You are an expert vector illustrator. Draw ONE SVG character sprite.
CHARACTER: Ines - character. colleague in a purple shirt, long black hair.
STYLE: Playful minimalist 'stickman explainer' cartoon: a big perfectly round WHITE head with a thick dark outline and a very expressive face (large oval black eyes with two small white highlights, thin curved eyebrows, pink blush ellipses on the cheeks, simple smiling mouth), a very short thin black neck, thin black arms and legs drawn as strokes (stroke width 9, round caps), each hand is ONE small solid black dot (no fingers), clothes are simple flat colour shapes with a 4-5 px dark outline and at most one soft shading gradient. No real person, no sports kit, no brand, no logo, no text.
VIEW / EXPRESSION: FRONT view, talking. Same pose, clothes and head as the neutral front image; only the mouth changes: open mid-speech (dark inside, small pink tongue), eyebrows slightly raised.
CONSISTENCY: this is part of a set of images of the same character; keep the same proportions, head size, colours, clothes and line weight in all of them (if you already drew this character's neutral front image in this chat, reuse its design exactly).
TECHNICAL: output ONLY valid SVG code, no markdown fences, no explanation. Root element: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 800" width="400" height="800">. TRANSPARENT background (no background rectangle). Character centred at x=200, standing, soles of the feet touching y=780, whole body visible, nothing cropped. Head = circle centred at (200,175) with radius about 100 (top of head at y=75). Allowed elements: path, circle, ellipse, rect, polygon, g, linearGradient, radialGradient. No <image>, <text>, filters, masks, blur, clip-paths or external references; fewer than 150 elements; outline colour #1c1626.
```

### assets/ines_happy.svg  ·  FRONT view, very happy  (tùy chọn)

```text
You are an expert vector illustrator. Draw ONE SVG character sprite.
CHARACTER: Ines - character. colleague in a purple shirt, long black hair.
STYLE: Playful minimalist 'stickman explainer' cartoon: a big perfectly round WHITE head with a thick dark outline and a very expressive face (large oval black eyes with two small white highlights, thin curved eyebrows, pink blush ellipses on the cheeks, simple smiling mouth), a very short thin black neck, thin black arms and legs drawn as strokes (stroke width 9, round caps), each hand is ONE small solid black dot (no fingers), clothes are simple flat colour shapes with a 4-5 px dark outline and at most one soft shading gradient. No real person, no sports kit, no brand, no logo, no text.
VIEW / EXPRESSION: FRONT view, very happy. Same design. Eyes are closed happy arcs, big open laughing smile, extra rosy cheeks, arms raised a little.
CONSISTENCY: this is part of a set of images of the same character; keep the same proportions, head size, colours, clothes and line weight in all of them (if you already drew this character's neutral front image in this chat, reuse its design exactly).
TECHNICAL: output ONLY valid SVG code, no markdown fences, no explanation. Root element: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 800" width="400" height="800">. TRANSPARENT background (no background rectangle). Character centred at x=200, standing, soles of the feet touching y=780, whole body visible, nothing cropped. Head = circle centred at (200,175) with radius about 100 (top of head at y=75). Allowed elements: path, circle, ellipse, rect, polygon, g, linearGradient, radialGradient. No <image>, <text>, filters, masks, blur, clip-paths or external references; fewer than 150 elements; outline colour #1c1626.
```

### assets/ines_sad.svg  ·  FRONT view, sad  (tùy chọn)

```text
You are an expert vector illustrator. Draw ONE SVG character sprite.
CHARACTER: Ines - character. colleague in a purple shirt, long black hair.
STYLE: Playful minimalist 'stickman explainer' cartoon: a big perfectly round WHITE head with a thick dark outline and a very expressive face (large oval black eyes with two small white highlights, thin curved eyebrows, pink blush ellipses on the cheeks, simple smiling mouth), a very short thin black neck, thin black arms and legs drawn as strokes (stroke width 9, round caps), each hand is ONE small solid black dot (no fingers), clothes are simple flat colour shapes with a 4-5 px dark outline and at most one soft shading gradient. No real person, no sports kit, no brand, no logo, no text.
VIEW / EXPRESSION: FRONT view, sad. Same design. Eyebrows tilted up toward the middle, mouth a small downward curve, one small blue tear, shoulders lowered.
CONSISTENCY: this is part of a set of images of the same character; keep the same proportions, head size, colours, clothes and line weight in all of them (if you already drew this character's neutral front image in this chat, reuse its design exactly).
TECHNICAL: output ONLY valid SVG code, no markdown fences, no explanation. Root element: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 800" width="400" height="800">. TRANSPARENT background (no background rectangle). Character centred at x=200, standing, soles of the feet touching y=780, whole body visible, nothing cropped. Head = circle centred at (200,175) with radius about 100 (top of head at y=75). Allowed elements: path, circle, ellipse, rect, polygon, g, linearGradient, radialGradient. No <image>, <text>, filters, masks, blur, clip-paths or external references; fewer than 150 elements; outline colour #1c1626.
```

### assets/ines_side.svg  ·  SIDE view facing the viewer's RIGHT  (tùy chọn)

```text
You are an expert vector illustrator. Draw ONE SVG character sprite.
CHARACTER: Ines - character. colleague in a purple shirt, long black hair.
STYLE: Playful minimalist 'stickman explainer' cartoon: a big perfectly round WHITE head with a thick dark outline and a very expressive face (large oval black eyes with two small white highlights, thin curved eyebrows, pink blush ellipses on the cheeks, simple smiling mouth), a very short thin black neck, thin black arms and legs drawn as strokes (stroke width 9, round caps), each hand is ONE small solid black dot (no fingers), clothes are simple flat colour shapes with a 4-5 px dark outline and at most one soft shading gradient. No real person, no sports kit, no brand, no logo, no text.
VIEW / EXPRESSION: SIDE view facing the viewer's RIGHT. Full-body profile looking to the right edge of the canvas: head in profile with one eye, one eyebrow, mouth closed; both thin legs side by side, feet pointing right, one arm slightly forward.
CONSISTENCY: this is part of a set of images of the same character; keep the same proportions, head size, colours, clothes and line weight in all of them (if you already drew this character's neutral front image in this chat, reuse its design exactly).
TECHNICAL: output ONLY valid SVG code, no markdown fences, no explanation. Root element: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 800" width="400" height="800">. TRANSPARENT background (no background rectangle). Character centred at x=200, standing, soles of the feet touching y=780, whole body visible, nothing cropped. Head = circle centred at (200,175) with radius about 100 (top of head at y=75). Allowed elements: path, circle, ellipse, rect, polygon, g, linearGradient, radialGradient. No <image>, <text>, filters, masks, blur, clip-paths or external references; fewer than 150 elements; outline colour #1c1626.
```

### assets/ines_back.svg  ·  BACK view  (tùy chọn)

```text
You are an expert vector illustrator. Draw ONE SVG character sprite.
CHARACTER: Ines - character. colleague in a purple shirt, long black hair.
STYLE: Playful minimalist 'stickman explainer' cartoon: a big perfectly round WHITE head with a thick dark outline and a very expressive face (large oval black eyes with two small white highlights, thin curved eyebrows, pink blush ellipses on the cheeks, simple smiling mouth), a very short thin black neck, thin black arms and legs drawn as strokes (stroke width 9, round caps), each hand is ONE small solid black dot (no fingers), clothes are simple flat colour shapes with a 4-5 px dark outline and at most one soft shading gradient. No real person, no sports kit, no brand, no logo, no text.
VIEW / EXPRESSION: BACK view. Seen from behind: plain round head (hair or hat from behind if the character has one), no face, clothes seen from the back, arms down, legs slightly apart.
CONSISTENCY: this is part of a set of images of the same character; keep the same proportions, head size, colours, clothes and line weight in all of them (if you already drew this character's neutral front image in this chat, reuse its design exactly).
TECHNICAL: output ONLY valid SVG code, no markdown fences, no explanation. Root element: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 800" width="400" height="800">. TRANSPARENT background (no background rectangle). Character centred at x=200, standing, soles of the feet touching y=780, whole body visible, nothing cropped. Head = circle centred at (200,175) with radius about 100 (top of head at y=75). Allowed elements: path, circle, ellipse, rect, polygon, g, linearGradient, radialGradient. No <image>, <text>, filters, masks, blur, clip-paths or external references; fewer than 150 elements; outline colour #1c1626.
```

# Background (bối cảnh) — lưu PNG 1920×1080 vào assets/

Mỗi bối cảnh một ảnh. Dán prompt vào Gemini (tạo ảnh), tải về PNG và lưu đúng tên. Muốn dùng ảnh Gemini thay ảnh 3D của skill: thêm vào spec `"external_bg": true` (hoặc danh sách id bối cảnh) rồi chạy lại `generate.py --keep-srt --skip-bg`.

## assets/bg_living.png  (bối cảnh `living`)

```text
You are an expert background artist. Draw ONE 16:9 background image (1920x1080 px, PNG) for an animated video.
SCENE (living): interior scene, daytime / dusk; main elements: .
STYLE: Flat-colour 3D-toon illustration (soft cel shading, simple geometric shapes, thin dark ink outlines, gentle depth-of-field), same art style as a minimalist stickman cartoon explainer. Rich but clean details, warm/cool light contrast, subtle vignette.
COMPOSITION: wide establishing view with the camera at about eye height; horizon / floor line at about 62% of the height; the lower-middle area (x 15-85%, y 55-90%) is open ground or floor where characters will stand; keep the bottom 22% calm (no important detail, captions go there); important props near the left and right thirds, nothing tall in the exact centre. NO people, NO characters, NO animals, NO text, NO logos, NO watermarks, no frame or border. Seamless edges, no transparency (full-bleed picture).
```

## assets/bg_cafe.png  (bối cảnh `cafe`)

```text
You are an expert background artist. Draw ONE 16:9 background image (1920x1080 px, PNG) for an animated video.
SCENE (cafe): interior scene, daytime / dusk; main elements: .
STYLE: Flat-colour 3D-toon illustration (soft cel shading, simple geometric shapes, thin dark ink outlines, gentle depth-of-field), same art style as a minimalist stickman cartoon explainer. Rich but clean details, warm/cool light contrast, subtle vignette.
COMPOSITION: wide establishing view with the camera at about eye height; horizon / floor line at about 62% of the height; the lower-middle area (x 15-85%, y 55-90%) is open ground or floor where characters will stand; keep the bottom 22% calm (no important detail, captions go there); important props near the left and right thirds, nothing tall in the exact centre. NO people, NO characters, NO animals, NO text, NO logos, NO watermarks, no frame or border. Seamless edges, no transparency (full-bleed picture).
```

## assets/bg_bedroom.png  (bối cảnh `bedroom`)

```text
You are an expert background artist. Draw ONE 16:9 background image (1920x1080 px, PNG) for an animated video.
SCENE (bedroom): interior scene, daytime / dusk; main elements: .
STYLE: Flat-colour 3D-toon illustration (soft cel shading, simple geometric shapes, thin dark ink outlines, gentle depth-of-field), same art style as a minimalist stickman cartoon explainer. Rich but clean details, warm/cool light contrast, subtle vignette.
COMPOSITION: wide establishing view with the camera at about eye height; horizon / floor line at about 62% of the height; the lower-middle area (x 15-85%, y 55-90%) is open ground or floor where characters will stand; keep the bottom 22% calm (no important detail, captions go there); important props near the left and right thirds, nothing tall in the exact centre. NO people, NO characters, NO animals, NO text, NO logos, NO watermarks, no frame or border. Seamless edges, no transparency (full-bleed picture).
```

## assets/bg_grocery.png  (bối cảnh `grocery`)

```text
You are an expert background artist. Draw ONE 16:9 background image (1920x1080 px, PNG) for an animated video.
SCENE (grocery): interior scene, daytime / dusk; main elements: .
STYLE: Flat-colour 3D-toon illustration (soft cel shading, simple geometric shapes, thin dark ink outlines, gentle depth-of-field), same art style as a minimalist stickman cartoon explainer. Rich but clean details, warm/cool light contrast, subtle vignette.
COMPOSITION: wide establishing view with the camera at about eye height; horizon / floor line at about 62% of the height; the lower-middle area (x 15-85%, y 55-90%) is open ground or floor where characters will stand; keep the bottom 22% calm (no important detail, captions go there); important props near the left and right thirds, nothing tall in the exact centre. NO people, NO characters, NO animals, NO text, NO logos, NO watermarks, no frame or border. Seamless edges, no transparency (full-bleed picture).
```

## assets/bg_shop.png  (bối cảnh `shop`)

```text
You are an expert background artist. Draw ONE 16:9 background image (1920x1080 px, PNG) for an animated video.
SCENE (shop): interior scene, daytime / dusk; main elements: .
STYLE: Flat-colour 3D-toon illustration (soft cel shading, simple geometric shapes, thin dark ink outlines, gentle depth-of-field), same art style as a minimalist stickman cartoon explainer. Rich but clean details, warm/cool light contrast, subtle vignette.
COMPOSITION: wide establishing view with the camera at about eye height; horizon / floor line at about 62% of the height; the lower-middle area (x 15-85%, y 55-90%) is open ground or floor where characters will stand; keep the bottom 22% calm (no important detail, captions go there); important props near the left and right thirds, nothing tall in the exact centre. NO people, NO characters, NO animals, NO text, NO logos, NO watermarks, no frame or border. Seamless edges, no transparency (full-bleed picture).
```

## assets/bg_kitchen.png  (bối cảnh `kitchen`)

```text
You are an expert background artist. Draw ONE 16:9 background image (1920x1080 px, PNG) for an animated video.
SCENE (kitchen): interior scene, daytime / dusk; main elements: .
STYLE: Flat-colour 3D-toon illustration (soft cel shading, simple geometric shapes, thin dark ink outlines, gentle depth-of-field), same art style as a minimalist stickman cartoon explainer. Rich but clean details, warm/cool light contrast, subtle vignette.
COMPOSITION: wide establishing view with the camera at about eye height; horizon / floor line at about 62% of the height; the lower-middle area (x 15-85%, y 55-90%) is open ground or floor where characters will stand; keep the bottom 22% calm (no important detail, captions go there); important props near the left and right thirds, nothing tall in the exact centre. NO people, NO characters, NO animals, NO text, NO logos, NO watermarks, no frame or border. Seamless edges, no transparency (full-bleed picture).
```

## assets/bg_office.png  (bối cảnh `office`)

```text
You are an expert background artist. Draw ONE 16:9 background image (1920x1080 px, PNG) for an animated video.
SCENE (office): interior scene, daytime / dusk; main elements: .
STYLE: Flat-colour 3D-toon illustration (soft cel shading, simple geometric shapes, thin dark ink outlines, gentle depth-of-field), same art style as a minimalist stickman cartoon explainer. Rich but clean details, warm/cool light contrast, subtle vignette.
COMPOSITION: wide establishing view with the camera at about eye height; horizon / floor line at about 62% of the height; the lower-middle area (x 15-85%, y 55-90%) is open ground or floor where characters will stand; keep the bottom 22% calm (no important detail, captions go there); important props near the left and right thirds, nothing tall in the exact centre. NO people, NO characters, NO animals, NO text, NO logos, NO watermarks, no frame or border. Seamless edges, no transparency (full-bleed picture).
```

## assets/bg_street.png  (bối cảnh `street`)

```text
You are an expert background artist. Draw ONE 16:9 background image (1920x1080 px, PNG) for an animated video.
SCENE (street): interior scene, daytime / dusk; main elements: .
STYLE: Flat-colour 3D-toon illustration (soft cel shading, simple geometric shapes, thin dark ink outlines, gentle depth-of-field), same art style as a minimalist stickman cartoon explainer. Rich but clean details, warm/cool light contrast, subtle vignette.
COMPOSITION: wide establishing view with the camera at about eye height; horizon / floor line at about 62% of the height; the lower-middle area (x 15-85%, y 55-90%) is open ground or floor where characters will stand; keep the bottom 22% calm (no important detail, captions go there); important props near the left and right thirds, nothing tall in the exact centre. NO people, NO characters, NO animals, NO text, NO logos, NO watermarks, no frame or border. Seamless edges, no transparency (full-bleed picture).
```
