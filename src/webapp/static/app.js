(function () {
  "use strict";

  // ---- light / dark switch ----
  var toggle = document.getElementById("theme-toggle");
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

  // ---- upload page ----
  var zone = document.getElementById("dropzone");
  var input = document.getElementById("file");
  var nameBox = document.getElementById("file-name");
  var form = document.getElementById("upload-form");
  var submit = document.getElementById("submit-btn");

  function showName() {
    if (!input || !nameBox) return;
    var file = input.files && input.files[0];
    nameBox.textContent = file ? file.name + " (" + Math.max(1, Math.round(file.size / 1024)) + " KB)" : "";
    if (zone) zone.classList.toggle("has-file", !!file);
  }

  if (zone && input) {
    input.addEventListener("change", showName);
    ["dragenter", "dragover"].forEach(function (evt) {
      zone.addEventListener(evt, function (e) { e.preventDefault(); zone.classList.add("is-dragging"); });
    });
    ["dragleave", "drop"].forEach(function (evt) {
      zone.addEventListener(evt, function (e) { e.preventDefault(); zone.classList.remove("is-dragging"); });
    });
    zone.addEventListener("drop", function (e) {
      if (e.dataTransfer && e.dataTransfer.files.length) {
        input.files = e.dataTransfer.files;
        showName();
      }
    });
  }

  if (form && submit) {
    form.addEventListener("submit", function () {
      submit.classList.add("is-loading");
      submit.textContent = "Checking…";
    });
  }

  // ---- report page: filters, download, print ----
  var table = document.getElementById("findings");
  var filterButtons = document.querySelectorAll("[data-filter]");
  filterButtons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      var wanted = btn.getAttribute("data-filter");
      filterButtons.forEach(function (b) { b.classList.toggle("is-active", b === btn); });
      if (!table) return;
      table.querySelectorAll("tbody tr").forEach(function (row) {
        row.hidden = wanted !== "all" && row.getAttribute("data-severity") !== wanted;
      });
    });
  });

  function csvCell(value) {
    var text = String(value).replace(/\s+/g, " ").trim();
    if (/^[=+\-@]/.test(text)) text = "'" + text; // stop spreadsheet formula tricks
    return '"' + text.replace(/"/g, '""') + '"';
  }

  var download = document.getElementById("download-csv");
  if (download && table) {
    download.addEventListener("click", function () {
      var lines = [["Level", "Rule", "Where", "Problem", "How to fix it"].map(csvCell).join(",")];
      table.querySelectorAll("tbody tr").forEach(function (row) {
        if (row.hidden) return;
        var cells = Array.prototype.map.call(row.children, function (td) { return csvCell(td.textContent); });
        lines.push(cells.join(","));
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

  var print = document.getElementById("print-report");
  if (print) print.addEventListener("click", function () { window.print(); });
})();
