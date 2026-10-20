(() => {
  const editor = document.getElementById('post-editor'); if (!editor) return;
  const fields = ['id', 'title', 'slug', 'category', 'excerpt', 'body', 'published'];
  const nodes = Object.fromEntries(fields.map(name => [name, document.getElementById('post-' + name)]));
  document.querySelectorAll('.edit-post').forEach(button => {
    button.addEventListener('click', () => {
      const post = JSON.parse(button.dataset.post);
      fields.forEach(key => { if (key === 'published') nodes[key].checked = Boolean(post[key]);
        else nodes[key].value = post[key] || ''; });
      document.getElementById('editor-heading').textContent = 'Edit journal entry';
      editor.scrollIntoView({behavior:'smooth',block:'start'});
    });
  });
  document.getElementById('post-reset').addEventListener('click', () => {
    editor.reset(); nodes.id.value = 0;
    document.getElementById('editor-heading').textContent = 'New journal entry';
  });
})();
