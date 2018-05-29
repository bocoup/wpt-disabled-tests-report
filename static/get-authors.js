async function getAuthors(path) {
  const response = await fetch("https://api.github.com/repos/web-platform-tests/wpt/commits?path=" + encodeURIComponent(path));
  const commits = await response.json();
  let authors = [];
  for (const commit of commits) {
    const author = commit.author && commit.author.login;
    if (author && authors.indexOf(author) == -1) {
      authors.push(author);
    }
  }
  return authors;
}
addEventListener('click', async function(e) {
  const target = e.target;
  if (target instanceof HTMLAnchorElement && target.textContent === "New issue") {
    if (e.ctrlKey || e.metaKey || e.button != 0 ||
        target.classList.contains('has-authors')) {
      return true;
    }
    e.preventDefault();
    const path = target.parentNode.parentNode.firstElementChild.textContent;
    const authors = await getAuthors(path);
    if (authors.length) {
      target.href = target.href.replace("%40zcorpan", "%40" + authors.join(" %40"));
    }
    target.classList.add('has-authors');
    target.click();
  }
}, false);
