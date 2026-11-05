// Favorite words, kept in this browser only (localStorage), so each person
// has their own list and nothing is sent anywhere.
const Favorites = (() => {
  const KEY = 'wordlist-favorites';

  function all() {
    try {
      const list = JSON.parse(localStorage.getItem(KEY));
      return Array.isArray(list) ? list : [];
    } catch {
      return [];
    }
  }

  function save(list) {
    try {
      localStorage.setItem(KEY, JSON.stringify(list));
      return true;
    } catch {
      return false;
    }
  }

  const has = url => all().some(f => f.url === url);

  // Adds the word if it isn't a favorite yet, removes it if it is.
  // Returns whether it is a favorite afterwards.
  function toggle(word, url) {
    const list = all();
    const i = list.findIndex(f => f.url === url);
    if (i >= 0) list.splice(i, 1);
    else list.unshift({ word, url, added: Date.now() });
    save(list);
    return i < 0;
  }

  const remove = url => save(all().filter(f => f.url !== url));

  return { all, has, toggle, remove };
})();
