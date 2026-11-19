/* ==========================================================================
   api.js - lớp gọi API dùng chung cho mọi trang.
   Mọi trang PHẢI dùng các hàm ở đây thay vì tự viết fetch, để xử lý lỗi,
   trạng thái đang tải và thông báo được thống nhất.
   ========================================================================== */
(function () {
  'use strict';

  var BASE = '/api/v1';

  /** Gọi API; trả về dữ liệu JSON. Ném lỗi kèm thông báo tiếng Việt từ backend. */
  async function request(method, path, options) {
    options = options || {};
    var init = {
      method: method,
      credentials: 'same-origin',
      headers: { 'Accept': 'application/json' }
    };
    if (options.body !== undefined) {
      if (options.body instanceof FormData) {
        init.body = options.body;                        // để trình duyệt tự đặt Content-Type
      } else {
        init.headers['Content-Type'] = 'application/json';
        init.body = JSON.stringify(options.body);
      }
    }
    var response = await fetch(BASE + path, init);

    if (response.status === 204) return null;

    var payload = null;
    var text = await response.text();
    if (text) {
      try { payload = JSON.parse(text); } catch (e) { payload = { detail: text }; }
    }

    if (!response.ok) {
      var detail = payload && (payload.detail || payload.message);
      if (Array.isArray(detail)) {                        // lỗi validate của FastAPI
        detail = detail.map(function (item) {
          var loc = (item.loc || []).slice(1).join('.');
          return (loc ? loc + ': ' : '') + (item.msg || '');
        }).join('; ');
      }
      var error = new Error(detail || ('Lỗi ' + response.status));
      error.status = response.status;
      error.payload = payload;
      if (response.status === 401) {
        error.message = detail || 'Bạn cần đăng nhập.';
      }
      throw error;
    }
    return payload;
  }

  var ANA = {
    base: BASE,
    get: function (path) { return request('GET', path); },
    post: function (path, body) { return request('POST', path, { body: body }); },
    put: function (path, body) { return request('PUT', path, { body: body }); },
    del: function (path, body) { return request('DELETE', path, { body: body }); },
    upload: function (path, file) {
      var form = new FormData();
      form.append('file', file, file.name);
      return request('POST', path, { body: form });
    },
    call: request,

    /** Hiện thông báo nhanh ở góc phải. */
    toast: function (message, kind, ms) {
      var region = document.getElementById('toast-region');
      if (!region) { return; }
      var el = document.createElement('div');
      el.className = 'toast' + (kind === 'error' ? ' error' : kind === 'warn' ? ' warn' : '');
      el.setAttribute('role', kind === 'error' ? 'alert' : 'status');
      el.textContent = message;
      region.appendChild(el);
      setTimeout(function () { el.remove(); }, ms || (kind === 'error' ? 7000 : 3500));
    },

    /** Thông báo trong vùng flash phía trên nội dung trang. */
    flash: function (message, kind) {
      var region = document.getElementById('flash');
      if (!region) { return; }
      var el = document.createElement('div');
      el.className = 'flash flash-' + (kind || 'info');
      el.textContent = message;
      region.innerHTML = '';
      region.appendChild(el);
      if (kind === 'success') { setTimeout(function () { el.remove(); }, 5000); }
    },

    error: function (err) {
      var message = (err && err.message) || 'Có lỗi không xác định.';
      if (err && err.status === 401) {
        ANA.toast('Phiên đăng nhập đã hết hạn. Đang chuyển tới trang đăng nhập…', 'warn');
        setTimeout(function () { window.location.href = '/login'; }, 1200);
        return;
      }
      ANA.toast(message, 'error');
    },

    /** Bật/tắt trạng thái đang tải cho một vùng. */
    loading: function (target, on, rows) {
      var el = typeof target === 'string' ? document.querySelector(target) : target;
      if (!el) { return; }
      if (on) {
        el.dataset.previousHtml = el.innerHTML;
        var html = '';
        for (var i = 0; i < (rows || 3); i++) { html += '<div class="skeleton"></div>'; }
        el.innerHTML = html;
      } else if (el.dataset.previousHtml !== undefined) {
        el.innerHTML = el.dataset.previousHtml;
        delete el.dataset.previousHtml;
      }
    },

    busy: function (button, on, busyLabel) {
      if (!button) { return; }
      if (on) {
        button.dataset.label = button.textContent;
        button.disabled = true;
        button.innerHTML = '<span class="spinner"></span> ' + (busyLabel || 'Đang xử lý…');
      } else {
        button.disabled = false;
        if (button.dataset.label) { button.textContent = button.dataset.label; }
      }
    },

    /** Định dạng số: thiếu dữ liệu thì hiện "chưa có dữ liệu", KHÔNG hiện 0. */
    num: function (value, digits) {
      if (value === null || value === undefined || value === '') {
        return '<span class="muted">chưa có dữ liệu</span>';
      }
      var n = Number(value);
      if (!isFinite(n)) { return '<span class="muted">chưa có dữ liệu</span>'; }
      return n.toFixed(digits === undefined ? 1 : digits);
    },

    text: function (value, fallback) {
      return (value === null || value === undefined || value === '') ? (fallback || '—') : value;
    },

    escape: function (value) {
      return String(value === null || value === undefined ? '' : value)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    },

    mealTypeLabel: function (value) {
      return { breakfast: 'Bữa sáng', lunch: 'Bữa trưa', dinner: 'Bữa tối', snack: 'Bữa phụ' }[value] || value;
    },
    cookingStateLabel: function (value) {
      return { raw: 'Sống', cooked: 'Đã nấu', processed: 'Chế biến sẵn', unknown: 'Chưa rõ' }[value] || value;
    },

    /** Đăng ký chạy sau khi DOM sẵn sàng. */
    ready: function (fn) {
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', fn);
      } else {
        fn();
      }
    },

    /** Tô đậm mục đang mở trên sidebar. */
    markActiveNav: function () {
      var page = document.body.getAttribute('data-page');
      if (!page) { return; }
      document.querySelectorAll('.nav-link').forEach(function (link) {
        if (link.getAttribute('data-nav') === page) { link.classList.add('active'); }
      });
    },

    /** Vẽ biểu đồ Chart.js nếu thư viện đã tải; trả về instance hoặc null. */
    chart: function (canvasId, config) {
      var el = document.getElementById(canvasId);
      if (!el) { return null; }
      if (typeof Chart === 'undefined') {
        el.parentElement.innerHTML = '<div class="empty-state">Không tải được thư viện biểu đồ Chart.js ' +
          '(cần Internet). Số liệu vẫn xem được ở dạng bảng bên dưới.</div>';
        return null;
      }
      var existing = Chart.getChart(el);
      if (existing) { existing.destroy(); }
      return new Chart(el, config);
    }
  };

  window.ANA = ANA;
  ANA.ready(ANA.markActiveNav);
})();
