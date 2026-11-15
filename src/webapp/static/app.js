(function () {
  "use strict";

  function $(id) { return document.getElementById(id); }

  // ---- light / dark switch ----
  var toggle = $("theme-toggle");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var root = document.documentElement;
      var dark = root.dataset.theme
        ? root.dataset.theme === "dark"
        : window.matchMedia("(prefers-color-scheme: dark)").matches;
      var next = dark ? "light" : "dark";
      root.dataset.theme = next;
      try { localStorage.setItem("dg-theme", next); } catch (e) { /* storage may be blocked */ }
    });
  }

  // ---- upload page (Figma 01, 02, 03) ----
  var form = $("upload-form");
  if (form) {
    var zone = $("dropzone");
    var input = $("file");
    var submit = $("submit-btn");
    var select = $("template");
    var ruleSets = [];
    try { ruleSets = JSON.parse($("rule-sets").textContent); } catch (e) { /* menu still works */ }
    var fileInfo = { rows: null, cols: null };

    function chosenSet() {
      for (var i = 0; i < ruleSets.length; i++) if (ruleSets[i].value === select.value) return ruleSets[i];
      return { columns: [], rules: [], source: "" };
    }

    function el(tag, cls, text) {
      var node = document.createElement(tag);
      if (cls) node.className = cls;
      if (text !== undefined) node.textContent = text;
      return node;
    }

    function showChecks() {
      var set = chosenSet();
      var box = $("check-columns");
      box.replaceChildren();
      set.columns.forEach(function (c) { box.appendChild(el("span", "tag mono", c)); });
      var names = set.rules.map(function (r) { return r.replace(/_/g, " "); });
      $("check-summary").textContent = set.value === "auto"
        ? "Rules are picked from your file's column names when you validate."
        : set.rules.length + " rule" + (set.rules.length === 1 ? "" : "s") + " from " + set.source + " · " + names.join(", ");
    }

    function countCsv(file) {
      fileInfo = { rows: null, cols: null };
      if (!/\.(csv|tsv|txt)$/i.test(file.name) || !window.FileReader) return;
      var reader = new FileReader();
      reader.onload = function () {
        var lines = String(reader.result).split(/\r?\n/).filter(function (l) { return l.trim() !== ""; });
        if (!lines.length) return;
        var delim = (lines[0].match(/\t/g) || []).length > (lines[0].match(/,/g) || []).length ? "\t" : ",";
        fileInfo = { rows: Math.max(0, lines.length - 1), cols: lines[0].split(delim).length };
        showFile();
      };
      reader.readAsText(file.slice(0, 5 * 1024 * 1024));
    }

    function showFile() {
      var file = input.files && input.files[0];
      zone.classList.toggle("has-file", !!file);
      $("browse-btn").hidden = !!file;
      $("change-file").hidden = !file;
      $("submit-help").hidden = !!file;
      submit.disabled = !file;
      if (!file) {
        $("drop-title").textContent = "Drag and drop your CSV file here";
        $("drop-sub").textContent = "Supported file formats: .csv or .xlsx · up to 5 MB";
        return;
      }
      $("drop-title").textContent = file.name;
      var detail = fileInfo.rows === null
        ? Math.max(1, Math.round(file.size / 1024)) + " KB"
        : fileInfo.rows + " row" + (fileInfo.rows === 1 ? "" : "s") + " · " + fileInfo.cols + " column" + (fileInfo.cols === 1 ? "" : "s");
      $("drop-sub").textContent = "Ready to check · " + detail;
    }

    function fileChanged() {
      var file = input.files && input.files[0];
      fileInfo = { rows: null, cols: null };
      showFile();
      if (file) countCsv(file);
    }

    input.addEventListener("change", fileChanged);
    ["dragenter", "dragover"].forEach(function (evt) {
      zone.addEventListener(evt, function (e) { e.preventDefault(); zone.classList.add("is-dragging"); });
    });
    ["dragleave", "drop"].forEach(function (evt) {
      zone.addEventListener(evt, function (e) { e.preventDefault(); zone.classList.remove("is-dragging"); });
    });
    zone.addEventListener("drop", function (e) {
      if (e.dataTransfer && e.dataTransfer.files.length) {
        input.files = e.dataTransfer.files;
        fileChanged();
      }
    });
    select.addEventListener("change", showChecks);

    // Checking screen: shown while the server works. Rules are marked "done" in
    // turn for feedback only; the real results appear on the next page.
    var timers = [];
    var submitted = false;

    function setProgress(pct) {
      $("check-bar").style.width = pct + "%";
      $("check-pct").textContent = pct + "%";
      document.querySelector(".progress").setAttribute("aria-valuenow", pct);
    }

    function showUpload() {
      timers.forEach(clearTimeout);
      timers = [];
      if (submitted) window.stop();
      submitted = false;
      $("checking-view").hidden = true;
      $("upload-view").hidden = false;
      showFile();
    }

    form.addEventListener("submit", function (e) {
      if (submitted) return;
      e.preventDefault();
      var set = chosenSet();
      var rules = set.rules.length ? set.rules : ["required_columns"];
      $("check-file").textContent = input.files[0].name;
      $("check-count").textContent = (fileInfo.rows === null ? "Checking your file" : "Checking " + fileInfo.rows + " rows") +
        " against " + rules.length + " rule" + (rules.length === 1 ? "" : "s");
      var list = $("check-rules");
      list.replaceChildren();
      var items = rules.map(function (name) {
        var li = el("li", "is-wait");
        li.appendChild(el("span", "dot"));
        li.appendChild(el("span", "mono", name));
        li.appendChild(el("span", "status", "waiting"));
        list.appendChild(li);
        return li;
      });
      setProgress(0);
      $("upload-view").hidden = true;
      $("checking-view").hidden = false;
      window.scrollTo(0, 0);

      var quick = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      var step = quick ? 0 : 220;
      items.forEach(function (li, i) {
        timers.push(setTimeout(function () {
          if (i > 0) { items[i - 1].className = "is-done"; items[i - 1].lastChild.textContent = "done"; }
          li.className = "is-run";
          li.lastChild.textContent = "checking";
          setProgress(Math.round((i / items.length) * 90));
        }, i * step));
      });
      timers.push(setTimeout(function () {
        var last = items[items.length - 1];
        last.className = "is-done";
        last.lastChild.textContent = "done";
        setProgress(95);
        submitted = true;
        form.submit();
      }, items.length * step));
    });

    $("cancel-check").addEventListener("click", showUpload);
    // Coming back with the browser's Back button: show the upload screen again.
    window.addEventListener("pageshow", function () { submitted = false; showUpload(); });

    showChecks();
    showFile();
  }

  // ---- report page: summary (04) and findings (05, 06) ----
  var summary = $("view-summary");
  var findings = $("view-findings");
  if (summary && findings) {
    function route() {
      var showFindings = location.hash === "#findings";
      summary.hidden = showFindings;
      findings.hidden = !showFindings;
      window.scrollTo(0, 0);
    }
    window.addEventListener("hashchange", route);
    route();
  }

  var cards = document.querySelectorAll(".finding");
  var filterButtons = document.querySelectorAll("[data-filter]");
  var words = { error: "errors", warning: "warnings", info: "notes" };
  filterButtons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      var wanted = btn.getAttribute("data-filter");
      var shown = 0;
      filterButtons.forEach(function (b) {
        var on = b === btn;
        b.classList.toggle("is-active", on);
        b.setAttribute("aria-pressed", on ? "true" : "false");
      });
      cards.forEach(function (card) {
        card.hidden = wanted !== "all" && card.getAttribute("data-severity") !== wanted;
        if (!card.hidden) shown++;
      });
      var others = Object.keys(words).filter(function (k) { return k !== wanted; })
        .filter(function (k) { return document.querySelector('[data-filter="' + k + '"]'); })
        .map(function (k) { return words[k].charAt(0).toUpperCase() + words[k].slice(1); });
      $("filter-status").textContent = wanted === "all"
        ? "Review the affected records and use the suggested fixes to update your CSV."
        : "Showing " + shown + " " + words[wanted] + ". " + others.join(" and ") + " are hidden.";
    });
  });

  function csvCell(value) {
    var text = String(value).replace(/\s+/g, " ").trim();
    if (/^[=+\-@]/.test(text)) text = "'" + text; // stop spreadsheet formula tricks
    return '"' + text.replace(/"/g, '""') + '"';
  }

  var download = $("download-csv");
  if (download) {
    download.addEventListener("click", function () {
      var lines = [["Level", "Rule", "Where", "Problem", "How to fix it"].map(csvCell).join(",")];
      cards.forEach(function (card) {
        if (card.hidden) return;
        lines.push([".badge", ".f-rule", ".f-where", ".f-msg", ".f-hint"].map(function (sel) {
          var node = card.querySelector(sel);
          return csvCell(sel === ".badge" ? node.lastChild.textContent : node.textContent);
        }).join(","));
      });
      var blob = new Blob(["﻿" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
      var link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = "dataguard-problems.csv";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(link.href);
    });
  }

  var print = $("print-report");
  if (print) print.addEventListener("click", function () { window.print(); });
})();
