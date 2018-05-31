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
  function filter(skipHashUpdate) {
    pending = null;
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
      if (!table.hasAttribute('class')) {
        table.className = 'filtered';
      }
      const trs = table.querySelectorAll('tr');
      let count = 0;
      for (let i = 1; i < trs.length; i++) {
        const match = re.test(trs[i].textContent);
        trs[i].hidden = !match;
        if (match) {
          count++;
          // even/odd is off by 1 because the header row is skipped
          trs[i].className = count % 2 == 0 ? '' : 'even';
        }
      }
      const prev = table.previousElementSibling;
      prev.textContent = prev.textContent.replace(/\(\d+/, "(" + count);
      if (prev.localName === 'summary') {
        count1Browser += count;
      }
    }
    heading1Browser.textContent = heading1Browser.textContent.replace(/\(\d+/, "(" + count1Browser);
    history.replaceState(null, document.title, value ? '#filter=' + encodeURIComponent(value) : location.pathname);
  }
  filterInput.oninput = queueFilter;
  if (location.hash.indexOf('#filter=') != -1) {
    filterInput.value = decodeURIComponent(location.hash.match(/^\#filter=(.*)$/)[1]);
    filter();
  }
})();
