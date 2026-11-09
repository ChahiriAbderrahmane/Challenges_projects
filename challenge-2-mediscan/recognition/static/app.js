"use strict";

const byId = (id) => document.getElementById(id);
const input = byId("image-input");
const dropzone = byId("dropzone");
const button = byId("analyze");
const preview = byId("preview");
const maxBytes = 8 * 1024 * 1024;
let selectedFile = null;
let previewURL = null;
let ready = false;
let busy = false;

const forms = {
  tablet: "Comprimés", capsule: "Gélules", syrup: "Sirop", cream: "Crème",
  powder_oral_solution: "Poudre pour solution buvable",
};
const statuses = {
  matched: ["Identifié", "Correspondance au catalogue", "Les éléments lus correspondent à cette référence du catalogue."],
  ambiguous: ["À confirmer", "Plusieurs possibilités", "Les informations ne suffisent pas à distinguer une référence. Ajoutez une image plus nette montrant la force, la forme et le conditionnement."],
  unknown: ["Inconnu", "Produit non identifié", "Le produit peut être absent du catalogue, ou les éléments lus sont insuffisants ou contradictoires. Aucun produit n’a été retenu."],
  unreadable: ["Illisible", "Texte insuffisamment lisible", "Essayez une image plus nette, bien éclairée, avec le nom et la force visibles."],
};
const errors = {
  400: "L’image ou l’envoi est endommagé. Essayez un autre fichier JPEG ou PNG.",
  413: "L’image est trop volumineuse. Limites : 8 Mio et 16 mégapixels.",
  415: "Format non pris en charge. Choisissez une véritable image JPEG ou PNG.",
  422: "Sélectionnez une seule image à analyser.",
  429: "Une analyse est déjà en cours sur le serveur. Réessayez dans un instant.",
  503: "Le moteur OCR est indisponible. Vérifiez son démarrage et les modèles de langue sur le serveur.",
  504: "Le délai de traitement a été dépassé. Réessayez avec une image plus petite ou plus nette.",
  500: "Une erreur interne a empêché l’analyse. Vous pouvez réessayer.",
};

function showError(message) {
  byId("error").textContent = message;
  byId("error").hidden = !message;
}

function clearResult() {
  byId("result").hidden = true;
  byId("empty-state").hidden = false;
  byId("result-badge").className = "result-badge";
  byId("result-badge").textContent = "En attente";
}

function selectFile(file) {
  if (busy) return;
  if (previewURL) URL.revokeObjectURL(previewURL);
  previewURL = null;
  selectedFile = null;
  ready = false;
  button.disabled = true;
  preview.hidden = true;
  preview.removeAttribute("src");
  byId("change-image").hidden = true;
  byId("upload-prompt").hidden = false;
  byId("file-row").hidden = true;
  clearResult();
  showError("");
  if (!file) return;
  if (file.size > maxBytes) return showError(errors[413]);
  selectedFile = file;
  previewURL = URL.createObjectURL(file);
  preview.src = previewURL;
  preview.hidden = false;
  byId("upload-prompt").hidden = true;
  byId("change-image").hidden = false;
  byId("file-row").hidden = false;
  byId("filename").textContent = `${file.name} · ${(file.size / 1024).toLocaleString("fr-FR", { maximumFractionDigits: 0 })} Ko`;
}

preview.addEventListener("load", () => {
  if (!selectedFile) return;
  ready = true;
  button.disabled = busy;
});
preview.addEventListener("error", () => {
  if (!selectedFile) return;
  ready = false;
  button.disabled = true;
  preview.hidden = true;
  byId("upload-prompt").hidden = false;
  showError("Impossible d’afficher cette image. Choisissez un fichier JPEG ou PNG lisible.");
});
input.addEventListener("change", () => selectFile(input.files[0]));
byId("clear-image").addEventListener("click", () => {
  input.value = "";
  selectFile(null);
  input.focus();
});
for (const name of ["dragenter", "dragover"]) {
  dropzone.addEventListener(name, (event) => {
    event.preventDefault();
    if (!busy) dropzone.classList.add("dragover");
  });
}
for (const name of ["dragleave", "drop"]) {
  dropzone.addEventListener(name, (event) => {
    event.preventDefault();
    dropzone.classList.remove("dragover");
  });
}
dropzone.addEventListener("drop", (event) => {
  if (busy) return;
  input.value = "";
  if (event.dataTransfer.files.length !== 1) {
    selectFile(null);
    showError("Déposez une seule image à la fois.");
    return;
  }
  selectFile(event.dataTransfer.files[0]);
});

function setBusy(value) {
  busy = value;
  input.disabled = value;
  byId("clear-image").disabled = value;
  button.disabled = value || !ready;
  byId("spinner").hidden = !value;
  byId("analyze-arrow").hidden = value;
  byId("analyze-label").textContent = value ? "Lecture et identification…" : "Analyser la boîte";
  byId("result-panel").setAttribute("aria-busy", String(value));
  if (value) {
    byId("result-badge").className = "result-badge loading";
    byId("result-badge").textContent = "Analyse en cours";
    byId("announcement").textContent = "Analyse de l’image en cours.";
  }
}

function showField(id, value) {
  const element = byId(id);
  element.textContent = value == null || value === "" ? "Non lu" : String(value);
  element.classList.toggle("missing", value == null || value === "");
}

function fillList(id, entries) {
  const list = byId(id);
  list.replaceChildren();
  for (const text of entries.length ? entries : ["Aucun élément supplémentaire."]) {
    const item = document.createElement("li");
    item.textContent = text;
    list.append(item);
  }
}

function renderResult(data) {
  const state = statuses[data.status];
  if (!state || !data.extracted_fields) throw new Error("invalid-response");
  const product = data.status === "matched" ? data.matched_product : null;
  if (data.status === "matched" && !product) throw new Error("invalid-response");
  byId("empty-state").hidden = true;
  byId("result").hidden = false;
  byId("result-badge").className = `result-badge ${data.status}`;
  byId("result-badge").textContent = state[0];
  byId("outcome-kicker").textContent = product ? state[1] : "Identification non confirmée";
  byId("product-title").textContent = product ? product.name : state[1];
  byId("outcome-description").textContent = state[2];
  const fields = data.extracted_fields;
  showField("field-name", fields.product_name);
  showField("field-strength", fields.strength);
  showField("field-form", forms[fields.form] || fields.form);
  showField("field-pack", fields.pack_size == null ? null : `${fields.pack_size} unité${fields.pack_size > 1 ? "s" : ""}`);
  byId("product-reference").hidden = !product;
  byId("product-reference").textContent = product
    ? `Référence ${product.product_id} · Indice ${product.score} / 100 (classement, pas une probabilité).` : "";
  const candidates = (data.candidates || []).filter((candidate) => candidate.product_id !== product?.product_id);
  byId("candidates-section").hidden = candidates.length === 0;
  byId("candidates-title").textContent = product ? "Autres correspondances possibles" : "Candidats du catalogue — non confirmés";
  byId("candidates").replaceChildren();
  for (const candidate of candidates) {
    const row = document.createElement("div");
    row.className = "candidate";
    const description = document.createElement("div");
    const name = document.createElement("strong");
    name.textContent = candidate.name;
    const subtitle = document.createElement("small");
    subtitle.textContent = `${candidate.strength} · ${forms[candidate.form] || candidate.form} · ${candidate.pack_size} unités`;
    description.append(name, subtitle);
    const score = document.createElement("span");
    score.className = "candidate-score";
    score.textContent = `${candidate.score} / 100`;
    row.append(description, score);
    byId("candidates").append(row);
  }
  byId("ocr-text").textContent = data.raw_ocr_text || "Aucun texte lisible extrait.";
  byId("json-output").textContent = JSON.stringify(data, null, 2);
  fillList("evidence", data.matching_evidence || []);
  fillList("warnings", data.warnings || []);
  byId("timing").textContent = `${(data.processing_time_ms / 1000).toLocaleString("fr-FR", { maximumFractionDigits: 2 })} s · Traitement local`;
  byId("request-id").textContent = `ID ${data.request_id}`;
  byId("announcement").textContent = `${state[0]}. ${product ? product.name : state[1]}.`;
  byId("product-title").focus({ preventScroll: true });
}

byId("recognition-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!selectedFile || !ready || busy) return;
  showError("");
  clearResult();
  setBusy(true);
  // Do not impose a client-side timeout: aborting fetch would not stop native OCR.
  try {
    const body = new FormData();
    body.append("image", selectedFile, selectedFile.name);
    const response = await fetch("/api/recognize", { method: "POST", body });
    const data = await response.json();
    if (!response.ok) {
      const requestId = data.detail?.request_id || response.headers.get("X-Request-ID");
      throw new Error(`${errors[response.status] || "La requête a échoué."}${requestId ? ` Référence : ${requestId}` : ""}`);
    }
    renderResult(data);
  } catch (error) {
    clearResult();
    const message = error instanceof TypeError ? "Connexion impossible. Vérifiez que le serveur est démarré, puis réessayez."
      : error.message === "invalid-response" || error instanceof SyntaxError ? "Le serveur a renvoyé une réponse inattendue. Réessayez." : error.message;
    showError(message);
    byId("announcement").textContent = "L’analyse a échoué. Consultez le message sous l’image.";
  } finally {
    setBusy(false);
    checkHealth();
  }
});

async function checkHealth() {
  try {
    const response = await fetch("/health", { cache: "no-store" });
    const data = await response.json();
    const available = response.ok && data.ocr_ready;
    byId("health").className = `health ${available ? "ready" : "degraded"}`;
    byId("health-text").textContent = available ? "OCR opérationnel" : "OCR indisponible";
  } catch {
    byId("health").className = "health degraded";
    byId("health-text").textContent = "Serveur injoignable";
  }
}
checkHealth();
