(() => {
  const button = document.getElementById('menu-toggle');
  const nav = document.getElementById('primary-nav');
  if (!button || !nav) return;
  button.addEventListener('click', () => {
    const open = nav.classList.toggle('open');
    button.setAttribute('aria-expanded', String(open));
    button.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
  });
  nav.querySelectorAll('a').forEach(a => a.addEventListener('click', () => {
    nav.classList.remove('open'); button.setAttribute('aria-expanded', 'false');
  }));
})();
