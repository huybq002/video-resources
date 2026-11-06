// Phản hồi người dùng dùng chung: toast thông báo + spinner cho nút/vùng đang xử lý.
(function () {
  const MAX_TOASTS = 4;

  function host() {
    let el = document.getElementById("toasts");
    if (!el) {
      el = document.createElement("div");
      el.id = "toasts";
      el.className = "toasts";
      el.setAttribute("aria-live", "polite");
      document.body.appendChild(el);
    }
    return el;
  }

  // kind: info | success | error. Lỗi ở lại lâu hơn và có role=alert.
  window.toast = function (message, kind, ms) {
    kind = kind || "info";
    const box = host();
    const el = document.createElement("div");
    el.className = "toast toast-" + kind;
    el.setAttribute("role", kind === "error" ? "alert" : "status");
    const text = document.createElement("span");
    text.className = "toast-text";
    text.textContent = String(message);
    const close = document.createElement("button");
    close.type = "button";
    close.className = "toast-close";
    close.setAttribute("aria-label", "Đóng thông báo");
    close.textContent = "×";
    el.append(text, close);
    const remove = () => { el.classList.add("is-leaving"); setTimeout(() => el.remove(), 180); };
    close.addEventListener("click", remove);
    box.appendChild(el);
    while (box.children.length > MAX_TOASTS) box.firstChild.remove();
    setTimeout(remove, ms || (kind === "error" ? 9000 : 4500));
    return el;
  };

  const asList = (b) => (Array.isArray(b) ? b : [b]).filter(Boolean);

  // Bật/tắt trạng thái bận (spinner + khóa nút). Trả hàm tắt.
  window.busyOn = function (buttons) {
    const list = asList(buttons).map((btn) => {
      const prior = btn.disabled;
      btn.classList.add("is-busy");
      btn.setAttribute("aria-busy", "true");
      btn.disabled = true;
      return { btn, prior };
    });
    return function busyOff() {
      list.forEach(({ btn, prior }) => {
        btn.classList.remove("is-busy");
        btn.removeAttribute("aria-busy");
        btn.disabled = prior;
      });
    };
  };

  // Chạy fn khi nút bận; bỏ qua nếu đang bận (chặn bấm đúp).
  window.withBusy = async function (buttons, fn) {
    const list = asList(buttons);
    if (list.some((b) => b.classList.contains("is-busy"))) return undefined;
    const off = window.busyOn(list);
    try { return await fn(); } finally { off(); }
  };

  // Spinner phủ lên một vùng (đang tải dữ liệu).
  window.setLoading = function (el, on) {
    if (!el) return;
    el.classList.toggle("is-loading", !!on);
    if (on) el.setAttribute("aria-busy", "true"); else el.removeAttribute("aria-busy");
  };

  // Spinner nhỏ đứng trước dòng trạng thái (job đang chạy).
  window.setRunning = function (el, on) {
    if (el) el.classList.toggle("is-running", !!on);
  };
})();
