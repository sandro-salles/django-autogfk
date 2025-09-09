(function () {

  // Helper: is this element inside the empty template form?
  function inEmptyForm(el) {
    if (!el) return false;
    var cur = el;
    while (cur && cur !== document) {
      if (cur.classList && cur.classList.contains("empty-form")) return true;
      cur = cur.parentNode;
    }
    return false;
  }
  // Initialize a field row (ex.: .form-row) that contains our CT/OBJ pair
  function initRow(row) {
    if (!row || row.dataset.autogfkInitialized === "1") return;
    if (inEmptyForm(row)) return; // never init the template
    const ct = row.querySelector('select[data-autogfk="ct"]');
    const obj = row.querySelector('select[data-autogfk="obj"]');
    if (!ct || !obj) return; // not our line

    function fetchOptions(term, page) {
      const base = obj.getAttribute("data-autogfk-url");
      if (!base) return Promise.resolve({ results: [], more: false });
      const url = new URL(base, window.location.origin);
      url.searchParams.set("ct", ct.value || "");
      if (term) url.searchParams.set("q", term);
      if (page) url.searchParams.set("page", page);
      return fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } })
        .then((r) => r.json())
        .catch(() => ({ results: [], more: false }));
    }

    const $ = (window.django && window.django.jQuery) || window.jQuery || window.$;
    if (!$ || !$.fn || !$.fn.select2) return;

    // Rehydrate CT if the inline template came without options
    try {
      if (ct.options.length <= 1) {
        const raw = ct.getAttribute("data-autogfk-choices");
        if (raw) {
          const pairs = JSON.parse(raw);
          if (Array.isArray(pairs)) {
            pairs.forEach(function (p) {
              if (!p || p.length < 2) return;
              const opt = new Option(String(p[1]), String(p[0]), false, false);
              ct.add(opt);
            });
          }
        }
      }
    } catch (e) { /* silent */ }

    function safeDestroy($el) {
      if ($el && ($el.data("select2") || $el.hasClass("select2-hidden-accessible"))) {
        $el.select2("destroy");
      }
    }

    // Defer init until layout is stable (prevents forced reflow issues)
    requestAnimationFrame(function () {
      setTimeout(function () {
        const $ct = $(ct);
        const $obj = $(obj);
        safeDestroy($ct);
        safeDestroy($obj);

        // obj: remote Select2, always dependent on CT
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

        // ct: simple Select2; when changing, clear the object
        $(ct).select2({ width: "style" }).on("change", function () {
          $(obj).val(null).trigger("change");
        });

        // only mark initialized after successful init
        row.dataset.autogfkInitialized = "1";
      }, 0);
    });
  }

  function initAllIn(root) {
    const scope = root || document;
    // Search lines that contain explicitly our marked selects
    const rows = scope.querySelectorAll('.form-row, .form-group, .fieldBox, .inline-related .form-row');
    rows.forEach(function (row) {
      if (!inEmptyForm(row) && row.querySelector('select[data-autogfk="obj"]')) {
        initRow(row);
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initAllIn(document);
  });

  // Django triggers this event when an inline is added dynamically
  document.addEventListener("formset:added", function (e) {
    const root = e.target || (e.detail && e.detail.formset) || null;
    initAllIn(root || document);
  });


  // Prefer jQuery event signature from Django admin: (event, $row, formsetName)
  try {
    const $ = (window.django && window.django.jQuery) || window.jQuery || window.$;
    if ($ && $.fn && $.fn.on) {
      $(document).on("formset:added", function (event, $row /* , formsetName */) {
        if ($row && $row.length) {
          initAllIn($row[0]);
        }
      });
    }
  } catch (e) { /* silent */ }

})();