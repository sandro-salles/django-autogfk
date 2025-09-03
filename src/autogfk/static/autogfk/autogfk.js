(function() {
  function init(root) {
    const ct = root.querySelector("select[name$='content_type']");
    const obj = root.querySelector("select[name$='object_id']");
    if (!ct || !obj) return;

    function fetchOptions(term, page) {
      const url = new URL(obj.dataset.autocompleteUrl, window.location.origin);
      url.searchParams.set('ct', ct.value || '');
      if (term) url.searchParams.set('q', term);
      if (page) url.searchParams.set('page', page);
      return fetch(url, {headers: {'X-Requested-With': 'XMLHttpRequest'}}).then(r => r.json());
    }

    window.jQuery(obj).select2({
      ajax: {
        transport: function (params, success, failure) {
          fetchOptions(params.data.q, params.data.page).then(success).catch(failure);
        },
        processResults: function (data, params) {
          params.page = params.page || 1;
          return { results: data.results, pagination: { more: data.more } };
        }
      },
      minimumInputLength: 0,
      width: 'style'
    });

    window.jQuery(ct).select2({width: 'style'}).on('change', function(){
      window.jQuery(obj).val(null).trigger('change');
    });
  }

  document.addEventListener('DOMContentLoaded', function(){
    document.querySelectorAll('.form-row, .form-group, .fieldBox').forEach(init);
  });
})();
