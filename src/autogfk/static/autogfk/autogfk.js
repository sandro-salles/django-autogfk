// src/autogfk/static/autogfk/autogfk.js
(function () {
  function init(container) {
    if (!container || container.dataset.autogfkInitialized === "1") return;

    const obj = container.querySelector("select[data-autocomplete-url]");
    if (!obj) return;
    const selects = Array.from(container.querySelectorAll("select"));
    const ct = selects.find((el) => el !== obj);
    if (!ct) return;

    container.dataset.autogfkInitialized = "1";

    function fetchOptions(term, page) {
      const base = obj.dataset.autocompleteUrl;
      if (!base) return Promise.resolve({ results: [], more: false });
      const url = new URL(base, window.location.origin);
      url.searchParams.set("ct", ct.value || "");
      if (term) url.searchParams.set("q", term);
      if (page) url.searchParams.set("page", page);
      return fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } })
        .then((r) => r.json())
        .catch(() => ({ results: [], more: false }));
    }

    // 👇 Django 5 exposes jQuery as django.jQuery
    const $ = (window.django && window.django.jQuery) || window.jQuery || window.$;
    if (!$ || !$.fn || !$.fn.select2) return;

    $(obj).select2({
      ajax: {
        transport: function (params, success, failure) {
          fetchOptions(params.data && params.data.q, params.data && params.data.page)
            .then(success)
            .catch(failure);
        },
        processResults: function (data, params) {
          params.page = params.page || 1;
          return { results: data.results || [], pagination: { more: !!data.more } };
        },
      },
      minimumInputLength: 0,
      width: "style",
    });

    $(ct).select2({ width: "style" }).on("change", function () {
      $(obj).val(null).trigger("change");
    });
  }

  function initAll() {
    const containers = document.querySelectorAll(
      ".form-row, .form-group, .fieldBox, .inline-related .form-row"
    );
    containers.forEach(init);
  }

  document.addEventListener("DOMContentLoaded", initAll);
  document.addEventListener("formset:added", function (e) {
    init(e.target || (e.detail && e.detail.formset));
  });
})();
