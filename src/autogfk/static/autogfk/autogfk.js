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
    console.log(row.innerHTML);
    const actionsSlot = row.querySelector('div.autogfk-wrapper');
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


    function parseCTMap(selectCt) {
      try {
        const raw = selectCt.getAttribute("data-autogfk-ctmap");
        const arr = JSON.parse(raw || "[]");
        // create map { "ctId": {app, model} }
        const map = {};
        arr.forEach(function (triple) {
          if (triple && triple.length >= 3) {
            map[String(triple[0])] = { app: String(triple[1]), model: String(triple[2]) };
          }
        });
        return map;
      } catch (e) { return {}; }
    }

    const CTMAP = parseCTMap(ct);

    function buildAdminUrls(ctId, objId) {
      const root = obj.getAttribute("data-autogfk-admin-root") || "/admin/";
      const meta = CTMAP[String(ctId)];
      if (!meta) return null;
      const base = root.replace(/\/?$/, "/") + meta.app + "/" + meta.model + "/";
      return {
        add: base + "add/?_to_field=id&_popup=1",
        edit: objId ? base + String(objId) + "/change/?_to_field=id&_popup=1" : null,
        view: objId ? base + String(objId) + "/change/?_popup=1" : null, // uses change in view-only mode if permission is missing
      };
    }

    function updateActions() {
      if (!actionsSlot) return;
      const ctVal = ct.value || "";
      const objVal = obj.value || "";
      // delete all related-widget-wrapper-link
      actionsSlot.querySelectorAll('a.related-widget-wrapper-link').forEach(function (a) {
        a.remove();
      });
      if (!ctVal) return;                 // no CT → no buttons
      const urls = buildAdminUrls(ctVal, objVal || "__");
      if (!urls) return;

      // helper to create link that opens the admin popup
      function mkLink(href, css, title, onclickName) {
        const a = document.createElement("a");
        if (href) {
          a.href = href;
        }
        a.className = "related-widget-wrapper-link " + css;
        a.title = title;
        // id in the standard admin helps dismissAddRelatedObjectPopup:
        // "add_id_<fieldId>" / "change_id_<fieldId>" / "view_id_<fieldId>"
        const fieldId = obj.id || "";
        if (css.indexOf("add-related") !== -1) a.id = "add_id_" + fieldId;
        if (css.indexOf("change-related") !== -1) a.id = "change_id_" + fieldId;
        if (css.indexOf("view-related") !== -1) a.id = "view_id_" + fieldId;
        // use global admin functions to open popup
        a.setAttribute("onclick", "return " + onclickName + "(this);");
        return a;
      }

      // With CT and object → shows add, change, view
      if (ctVal) {
        const aAdd = mkLink(urls.add, "add-related", "Add another", "showAddAnotherPopup");
        aAdd.innerHTML = '<img src="/static/admin/img/icon-addlink.svg" alt="">'
        const aEdit = mkLink(buildAdminUrls(ctVal, objVal).edit, "change-related", "Change", "showRelatedObjectLookupPopup");
        aEdit.innerHTML = '<img src="/static/admin/img/icon-changelink.svg" alt="">'
        const aView = mkLink(buildAdminUrls(ctVal, objVal).view, "view-related", "View", "showRelatedObjectLookupPopup");
        aView.innerHTML = '<img src="/static/admin/img/icon-viewlink.svg" alt="">'
        actionsSlot.appendChild(aEdit);
        actionsSlot.appendChild(aAdd);
        actionsSlot.appendChild(aView);
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
          updateActions();
        });

        // Update when the object changes (selected via Select2)
        $obj.on("change", function () {
          updateActions();
        });

        // Initialize
        updateActions();

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