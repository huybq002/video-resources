// ── Workflow theo step: mỗi engine có đủ các bước từ ý tưởng tới video hoàn chỉnh ──
(function () {
  const STEP_INFO = {
    idea: { label: "Ý tưởng", desc: "Nhập prompt: video này nói về điều gì.", config: { text: "", language: "vi", minutes: 3 } },
    skill: { label: "Skill", desc: "Tùy chọn. Chọn tối đa 4 skill, gộp lại làm system prompt cho AI viết kịch bản.", config: { skills: [] } },
    "ai-script": { label: "AI kịch bản", desc: "AI viết kịch bản chia theo cảnh và câu thoại.", config: { provider: "demo", skill: "whiteboard", prompt: "", characters: [] } },
    "build-scenes": { label: "Hình ảnh", desc: "Dựng hình từng cảnh từ bộ doodle có sẵn của app.", config: {} },
    "ai-image": { label: "Hình ảnh", desc: "AI tự vẽ ảnh cho từng cảnh theo kịch bản.", config: { provider: "", prompt: "", size: "" } },
    "ai-html": { label: "AI dựng HTML", desc: "AI sinh trang HTML có animation, bám đúng thời gian giọng đọc thật ở bước trước.", config: { provider: "", prompt: "" } },
    tts: { label: "Giọng đọc", desc: "Đọc kịch bản thành giọng nói và canh thời gian.", config: { voice: "", ttsMode: "v3turbo", dryRun: false } },
    render: { label: "Render", desc: "Xuất video từ hình và giọng đọc.", config: { fps: 60, format: "16:9", formatMode: "fit", longEdge: 1080, quality: "delivery" } },
    merge: { label: "Ghép cảnh", desc: "Ghép các cảnh thành một video hoàn chỉnh.", config: {} },
  };
  const AI_TYPES = ["ai-script", "ai-image", "ai-html"];
  const DEFAULT_IDS = { idea: "idea", skill: "skill", "ai-script": "script", "build-scenes": "scenes", "ai-image": "image", "ai-html": "html", tts: "tts", render: "render", merge: "merge" };
  const DEFAULT_RETRIES = 2;
  const MAX_SKILLS = 4;

  const st = { draft: null, id: null, step: "idea", dirty: false, list: [], providers: [], skills: [], es: null, run: null, ticker: null, panelKey: "" };
  const q = (id) => document.getElementById(id);
  const clone = (x) => JSON.parse(JSON.stringify(x));

  function msg(text, kind) {
    const el = q("wfMsg");
    el.textContent = text || "";
    el.className = "wf-msg" + (kind ? " is-" + kind : "");
    if (text && kind) toast(text, kind === "ok" ? "success" : kind);
  }

  async function api(url, options) {
    const res = await fetch(url, options);
    let data = null;
    try { data = await res.json(); } catch (_) { /* không có body */ }
    if (!res.ok) throw new Error((data && data.detail) || res.statusText);
    return data;
  }
  const jsonOpts = (method, body) => ({ method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

  function slug(name) {
    return (name || "flow").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/g, "d")
      .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 48) || "flow";
  }

  // ── bản nháp <-> flow JSON ──
  function newDraft(engine, name) {
    const cfg = {};
    for (const [type, info] of Object.entries(STEP_INFO)) cfg[type] = clone(info.config);
    // không tự chọn provider hay model: người dùng phải chọn ở từng bước (bước chưa chọn sẽ có dấu ⚠)
    cfg["ai-script"].provider = "";
    cfg["ai-html"].provider = "";
    cfg["ai-image"].provider = "";
    return { name: name || "Video mới", engine, useSkill: false, visual: "build-scenes", retries: { "ai-script": DEFAULT_RETRIES, "ai-image": DEFAULT_RETRIES, "ai-html": DEFAULT_RETRIES }, cfg, ids: { ...DEFAULT_IDS } };
  }

  function draftFromFlow(flow) {
    const d = newDraft(flow.engine || "whiteboard", flow.name);
    const nodes = Object.entries(flow.nodes || {});
    for (const [id, node] of nodes) {
      if (!STEP_INFO[node.type]) continue;
      d.ids[node.type] = id;
      d.cfg[node.type] = { ...d.cfg[node.type], ...(node.config || {}) };
    }
    const sk = d.cfg.skill;   // flow cũ chỉ có một skill
    if (!Array.isArray(sk.skills) || !sk.skills.length) sk.skills = sk.skill ? [sk.skill] : [];
    delete sk.skill;
    const has = (t) => nodes.some(([, n]) => n.type === t);
    d.useSkill = has("skill");
    d.visual = has("build-scenes") && !has("ai-image") ? "build-scenes" : "ai-image";
    for (const e of flow.edges || []) {
      const node = flow.nodes[e.from];
      if (e.from === e.to && node && AI_TYPES.includes(node.type) && e.maxLoop) d.retries[node.type] = e.maxLoop;
    }
    return d;
  }

  // chuỗi bước đầy đủ của engine; bước Skill vẫn hiện nhưng có thể tắt
  function stepTypes(d) {
    return d.engine === "whiteboard"
      ? ["idea", "skill", "ai-script", d.visual, "tts", "render", "merge"]
      : ["idea", "skill", "ai-script", "tts", "ai-html", "render"];
  }
  const activeTypes = (d) => stepTypes(d).filter((t) => t !== "skill" || d.useSkill);
  const labelOf = (type) => STEP_INFO[type].label;

  function buildFlow(d) {
    const chain = activeTypes(d);
    const nodes = {}, edges = [];
    chain.forEach((type) => { nodes[d.ids[type]] = { type, label: labelOf(type), config: clone(d.cfg[type]) }; });
    chain.forEach((type, i) => {
      const id = d.ids[type];
      if (AI_TYPES.includes(type)) edges.push({ from: id, to: id, condition: { field: `${id}.error`, op: "exists" }, maxLoop: d.retries[type] || DEFAULT_RETRIES });
      if (i < chain.length - 1) edges.push({ from: id, to: d.ids[chain[i + 1]] });
    });
    return { name: d.name, engine: d.engine, start: d.ids[chain[0]], nodes, edges };
  }

  // ── kiểm tra từng bước trước khi chạy ──
  function providerIssue(id, needImage) {
    if (!id) return "Chưa chọn provider.";
    const p = st.providers.find((x) => x.id === id);
    if (!p) return `Provider "${id}" không còn trong Settings.`;
    if (!p.hasKey) return `${p.label} chưa có API key (vào Settings).`;
    if (needImage) return p.imageModel ? null : `${p.label} chưa có "Model tạo ảnh" (vào Settings).`;
    return p.model ? null : `${p.label} chưa chọn model (vào Settings).`;
  }

  function stepIssue(type) {
    const c = st.draft.cfg[type];
    if (type === "idea") return String(c.text || "").trim() ? null : "Chưa nhập ý tưởng.";
    if (type === "skill") {
      if (!st.draft.useSkill) return null;
      const valid = c.skills.filter((id) => st.skills.some((s) => s.id === id));
      if (!valid.length) return "Chưa chọn skill nào.";
      return valid.length > MAX_SKILLS ? `Chỉ dùng tối đa ${MAX_SKILLS} skill.` : null;
    }
    if (type === "ai-script") return c.provider === "demo" ? null : providerIssue(c.provider);
    if (type === "ai-image") return providerIssue(c.provider, true);
    if (type === "ai-html") return providerIssue(c.provider);
    return null;
  }

  function stepSummary(type) {
    const c = st.draft.cfg[type];
    switch (type) {
      case "idea": return c.text ? c.text : "Chưa nhập";
      case "skill": {
        if (!st.draft.useSkill) return "Không dùng";
        const names = c.skills.map((id) => (st.skills.find((x) => x.id === id) || {}).name).filter(Boolean);
        return names.length ? names.join(" + ") : "Chưa chọn";
      }
      case "ai-script": return (c.provider === "demo" ? "Demo (không gọi AI)" : c.provider || "Chưa chọn provider") + ((c.characters || []).length >= 2 ? ` · ${c.characters.length} nhân vật` : "");
      case "ai-image": return `AI vẽ · ${c.provider || "chưa chọn provider"}`;
      case "build-scenes": return "Doodle của app";
      case "ai-html": return c.provider || "Chưa chọn provider";
      case "tts": {
        const n = characterNames().length >= 2 ? Object.keys(c.speakers || {}).filter((k) => characterNames().includes(k)).length : 0;
        return c.dryRun ? "Dry-run (im lặng)" : `${c.ttsMode}${n ? ` · ${n} giọng riêng` : c.voice ? " · " + c.voice : ""}`;
      }
      case "render": return `${c.fps}fps · ${c.format}`;
      case "merge": return "Video cuối";
      default: return "";
    }
  }

  // ── nạp/lưu ──
  async function refreshList(selectId) {
    st.list = await api("/api/flow");
    const sel = q("wfFlowSelect");
    sel.innerHTML = `<option value="">— video đã lưu —</option>` +
      st.list.map((f) => `<option value="${esc(f.id)}">${esc(f.name)} (${esc(f.engine)})</option>`).join("");
    sel.value = selectId !== undefined ? selectId : st.id || "";
  }

  function setDraft(draft, id) {
    if (st.es) { st.es.close(); st.es = null; }
    stopTicker();
    st.draft = draft; st.id = id; st.step = "idea"; st.dirty = false; st.run = null;
    q("wfName").value = draft.name || "";
    q("wfEngine").value = draft.engine;
    q("wfResult").hidden = true;
    renderAll();
  }

  async function openFlow(id) {
    if (!id) return;
    setLoading(q("wfBody"), true);
    try {
      setDraft(draftFromFlow(await api("/api/flow/" + encodeURIComponent(id))), id);
      msg("");
      await loadLastRun(id);
    } catch (e) { msg(e.message, "error"); }
    finally { setLoading(q("wfBody"), false); }
  }

  function createNew() {
    if (st.dirty && !confirm("Bản đang sửa chưa lưu. Tạo video mới và bỏ các thay đổi?")) return;
    setDraft(newDraft(q("wfEngine").value, ""), null);
    q("wfFlowSelect").value = "";
    st.dirty = true;
    msg("Video mới. Đi lần lượt từng bước rồi bấm Chạy.");
  }

  async function saveFlow() {
    const d = st.draft;
    if (!d) return false;
    d.name = q("wfName").value.trim() || d.name || "Video";
    let id = st.id;
    if (!id) {
      const taken = new Set(st.list.map((f) => f.id));
      const base = slug(d.name);
      id = base;
      for (let n = 2; taken.has(id); n++) id = `${base}-${n}`;
    }
    try {
      await api("/api/flow/" + encodeURIComponent(id), jsonOpts("PUT", buildFlow(d)));
      st.id = id; st.dirty = false;
      await refreshList(id);
      msg("Đã lưu.", "ok");
      renderToolbar();
      return true;
    } catch (e) { msg("Không lưu được: " + e.message, "error"); return false; }
  }

  async function deleteFlow() {
    if (!st.id) { msg("Video này chưa lưu nên không có gì để xóa.", "error"); return; }
    if (!confirm(`Xóa "${st.draft.name}" và kết quả của nó?`)) return;
    try {
      await api("/api/flow/" + encodeURIComponent(st.id), { method: "DELETE" });
      await refreshList("");
      setDraft(newDraft(q("wfEngine").value, ""), null);
      msg("Đã xóa.", "ok");
    } catch (e) { msg(e.message, "error"); }
  }

  // ── trạng thái một bước ──
  const nodeId = (type) => st.draft.ids[type];

  function stepState(type) {
    const run = st.run, id = nodeId(type);
    if (type === "skill" && !st.draft.useSkill) return "skipped";
    if (run && run.failed === id) return "error";
    if (run && run.active === id) return "running";
    if (run && run.done.has(id)) return "done";
    return stepIssue(type) ? "issue" : "pending";
  }
  const isLocked = (type) => !!st.run && st.run.done.has(nodeId(type)) && !st.run.unlocked.has(type);

  // ── danh sách bước bên trái ──
  function renderStepList() {
    const ol = q("wfSteps");
    if (!st.draft) { ol.innerHTML = ""; return; }
    const run = st.run;
    ol.innerHTML = stepTypes(st.draft).map((type, i) => {
      const state = stepState(type), id = nodeId(type);
      const time = run && run.active === id && run.t0[id] ? fmtSec(Date.now() - run.t0[id]) : run && run.dur[id] ? fmtSec(run.dur[id]) : "";
      return `<li><button type="button" class="wf-step is-${state}${st.step === type ? " is-current" : ""}" data-type="${esc(type)}"${st.step === type ? ' aria-current="step"' : ""}>
        <span class="wf-step-no" aria-hidden="true">${state === "done" ? "✓" : state === "error" ? "✗" : state === "running" ? "" : i + 1}</span>
        <span class="wf-step-text"><span class="wf-step-name">${esc(labelOf(type))}</span>
        <span class="wf-step-sum">${esc(state === "issue" ? "⚠ " + stepIssue(type) : stepSummary(type))}</span></span>
        <span class="wf-step-time">${esc(time)}</span></button></li>`;
    }).join("");
    ol.querySelectorAll(".wf-step").forEach((b) => b.addEventListener("click", () => goTo(b.dataset.type)));
  }

  function goTo(type) { st.step = type; renderStepList(); renderPanel(); }

  // ── cài đặt từng bước ──
  function providerOptions(current, allowDemo) {
    const mark = (p) => (p.hasKey ? " ✓ có key" : " ✗ chưa có key");
    const opts = [{ id: "", label: "— chọn provider —" }].concat(allowDemo ? [{ id: "demo", label: "Demo (offline, không gọi AI)" }] : [])
      .concat(st.providers.map((p) => ({ ...p, label: p.label + mark(p) })));
    return opts.map((p) => `<option value="${esc(p.id)}" ${p.id === current ? "selected" : ""}>${esc(p.label)}</option>`).join("");
  }
  const sel = (arr, current) => arr.map((v) => `<option value="${esc(v)}" ${String(v) === String(current) ? "selected" : ""}>${esc(v)}</option>`).join("");
  const skillOptions = (current) => st.skills.map((s) => `<option value="${esc(s.id)}" ${s.id === current ? "selected" : ""}>${esc(s.name)}${s.source ? " 📎" : ""}</option>`).join("");

  function imageProviderOptions(current) {
    const withImage = st.providers.filter((p) => p.imageModel);
    const opts = [{ id: "", label: withImage.length ? "— chọn provider tạo ảnh —" : "— chưa có provider nào có Model tạo ảnh (vào Settings) —" }]
      .concat(withImage.map((p) => ({ id: p.id, label: `${p.label} · ${p.imageModel}${p.hasKey ? "" : " ✗ chưa có key"}` })));
    return opts.map((p) => `<option value="${esc(p.id)}" ${p.id === current ? "selected" : ""}>${esc(p.label)}</option>`).join("");
  }

  // ── giọng đọc: danh sách giọng theo ngôn ngữ (VieNeu cho tiếng Việt, Edge cho ngôn ngữ khác) ──
  function voiceList(mode) {
    const lang = st.draft.cfg.idea.language, cfg = typeof config !== "undefined" && config ? config : {};
    if (lang === "vi") return (cfg.voicePresets && cfg.voicePresets[mode]) || [];
    return ((cfg.edgeVoices || {})[lang] || []).map((v) => v.id);
  }
  function voiceOptions(current, voices, placeholder) {
    const list = current && !voices.includes(current) ? [current, ...voices] : voices;
    return `<option value="">${esc(placeholder)}</option>` + list.map((v) => `<option value="${esc(v)}" ${v === current ? "selected" : ""}>${esc(v)}</option>`).join("");
  }
  const characterNames = () => (st.draft.cfg["ai-script"].characters || []);

  function retriesField(type) {
    return `<label>Số lần thử lại khi AI lỗi<input data-retries="${esc(type)}" type="number" min="1" max="5" value="${esc(st.draft.retries[type])}"></label>`;
  }

  function stepFields(type) {
    const c = st.draft.cfg[type];
    const langs = (typeof config !== "undefined" && config && config.languages) ? config.languages.map((l) => l.code) : ["vi", "en"];
    const fmts = (typeof config !== "undefined" && config && config.formats) ? config.formats.map((f) => f.code) : ["16:9", "9:16", "1:1"];
    const voices = (typeof config !== "undefined" && config && config.voicePresets && config.voicePresets[c.ttsMode]) || [];
    const visualChoice = `<label>Cách tạo hình<select data-visual="1">
        <option value="build-scenes" ${st.draft.visual === "build-scenes" ? "selected" : ""}>Doodle có sẵn của app (khuyên dùng, nét vẽ tay đồng nhất)</option>
        <option value="ai-image" ${st.draft.visual === "ai-image" ? "selected" : ""}>AI tự vẽ ảnh</option></select></label>`;
    const fields = {
      idea: () => `<label>Ý tưởng / prompt<textarea data-k="text" rows="5" placeholder="vd: Vụ án phòng kín bất khả thi">${esc(c.text)}</textarea></label>
        <div class="wf-grid2"><label>Ngôn ngữ<select data-k="language">${sel(langs, c.language)}</select></label>
        <label>Thời lượng (phút)<input data-k="minutes" data-n="1" type="number" min="1" max="10" value="${esc(c.minutes)}"></label></div>`,
      skill: () => {
        const uploaded = st.skills.filter((s) => s.source).length;
        const full = c.skills.length >= MAX_SKILLS;
        return `<label class="wf-check"><input data-useskill="1" type="checkbox" ${st.draft.useSkill ? "checked" : ""}> Dùng skill riêng cho video này</label>
        <div ${st.draft.useSkill ? "" : "hidden"}>
        <p class="empty">Chọn tối đa ${MAX_SKILLS} skill (đã chọn ${c.skills.length}/${MAX_SKILLS}). Skill được gộp theo thứ tự chọn.</p>
        <div class="wf-skills">${st.skills.map((s) => `<label class="wf-check"><input type="checkbox" data-skillid="${esc(s.id)}"
          ${c.skills.includes(s.id) ? "checked" : ""} ${full && !c.skills.includes(s.id) ? "disabled" : ""}> ${esc(s.name)}${s.source ? " 📎" : ""}</label>`).join("")}</div>
        <div class="row-actions"><button type="button" class="ghost" id="wfUploadSkill" ${uploaded >= MAX_SKILLS ? "disabled" : ""}>⬆ Tải skill lên (.md / .txt)</button>
        <input type="file" id="wfSkillFile" accept=".md,.markdown,.txt" multiple hidden></div>
        <p class="empty">Đã tải lên ${uploaded}/${MAX_SKILLS} file (tối đa ${MAX_SKILLS}). Có thể chọn nhiều file một lúc. Xóa bớt ở Settings → Tệp đã tải lên.</p></div>`;
      },
      "ai-script": () => `<label>Provider<select data-k="provider">${providerOptions(c.provider, true)}</select></label>
        ${st.draft.useSkill ? `<p class="empty">Đang dùng skill từ bước Skill.</p>` : `<label>Skill<select data-k="skill">${skillOptions(c.skill)}</select></label>`}
        <label>Nhân vật (mỗi dòng một tên, 2–4 người; để trống = một người dẫn)<textarea data-lines="characters" rows="3" placeholder="vd:&#10;Người dẫn&#10;Thám tử">${esc((c.characters || []).join("\n"))}</textarea></label>
        <label>Yêu cầu thêm<textarea data-k="prompt" rows="4" placeholder="vd: giọng hài hước, kết bằng câu hỏi">${esc(c.prompt)}</textarea></label>
        ${retriesField(type)}`,
      "ai-image": () => `${visualChoice}<label>Provider tạo ảnh<select data-k="provider">${imageProviderOptions(c.provider)}</select></label>
        <label>Kích thước ảnh<select data-k="size">${["", "1024x1024", "1536x1024", "1792x1024"].map((v) => `<option value="${v}" ${v === (c.size || "") ? "selected" : ""}>${v || "mặc định của model"}</option>`).join("")}</select></label>
        <label>Phong cách / yêu cầu thêm<textarea data-k="prompt" rows="3" placeholder="vd: nét marker dày, ít chi tiết">${esc(c.prompt)}</textarea></label>
        ${retriesField(type)}`,
      "build-scenes": () => `${visualChoice}<p class="empty">Bước này không cần AI và không có thêm tham số.</p>`,
      "ai-html": () => `<label>Provider<select data-k="provider">${providerOptions(c.provider, false)}</select></label>
        <label>Yêu cầu thêm<textarea data-k="prompt" rows="4" placeholder="vd: tông màu tối, chữ lớn">${esc(c.prompt)}</textarea></label>
        ${retriesField(type)}`,
      tts: () => `<label>VieNeu mode<select data-k="ttsMode">${sel(["v3turbo", "v3nano", "remote"], c.ttsMode)}</select></label>
        <label>${characterNames().length >= 2 ? "Giọng mặc định (cho người chưa gán giọng)" : "Giọng đọc"}<select data-k="voice">${voiceOptions(c.voice, voices, "— mặc định —")}</select></label>
        ${characterNames().length >= 2 ? `<p class="empty">Gán giọng riêng cho từng nhân vật (${st.draft.cfg.idea.language === "vi" ? "giọng VieNeu" : "giọng Edge"}):</p>` +
          characterNames().map((n) => `<label>${esc(n)}<select data-speaker="${esc(n)}">${voiceOptions((c.speakers || {})[n] || "", voices, "— giọng mặc định —")}</select></label>`).join("") : ""}
        <label class="wf-check"><input data-k="dryRun" data-b="1" type="checkbox" ${c.dryRun ? "checked" : ""}> Dry-run (audio im lặng, để thử nhanh)</label>`,
      render: () => `<div class="wf-grid2"><label>FPS (số khung chụp mỗi giây, cao hơn thì chuyển động mượt hơn)<select data-k="fps" data-n="1">${sel(st.draft.engine === "whiteboard" ? [24, 30, 60] : [24, 30, 48, 60, 120], c.fps)}</select></label>
        <label>Khung hình<select data-k="format">${sel(fmts, c.format)}</select></label></div>
        <label>Kiểu khung<select data-k="formatMode">${sel(["fit", "fill"], c.formatMode)}</select></label>
        ${st.draft.engine === "whiteboard" ? `<label>Độ nét (Whiteboard)<select data-k="longEdge" data-n="1">
          <option value="1080" ${Number(c.longEdge) !== 1920 ? "selected" : ""}>1080 px (mặc định)</option>
          <option value="1920" ${Number(c.longEdge) === 1920 ? "selected" : ""}>1920 px (nét nhất, chậm hơn khoảng 18 lần)</option></select></label>`
          : `<label>Chất lượng render (HyperFrames)<select data-k="quality">
          <option value="delivery" ${c.quality !== "looks" && c.quality !== "draft" ? "selected" : ""}>Cao nhất (delivery)</option>
          <option value="looks" ${c.quality === "looks" ? "selected" : ""}>Cao (mặc định HyperFrames)</option>
          <option value="draft" ${c.quality === "draft" ? "selected" : ""}>Xem thử (nhanh)</option></select></label>`}`,
    };
    return (fields[type] || (() => `<p class="empty">Bước này chạy tự động, không có tham số.</p>`))();
  }

  // ── kết quả của từng bước ──
  const fileUrl = (p) => `/api/flow/${encodeURIComponent(st.id)}/file?path=${encodeURIComponent(p)}`;

  function resultBody(type, out) {
    const list = (items) => `<ul>${items.map((t) => `<li>${t}</li>`).join("")}</ul>`;
    if (out.error) return `<p class="wf-warn">AI báo lỗi: ${esc(out.error)}</p>`;
    switch (type) {
      case "idea": return list([`Chủ đề: ${esc(out.topic)}`, `Ngôn ngữ: ${esc(out.language)} · ${esc(out.minutes)} phút`]);
      case "skill": return list([`Skill: ${esc(out.name)}`, `${esc(out.chars)} ký tự system prompt`]);
      case "ai-script": return `<div class="wf-scroll">${(out.scenes || []).map((s, i) =>
        `<p><b>Cảnh ${i + 1}: ${esc(s.title)}</b></p>${list((s.cues || []).map((c) => esc(c.text)))}`).join("")}</div>`;
      case "build-scenes": case "ai-image": return `<div class="wf-thumbs">${(out.images || []).map((p) =>
        `<a href="${fileUrl(p)}" target="_blank" rel="noopener"><img class="wf-thumb" alt="Ảnh cảnh" src="${fileUrl(p)}"></a>`).join("")}</div>`;
      case "ai-html": return list([`Project HTML: ${esc(out.dir)}`]);
      case "tts": return `<p class="empty">Đã tạo giọng đọc cho ${(out.dirs || []).length} thư mục.</p>`;
      case "render": return `<div class="wf-thumbs">${(out.videos || []).map((p) => `<video class="wf-mini" controls preload="metadata" src="${fileUrl(p)}"></video>`).join("")}</div>`;
      case "merge": return out.video ? `<video class="wf-mini" controls preload="metadata" src="${fileUrl(out.video)}"></video>` : "";
      default: return `<pre>${esc(JSON.stringify(out, null, 2).slice(0, 1500))}</pre>`;
    }
  }

  function resultSection(type) {
    const run = st.run, id = nodeId(type);
    if (!run) return "";
    if (run.active === id) return `<section class="wf-res"><h4>Kết quả</h4><p class="wf-res-run">Bước này đang chạy…</p></section>`;
    if (run.failed === id) return `<section class="wf-res"><h4>Kết quả</h4><p class="wf-warn">Bước này lỗi: ${esc(run.message || "không rõ nguyên nhân")}</p></section>`;
    if (!run.done.has(id)) return "";
    const out = run.outputs && run.outputs[id];
    const stale = run.unlocked.has(type) ? `<p class="empty">Đã mở khóa: đây là kết quả của lần chạy trước, chạy lại để cập nhật.</p>` : "";
    return `<section class="wf-res"><h4>Kết quả</h4>${stale}${out ? resultBody(type, out) : `<p class="empty">Không có dữ liệu đầu ra.</p>`}</section>`;
  }

  function panelKey() {
    const run = st.run;
    if (!run || !st.draft) return "-";
    const id = nodeId(st.step);
    return [st.step, run.done.has(id), run.active === id, run.failed === id, run.unlocked.has(st.step), !!(run.outputs && run.outputs[id])].join("|");
  }

  function renderPanel() {
    const box = q("wfPanel");
    st.panelKey = panelKey();
    if (!st.draft) { box.innerHTML = ""; return; }
    const type = st.step, types = stepTypes(st.draft), index = types.indexOf(type);
    const locked = isLocked(type);
    const issue = stepIssue(type);
    box.innerHTML = `<p class="wf-panel-no">Bước ${index + 1}/${types.length}${locked ? ' · <span class="wf-lock">🔒 đã chạy xong</span>' : ""}</p>
      <h3 class="wf-panel-title">${esc(labelOf(type))}</h3>
      <p class="wf-panel-desc">${esc(STEP_INFO[type].desc)}</p>
      ${locked ? `<div class="wf-banner">Bước này đã chạy thành công nên các ô nhập bị khóa để khớp với kết quả bên dưới.
        <button type="button" class="ghost" id="wfUnlock">Mở khóa để sửa</button></div>` : ""}
      <fieldset class="wf-fieldset" ${locked ? "disabled" : ""}>${stepFields(type)}</fieldset>
      <p class="wf-warn" id="wfIssue" ${issue && !locked ? "" : "hidden"}>⚠ ${esc(issue || "")}</p>
      ${resultSection(type)}
      <div class="wf-panel-nav">
        <button type="button" class="ghost" id="wfPrev" ${index === 0 ? "disabled" : ""}>← Bước trước</button>
        ${index < types.length - 1 ? `<button type="button" class="ghost" id="wfNext">Bước tiếp →</button>` : ""}
      </div>`;
    if (locked) q("wfUnlock").addEventListener("click", () => { st.run.unlocked.add(type); renderPanel(); });
    q("wfPrev").addEventListener("click", () => goTo(types[index - 1]));
    if (q("wfNext")) q("wfNext").addEventListener("click", () => goTo(types[index + 1]));
    bindFields(box, type);
  }

  function changed(rerenderPanel) {
    st.dirty = true;
    renderStepList();
    if (rerenderPanel) { renderPanel(); return; }
    const issue = stepIssue(st.step), box = q("wfIssue");   // không vẽ lại panel để giữ con trỏ trong ô đang gõ
    if (box) { box.hidden = !issue; box.textContent = issue ? "⚠ " + issue : ""; }
  }

  function bindFields(box, type) {
    const c = st.draft.cfg[type];
    box.querySelectorAll("fieldset [data-k]").forEach((el) => {
      const isChoice = el.tagName === "SELECT" || el.type === "checkbox";
      el.addEventListener(isChoice ? "change" : "input", () => {
        c[el.dataset.k] = el.dataset.b ? el.checked : el.dataset.n ? Number(el.value) : el.value;
        changed(isChoice && el.tagName === "SELECT");
      });
    });
    box.querySelectorAll("[data-retries]").forEach((el) => el.addEventListener("input", () => {
      const n = Math.floor(Number(el.value));
      if (n >= 1 && n <= 5) { st.draft.retries[el.dataset.retries] = n; st.dirty = true; }
    }));
    box.querySelectorAll("[data-skillid]").forEach((el) => el.addEventListener("change", () => {
      const list = st.draft.cfg.skill.skills.filter((id) => id !== el.dataset.skillid);
      if (el.checked) list.push(el.dataset.skillid);
      st.draft.cfg.skill.skills = list;
      changed(true);
    }));
    box.querySelectorAll("[data-lines]").forEach((el) => el.addEventListener("input", () => {
      c[el.dataset.lines] = el.value.split("\n").map((v) => v.replace(/[\[\]:]/g, "").trim()).filter(Boolean).filter((v, i, a) => a.indexOf(v) === i).slice(0, 4);
      changed(false);
    }));
    box.querySelectorAll("[data-speaker]").forEach((el) => el.addEventListener("change", () => {
      c.speakers = { ...(c.speakers || {}) };
      if (el.value) c.speakers[el.dataset.speaker] = el.value; else delete c.speakers[el.dataset.speaker];
      changed(false);
    }));
    const useSkill = box.querySelector("[data-useskill]");
    if (useSkill) useSkill.addEventListener("change", () => { st.draft.useSkill = useSkill.checked; changed(true); });
    const visual = box.querySelector("[data-visual]");
    if (visual) visual.addEventListener("change", () => { st.draft.visual = visual.value; st.step = visual.value; changed(true); });
    if (q("wfUploadSkill")) bindSkillUpload();
  }

  function bindSkillUpload() {
    q("wfUploadSkill").addEventListener("click", () => q("wfSkillFile").click());
    q("wfSkillFile").addEventListener("change", (ev) => {
      const files = [...ev.target.files];
      ev.target.value = "";
      if (!files.length) return;
      withBusy(q("wfUploadSkill"), async () => {
        const c = st.draft.cfg.skill;
        for (const file of files) {
          try {
            const skill = await window.uploadSkillFile(file);
            await loadSettings();
            if (c.skills.length < MAX_SKILLS) c.skills.push(skill.id);
            toast(`Đã tải skill “${skill.name}” lên (lưu local).`, "success");
          } catch (e) { toast(`Không tải được ${file.name}: ${e.message}`, "error"); break; }
        }
        changed(true);
      });
    });
  }

  function renderToolbar() {
    const none = !st.draft;
    ["wfSave", "wfRun"].forEach((id) => { q(id).disabled = none; });
    q("wfDelete").disabled = none || !st.id;
  }

  function renderAll() {
    renderStepList();
    renderPanel();
    renderToolbar();
  }

  // ── chạy ──
  const fmtSec = (ms) => (ms / 1000).toFixed(ms < 10000 ? 1 : 0) + "s";
  function newRun() { return { done: new Set(), active: null, failed: null, outputs: {}, unlocked: new Set(), t0: {}, dur: {}, message: "", status: "" }; }

  function activeStatusText() {
    const run = st.run;
    if (!run || !run.active || !st.draft) return null;
    const chain = activeTypes(st.draft);
    const type = chain.find((t) => nodeId(t) === run.active);
    if (!type) return null;
    const elapsed = run.t0[run.active] ? " · " + fmtSec(Date.now() - run.t0[run.active]) : "";
    return `Bước ${chain.indexOf(type) + 1}/${chain.length}: ${labelOf(type)} — đang xử lý${elapsed}`;
  }

  function startTicker() {
    stopTicker();
    st.ticker = setInterval(() => {
      const text = activeStatusText();
      if (text) q("wfStatus").textContent = text;
      const time = q("wfSteps").querySelector(".wf-step.is-running .wf-step-time");
      if (time && st.run && st.run.t0[st.run.active]) time.textContent = fmtSec(Date.now() - st.run.t0[st.run.active]);
    }, 500);
  }
  function stopTicker() { if (st.ticker) { clearInterval(st.ticker); st.ticker = null; } }

  function paintRun(result, failed) {
    if (!result || !st.run) return;
    const run = st.run, now = Date.now();
    run.done = new Set(result.doneNodes || []);
    const active = result.activeNode || null;
    if (active && !run.t0[active]) run.t0[active] = now;
    run.done.forEach((id) => { if (!(id in run.dur) && run.t0[id]) run.dur[id] = now - run.t0[id]; });
    run.active = active;
    run.failed = result.failedNode || (failed ? result.activeNode : null) || null;
    if (result.outputs) run.outputs = result.outputs;
    renderStepList();
    if (panelKey() !== st.panelKey) renderPanel();
  }

  function showVideo(path) {
    if (!path) return;
    const url = fileUrl(path);
    q("wfVideo").src = url; q("wfVideo").hidden = false;
    q("wfLinks").innerHTML = `<a href="${url}" download>output.mp4</a>`;
  }

  function setProgress(pct) { q("wfBar").style.width = pct + "%"; q("wfPct").textContent = pct + "%"; }

  function followJob(jobId, finish) {
    if (st.es) st.es.close();
    startTicker();
    st.es = new EventSource(`/api/jobs/${jobId}/events`);
    st.es.addEventListener("stage", (e) => {
      const d = JSON.parse(e.data);
      setProgress(Math.round(d.progress * 100));
      paintRun(d.result);
      q("wfStatus").textContent = activeStatusText() || d.label;
    });
    st.es.addEventListener("done", (e) => {
      const d = JSON.parse(e.data);
      setProgress(100);
      st.run.status = "done";
      q("wfStatus").textContent = "Hoàn tất. Bấm vào từng bước để xem kết quả.";
      toast("Đã tạo xong video" + (d.video ? ", xem ở bên dưới." : "."), "success");
      finish();
      paintRun({ ...d, activeNode: null });
      showVideo(d.video);
      st.es.close();
      if (typeof refreshQueue === "function") refreshQueue();
    });
    st.es.addEventListener("error", (e) => {
      let m = "Job lỗi hoặc mất kết nối.";
      try { const d = JSON.parse(e.data); m = d.message; if (st.run) st.run.message = m; paintRun(d.result, true); } catch (_) { /* mất kết nối */ }
      if (st.run) { st.run.status = "error"; st.run.message = st.run.message || m; }
      q("wfStatus").textContent = "Lỗi: " + m;
      toast("Chạy lỗi: " + m, "error");
      finish();
      renderStepList();
      renderPanel();
      if (st.run && st.run.failed) { const t = activeTypes(st.draft).find((x) => nodeId(x) === st.run.failed); if (t) goTo(t); }
      st.es.close();
      if (typeof refreshQueue === "function") refreshQueue();
    });
  }

  async function runFlow() {
    if (!st.draft) return;
    const bad = activeTypes(st.draft).find((t) => stepIssue(t));
    if (bad) { goTo(bad); msg(`Bước "${labelOf(bad)}" chưa đủ: ${stepIssue(bad)}`, "error"); return; }
    const off = busyOn(q("wfRun"));
    const finish = () => { off(); stopTicker(); setRunning(q("wfStatus"), false); renderToolbar(); };
    if (!(await saveFlow())) { finish(); return; }
    if (st.es) st.es.close();
    st.run = newRun();
    renderAll();
    q("wfResult").hidden = false;
    q("wfVideo").hidden = true; q("wfLinks").innerHTML = "";
    setProgress(0);
    q("wfStatus").textContent = "Đang gửi yêu cầu...";
    setRunning(q("wfStatus"), true);
    let job;
    try { job = await api("/api/flow/run", jsonOpts("POST", { flowId: st.id })); }
    catch (e) { q("wfStatus").textContent = "Lỗi: " + e.message; msg("Không chạy được: " + e.message, "error"); finish(); return; }
    if (typeof refreshQueue === "function") refreshQueue();
    st.run.status = "running";
    followJob(job.jobId, finish);
  }

  // mở lại: nạp kết quả lần chạy gần nhất đã lưu local
  async function loadLastRun(id) {
    let data;
    try { data = await api(`/api/flow/${encodeURIComponent(id)}/last-run`); } catch (_) { return; }
    if (!data || !data.status || st.id !== id) return;
    const run = newRun();
    run.done = new Set(data.doneNodes || []);
    run.outputs = data.outputs || {};
    run.failed = data.failedNode || null;
    run.message = data.message || "";
    run.status = data.status;
    st.run = run;
    q("wfResult").hidden = false;
    q("wfVideo").hidden = true; q("wfLinks").innerHTML = "";
    const total = activeTypes(st.draft).length || 1;
    setProgress(data.status === "done" ? 100 : Math.min(95, Math.round((run.done.size / total) * 100)));
    if (data.status === "done") {
      q("wfStatus").textContent = "Kết quả lần chạy gần nhất (đã lưu local). Bấm vào từng bước để xem.";
      showVideo(data.video);
    } else if (data.status === "error") {
      q("wfStatus").textContent = "Lần chạy gần nhất bị lỗi: " + (data.message || "");
    } else {
      let alive = false;
      try { await api("/api/jobs/" + encodeURIComponent(data.jobId)); alive = true; } catch (_) { /* job không còn */ }
      if (alive) {
        run.active = data.activeNode || null;
        const off = busyOn(q("wfRun"));
        setRunning(q("wfStatus"), true);
        q("wfStatus").textContent = "Đang theo dõi lần chạy đang diễn ra…";
        followJob(data.jobId, () => { off(); stopTicker(); setRunning(q("wfStatus"), false); renderToolbar(); });
      } else {
        q("wfStatus").textContent = "Lần chạy trước bị gián đoạn (server đã khởi động lại). Chạy lại để có kết quả đầy đủ.";
      }
    }
    renderAll();
  }

  // ── khởi tạo ──
  async function loadSettings() {
    try {
      const data = await api("/api/ai/settings");
      st.providers = data.providers; st.skills = data.skills;
    } catch (_) { st.providers = []; st.skills = []; }
  }

  document.addEventListener("viewchange", (e) => {
    if (e.detail === "workflow") {
      loadSettings().then(async () => {
        try { await refreshList(); } catch (err) { msg(err.message, "error"); }
        if (!st.draft) setDraft(newDraft(q("wfEngine").value, ""), null); else renderAll();
      });
    } else if (e.detail === "settings" && typeof loadAiSettings === "function") {
      loadAiSettings().catch((err) => { $("status").textContent = "Lỗi settings: " + err.message; });
    }
  });

  function setGuide(open) {
    q("wfGuide").hidden = !open;
    q("wfGuideBtn").setAttribute("aria-expanded", String(open));
    try { if (!open) localStorage.setItem("wfGuideSeen", "1"); } catch (_) { /* không có storage */ }
  }

  function init() {
    q("wfFlowSelect").addEventListener("change", (e) => openFlow(e.target.value));
    q("wfCreate").addEventListener("click", createNew);
    q("wfSave").addEventListener("click", () => withBusy(q("wfSave"), saveFlow));
    q("wfDelete").addEventListener("click", () => withBusy(q("wfDelete"), deleteFlow));
    q("wfRun").addEventListener("click", () => { if (!q("wfRun").classList.contains("is-busy")) runFlow(); });
    q("wfGuideBtn").addEventListener("click", () => setGuide(q("wfGuide").hidden));
    q("wfGuideClose").addEventListener("click", () => setGuide(false));
    q("wfName").addEventListener("input", () => { st.dirty = true; if (st.draft) st.draft.name = q("wfName").value; });
    q("wfEngine").addEventListener("change", () => {
      if (!st.draft) return;
      st.draft.engine = q("wfEngine").value;   // đổi engine giữ lại phần đã nhập, đổi các bước theo engine
      st.run = null;
      q("wfResult").hidden = true;
      if (!stepTypes(st.draft).includes(st.step)) st.step = "idea";
      changed(true);
    });
    window.addEventListener("beforeunload", (ev) => { if (st.dirty && st.id) { ev.preventDefault(); ev.returnValue = ""; } });
    let seen = false;
    try { seen = !!localStorage.getItem("wfGuideSeen"); } catch (_) { /* không có storage */ }
    if (!seen) setGuide(true);
    renderToolbar();
  }

  init();
  window.__wf = st; // phục vụ kiểm thử thủ công
})();
