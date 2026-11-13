
var MI = null, R = null, H = {};
var TEXTURE_SUM_MAX = 100.5;   // mirrors afsis_data.clean(), not a measurement

function $(id){ return document.getElementById(id); }
function fmt(v, d){
  if (v === null || v === undefined || v === "") return "n/a";
  var n = Number(v);
  return isFinite(n) ? n.toFixed(d === undefined ? 2 : d) : "n/a";
}
function pct(v, d){
  if (v === null || v === undefined) return "n/a";
  var n = Number(v);
  return isFinite(n) ? (n * 100).toFixed(d === undefined ? 1 : d) + "%" : "n/a";
}
function esc(s){
  return String(s === null || s === undefined ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
function must(r, what){
  if (!r.ok) throw new Error(what + " returned " + r.status);
  return r.json();
}

// ---------------------------------------------------------------- boot
Promise.all([
  fetch("/results").then(function(r){ return must(r, "/results"); }),
  fetch("/model-info").then(function(r){ return must(r, "/model-info"); }),
  fetch("/health").then(function(r){ return r.ok ? r.json() : {}; }).catch(function(){ return {}; })
]).then(function(x){
  R = x[0]; MI = x[1]; H = x[2] || {};
  renderHeader();
  renderFields();
  renderEvidence();
  $("main").setAttribute("aria-busy", "false");
}).catch(function(e){
  $("main").setAttribute("aria-busy", "false");
  $("loaderr").innerHTML = '<div class="banner b-bad"><b>The bundle could not be read.</b><br>' +
    esc(e.message) + '<br>Start the server pointing at a bundle, for example ' +
    '<code>MODEL_DIR=export_afsis_real python soil_api.py</code>, then reload.</div>';
});

function renderHeader(){
  var real = R && R.data && R.data.is_real_data;
  var chip = $("chip");
  chip.className = "chip " + (real ? "chip-real" : "chip-syn");
  chip.textContent = (real ? "REAL DATA" : "SYNTHETIC STAND-IN") + " \u00b7 " +
    ((R.data && R.data.dataset_version) || "?") + " \u00b7 " +
    (MI.model_version || "?") + " \u00b7 " + (H.model_dir || "?");
  chip.title = (R.data && R.data.kind) || "";

  $("h1sub").textContent = "Target: " + (MI.target || "soil carbon") +
    " (" + (MI.units || "?") + "), " + (MI.n_training_rows || "?") +
    " training rows. Every figure on this page is read from this bundle.";

  if (!real){
    $("kindbanner").innerHTML = '<div class="banner b-bad"><b>Synthetic stand-in bundle.</b> ' +
      'These rows were generated to exercise the pipeline. Nothing here is a measurement of any soil.</div>';
  }
}

// ------------------------------------------------------------ measurement form
function renderFields(){
  var box = $("fields");
  var units = (R && R.feature_units) || {};
  var ranges = MI.feature_ranges || {};
  box.innerHTML = "";
  (MI.features || []).forEach(function(name, i){
    var rng = ranges[name] || {};
    var d = document.createElement("div");
    d.className = "field";
    d.innerHTML =
      '<div class="flab"><label for="f' + i + '">' + esc(name) + '</label>' +
      '<span class="unit">' + esc(units[name] || "") + '</span></div>' +
      '<input type="number" step="any" id="f' + i + '" data-name="' + esc(name) +
      '" value="' + (rng.median === undefined ? "" : rng.median) + '">' +
      '<p class="hint">Training p5\u2013p95: ' + fmt(rng.p5, 3) + ' \u2013 ' + fmt(rng.p95, 3) +
      ' \u00b7 median ' + fmt(rng.median, 3) + '. Values outside this range are still sent, ' +
      'and the answer says so.</p>';
    box.appendChild(d);
  });
  box.addEventListener("input", updateTexture);
  updateTexture();
}

function fields(){
  return Array.prototype.slice.call(document.querySelectorAll("#fields input"));
}
function valuesFromForm(){
  var out = {}, missing = [];
  fields().forEach(function(el){
    var v = el.value.trim();
    if (v === "") { missing.push(el.getAttribute("data-name")); return; }
    out[el.getAttribute("data-name")] = Number(v);   // numbers, not strings
  });
  return { values: out, missing: missing };
}

function textureFields(){
  var units = (R && R.feature_units) || {};
  return (MI.features || []).filter(function(n){
    return String(units[n] || "").indexOf("percent") !== -1;
  });
}
function updateTexture(){
  var names = textureFields(), sum = 0, seen = 0, missing = false;
  fields().forEach(function(el){
    if (names.indexOf(el.getAttribute("data-name")) === -1) return;
    seen++;
    if (el.value.trim() === "") { missing = true; return; }
    sum += Number(el.value);
  });
  var chip = $("texchip");
  if (!seen){ chip.className = "chip"; chip.textContent = "texture sum: not used"; return; }
  if (missing){ chip.className = "chip"; chip.textContent = "texture sum: n/a"; return; }
  var bad = sum > TEXTURE_SUM_MAX;
  chip.className = "chip" + (bad ? " chip-bad" : "");
  chip.textContent = "texture sum: " + fmt(sum, 1) + (bad ? " over " + TEXTURE_SUM_MAX : "");
}

function resetMedians(){
  var ranges = MI.feature_ranges || {};
  fields().forEach(function(el){
    var rng = ranges[el.getAttribute("data-name")] || {};
    el.value = rng.median === undefined ? "" : rng.median;
  });
  updateTexture();
}

$("btn-reset").addEventListener("click", resetMedians);
$("btn-estimate").addEventListener("click", submit);
$("theme").addEventListener("click", function(){
  var dark = document.documentElement.getAttribute("data-theme") === "dark";
  document.documentElement.setAttribute("data-theme", dark ? "light" : "dark");
  this.setAttribute("aria-pressed", dark ? "false" : "true");
  this.textContent = dark ? "Dark" : "Light";
});

// ---------------------------------------------------------------- submit
function submit(){
  var got = valuesFromForm();
  if (got.missing.length){
    $("est").innerHTML = '<div class="banner b-bad"><b>Not sent.</b> Missing: ' +
      esc(got.missing.join(", ")) + '.</div>';
    return;
  }
  $("est").innerHTML = '<p class="note">Sending one reading to the model\u2026</p>';
  fetch("/api/predict", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ values: got.values })
  }).then(function(r){
    return r.json().then(function(body){ return { ok: r.ok, status: r.status, body: body }; });
  }).then(function(res){
    if (!res.ok) { renderRefusal(res); return; }
    renderResult(res.body, got.values);
  }).catch(function(e){
    $("est").innerHTML = '<div class="banner b-bad"><b>No answer.</b> ' + esc(e.message) + '</div>';
  });
}

function renderRefusal(res){
  var det = res.body.detail || res.body || {};
  var lines = [];
  (det.offending || []).forEach(function(o){
    var f = Object.keys(o)[0], v = o[f] || {};
    lines.push(esc(f) + ": given " + esc(v.given) + ", physically valid " +
      esc(JSON.stringify(v.physically_valid_range)));
  });
  $("est").innerHTML = '<div class="banner b-bad"><b>Refused (' + res.status + ').</b> ' +
    esc(det.message || "") + (lines.length ? "<br>" + lines.join("<br>") : "") +
    '<br>No estimate is shown for a physically impossible reading.</div>';
  $("sheet").innerHTML = '<p class="note">Refused reading. Nothing to print as an estimate.</p>';
  $("sheet-actions").innerHTML = "";
}

function lightFor(conf){
  if (conf === "High")   return { cls: "high", ico: "\u25cf" };
  if (conf === "Medium") return { cls: "med",  ico: "\u25d0" };
  return { cls: "low", ico: "\u25cb" };
}

function renderResult(d, sent){
  var b = d.band || {};
  var tl = lightFor(b.confidence);
  var unit = (d.target && d.target.unit) || (MI.units || "");
  var lead = leadingRow();
  var html = "";

  if (!d.data_is_real){
    html += '<div class="banner b-bad"><b>Synthetic stand-in.</b> This number came from a model ' +
      'trained on generated rows. It is a pipeline check, not a soil measurement.</div>';
  }

  html += '<div class="tl ' + tl.cls + '">' +
    '<span class="ico" aria-hidden="true">' + tl.ico + '</span>' +
    '<span><span class="who">Placement: ' + esc(b.confidence || "Low") + '</span><br>' +
    esc(b.message || "No placement was returned.") +
    (b.band ? '<br><b>Band: ' + esc(b.band) + '</b>' : "") + '</span></div>';

  html += '<p class="big" style="margin:12px 0 0">' + fmt(d.prediction, 2) +
    ' <span class="unit">' + esc(unit) + '</span></p>';
  html += '<p class="note">Predicted ' + esc((d.target && d.target.name) || MI.target) +
    ', with a ' + pct(d.interval && d.interval.nominal, 0) + ' interval of ' +
    fmt(d.interval && d.interval.low, 2) + ' to ' + fmt(d.interval && d.interval.high, 2) +
    ' ' + esc(unit) + '. This is an estimate of a laboratory value, not of a stock or a quality rating.</p>';

  html += '<table><thead><tr><th>Field</th><th class="num">Value</th></tr></thead><tbody>' +
    '<tr><td>Interval half-width (one width for all inputs)</td><td class="num">' +
      fmt(d.interval && d.interval.half_width, 3) + ' ' + esc(unit) + '</td></tr>' +
    '<tr><td>Measured coverage at ' + pct(d.interval && d.interval.nominal, 0) + ' nominal</td>' +
      '<td class="num">' + pct(d.interval && d.interval.empirical_coverage) +
      ' \u00b1 ' + (d.interval && d.interval.coverage_sd !== undefined ?
        fmt(d.interval.coverage_sd * 100, 2) + " pp" : "n/a") + '</td></tr>' +
    '<tr><td>Mean interval width on the calibration folds</td><td class="num">' +
      fmt(d.interval && d.interval.mean_width, 2) + ' ' + esc(unit) + '</td></tr>' +
    '<tr><td>Spatial RMSE of the interval model</td><td class="num">' +
      fmt(d.accuracy && d.accuracy.spatial_rmse, 3) + ' ' + esc(unit) + '</td></tr>' +
    (lead ? '<tr><td>Leading model under spatial CV</td><td class="num">' +
      fmt(lead.r2_spatial, 3) + ' R\u00b2</td></tr>' +
      '<tr><td>Same model under random CV</td><td class="num">' +
      fmt(lead.r2_random, 3) + ' R\u00b2</td></tr>' : '') +
    '</tbody></table>';

  if (b.out_of_range && b.out_of_range.length){
    html += '<div class="banner b-bad"><b>Outside the training range.</b><ul>' +
      b.out_of_range.map(function(o){
        return '<li>' + esc(o.feature) + ': ' + fmt(o.value, 3) + ' against a training range of ' +
          fmt(o.training_p5, 3) + ' \u2013 ' + fmt(o.training_p95, 3) + '</li>';
      }).join("") + '</ul>The estimate is shown so the failure is visible, not to be used.</div>';
  }

  html += '<details><summary>How this placement was reached (rules that fired)</summary>' +
    '<p class="mono">' + esc((b.rules || []).join(", ") || "none") + '</p>' +
    '<p class="mono">' + esc((b.flags || []).join(", ") || "no flags") + '</p>' +
    '<p class="note">' + esc((d.interval && d.interval.note) || "") + '</p>' +
    '<p class="note">Interval method: ' + esc((d.interval && d.interval.method) || "n/a") + '</p>' +
    '</details>';

  $("est").innerHTML = html;
  renderSheet(d, sent);
}

function leadingRow(){
  var rows = ((R.results || {}).validation_gap) || [];
  var best = null;
  rows.forEach(function(r){
    if (r.r2_spatial === null || r.r2_spatial === undefined) return;
    if (!best || Number(r.r2_spatial) > Number(best.r2_spatial)) best = r;
  });
  return best;
}

// ------------------------------------------------- evidence from this bundle
function renderEvidence(){
  var lead = leadingRow();
  var html = "";

  // (a) noise: what the model does when readings get noisier
  var sweep = (R.results || {}).noise_sweep || [];
  if (lead && sweep.length){
    var rows = sweep.filter(function(r){
      return r.model === lead.model && r.cv === "spatial";
    }).sort(function(a, b){ return a.noise - b.noise; });
    var arms = [];
    rows.forEach(function(r){ if (arms.indexOf(r.arm) === -1) arms.push(r.arm); });
    var be = (R.headline && R.headline.break_even_noise) || {};
    html += '<div class="card" style="margin:12px 0 0">' +
      '<h3>Noise sweep, ' + esc(lead.model) + ', spatial CV</h3>' +
      '<p class="note">Additive noise in feature standard deviations. Both arms named: ' +
      esc(arms.join(" and ")) + '. The field-mean baseline is ' +
      fmt((R.results.baseline_rmse || {}).spatial, 3) + ' RMSE spatially.</p>' +
      sweepChart(rows, arms) +
      '<p class="note">Break-even noise (train_clean|spatial): ' +
      (be["train_clean|spatial"] === null ? 'the sweep never reached it' :
        fmt(be["train_clean|spatial"], 2)) + '.</p>' +
      '<details><summary>Rows</summary><table><thead><tr><th>Arm</th><th class="num">Noise</th>' +
      '<th class="num">R\u00b2 mean</th><th class="num">R\u00b2 sd</th><th class="num">RMSE</th></tr></thead><tbody>' +
      rows.map(function(r){
        return '<tr><td>' + esc(r.arm) + '</td><td class="num">' + fmt(r.noise, 2) +
          '</td><td class="num">' + fmt(r.r2_mean, 3) + '</td><td class="num">' +
          fmt(r.r2_sd, 3) + '</td><td class="num">' + fmt(r.rmse_mean, 3) + '</td></tr>';
      }).join("") + '</tbody></table></details></div>';
  } else {
    html += '<div class="card" style="margin:12px 0 0"><h3>Noise sweep</h3>' +
      '<p class="note">No noise sweep in this run.</p></div>';
  }

  // (b) systematic gain error, when the bundle carries the sweep
  var gains = (R.results || {}).gain_sweep || [];
  if (lead && gains.length){
    var g = gains.filter(function(r){ return r.model === lead.model && r.cv === "spatial"; })
      .sort(function(a, b){ return a.gain - b.gain; });
    html += '<div class="card" style="margin:12px 0 0"><h3>Gain error sweep, ' +
      esc(lead.model) + ', spatial CV</h3>' +
      '<p class="note">Each channel multiplied by 1 + g\u00b7u, one u per channel per fold. ' +
      'train_gain applies the same factor in fit and deployment; train_clean does not.</p>' +
      '<table><thead><tr><th class="num">Gain</th><th>Arm</th><th class="num">R\u00b2 mean</th>' +
      '<th class="num">RMSE</th></tr></thead><tbody>' +
      g.map(function(r){
        return '<tr><td class="num">' + fmt(r.gain, 2) + '</td><td>' + esc(r.arm) +
          '</td><td class="num">' + fmt(r.r2_mean, 3) + '</td><td class="num">' +
          fmt(r.rmse_mean, 3) + '</td></tr>';
      }).join("") + '</tbody></table></div>';
  } else {
    html += '<div class="card" style="margin:12px 0 0"><h3>Gain error sweep</h3>' +
      '<p class="note">No gain sweep in this run. It is opt-in: add <code>--gain-sweep</code> ' +
      'to the experiment command and serve that bundle.</p></div>';
  }

  // (c) feature ablation, when this bundle was trained without some features
  var ab = R.feature_ablation;
  if (ab && ab.dropped && ab.dropped.length){
    html += '<div class="banner b-warn"><b>Reduced model.</b> This bundle was trained without ' +
      esc(ab.dropped.join(", ")) + ', leaving ' + esc((ab.remaining || []).join(", ")) +
      '. Its scores describe that reduced model, not the headline run. ' + esc(ab.note || "") + '</div>';
  }

  $("evidence").innerHTML = html;
}

// Own scale, zero drawn, extremes printed: index.html's chart contract, applied here.
function sweepChart(rows, arms){
  if (!rows.length) return "";
  var W = 560, Hh = 150, L = 44, Rr = 10, T = 12, B = 26;
  var xs = [], ys = [];
  rows.forEach(function(r){ xs.push(Number(r.noise)); ys.push(Number(r.r2_mean)); });
  var xmin = Math.min.apply(null, xs), xmax = Math.max.apply(null, xs);
  ys.push(0);
  var ymin = Math.min.apply(null, ys), ymax = Math.max.apply(null, ys);
  if (ymax === ymin) ymax = ymin + 1;
  var pad = (ymax - ymin) * 0.08;
  ymin -= pad; ymax += pad;
  function X(v){ return L + (xmax === xmin ? 0 : (v - xmin) / (xmax - xmin)) * (W - L - Rr); }
  function Y(v){ return T + (1 - (v - ymin) / (ymax - ymin)) * (Hh - T - B); }

  var parts = [];
  [ymin, 0, ymax].forEach(function(v, i){
    parts.push('<line class="' + (i === 1 ? 'zero' : 'grid') + '" x1="' + L + '" x2="' + (W - Rr) +
      '" y1="' + Y(v).toFixed(1) + '" y2="' + Y(v).toFixed(1) + '"/>');
    parts.push('<text class="tk" x="' + (L - 6) + '" y="' + (Y(v) + 3).toFixed(1) + '" text-anchor="end">' +
      v.toFixed(2) + '</text>');
  });
  xs.forEach(function(v, i){
    if (xs.indexOf(v) === i){
      parts.push('<text class="tk" x="' + X(v).toFixed(1) + '" y="' + (Hh - 8) +
        '" text-anchor="middle">' + v.toFixed(2) + '</text>');
    }
  });
  arms.forEach(function(arm, ai){
    var pts = rows.filter(function(r){ return r.arm === arm; })
      .sort(function(a, b){ return a.noise - b.noise; });
    parts.push('<polyline class="' + (ai ? 'dash' : 's') + '" points="' +
      pts.map(function(r){ return X(Number(r.noise)).toFixed(1) + ',' + Y(Number(r.r2_mean)).toFixed(1); })
        .join(" ") + '"/>');
    pts.forEach(function(r){
      parts.push('<circle class="' + (ai ? 'dot-r' : 'dot-s') + '" cx="' + X(Number(r.noise)).toFixed(1) +
        '" cy="' + Y(Number(r.r2_mean)).toFixed(1) + '" r="3"/>');
    });
  });
  parts.push('<text class="tk" x="' + L + '" y="' + (T - 2) + '">R\u00b2 by noise level (zero dashed)</text>');
  return '<svg viewBox="0 0 ' + W + ' ' + Hh + '" role="img" aria-label="R squared against noise level, ' +
    esc(arms.join(" and ")) + ', from ' + ymin.toFixed(2) + ' to ' + ymax.toFixed(2) + '">' +
    parts.join("") + '</svg>';
}

// ------------------------------------------------------------- session sheet
function sheetRows(d, sent){
  var unit = (MI.units || "");
  var rows = [
    ["Sample label", $("s-label").value || "not recorded"],
    ["Site label", $("s-site").value || "not recorded"],
    ["Printed at", new Date().toISOString()]
  ];
  (MI.features || []).forEach(function(n){
    rows.push([n + " (" + ((R.feature_units || {})[n] || "") + ")", fmt(sent[n], 3)]);
  });
  rows.push(["Predicted " + ((d.target && d.target.name) || MI.target), fmt(d.prediction, 2) + " " + unit]);
  rows.push(["Interval " + pct(d.interval && d.interval.nominal, 0),
    fmt(d.interval && d.interval.low, 2) + " to " + fmt(d.interval && d.interval.high, 2) + " " + unit]);
  rows.push(["Measured coverage", pct(d.interval && d.interval.empirical_coverage)]);
  rows.push(["Placement", (d.band && d.band.confidence) || "Low"]);
  rows.push(["Placement message", (d.band && d.band.message) || ""]);
  rows.push(["Rules fired", ((d.band && d.band.rules) || []).join(", ") || "none"]);
  return rows;
}

function renderSheet(d, sent){
  var rows = sheetRows(d, sent);
  $("sheet").innerHTML = '<table><tbody>' + rows.map(function(r){
    return '<tr><td class="muted">' + esc(r[0]) + '</td><td>' + esc(r[1]) + '</td></tr>';
  }).join("") + '</tbody></table>' +
  '<p class="prov">' + esc(R.data.dataset_version || "?") + ' | ' +
  esc(MI.model_version || "?") + ' | ' + esc(MI.n_training_rows || "?") + ' rows | ' +
  esc(MI.target || "?") + ' | ' + esc(MI.units || "?") + ' | ' + esc(H.model_dir || "?") + '</p>' +
  '<p class="note">' + esc(MI.disclaimer || "") + '</p>';

  $("sheet-actions").innerHTML = "";
  var copy = document.createElement("button");
  copy.type = "button";
  copy.className = "ghost";
  copy.textContent = "Copy sheet as text";
  copy.addEventListener("click", function(){
    var text = rows.map(function(r){ return r[0] + ": " + r[1]; }).join("\n") +
      "\n" + (MI.model_version || "") + "\n" + (MI.disclaimer || "");
    if (navigator.clipboard) navigator.clipboard.writeText(text);
  });
  var print = document.createElement("button");
  print.type = "button";
  print.textContent = "Print / save as PDF";
  print.addEventListener("click", function(){ window.print(); });
  $("sheet-actions").appendChild(copy);
  $("sheet-actions").appendChild(print);
}
