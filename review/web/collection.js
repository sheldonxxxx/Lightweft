import {el, button} from './dom.js';

export function matchCollection(item, query) {
  if (!query) return true;
  const text = [item.title, item.description, item.id].filter(Boolean).join(' ').toLowerCase();
  return query.toLowerCase().split(/\s+/).every(word => text.includes(word));
}

export function createCollectionPicker({onSelect, onShowDisabled}) {
  let items = [];
  let selectedId = '';
  let query = '';
  let activeIndex = -1;
  let open = false;
  let locked = false;
  let canRevealHidden = false;
  let emptyMessage = 'No collections yet.';

  const titleNode = el('span', {class: 'collection-trigger-title'}, 'No collections yet');
  const trigger = el('button', {
    type: 'button',
    class: 'collection-trigger',
    'aria-haspopup': 'listbox',
    'aria-expanded': 'false',
    'aria-controls': 'collection-menu',
    disabled: true,
    onClick: () => (open ? closeMenu() : openMenu()),
    onKeydown: event => {
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp' || event.key === 'Enter' || event.key === ' ') {
        if (open) return;
        event.preventDefault();
        openMenu({focus: event.key === 'ArrowUp' ? 'last' : 'first'});
      } else if (event.key === 'Escape' && open) {
        event.preventDefault();
        closeMenu({focusTrigger: true});
      }
    },
  },
  el('span', {class: 'collection-trigger-title-row'}, titleNode),
  el('span', {class: 'collection-trigger-chevron', 'aria-hidden': 'true'}, '▾'));

  const search = el('input', {
    type: 'search',
    class: 'collection-menu-search',
    placeholder: 'Find a collection…',
    'aria-label': 'Filter collections',
    'aria-controls': 'collection-menu',
    'aria-expanded': 'false',
    'aria-autocomplete': 'list',
    autocomplete: 'off',
    role: 'combobox',
    onInput: event => { query = event.target.value; renderList(); },
    onKeydown: event => onListKeydown(event),
  });
  const searchRow = el('div', {class: 'collection-menu-search-row'}, search);
  const list = el('div', {
    class: 'collection-menu-list',
    role: 'listbox',
    id: 'collection-menu',
    'aria-label': 'Review collections',
    tabIndex: -1,
    onKeydown: event => onListKeydown(event),
  });
  const empty = el('p', {class: 'collection-menu-empty', hidden: true});
  const menu = el('div', {class: 'collection-menu', hidden: true}, searchRow, list, empty);
  const root = el('div', {class: 'collection-picker'}, trigger, menu);

  const visibleItems = () => items.filter(item => matchCollection(item, query));

  function renderList() {
    const matches = visibleItems();
    searchRow.hidden = items.length < 5;
    list.replaceChildren(...matches.map((item, index) => {
      const option = el('div', {
        class: 'collection-option',
        role: 'option',
        id: `collection-option-${index}`,
        'aria-selected': item.id === selectedId ? 'true' : 'false',
        tabIndex: -1,
        dataset: {id: item.id},
        onClick: () => choose(item.id),
        onKeydown: event => {
          if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); choose(item.id); }
        },
      },
      el('span', {class: 'collection-option-row'},
        el('span', {class: 'collection-option-title'}, item.title),
        item.disabled && el('span', {class: 'collection-option-badge'}, 'disabled')),
      item.description && el('span', {class: 'collection-option-desc'}, item.description));
      if (item.id === selectedId) option.classList.add('is-current');
      return option;
    }));
    empty.replaceChildren();
    if (!matches.length) {
      empty.hidden = false;
      if (query) empty.append('No collections match your filter.');
      else {
        empty.append(emptyMessage);
        if (canRevealHidden && /^No enabled/i.test(emptyMessage)) {
          empty.append(button('Show disabled collections', () => onShowDisabled?.(), {class: 'collection-menu-action'}));
        }
      }
    } else empty.hidden = true;
    activeIndex = matches.findIndex(item => item.id === selectedId);
    if (activeIndex < 0) activeIndex = matches.length ? 0 : -1;
    highlightActive(false);
  }

  function highlightActive(scroll = true) {
    const options = [...list.querySelectorAll('.collection-option')];
    let activeId = '';
    options.forEach((node, index) => {
      const active = index === activeIndex;
      node.classList.toggle('is-active', active);
      if (active) {
        activeId = node.id;
        if (scroll) node.scrollIntoView({block: 'nearest'});
      }
    });
    if (activeId) {
      list.setAttribute('aria-activedescendant', activeId);
      search.setAttribute('aria-activedescendant', activeId);
    } else {
      list.removeAttribute('aria-activedescendant');
      search.removeAttribute('aria-activedescendant');
    }
  }

  function moveActive(delta) {
    const options = visibleItems();
    if (!options.length) return;
    activeIndex = (activeIndex + delta + options.length) % options.length;
    highlightActive();
  }

  function onListKeydown(event) {
    if (event.key === 'ArrowDown') { event.preventDefault(); moveActive(1); }
    else if (event.key === 'ArrowUp') { event.preventDefault(); moveActive(-1); }
    else if (event.key === 'Home') { event.preventDefault(); activeIndex = 0; highlightActive(); }
    else if (event.key === 'End') { event.preventDefault(); activeIndex = Math.max(0, visibleItems().length - 1); highlightActive(); }
    else if ((event.key === 'Enter' || event.key === ' ') && event.target !== search) {
      event.preventDefault();
      const item = visibleItems()[activeIndex];
      if (item) choose(item.id);
    } else if (event.key === 'Enter' && event.target === search) {
      event.preventDefault();
      const item = visibleItems()[activeIndex];
      if (item) choose(item.id);
    } else if (event.key === 'Escape') {
      event.preventDefault();
      closeMenu({focusTrigger: true});
    } else if (event.key === 'Tab') closeMenu();
  }

  function choose(id) {
    closeMenu({focusTrigger: true});
    if (id && id !== selectedId) onSelect(id);
    else renderList();
  }

  function openMenu({focus} = {}) {
    if (locked || trigger.disabled) return;
    open = true;
    query = '';
    search.value = '';
    menu.hidden = false;
    trigger.setAttribute('aria-expanded', 'true');
    search.setAttribute('aria-expanded', 'true');
    root.classList.add('is-open');
    renderList();
    if (focus === 'last') {
      const matches = visibleItems();
      activeIndex = Math.max(0, matches.length - 1);
      highlightActive(false);
    }
    if (visibleItems().length && !searchRow.hidden) search.focus();
    else if (visibleItems().length) list.focus();
    else {
      const action = empty.querySelector('button');
      action?.focus();
    }
  }

  function closeMenu({focusTrigger = false} = {}) {
    if (!open) return;
    open = false;
    menu.hidden = true;
    trigger.setAttribute('aria-expanded', 'false');
    search.setAttribute('aria-expanded', 'false');
    search.removeAttribute('aria-activedescendant');
    root.classList.remove('is-open');
    if (focusTrigger) trigger.focus();
  }

  document.addEventListener('pointerdown', event => {
    if (open && !root.contains(event.target)) closeMenu();
  });

  return {
    element: root,
    closeMenu,
    setLocked(value) {
      locked = value;
      trigger.disabled = value || (!items.length && !canRevealHidden);
      root.classList.toggle('is-disabled', trigger.disabled);
      root.classList.toggle('is-loading', value);
      if (value) closeMenu();
    },
    render(nextItems, currentId, {empty: message, loading = false, canRevealHidden: reveal = false} = {}) {
      items = nextItems;
      selectedId = currentId;
      if (message != null) emptyMessage = message;
      canRevealHidden = reveal;
      locked = loading;
      const current = items.find(item => item.id === selectedId);
      if (current) {
        titleNode.textContent = current.title;
        trigger.setAttribute('aria-label', `Review collection: ${current.title}`);
        trigger.title = current.description || current.title;
      } else {
        titleNode.textContent = items.length ? 'Select a collection' : emptyMessage.replace(/\.$/, '');
        trigger.setAttribute('aria-label', 'Review collection');
        trigger.title = items.length ? 'Choose a review collection' : emptyMessage;
      }
      const openable = items.length > 0 || (canRevealHidden && !loading);
      trigger.disabled = loading || !openable;
      root.classList.toggle('is-disabled', trigger.disabled);
      root.classList.toggle('is-loading', loading);
      if (open) {
        if (!openable) closeMenu();
        else renderList();
      }
    },
  };
}
