(function() {
  const tables = Array.from(document.querySelectorAll('table'));
  const heading1Browser = document.getElementById('1-browser');
  function filter(event) {
    const input = event.target;
    input.setCustomValidity('');
    const value = input.value;
    let re;
    try {
      re = new RegExp(value);
    } catch(e) {
      input.setCustomValidity(e);
      input.reportValidity();
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
  const filterInput = document.querySelector('#filter-input');
  filterInput.oninput = filter;
  if (location.hash.indexOf('#filter=') != -1) {
    filterInput.value = location.hash.match(/^\#filter=(.*)$/)[1];
    filter({target: filterInput});
  }
})();
