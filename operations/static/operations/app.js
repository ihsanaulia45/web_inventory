document.addEventListener('DOMContentLoaded',()=>{
  const sidebar=document.querySelector('#sidebar');
  const backdrop=document.querySelector('.mobile-backdrop');
  const closeMenu=()=>{sidebar?.classList.remove('open');backdrop?.classList.remove('active')};
  document.querySelector('[data-menu-toggle]')?.addEventListener('click',()=>{sidebar?.classList.toggle('open');backdrop?.classList.toggle('active')});
  document.querySelector('[data-menu-close]')?.addEventListener('click',closeMenu);
  document.addEventListener('keydown',event=>{if(event.key==='Escape')closeMenu();if((event.metaKey||event.ctrlKey)&&event.key.toLowerCase()==='k'){event.preventDefault();document.querySelector('.global-search input')?.focus()}});
  const tabs=[...document.querySelectorAll('[data-tab]')];
  tabs.forEach(tab=>tab.addEventListener('click',()=>{
    tabs.forEach(item=>item.classList.toggle('active',item===tab));
    document.querySelectorAll('[data-panel]').forEach(panel=>panel.classList.toggle('active',panel.dataset.panel===tab.dataset.tab));
  }));
});
