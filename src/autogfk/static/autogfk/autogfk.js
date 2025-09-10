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
    let obj = row.querySelector('select[data-autogfk="obj"]');
    if (!ct || !obj) return; // not our line

    const relatedWidgetWrapper = row.querySelector('[data-autogfk-wrapper]');
    const addLink = row.querySelector('a.related-widget-wrapper-link.add-related');
    const changeLink = row.querySelector('a.related-widget-wrapper-link.change-related');
    const viewLink = row.querySelector('a.related-widget-wrapper-link.view-related');


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

    // Retorna todas as instâncias de jQuery que podem existir no admin/app
    function getJQList() {
      var list = [];
      if (window.django && window.django.jQuery) list.push(window.django.jQuery);
      if (window.jQuery && list.indexOf(window.jQuery) === -1) list.push(window.jQuery);
      return list;
    }

    // Checa se o select tem Select2 acoplado (robusto p/ 4.0.x e 4.1+)
    function hasSelect2Attached(el, $jq) {
      if (!el) return false;
      // flags de Select2
      if (el.classList && el.classList.contains('select2-hidden-accessible')) return true;
      if (el.hasAttribute && el.hasAttribute('data-select2-id')) return true;
      // via jQuery data
      if ($jq) {
        try {
          var $el = $jq(el);
          var d = $el.data('select2');
          if (typeof d !== 'undefined' && d !== null) return true;
        } catch (e) { }
      }
      return false;
    }

    // Destrói em TODAS as instâncias de jQuery que conhecemos, só se estiver anexado
    function destroySelect2Everywhere(el) {
      var jqs = getJQList();
      for (var i = 0; i < jqs.length; i++) {
        var $jq = jqs[i];
        try {
          var $el = $jq(el);
          if (typeof $el.select2 === 'function' && hasSelect2Attached(el, $jq)) {
            $el.select2('destroy'); // não deve logar warning
          }
        } catch (e) { /* silent */ }
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
            var perms = { add: false, change: false, view: false };
            if (triple.length >= 4 && triple[3] && typeof triple[3] === 'object') {
              try {
                perms = {
                  add: !!triple[3].add,
                  change: !!triple[3].change,
                  view: !!triple[3].view,
                };
              } catch (e) { /* silent */ }
            }
            map[String(triple[0])] = { app: String(triple[1]), model: String(triple[2]), perms: perms };
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
        view: objId ? base + String(objId) + "/change/?_to_field=id&_popup=1" : null,
        template: base + "__fk__/change/?_to_field=id&_popup=1",
      };
    }

    function updateActions() {
      const ctVal = ct.value || "";
      const objVal = obj.value || "";
      // Helper to toggle links according to permission while keeping layout stable
      function setLink(el, enabled, href, templateHref) {
        if (!el) return;
        if (typeof href === 'string' && href.length) {
          el.href = href;
        }
        if (typeof templateHref === 'string' && templateHref.length) {
          el.setAttribute('data-href-template', templateHref);
        }
        if (enabled) {
          el.classList.remove('autogfk-disabled-link');
          el.removeAttribute('aria-disabled');
          el.removeAttribute('tabindex');
        } else {
          el.classList.add('autogfk-disabled-link');
          el.setAttribute('aria-disabled', 'true');
          el.setAttribute('tabindex', '-1');
        }
      }

      if (!ctVal) {
        // No CT: keep all links visible but disabled
        setLink(addLink, false);
        setLink(changeLink, false);
        setLink(viewLink, false);
        if (relatedWidgetWrapper) relatedWidgetWrapper.removeAttribute('data-model-ref');
        return;
      }

      const meta = CTMAP[ctVal] || { perms: { add: false, change: false, view: false }, model: '' };
      const urlsWithObj = objVal ? buildAdminUrls(ctVal, objVal) : null;
      const urlsNoObj = buildAdminUrls(ctVal, null);

      // Add: enabled if user can add
      setLink(addLink, !!(meta.perms && meta.perms.add), urlsNoObj && urlsNoObj.add, null);

      // Change/View: keep links, disable when no object or no permission
      const canChange = !!(meta.perms && meta.perms.change) && !!objVal;
      const canView = !!(meta.perms && meta.perms.view) && !!objVal;
      setLink(changeLink, canChange, urlsWithObj && urlsWithObj.edit, urlsNoObj && urlsNoObj.template);
      setLink(viewLink, canView, urlsWithObj && urlsWithObj.view, urlsNoObj && urlsNoObj.template);

      if (relatedWidgetWrapper) relatedWidgetWrapper.setAttribute('data-model-ref', meta.model || '');
    }

    // Defer init until layout is stable (prevents forced reflow issues)
    requestAnimationFrame(function () {
      setTimeout(function () {
        const $ct = $(ct);
        const $obj = $(obj);
        destroySelect2Everywhere(ct);
        destroySelect2Everywhere(obj);

        // obj: remote Select2, always dependent on CT
        $obj.select2({
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
        $ct.select2({ width: "style" }).on("change", function () {
          $(obj).val(null).trigger("change");
          updateActions();
        });

        // Update when the object changes (selected via Select2)
        $obj.on("change", function () {
          updateActions();
        });

        // Prevent navigation on disabled links while keeping layout stable
        [addLink, changeLink, viewLink].forEach(function (lnk) {
          if (!lnk) return;
          lnk.addEventListener('click', function (e) {
            if (lnk.classList.contains('autogfk-disabled-link')) {
              e.preventDefault();
              e.stopPropagation();
            }
          });
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
