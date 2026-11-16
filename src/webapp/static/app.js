/* DataGuard front end. Everything here is progressive: the pages work without it. */
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };

  /* ---------- Theme toggle ---------- */
  var toggle = $("theme-toggle");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var root = document.documentElement;
      var dark = root.dataset.theme
        ? root.dataset.theme === "dark"
        : window.matchMedia("(prefers-color-scheme: dark)").matches;
      root.dataset.theme = dark ? "light" : "dark";
      try { localStorage.setItem("dg-theme", root.dataset.theme); } catch (e) { /* storage blocked */ }
    });
  }

  /* ---------- Upload page ---------- */
  var RULE_TEXT = {
    required_columns: "Every expected column is present",
    missing_values: "No blank cells in required fields",
    duplicates: "No repeated rows (reported as a warning)",
    range_and_format: "Emails, dates and numbers are well formed and in range",
    india_formats: "Indian mobile numbers and other Indian formats you configure"
  };

  var RULE_NAME = {
    required_columns: "Required columns",
    missing_values: "Missing values",
    duplicates: "Duplicate rows",
    range_and_format: "Ranges and formats",
    india_formats: "Indian formats"
  };

  var form = $("upload-form");
  if (form) {
    var input = $("file"), zone = $("dropzone"), submit = $("submit-btn"), help = $("submit-help");
    var select = $("template"), setsEl = $("rule-sets");
    var sets = [];
    try { sets = JSON.parse(setsEl ? setsEl.textContent : "[]"); } catch (e) { sets = []; }

    var showRules = function () {
      var set = sets.filter(function (s) { return s.value === select.value; })[0];
      if (!set) return;
      var list = $("check-rules"), tags = $("check-columns"), summary = $("check-summary");
      list.innerHTML = "";
      set.rules.forEach(function (r) {
        var li = document.createElement("li");
        li.innerHTML = '<strong class="r"></strong><span class="d"></span>';
        li.title = r;
        li.querySelector(".r").textContent = RULE_NAME[r] || r;
        li.querySelector(".d").textContent = RULE_TEXT[r] || "";
        list.appendChild(li);
      });
      summary.textContent = set.value === "auto"
        ? "DataGuard looks at your column names and picks the rules that fit."
        : set.rules.length + " rule" + (set.rules.length === 1 ? "" : "s") + " from " + set.source + ".";
      tags.textContent = set.columns.length ? "Expects the columns " + set.columns.join(", ") + "." : "";
    };
    if (select) { select.addEventListener("change", showRules); showRules(); }

    var setReady = function (ready) {
      submit.disabled = !ready;
      help.textContent = ready ? "Ready to check." : "Choose a file to continue";
    };
    setReady(false);

    var splitLine = function (line) {
      var out = [], cur = "", q = false;
      for (var i = 0; i < line.length; i++) {
        var ch = line[i];
        if (ch === '"') { if (q && line[i + 1] === '"') { cur += '"'; i++; } else { q = !q; } }
        else if (ch === "," && !q) { out.push(cur); cur = ""; }
        else { cur += ch; }
      }
      out.push(cur);
      return out;
    };

    var peek = function (file) {
      $("peek-name").textContent = file.name;
      var kb = file.size / 1024;
      $("peek-size").textContent = kb < 1024 ? Math.max(1, Math.round(kb)) + " KB" : (kb / 1024).toFixed(1) + " MB";
      var table = $("peek-table");
      table.innerHTML = "";
      $("file-peek").hidden = false;
      if (!/\.(csv|txt|tsv)$/i.test(file.name)) {
        table.innerHTML = '<tbody><tr><td>Excel file: the preview appears after checking.</td></tr></tbody>';
        return;
      }
      var reader = new FileReader();
      reader.onload = function () {
        var lines = String(reader.result).split(/\r?\n/).filter(function (l) { return l.trim() !== ""; }).slice(0, 5);
        if (!lines.length) { table.innerHTML = "<tbody><tr><td>This file looks empty.</td></tr></tbody>"; return; }
        var head = document.createElement("thead"), body = document.createElement("tbody");
        lines.forEach(function (line, i) {
          var tr = document.createElement("tr");
          var num = document.createElement("th");
          num.className = "rownum"; num.textContent = String(i + 1); tr.appendChild(num);
          splitLine(line).forEach(function (v) {
            var cell = document.createElement(i === 0 ? "th" : "td");
            cell.textContent = v; tr.appendChild(cell);
          });
          (i === 0 ? head : body).appendChild(tr);
        });
        table.appendChild(head); table.appendChild(body);
      };
      reader.readAsText(file.slice(0, 64 * 1024));
    };

    var chosen = function () {
      var file = input.files && input.files[0];
      if (!file) { setReady(false); zone.classList.remove("has-file"); $("file-peek").hidden = true; return; }
      zone.classList.add("has-file");
      $("drop-title").textContent = file.name;
      $("drop-sub").innerHTML = '<span class="link-text">Choose a different file</span>';
      peek(file);
      setReady(true);
    };
    input.addEventListener("change", chosen);

    ["dragenter", "dragover"].forEach(function (t) {
      zone.addEventListener(t, function (e) { e.preventDefault(); zone.classList.add("is-over"); });
    });
    ["dragleave", "drop"].forEach(function (t) {
      zone.addEventListener(t, function (e) { e.preventDefault(); zone.classList.remove("is-over"); });
    });
    zone.addEventListener("drop", function (e) {
      if (e.dataTransfer && e.dataTransfer.files.length) {
        try { input.files = e.dataTransfer.files; } catch (err) { /* older browsers */ }
        chosen();
      }
    });

    form.addEventListener("submit", function (e) {
      if (!input.files || !input.files.length) { e.preventDefault(); setReady(false); return; }
      submit.classList.add("is-busy");
      submit.querySelector(".btn-label").textContent = "Checking…";
      help.textContent = "Checking every row against " + (select.options[select.selectedIndex] || {}).text + ".";
    });
    // Coming back with the browser's Back button must not leave the button stuck.
    window.addEventListener("pageshow", function () {
      submit.classList.remove("is-busy");
      submit.querySelector(".btn-label").textContent = "Validate CSV";
    });
  }

  /* ---------- Report page ---------- */
  var report = $("dataguard-report");
  if (!report) return;

  var xray = document.querySelector(".xray");
  var findings = $$(".finding");

  // Original / after auto-fix
  $$(".seg").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var cleaned = btn.getAttribute("data-version") === "cleaned";
      xray.classList.toggle("is-cleaned", cleaned);
      $$(".seg").forEach(function (b) {
        var on = b === btn;
        b.classList.toggle("is-on", on);
        b.setAttribute("aria-pressed", on ? "true" : "false");
      });
    });
  });

  // Filters
  var words = { all: "all problems", error: "errors", warning: "warnings", info: "notes" };
  $$("[data-filter]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var wanted = btn.getAttribute("data-filter");
      $$("[data-filter]").forEach(function (b) {
        var on = b === btn;
        b.classList.toggle("is-active", on);
        b.setAttribute("aria-pressed", on ? "true" : "false");
      });
      var shown = 0;
      findings.forEach(function (f) {
        var keep = wanted === "all" || f.getAttribute("data-severity") === wanted;
        f.hidden = !keep;
        if (keep) shown++;
      });
      var status = $("filter-status");
      if (status) status.textContent = "Showing " + shown + " " + words[wanted] + ".";
    });
  });

  // Grid <-> problems list
  var focusTarget = function (fid) {
    var target = document.querySelector('.grid [data-fid="' + fid + '"]');
    if (!target) return;
    $$(".grid .is-focus").forEach(function (el) { el.classList.remove("is-focus"); });
    void target.offsetWidth; // restart the pulse
    target.classList.add("is-focus");
    target.scrollIntoView({ block: "center", inline: "center", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  };
  var selectFinding = function (fid, scrollList) {
    findings.forEach(function (f) { f.classList.toggle("is-selected", f.getAttribute("data-fid") === String(fid)); });
    var item = document.querySelector('.finding[data-fid="' + fid + '"]');
    if (item && scrollList) {
      if (item.hidden) { var all = document.querySelector('[data-filter="all"]'); if (all) all.click(); }
      item.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  };
  findings.forEach(function (f) {
    f.querySelector(".finding-hit").addEventListener("click", function () {
      var fid = f.getAttribute("data-fid");
      selectFinding(fid, false);
      focusTarget(fid);
    });
  });
  $$(".grid [data-fid]").forEach(function (el) {
    var go = function () { var fid = el.getAttribute("data-fid"); selectFinding(fid, true); focusTarget(fid); };
    var hit = el.tagName === "TR" ? el.querySelector(".rownum") : el;
    hit.addEventListener("click", go);
    if (el.tagName === "TD") el.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(); } });
  });

  // Row map: jump to a row in the sheet
  $$("[data-goto-row]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var tr = document.querySelector('.grid tr[data-row="' + btn.getAttribute("data-goto-row") + '"]');
      if (!tr) return;
      var marked = tr.querySelector("[data-fid]") || (tr.hasAttribute("data-fid") ? tr : null);
      if (marked) { var fid = marked.getAttribute("data-fid"); selectFinding(fid, true); focusTarget(fid); return; }
      $$(".grid .is-focus").forEach(function (el) { el.classList.remove("is-focus"); });
      void tr.offsetWidth;
      tr.classList.add("is-focus");
      tr.scrollIntoView({ block: "center", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
    });
  });

  // Export the problems list as CSV
  var exportBtn = $("download-csv");
  if (exportBtn) {
    exportBtn.addEventListener("click", function () {
      var q = function (v) { return '"' + String(v).replace(/"/g, '""') + '"'; };
      var rows = [["severity", "rule", "row", "column", "problem", "how_to_fix"]];
      findings.forEach(function (f) {
        rows.push([
          f.getAttribute("data-severity"), f.getAttribute("data-rule"),
          f.getAttribute("data-row"), f.getAttribute("data-col"),
          f.querySelector(".f-msg").textContent.trim(), f.querySelector(".f-hint").textContent.trim()
        ]);
      });
      var blob = new Blob([rows.map(function (r) { return r.map(q).join(","); }).join("\n")], { type: "text/csv" });
      var a = document.createElement("a");
      var name = (document.querySelector(".file-title") || {}).textContent || "data.csv";
      a.href = URL.createObjectURL(blob);
      a.download = name.trim().replace(/\.[^.]+$/, "") + "_problems.csv";
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
    });
  }
})();
