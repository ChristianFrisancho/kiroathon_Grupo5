// Visualizaciones con D3 (front/vendor/d3.min.js, mismo origen: compatible con la CSP).
// Reglas: cada gráfico apoya una tarea real del docente, tiene alternativa en texto o en controles
// existentes, respeta prefers-reduced-motion y nunca usa .html(): todo texto entra con .text().

const d3 = window.d3;
const SVG_NS = 'http://www.w3.org/2000/svg';

export const vizAvailable = () => Boolean(d3);
const reduceMotion = () => window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const dur = (ms) => (reduceMotion() ? 0 : ms);

function stopWhenDetached(node, timer) {
  // Los gráficos animados se detienen solos al salir de la vista (sin fugas de temporizadores).
  const check = d3.interval(() => {
    if (!node.isConnected) { timer.stop(); check.stop(); }
  }, 1000);
}

// ---------------------------------------------------------------------------------------------
// 1. Portada: el recorrido del docente como un caldero de luz que fluye entre cuatro estaciones.
// ---------------------------------------------------------------------------------------------
export function journeyFlow(container) {
  if (!d3) return null;
  const steps = [
    { id: 'modulo', label: 'Módulo', sub: 'M1 · M2 · M3' },
    { id: 'borrador', label: 'Borrador IA', sub: 'Bedrock prepara' },
    { id: 'revision', label: 'Tu revisión', sub: 'Tú decides' },
    { id: 'portafolio', label: 'Portafolio', sub: 'Guardado y versiones' },
  ];
  const W = 760; const H = 190;
  const svg = d3.select(container).append('svg')
    .attr('viewBox', `0 0 ${W} ${H}`).attr('class', 'viz viz-journey')
    .attr('role', 'img')
    .attr('aria-label', 'Recorrido: del módulo al borrador de la IA, a tu revisión y al portafolio.');
  const defs = svg.append('defs');
  const glow = defs.append('filter').attr('id', 'glow').attr('x', '-50%').attr('y', '-50%').attr('width', '200%').attr('height', '200%');
  glow.append('feGaussianBlur').attr('stdDeviation', 4).attr('result', 'blur');
  const merge = glow.append('feMerge');
  merge.append('feMergeNode').attr('in', 'blur');
  merge.append('feMergeNode').attr('in', 'SourceGraphic');

  const x = d3.scalePoint().domain(steps.map((s) => s.id)).range([80, W - 80]);
  const y = 82;
  // Camino ondulado que une las estaciones.
  const pts = steps.map((s, i) => [x(s.id), y + (i % 2 ? 18 : -18)]);
  const line = d3.line().curve(d3.curveCatmullRom.alpha(0.6));
  const path = svg.append('path').attr('class', 'journey-path').attr('d', line(pts));
  const length = path.node().getTotalLength();
  path.attr('stroke-dasharray', `${length} ${length}`).attr('stroke-dashoffset', length)
    .transition().duration(dur(1400)).ease(d3.easeCubicOut).attr('stroke-dashoffset', 0);

  // Capa de chispas debajo de las estaciones: no tapa los números ni las etiquetas.
  const sparks = svg.append('g').attr('class', 'sparks');
  const node = svg.selectAll('g.station').data(steps).join('g')
    .attr('class', (d, i) => `station station-${i}`)
    .attr('transform', (d, i) => `translate(${pts[i][0]},${pts[i][1]})`);
  node.append('circle').attr('class', 'station-halo').attr('r', 0)
    .transition().delay((d, i) => dur(300 + i * 250)).duration(dur(600)).attr('r', 30);
  node.append('circle').attr('class', 'station-core').attr('r', 0).attr('filter', 'url(#glow)')
    .transition().delay((d, i) => dur(300 + i * 250)).duration(dur(500)).ease(d3.easeBackOut).attr('r', 16);
  node.append('text').attr('class', 'station-num').attr('dy', '0.35em').attr('text-anchor', 'middle')
    .text((d, i) => String(i + 1));
  node.append('text').attr('class', 'station-label').attr('y', 52).attr('text-anchor', 'middle').text((d) => d.label);
  node.append('text').attr('class', 'station-sub').attr('y', 70).attr('text-anchor', 'middle').text((d) => d.sub);

  if (reduceMotion()) return svg.node();
  // Chispas que viajan por el camino: el contenido del módulo «fluye» hacia el portafolio.
  const pool = d3.range(14).map((i) => ({ t: i / 14, speed: 0.0009 + Math.random() * 0.0007, r: 1.5 + Math.random() * 2.5 }));
  const dots = sparks.selectAll('circle').data(pool).join('circle').attr('class', 'spark').attr('r', (d) => d.r);
  // Brasas que suben (detalle de la temática): pocas, lentas y sin bloquear nada.
  const embers = svg.append('g').attr('class', 'embers').selectAll('circle')
    .data(d3.range(10).map(() => ({ x: Math.random() * W, y: H + Math.random() * 60, v: 0.15 + Math.random() * 0.35 })))
    .join('circle').attr('class', 'ember').attr('r', () => 1 + Math.random() * 1.6);
  let last = 0;
  const timer = d3.timer((elapsed) => {
    const dt = Math.min(elapsed - last, 50);
    last = elapsed;
    dots.each(function move(d) {
      d.t = (d.t + d.speed * dt) % 1;
      const p = path.node().getPointAtLength(d.t * length);
      d3.select(this).attr('cx', p.x).attr('cy', p.y).attr('opacity', Math.sin(Math.PI * d.t));
    });
    embers.each(function rise(d) {
      d.y -= d.v * dt * 0.06;
      if (d.y < -10) { d.y = H + 10; d.x = Math.random() * W; }
      d3.select(this).attr('cx', d.x + Math.sin((elapsed / 900) + d.x) * 6).attr('cy', d.y)
        .attr('opacity', Math.max(0, Math.min(0.6, d.y / H)));
    });
  });
  stopWhenDetached(svg.node(), timer);
  return svg.node();
}

// ---------------------------------------------------------------------------------------------
// 2. Revisar: presupuesto de tiempo interactivo. Arrastra el borde entre dos actividades para pasar
//    minutos de una a otra (el total no cambia). Alternativa: los campos «Minutos» de cada actividad.
// ---------------------------------------------------------------------------------------------
export function timeBudget(container, { getActivities, getTotal, onShift, isLocked = () => false }) {
  if (!d3) return { update() {} };
  const W = 760; const H = 96; const top = 24; const barH = 40;
  const svg = d3.select(container).append('svg').attr('viewBox', `0 0 ${W} ${H}`).attr('class', 'viz viz-budget')
    .attr('role', 'img');
  const x = d3.scaleLinear().range([0, W]);
  const gSeg = svg.append('g');
  const gHandles = svg.append('g');
  const targetLine = svg.append('line').attr('class', 'budget-target').attr('y1', top - 10).attr('y2', top + barH + 10);
  const targetLabel = svg.append('text').attr('class', 'budget-target-label').attr('y', top - 12);
  const scaleText = svg.append('text').attr('class', 'budget-scale').attr('x', 0).attr('y', H - 4);
  const palette = ['seg-a', 'seg-b', 'seg-c', 'seg-d'];
  let dragState = null;

  function layout(acts) {
    let acc = 0;
    return acts.map((a, i) => {
      const m = Number.isInteger(a.minutes) && a.minutes > 0 ? a.minutes : 0;
      const seg = { i, id: a.id, title: a.title, minutes: m, start: acc };
      acc += m;
      return seg;
    });
  }

  function update() {
    const acts = getActivities();
    const total = Number(getTotal()) || 0;
    const segs = layout(acts);
    const sum = segs.reduce((s, d) => s + d.minutes, 0);
    x.domain([0, Math.max(total, sum, 1)]);
    svg.attr('aria-label', `Tiempos: ${segs.map((s) => `actividad ${s.i + 1}, ${s.minutes} min`).join('; ')}. Suman ${sum} de ${total} min en total.`);

    const g = gSeg.selectAll('g.seg').data(segs, (d) => d.id).join((enter) => {
      const e = enter.append('g').attr('class', 'seg');
      e.append('rect').attr('y', top).attr('height', barH).attr('rx', 6);
      e.append('text').attr('class', 'seg-label').attr('y', top + barH / 2).attr('dy', '0.35em');
      return e;
    });
    g.select('rect').attr('class', (d) => `${palette[d.i % palette.length]}${d.start + d.minutes > total ? ' seg-over' : ''}`)
      .transition().duration(dragState ? 0 : dur(350)).attr('x', (d) => x(d.start) + 1)
      .attr('width', (d) => Math.max(0, x(d.start + d.minutes) - x(d.start) - 2));
    g.select('text').transition().duration(dragState ? 0 : dur(350))
      .attr('x', (d) => x(d.start + d.minutes / 2)).attr('text-anchor', 'middle')
      .text((d) => (x(d.start + d.minutes) - x(d.start) > 58 ? `${d.i + 1} · ${d.minutes} min` : (x(d.start + d.minutes) - x(d.start) > 22 ? String(d.minutes) : '')));

    targetLine.transition().duration(dur(350)).attr('x1', x(total)).attr('x2', x(total));
    targetLabel.attr('x', Math.min(x(total), W - 4)).attr('text-anchor', x(total) > W - 120 ? 'end' : 'middle')
      .text(`Clase: ${total} min`);
    scaleText.attr('class', `budget-scale ${sum === total ? 'ok' : 'bad'}`)
      .text(sum === total ? `✓ Suman ${sum} de ${total} min · arrastra un borde para repartir el tiempo` : `Suman ${sum} min y la clase dura ${total}: arrastra un borde o edita los minutos`);

    const handles = segs.slice(0, -1);
    gHandles.selectAll('g.handle').data(handles, (d) => d.id).join((enter) => {
      const e = enter.append('g').attr('class', 'handle');
      e.append('rect').attr('class', 'handle-hit').attr('y', top - 6).attr('height', barH + 12).attr('width', 24).attr('x', -12);
      e.append('rect').attr('class', 'handle-bar').attr('y', top - 4).attr('height', barH + 8).attr('width', 6).attr('x', -3).attr('rx', 3);
      return e;
    })
      .attr('transform', (d) => `translate(${x(d.start + d.minutes)},0)`)
      .call(d3.drag()
        .container(svg.node())                      // coordenadas en el sistema del viewBox
        .subject((event) => ({ x: event.x, y: event.y }))
        .filter(() => !isLocked())
        .on('start', (event, d) => {
          const now = getActivities();
          dragState = { i: d.i, a: now[d.i].minutes, b: now[d.i + 1].minutes, x0: event.x };
          svg.classed('dragging', true);
        })
        .on('drag', (event) => {
          const s = dragState;
          const per = x.invert(1) - x.invert(0);
          const delta = Math.round((event.x - s.x0) * per);
          const a = Math.max(1, Math.min(s.a + s.b - 1, s.a + delta));
          onShift(s.i, a, s.a + s.b - a, false);
          update();
        })
        .on('end', () => {
          const s = dragState;
          dragState = null;
          svg.classed('dragging', false);
          const now = getActivities();
          onShift(s.i, now[s.i].minutes, now[s.i + 1].minutes, true);
          update();
        }));
  }

  update();
  return { update };
}

// ---------------------------------------------------------------------------------------------
// 3. Revisar: mapa de sustento. Une cada fragmento del módulo con las actividades que lo citan;
//    al pasar el ratón (o enfocar) se resaltan sus vínculos y se lee el fragmento.
// ---------------------------------------------------------------------------------------------
export function referenceMap(container, { fragments, getActivities }) {
  if (!d3) return { update() {} };
  const W = 760; const rowH = 34; const pad = 18;
  const svg = d3.select(container).append('svg').attr('class', 'viz viz-refs').attr('role', 'img');
  const gLinks = svg.append('g');
  const gLeft = svg.append('g');
  const gRight = svg.append('g');
  const readout = d3.select(container).append('p').attr('class', 'refs-readout small muted').attr('aria-live', 'polite')
    .text('Pasa el cursor o enfoca un fragmento para leerlo y ver qué actividades lo citan.');
  const leftX = 150; const rightX = W - 230;

  function update() {
    const acts = getActivities();
    const rows = Math.max(fragments.length, acts.length);
    const H = pad * 2 + rows * rowH;
    svg.attr('viewBox', `0 0 ${W} ${H}`);
    const yL = d3.scalePoint().domain(fragments.map((f) => f.id)).range([pad + rowH / 2, H - pad - rowH / 2]).padding(fragments.length < acts.length ? 0.5 : 0);
    const yR = d3.scalePoint().domain(acts.map((a) => a.id)).range([pad + rowH / 2, H - pad - rowH / 2]).padding(acts.length < fragments.length ? 0.5 : 0);
    const links = acts.flatMap((a) => a.references.filter((r) => fragments.some((f) => f.id === r)).map((r) => ({ from: r, to: a.id })));
    const uncited = fragments.filter((f) => !links.some((l) => l.from === f.id)).map((f) => f.id);
    svg.attr('aria-label', `${links.length} vínculos entre fragmentos y actividades.${uncited.length ? ` Sin citar: ${uncited.join(', ')}.` : ''}`);
    const link = d3.linkHorizontal().x((d) => d[0]).y((d) => d[1]);

    gLinks.selectAll('path').data(links, (d) => `${d.from}>${d.to}`).join(
      (enter) => enter.append('path').attr('class', 'ref-link')
        .attr('d', (d) => link({ source: [leftX, yL(d.from)], target: [leftX, yL(d.from)] }))
        .call((e) => e.transition().duration(dur(600)).attr('d', (d) => link({ source: [leftX, yL(d.from)], target: [rightX, yR(d.to)] }))),
      (upd) => upd.call((u) => u.transition().duration(dur(400)).attr('d', (d) => link({ source: [leftX, yL(d.from)], target: [rightX, yR(d.to)] }))),
      (exit) => exit.transition().duration(dur(300)).attr('opacity', 0).remove(),
    ).attr('data-from', (d) => d.from).attr('data-to', (d) => d.to);

    const left = gLeft.selectAll('g.frag').data(fragments, (d) => d.id).join((enter) => {
      const e = enter.append('g').attr('class', 'frag').attr('tabindex', 0).attr('role', 'button');
      e.append('circle').attr('r', 12);
      e.append('text').attr('class', 'frag-id').attr('dy', '0.35em').attr('text-anchor', 'middle');
      e.append('text').attr('class', 'frag-text').attr('x', -22).attr('dy', '0.35em').attr('text-anchor', 'end');
      return e;
    }).attr('transform', (d) => `translate(${leftX},${yL(d.id)})`)
      .classed('uncited', (d) => uncited.includes(d.id))
      .attr('aria-label', (d) => `Fragmento ${d.id}: ${d.text}`);
    left.select('.frag-id').text((d) => d.id);
    left.select('.frag-text').text((d) => (uncited.includes(d.id) ? 'sin citar' : `${links.filter((l) => l.from === d.id).length} cita(s)`));

    const right = gRight.selectAll('g.act').data(acts, (d) => d.id).join((enter) => {
      const e = enter.append('g').attr('class', 'act');
      e.append('rect').attr('x', 0).attr('y', -12).attr('width', 12).attr('height', 24).attr('rx', 4);
      e.append('text').attr('x', 20).attr('dy', '0.35em');
      return e;
    });
    right.transition().duration(dur(400)).attr('transform', (d) => `translate(${rightX},${yR(d.id)})`);
    right.select('text').text((d, i) => { const t = `${i + 1}. ${d.title}`; return t.length > 30 ? `${t.slice(0, 29)}…` : t; });
    right.classed('unsupported', (d) => !d.references.length);

    const focus = (fid) => {
      gLinks.selectAll('path').classed('dim', (l) => fid && l.from !== fid).classed('hot', (l) => fid && l.from === fid);
      gLeft.selectAll('g.frag').classed('dim', (f) => fid && f.id !== fid);
      gRight.selectAll('g.act').classed('hot', (a) => fid && a.references.includes(fid));
      const f = fragments.find((x2) => x2.id === fid);
      readout.text(f ? `${f.id}: ${f.text}` : 'Pasa el cursor o enfoca un fragmento para leerlo y ver qué actividades lo citan.');
    };
    left.on('mouseenter focus', (event, d) => focus(d.id)).on('mouseleave blur', () => focus(null));
  }

  update();
  return { update };
}

// ---------------------------------------------------------------------------------------------
// 4. Portafolio: línea de vida de la sesión. Cada versión es un nodo (revisada/borrador), la vigente
//    tiene un anillo y los registros de aplicación cuelgan como gotas sobre la versión que usaron.
//    Clic o Enter sobre un nodo muestra esa versión (los botones «Ver versión X» siguen disponibles).
// ---------------------------------------------------------------------------------------------
export function versionTimeline(container, { versions, records, currentId, shownId, onSelect }) {
  if (!d3) return null;
  const W = 760; const H = 150; const y = 92;
  const svg = d3.select(container).append('svg').attr('viewBox', `0 0 ${W} ${H}`).attr('class', 'viz viz-timeline')
    .attr('role', 'group').attr('aria-label', `Historial: ${versions.length} versiones y ${records.length} registros.`);
  const x = d3.scalePoint().domain(versions.map((v) => v.id)).range([60, W - 60]).padding(versions.length === 1 ? 0.5 : 0);
  svg.append('line').attr('class', 'timeline-axis').attr('x1', 40).attr('x2', 40).attr('y1', y).attr('y2', y)
    .transition().duration(dur(700)).attr('x2', W - 40);

  const byVersion = d3.group(records, (r) => r.versionId);
  const g = svg.selectAll('g.vnode').data(versions, (d) => d.id).join('g')
    .attr('class', (d) => `vnode ${d.reviewStatus === 'revisada' ? 'reviewed' : 'draft'}${d.id === currentId ? ' current' : ''}${d.id === shownId ? ' shown' : ''}`)
    .attr('transform', (d) => `translate(${x(d.id)},${y})`)
    .attr('tabindex', 0).attr('role', 'button')
    .attr('aria-label', (d) => `Versión ${d.number}, ${d.reviewStatus === 'revisada' ? 'revisada' : 'borrador'}${d.id === currentId ? ', vigente' : ''}. ${(byVersion.get(d.id) || []).length} registro(s).`)
    .on('click', (event, d) => onSelect(d.id))
    .on('keydown', (event, d) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onSelect(d.id); } });
  g.append('circle').attr('class', 'vring').attr('r', 0).transition().delay((d, i) => dur(i * 120)).duration(dur(500)).attr('r', 22);
  g.append('circle').attr('class', 'vcore').attr('r', 0).transition().delay((d, i) => dur(i * 120)).duration(dur(500)).ease(d3.easeBackOut).attr('r', 14);
  g.append('text').attr('class', 'vnum').attr('dy', '0.35em').attr('text-anchor', 'middle').text((d) => `v${d.number}`);
  g.append('text').attr('class', 'vstate').attr('y', 42).attr('text-anchor', 'middle')
    .text((d) => `${d.reviewStatus === 'revisada' ? 'Revisada' : 'Borrador'}${d.id === currentId ? ' · vigente' : ''}`);
  // Registros: gotas que caen sobre su versión.
  g.each(function drops(d) {
    const recs = byVersion.get(d.id) || [];
    d3.select(this).selectAll('circle.drop').data(recs).join('circle').attr('class', 'drop')
      .attr('cx', (r, i) => (i - (recs.length - 1) / 2) * 12).attr('cy', -70).attr('r', 5)
      .transition().delay((r, i) => dur(600 + i * 150)).duration(dur(700)).ease(d3.easeBounceOut).attr('cy', -38);
  });
  return svg.node();
}

// ---------------------------------------------------------------------------------------------
// 5. Mi red: radar de las cuatro dimensiones de la valoración de uso (solo valoraciones completas).
// ---------------------------------------------------------------------------------------------
export function ratingRadar(container, { criteriaMeans, ratings, labels }) {
  if (!d3) return null;
  const keys = Object.keys(labels);
  const complete = (ratings || []).filter((r) => r.complete);
  if (!complete.length) return null;
  const S = 320; const R = 110; const c = S / 2;
  const svg = d3.select(container).append('svg').attr('viewBox', `0 0 ${S} ${S}`).attr('class', 'viz viz-radar')
    .attr('role', 'img')
    .attr('aria-label', `Medias por criterio: ${keys.map((k) => `${labels[k]} ${criteriaMeans[k] ?? 'sin datos'}`).join('; ')}.`);
  const angle = (i) => (Math.PI * 2 * i) / keys.length - Math.PI / 2;
  const r = d3.scaleLinear().domain([0, 5]).range([0, R]);
  const g = svg.append('g').attr('transform', `translate(${c},${c})`);
  [1, 2, 3, 4, 5].forEach((lvl) => {
    g.append('polygon').attr('class', 'radar-grid')
      .attr('points', keys.map((k, i) => [Math.cos(angle(i)) * r(lvl), Math.sin(angle(i)) * r(lvl)].join(',')).join(' '));
  });
  keys.forEach((k, i) => {
    g.append('line').attr('class', 'radar-axis').attr('x2', Math.cos(angle(i)) * R).attr('y2', Math.sin(angle(i)) * R);
    const lx = Math.cos(angle(i)) * (R + 18); const ly = Math.sin(angle(i)) * (R + 18);
    g.append('text').attr('class', 'radar-label').attr('x', lx).attr('y', ly).attr('dy', '0.35em')
      .attr('text-anchor', Math.abs(lx) < 5 ? 'middle' : (lx > 0 ? 'start' : 'end')).text(labels[k]);
  });
  const pointsFor = (vals, scale = 1) => keys.map((k, i) => [Math.cos(angle(i)) * r((vals[k] || 0) * scale), Math.sin(angle(i)) * r((vals[k] || 0) * scale)].join(',')).join(' ');
  complete.forEach((rt) => g.append('polygon').attr('class', 'radar-one').attr('points', pointsFor(rt, 0))
    .transition().duration(dur(900)).attr('points', pointsFor(rt)));
  g.append('polygon').attr('class', 'radar-mean').attr('points', pointsFor(criteriaMeans, 0))
    .transition().delay(dur(250)).duration(dur(1100)).ease(d3.easeElasticOut.amplitude(1).period(0.5)).attr('points', pointsFor(criteriaMeans));
  keys.forEach((k, i) => {
    const v = criteriaMeans[k] || 0;
    g.append('circle').attr('class', 'radar-dot').attr('r', 4).attr('cx', 0).attr('cy', 0)
      .transition().delay(dur(250)).duration(dur(1100)).attr('cx', Math.cos(angle(i)) * r(v)).attr('cy', Math.sin(angle(i)) * r(v));
  });
  return svg.node();
}

export const svgNamespace = SVG_NS;
