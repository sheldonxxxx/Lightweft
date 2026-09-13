'use strict';

(() => {
  const sizes = '(min-width: 1400px) 1280px, 92vw';
  const collections = document.getElementById('collections');

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function imageSource(image, source) {
    image.src = source.src;
    image.srcset = source.srcset.map(item => `${item.src} ${item.width}w`).join(', ');
    image.sizes = sizes;
  }

  function largest(source) {
    return source.srcset.reduce((best, item) => item.width > best.width ? item : best).src;
  }

  function sideText(photo, side) {
    const defaults = side === 'before'
      ? {label: 'Before', description: 'Unadjusted RAW rendering'}
      : {label: 'After', description: 'Edited photograph'};
    return {label: photo[side].label ?? defaults.label, description: photo[side].description ?? defaults.description};
  }

  function makePhoto(photo, index, groupId) {
    const before = sideText(photo, 'before');
    const after = sideText(photo, 'after');
    const article = element('article', 'photo-story');
    const heading = element('div', 'photo-heading');
    const title = element('h3');
    title.id = `${groupId}-${photo.id}-title`;
    title.append(element('span', 'photo-index', String(index + 1).padStart(2, '0')), document.createTextNode(photo.title));
    heading.append(title, element('p', '', photo.description));
    article.append(heading);

    const figure = element('div', 'comparison');
    figure.dataset.photo = photo.id;
    figure.style.setProperty('--photo-ratio', `${photo.width} / ${photo.height}`);
    figure.setAttribute('role', 'group');
    figure.setAttribute('aria-labelledby', title.id);
    for (const version of ['after', 'before']) {
      const image = element('img', `${version}-image`);
      imageSource(image, photo[version]);
      image.width = photo.width;
      image.height = photo.height;
      image.loading = 'lazy';
      image.decoding = 'async';
      const side = version === 'before' ? before : after;
      image.alt = `${side.label} — ${side.description}: ${photo.alt}`;
      figure.append(image);
    }

    const beforeLabel = element('span', 'image-label image-label-before', before.label);
    const afterLabel = element('span', 'image-label image-label-after', after.label);
    const divider = element('span', 'compare-divider');
    divider.setAttribute('aria-hidden', 'true');
    divider.append(element('span', 'compare-handle', '↔'));
    const input = element('input', 'compare-range');
    input.type = 'range';
    input.min = '0';
    input.max = '100';
    input.step = '1';
    input.value = '50';
    input.setAttribute('aria-label', `Comparison divider for ${photo.title}: ${before.label} and ${after.label}`);
    const helpId = `${groupId}-${photo.id}-help`;
    input.setAttribute('aria-describedby', helpId);
    figure.append(beforeLabel, afterLabel, divider, input);
    article.append(figure);

    const toolbar = element('div', 'compare-toolbar');
    const buttons = element('div', 'compare-buttons');
    buttons.setAttribute('role', 'group');
    buttons.setAttribute('aria-label', `View options for ${photo.title}`);
    const state = element('strong', '', 'Split view');
    const help = element('p', 'compare-help');
    help.id = helpId;
    help.append(state, element('br'), document.createTextNode('Drag divider · Use arrow keys when focused'));
    const choices = [{label: before.label, description: before.description, value: 100},
      {label: 'Compare', value: 50}, {label: after.label, description: after.description, value: 0}];
    const controls = choices.map(choice => {
      const button = element('button', '', choice.label);
      button.type = 'button';
      button.setAttribute('aria-label', `${choice.value === 50 ? `Compare ${before.label} and ${after.label}` : `Show ${choice.label}: ${choice.description}`} — ${photo.title}`);
      button.addEventListener('click', () => update(choice.value));
      buttons.append(button);
      return {button, value: choice.value};
    });

    function update(rawValue) {
      const value = Math.max(0, Math.min(100, Number(rawValue)));
      input.value = String(value);
      figure.style.setProperty('--divider', `${value}%`);
      input.setAttribute('aria-valuetext', value === 100 ? `Full ${before.label} image: ${before.description}` : value === 0 ? `Full ${after.label} image: ${after.description}` : `${value}% ${before.label} and ${100 - value}% ${after.label}`);
      beforeLabel.hidden = value < 16;
      afterLabel.hidden = value > 84;
      divider.hidden = value === 0 || value === 100;
      state.textContent = value === 100 ? `${before.label} · ${before.description}` : value === 0 ? `${after.label} · ${after.description}` : `Split view · ${value}% ${before.label} / ${100 - value}% ${after.label}`;
      for (const control of controls) {
        const pressed = control.value === 50 ? value > 0 && value < 100 : value === control.value;
        control.button.setAttribute('aria-pressed', String(pressed));
      }
    }

    input.addEventListener('input', event => update(event.target.value));
    update(50);
    toolbar.append(buttons, help);
    article.append(toolbar);
    const links = element('p', 'photo-links');
    for (const version of ['before', 'after']) {
      const side = version === 'before' ? before : after;
      const link = element('a', '', `Open ${side.label} ↗`);
      link.setAttribute('aria-label', `Open ${side.label}: ${side.description} — ${photo.title}`);
      link.title = side.description;
      link.href = largest(photo[version]);
      links.append(link);
    }
    article.append(links);
    return article;
  }

  function checkedFields(value, required, optional = []) {
    return value !== null && typeof value === 'object' && !Array.isArray(value) &&
      required.every(field => Object.hasOwn(value, field)) &&
      Object.keys(value).every(field => required.includes(field) || optional.includes(field));
  }

  function validSource(source) {
    const localImage = value => typeof value === 'string' && /^assets\/[a-z0-9/-]+\.jpg$/.test(value) && !value.includes('..');
    return checkedFields(source, ['src', 'srcset'], ['label', 'description']) &&
      ['label', 'description'].every(field => !Object.hasOwn(source, field) || (typeof source[field] === 'string' && source[field].trim().length > 0)) &&
      localImage(source.src) && Array.isArray(source.srcset) && source.srcset.length > 0 &&
      source.srcset.every(item => checkedFields(item, ['src', 'width']) && localImage(item.src) && Number.isInteger(item.width) && item.width > 0);
  }

  function validData(data) {
    const slug = value => typeof value === 'string' && /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(value);
    const text = value => typeof value === 'string' && value.trim().length > 0;
    return checkedFields(data, ['schemaVersion', 'groups']) && data.schemaVersion === 1 && Array.isArray(data.groups) && data.groups.length > 0 &&
      data.groups.every(group => checkedFields(group, ['id', 'number', 'title', 'subtitle', 'photos'])) &&
      new Set(data.groups.map(group => group.id)).size === data.groups.length &&
      data.groups.every(group => slug(group.id) && text(group.number) && text(group.title) && text(group.subtitle) &&
        Array.isArray(group.photos) && group.photos.length > 0 &&
        group.photos.every(photo => checkedFields(photo, ['id', 'title', 'description', 'alt', 'width', 'height', 'before', 'after'])) &&
        new Set(group.photos.map(photo => photo.id)).size === group.photos.length &&
        group.photos.every(photo => slug(photo.id) && text(photo.title) && text(photo.description) && text(photo.alt) &&
          Number.isSafeInteger(photo.width) && photo.width > 0 && Number.isSafeInteger(photo.height) && photo.height > 0 &&
          validSource(photo.before) && validSource(photo.after)));
  }

  async function load() {
    try {
      const response = await fetch('data.json');
      if (!response.ok) throw new Error('Photo collection unavailable');
      const data = await response.json();
      if (!validData(data)) throw new Error('Invalid photo collection');
      const fragment = document.createDocumentFragment();
      const nav = document.getElementById('collection-nav');
      const navLinks = document.createDocumentFragment();
      for (const group of data.groups) {
        const section = element('section', 'photo-group');
        section.id = group.id;
        const headingId = `${group.id}-title`;
        section.setAttribute('aria-labelledby', headingId);
        const heading = element('div', 'group-heading');
        const groupTitle = element('h2', '', group.title);
        groupTitle.id = headingId;
        heading.append(element('p', 'eyebrow', `Collection ${group.number} / ${String(group.photos.length).padStart(2, '0')} photographs`), groupTitle, element('p', 'group-description', group.subtitle));
        section.append(heading);
        group.photos.forEach((photo, index) => section.append(makePhoto(photo, index, group.id)));
        fragment.append(section);
        const link = element('a', '', `${group.number} · ${group.title}`);
        link.href = `#${group.id}`;
        navLinks.append(link);
      }
      collections.replaceChildren(fragment);
      nav.replaceChildren(navLinks);
      nav.hidden = data.groups.length < 2;
      document.getElementById('hero-count').textContent = `${String(data.groups[0].photos.length).padStart(2, '0')} photographs`;
      if (window.location.hash) {
        const target = document.getElementById(decodeURIComponent(window.location.hash.slice(1)));
        if (target && collections.contains(target)) target.scrollIntoView();
      }
    } catch {
      // The static photographs and direct image links remain available.
    }
  }

  load();
})();
