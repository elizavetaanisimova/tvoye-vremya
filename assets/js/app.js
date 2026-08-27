/* Твоё Время. Клиентский код: меню, подбор массажа, ленивые iframe, появление блоков.
   Обработчиков scroll нет нигде: всё наблюдаемое сделано через IntersectionObserver,
   поэтому главный поток свободен и прокрутка не тормозит на телефоне. */
(function () {
  'use strict';

  document.documentElement.classList.add('js');

  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var hasIO = 'IntersectionObserver' in window;

  function readJSON(id) {
    var el = document.getElementById(id);
    if (!el) return null;
    try { return JSON.parse(el.textContent); } catch (e) { return null; }
  }

  // Карта услуг и варианты подбора приходят из content.py через build.py,
  // поэтому цены и названия не приходится дублировать здесь руками.
  var SERVICES = readJSON('tv-services');
  var PICKER = readJSON('tv-picker') || [];

  function param(name) {
    var m = new RegExp('[?&]' + name + '=([^&]*)').exec(location.search);
    return m ? decodeURIComponent(m[1]) : '';
  }

  function plural(n, one, few, many) {
    n = Math.abs(n);
    if (n % 10 === 1 && n % 100 !== 11) return one;
    if (n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 12 || n % 100 > 14)) return few;
    return many;
  }

  function humanTime(mins) {
    var h = Math.floor(mins / 60), m = mins % 60;
    if (!h) return m + ' мин';
    return h + ' ч' + (m ? ' ' + m + ' мин' : '');
  }

  /* ------------------------------------------------------------------ *
   * Шапка и нижняя панель. Обе завязаны на маячок внутри первого экрана.
   * ------------------------------------------------------------------ */
  var hdr = document.getElementById('hdr');
  var bar = document.querySelector('.bar');
  var hero = document.getElementById('top');

  if (hero && hasIO) {
    var sentinel = document.createElement('div');
    sentinel.setAttribute('aria-hidden', 'true');
    sentinel.style.cssText = 'position:absolute;top:55vh;left:0;width:1px;height:1px;pointer-events:none';
    hero.style.position = 'relative';
    hero.appendChild(sentinel);

    new IntersectionObserver(function (entries) {
      var passed = !entries[0].isIntersecting && entries[0].boundingClientRect.top < 0;
      hdr.classList.toggle('is-stuck', passed);
      if (bar) bar.classList.toggle('is-on', passed);
    }, { threshold: 0 }).observe(sentinel);
  } else {
    // Внутренние страницы: шапка и панель нужны сразу.
    hdr.classList.add('is-stuck');
    if (bar) bar.classList.add('is-on');
  }

  /* ------------------------------------------------------------------ *
   * Мобильное меню
   * ------------------------------------------------------------------ */
  var burger = document.getElementById('burger');
  var menu = document.getElementById('menu');
  var menuClose = document.getElementById('menuClose');

  function openMenu() {
    menu.hidden = false;
    document.body.classList.add('is-locked');
    burger.setAttribute('aria-expanded', 'true');
    menuClose.focus();
  }
  function closeMenu() {
    menu.hidden = true;
    document.body.classList.remove('is-locked');
    burger.setAttribute('aria-expanded', 'false');
    burger.focus();
  }
  if (burger && menu) {
    burger.addEventListener('click', openMenu);
    menuClose.addEventListener('click', closeMenu);
    menu.addEventListener('click', function (e) { if (e.target.closest('a')) closeMenu(); });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !menu.hidden) closeMenu();
    });
  }

  /* ------------------------------------------------------------------ *
   * Ленивые iframe: форма записи YCLIENTS и карта Яндекса.
   * Ставим их в DOM только когда пользователь близко, чтобы не тормозить
   * первую загрузку на мобильном интернете.
   * ------------------------------------------------------------------ */
  function mountFrame(host, src, title, allow) {
    if (host.dataset.mounted) return;
    host.dataset.mounted = '1';
    var f = document.createElement('iframe');
    f.src = src;
    f.title = title;
    f.loading = 'lazy';
    if (allow) f.setAttribute('allow', allow);
    f.setAttribute('allowfullscreen', '');
    f.addEventListener('load', function () { host.classList.add('is-ready'); });
    host.appendChild(f);
  }

  // Если пришли по ссылке /zapis/?u=<программа>, открываем форму сразу
  // с проставленными галочками на нужных услугах.
  var picked = [];
  if (SERVICES) {
    param('u').split(',').forEach(function (k) {
      if (k && SERVICES.items[k] && picked.indexOf(k) === -1) picked.push(k);
    });
  }

  var pickNote = document.getElementById('bookPick');
  if (picked.length && pickNote) {
    var names = picked.map(function (k) { return SERVICES.items[k].name; });
    var mins = picked.reduce(function (n, k) { return n + SERVICES.items[k].mins; }, 0);
    var sum = picked.reduce(function (n, k) { return n + SERVICES.items[k].price; }, 0);
    pickNote.hidden = false;
    pickNote.innerHTML = 'Уже отмечено: <strong>' + names.join(', ') + '</strong>. ' +
      humanTime(mins) + ', ' + sum + ' р. Состав можно изменить прямо в форме.';
  }

  var frames = [];
  Array.prototype.forEach.call(document.querySelectorAll('[data-yclients]'), function (h) {
    var src = h.getAttribute('data-yclients');
    if (picked.length) {
      src += (src.indexOf('?') > -1 ? '&' : '?') + 'o=' +
             picked.map(function (k) { return 's' + SERVICES.items[k].id; }).join('');
    }
    frames.push([h, src, 'Онлайн-запись в студию массажа «Твоё Время»',
                 'payment; clipboard-write']);
  });
  Array.prototype.forEach.call(document.querySelectorAll('[data-map]'), function (h) {
    frames.push([h, h.getAttribute('data-map'),
                 'Студия массажа «Твоё Время» на карте: Минск, ул. Петра Мстиславца, 18', '']);
  });

  function mountRow(r) { mountFrame(r[0], r[1], r[2], r[3]); }

  function nearViewport(el, factor) {
    var r = el.getBoundingClientRect();
    var vh = window.innerHeight || 0;
    if (!vh) return false;
    return r.top < vh * factor && r.bottom > -vh * factor;
  }

  if (frames.length) {
    // Что уже видно при загрузке, ставим сразу: ждать наблюдателя незачем.
    frames.forEach(function (r) { if (nearViewport(r[0], 1.5)) mountRow(r); });

    if (hasIO) {
      var fio = new IntersectionObserver(function (entries, obs) {
        entries.forEach(function (e) {
          if (!e.isIntersecting) return;
          for (var i = 0; i < frames.length; i++) {
            if (frames[i][0] === e.target) { mountRow(frames[i]); break; }
          }
          obs.unobserve(e.target);
        });
      }, { rootMargin: '400px 0px' });
      frames.forEach(function (r) { fio.observe(r[0]); });
    } else {
      frames.forEach(mountRow);
    }

    // Подстраховка: форма записи это главный смысл страницы, и она не должна
    // зависеть от того, сработал наблюдатель или нет.
    setTimeout(function () {
      frames.forEach(function (r) {
        if (!r[0].dataset.mounted && r[0].hasAttribute('data-yclients')) mountRow(r);
      });
    }, 3000);

    // Если человек тянется к форме мышью или пальцем, грузим её немедленно.
    ['pointerdown', 'touchstart', 'mouseover'].forEach(function (ev) {
      document.addEventListener(ev, function (e) {
        var host = e.target && e.target.closest && e.target.closest('[data-yclients],[data-map]');
        if (!host) return;
        for (var i = 0; i < frames.length; i++) {
          if (frames[i][0] === host) { mountRow(frames[i]); break; }
        }
      }, { passive: true });
    });
  }

  /* ------------------------------------------------------------------ *
   * Подбор массажа.
   * Состояний можно отметить сколько угодно. Из них собирается набор
   * программ, который дальше правится галочками, и всё это уходит
   * в форму записи одной ссылкой: YCLIENTS принимает несколько услуг сразу.
   * ------------------------------------------------------------------ */
  var chips = Array.prototype.slice.call(document.querySelectorAll('.chip'));
  var panel = document.getElementById('pickerPanel');
  var ITEMS = SERVICES ? SERVICES.items : {};
  var chosen = [];   // отмеченные состояния
  var basket = [];   // программы, которые поедут в запись

  function optionFor(key) {
    for (var i = 0; i < PICKER.length; i++) {
      if (PICKER[i].key === key) return PICKER[i];
    }
    return null;
  }

  // Основная программа под каждое отмеченное состояние, без повторов
  // и в том порядке, в котором отмечали.
  function suggest() {
    var out = [];
    chosen.forEach(function (key) {
      var o = optionFor(key);
      if (o && ITEMS[o.prog] && out.indexOf(o.prog) === -1) out.push(o.prog);
    });
    return out;
  }

  // Что предложить дополнительно: подсказки из content.py, кроме уже набранного.
  function extras() {
    var out = [];
    chosen.forEach(function (key) {
      var o = optionFor(key);
      (o && o.extra ? o.extra : []).forEach(function (k) {
        if (ITEMS[k] && basket.indexOf(k) === -1 && out.indexOf(k) === -1) out.push(k);
      });
    });
    return out;
  }

  // Подсказка про Signature показывается, только если она действительно
  // закрывает всё отмеченное: обещать лимфодренаж внутри Signature нельзя.
  function altHint() {
    var alt = SERVICES && SERVICES.alt;
    if (!alt || basket.length < 2 || basket.indexOf(alt) > -1) return '';
    var a = ITEMS[alt];
    if (!a) return '';
    var coversAll = chosen.every(function (k) { return a.covers.indexOf(k) > -1; });
    if (!coversAll) return '';
    var total = basket.reduce(function (n, k) { return n + ITEMS[k].price; }, 0);
    if (total <= a.price) return '';
    return '<p class="res__alt">Всё это есть и в одной программе: <a href="' + a.page +
      '">' + a.name + '</a>, ' + a.dur + ' за ' + a.price +
      ' р. Выходит дешевле, чем ' + basket.length + ' ' +
      plural(basket.length, 'отдельный сеанс', 'отдельных сеанса', 'отдельных сеансов') + '.</p>';
  }

  function row(key, checked, tag) {
    var p = ITEMS[key];
    return '<li><label class="pick' + (checked ? ' is-on' : '') + '">' +
      '<input type="checkbox" data-prog="' + key + '"' + (checked ? ' checked' : '') + '>' +
      '<span class="pick__box" aria-hidden="true"></span>' +
      '<span class="pick__t">' + p.name + '</span>' +
      '<span class="pick__d">' + p.dur +
        (tag ? '<span class="pick__tag">' + tag + '</span>' : '') + '</span>' +
      '<span class="pick__p">' + p.price + ' р.</span>' +
      '</label></li>';
  }

  function renderEmpty() {
    panel.innerHTML =
      '<div class="picker__empty">' +
        '<svg class="i i--xl" aria-hidden="true"><use href="#i-leaf"></use></svg>' +
        '<p>Не нужно разбираться в названиях. Отметьте, что беспокоит, и мы подскажем.</p>' +
        '<a class="lnk" href="https://t.me/marussy1987" target="_blank" rel="noopener">' +
        'Написать в Telegram</a>' +
      '</div>';
  }

  function render() {
    if (!panel) return;
    if (!chosen.length) { renderEmpty(); return; }

    var why = chosen.map(function (k) {
      var o = optionFor(k);
      return o ? o.why : '';
    }).filter(Boolean)[0] || '';

    var rows = basket.map(function (k) { return row(k, true, ''); }).join('');
    var add = extras().map(function (k) { return row(k, false, 'часто добавляют'); }).join('');

    var mins = basket.reduce(function (n, k) { return n + ITEMS[k].mins; }, 0);
    var sum = basket.reduce(function (n, k) { return n + ITEMS[k].price; }, 0);

    var total = basket.length
      ? '<div class="res__total">' +
          '<span>' + basket.length + ' ' +
          plural(basket.length, 'программа', 'программы', 'программ') + '</span>' +
          '<span>' + humanTime(mins) + '</span>' +
          '<strong>' + sum + ' р.</strong>' +
        '</div>'
      : '<p class="res__none">Ничего не отмечено. Выберите хотя бы одну программу, ' +
        'чтобы записаться.</p>';

    var href = '/zapis/' + (basket.length ? '?u=' + basket.join(',') : '');
    var cta = basket.length
      ? '<a class="btn btn--gold" href="' + href + '">Записаться' +
        (basket.length > 1 ? ' на ' + basket.length + ' ' +
          plural(basket.length, 'программу', 'программы', 'программ') : '') + '</a>'
      : '';

    panel.innerHTML =
      '<div class="res">' +
        '<div>' +
          '<p class="res__kicker">Мы поняли так</p>' +
          '<h3 class="res__name">' +
            (basket.length ? 'Вот что подойдёт' : 'Соберите визит') + '</h3>' +
          '<p class="res__why">' + why + '</p>' +
          altHint() +
        '</div>' +
        '<div class="res__side">' +
          '<ul class="picks">' + rows + add + '</ul>' +
          total +
          '<div class="res__act">' + cta +
            '<a class="lnk" href="https://t.me/marussy1987" target="_blank" rel="noopener">' +
            'Спросить совет</a>' +
          '</div>' +
        '</div>' +
      '</div>';
  }

  if (panel) {
    panel.addEventListener('change', function (e) {
      var box = e.target;
      if (!box || box.type !== 'checkbox' || !box.getAttribute('data-prog')) return;
      var key = box.getAttribute('data-prog');
      var at = basket.indexOf(key);
      if (box.checked && at === -1) basket.push(key);
      if (!box.checked && at > -1) basket.splice(at, 1);
      render();
    });
  }

  chips.forEach(function (chip) {
    chip.addEventListener('click', function () {
      var key = chip.getAttribute('data-key');
      var on = chip.getAttribute('aria-pressed') === 'true';
      chip.setAttribute('aria-pressed', on ? 'false' : 'true');
      var at = chosen.indexOf(key);
      if (!on && at === -1) chosen.push(key);
      if (on && at > -1) chosen.splice(at, 1);
      basket = suggest();
      render();
    });
  });

  /* ------------------------------------------------------------------ *
   * Появление блоков при прокрутке. Один проход, потом наблюдатель снимается.
   * ------------------------------------------------------------------ */
  if (!reduced && hasIO) {
    var groups = ['.sec__head', '.band__it', '.picker__chips', '.picker__panel',
                  '.scard', '.pcard', '.pgroup__head', '.step', '.gallery figure', '.rev',
                  '.panel', '.q', '.how__i', '.marks', '.way', '.rel__i', '.rsum',
                  '.kont__info', '.kont__map', '.note', '.book', '.strip__in'];
    var io = new IntersectionObserver(function (entries, obs) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-in');
        obs.unobserve(entry.target);
      });
    }, { rootMargin: '0px 0px -6% 0px', threshold: 0.1 });

    groups.forEach(function (sel) {
      Array.prototype.forEach.call(document.querySelectorAll(sel), function (node, i) {
        node.classList.add('reveal');
        node.style.setProperty('--d', Math.min(i, 5) * 60 + 'ms');
        io.observe(node);
      });
    });
  }

  /* ------------------------------------------------------------------ *
   * Подсветка активного раздела в шапке
   * ------------------------------------------------------------------ */
  var here = location.pathname;
  Array.prototype.forEach.call(document.querySelectorAll('.nav a'), function (a) {
    var href = a.getAttribute('href');
    if (href.charAt(0) === '/' && href.length > 1 && here.indexOf(href) === 0) {
      a.classList.add('is-active');
    }
  });
})();
