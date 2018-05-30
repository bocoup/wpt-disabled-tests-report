(function() {
  const filterInput = document.querySelector('#filter-input');
  const tables = Array.from(document.querySelectorAll('table'));
  const heading1Browser = document.getElementById('1-browser');
  let pending = null;
  function request(callback, ms) {
    if (window.requestIdleCallback) {
      pending = requestIdleCallback(callback, {timeout: ms});
    } else {
      pending = setTimeout(callback, ms)
    }
  }
  function cancel(handle) {
    (window.cancelIdleCallback || window.clearTimeout)(handle);
  }
  function queueFilter() {
    if (pending) {
      cancel(pending);
    }
    request(filter, 100);
  }
  function filter() {
    filterInput.setCustomValidity('');
    const value = filterInput.value;
    let re;
    try {
      re = new RegExp(value, 'i');
    } catch(e) {
      filterInput.setCustomValidity(e);
      filterInput.reportValidity();
      return;
    }
    let count1Browser = 0;
    for (const table of tables) {
      const trs = table.querySelectorAll('tr');
      let count = 0;
      for (let i = 1; i < trs.length; i++) {
        const path = trs[i].firstElementChild.firstElementChild.firstChild.data;
        const match = re.test(path);
        trs[i].hidden = !match;
        if (match) {
          count++;
        }
      }
      const prev = table.previousElementSibling;
      prev.textContent = prev.textContent.replace(/\(\d+/, "(" + count);
      if (prev.localName === 'summary') {
        count1Browser += count;
      }
    }
    heading1Browser.textContent = heading1Browser.textContent.replace(/\(\d+/, "(" + count1Browser);
    history.replaceState(null, document.title, value ? '#filter=' + value : location.pathname);
  }
  filterInput.oninput = queueFilter;
  if (location.hash.indexOf('#filter=') != -1) {
    filterInput.value = location.hash.match(/^\#filter=(.*)$/)[1];
    filter({target: filterInput});
  }
})();
