// Optional real-browser integration check; Node 22+, Chrome and Python venv.
// No browser download, npm dependencies, external URLs or uploaded-image retention.
import { spawn } from "node:child_process";
import { mkdtemp, rm, access, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve, join } from "node:path";
import { createServer } from "node:net";
import assert from "node:assert/strict";

const sleep = (ms) => new Promise((done) => setTimeout(done, ms));
const root = resolve(import.meta.dirname, "..");
const python = process.env.UI_TEST_PYTHON || join(root, ".venv/bin/python");
const chrome = process.env.UI_TEST_CHROME || "/usr/bin/google-chrome";
const profile = await mkdtemp(join(tmpdir(), "mediscan-browser-"));
const children = [];
let socket;

async function freePort() {
  const server = createServer();
  await new Promise((done) => server.listen(0, "127.0.0.1", done));
  const port = server.address().port;
  await new Promise((done) => server.close(done));
  return port;
}

async function until(predicate, message, attempts = 150) {
  for (let i = 0; i < attempts; i++) {
    try { if (await predicate()) return; } catch { /* bounded startup/processing wait */ }
    await sleep(100);
  }
  throw new Error(message);
}

function launch(executable, args) {
  const child = spawn(executable, args, { cwd: root, stdio: ["ignore", "ignore", "pipe"] });
  child.stderr.on("data", (data) => { child.log = (child.log || "") + data.toString(); });
  child.on("error", (error) => { child.launchError = error; });
  children.push(child);
  return child;
}

try {
  const port = await freePort();
  const debugPort = await freePort();
  const base = `http://127.0.0.1:${port}`;
  launch(python, ["-m", "uvicorn", "recognition.api:app", "--host", "127.0.0.1", "--port", String(port), "--workers", "1"]);
  await until(async () => (await fetch(`${base}/health`)).ok, "API / OCR failed to start");
  launch(chrome, ["--headless", "--no-sandbox", "--disable-dev-shm-usage", "--no-first-run", "--no-default-browser-check",
    `--user-data-dir=${profile}`, `--remote-debugging-port=${debugPort}`, "about:blank"]);
  await until(async () => (await fetch(`http://127.0.0.1:${debugPort}/json/version`)).ok, "Chrome failed to start");
  const target = await (await fetch(`http://127.0.0.1:${debugPort}/json/new?${base}`, { method: "PUT" })).json();
  socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((done, reject) => { socket.onopen = done; socket.onerror = reject; });
  let nextId = 0;
  const pending = new Map();
  const runtimeErrors = [];
  socket.onmessage = ({ data }) => {
    const message = JSON.parse(data);
    if (message.method === "Runtime.exceptionThrown") runtimeErrors.push(message.params.exceptionDetails.text);
    if (!message.id) return;
    const request = pending.get(message.id);
    if (!request) return;
    pending.delete(message.id);
    clearTimeout(request.timer);
    if (message.error) request.reject(new Error(JSON.stringify(message.error)));
    else request.resolve(message.result);
  };
  function send(method, params = {}) {
    const id = ++nextId;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => { pending.delete(id); reject(new Error(`CDP deadline: ${method}`)); }, 10_000);
      pending.set(id, { resolve, reject, timer });
      socket.send(JSON.stringify({ id, method, params }));
    });
  }
  async function evaluate(expression) {
    const result = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
    if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
    return result.result.value;
  }
  await send("Runtime.enable");
  await send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 1100, deviceScaleFactor: 1, mobile: false });
  await until(() => evaluate("Boolean(document.getElementById('analyze') && typeof renderResult === 'function')"), "UI did not load");
  assert.equal(await evaluate("document.querySelector('html').lang"), "fr");
  assert.equal(await evaluate("document.getElementById('analyze').disabled"), true);
  await until(() => evaluate("document.getElementById('health').classList.contains('ready')"), "UI health indicator unavailable");

  let file = join(root, "doliprane-1000-mg-8-sachets-9261.dsGPD15_Z9IFisZmfHVEVVw5uGg.png");
  let expected = "Doliprane";
  try { await access(file); } catch {
    file = join(root, "data/demo/images/demo-01-100-fr-test.png");
    expected = "Zefrano";
  }
  const documentNode = await send("DOM.getDocument");
  const input = await send("DOM.querySelector", { nodeId: documentNode.root.nodeId, selector: "#image-input" });
  await send("DOM.setFileInputFiles", { nodeId: input.nodeId, files: [file] });
  await until(() => evaluate("!document.getElementById('analyze').disabled"), "Preview did not become ready");
  await evaluate("document.getElementById('analyze').click()");
  await until(() => evaluate("document.getElementById('result-badge').classList.contains('matched')"), "Real OCR result not displayed", 300);
  assert.equal(await evaluate("document.getElementById('product-title').textContent"), expected);
  assert.equal(await evaluate("document.getElementById('error').hidden"), true);
  const result = JSON.parse(await evaluate("document.getElementById('json-output').textContent"));
  console.log(`PASS: preview → multipart API → real OCR → ${expected} / ${result.extracted_fields.strength}`);

  if (process.env.UI_SCREENSHOT) {
    const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
    await writeFile(process.env.UI_SCREENSHOT, Buffer.from(screenshot.data, "base64"));
    console.log(`Screenshot: ${process.env.UI_SCREENSHOT}`);
  }

  for (const status of ["ambiguous", "unknown", "unreadable"]) {
    const sample = { ...result, status, matched_product: null };
    await evaluate(`renderResult(${JSON.stringify(sample)})`);
    assert.equal(await evaluate(`document.getElementById('result-badge').classList.contains('${status}')`), true);
    assert.equal(await evaluate("document.getElementById('product-reference').hidden"), true);
  }
  console.log("PASS: ambiguous, unknown and unreadable states never display a confirmed product");

  const untrusted = "<img src=x onerror=alert('ocr')>";
  const xssSample = { ...result, raw_ocr_text: untrusted, matched_product: { ...result.matched_product, name: untrusted } };
  await evaluate(`renderResult(${JSON.stringify(xssSample)})`);
  assert.equal(await evaluate("document.getElementById('product-title').textContent"), untrusted);
  assert.equal(await evaluate("document.querySelectorAll('#result img').length"), 0);
  console.log("PASS: OCR/catalogue strings are rendered as text, not HTML");

  await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
  assert.equal(await evaluate("document.documentElement.scrollWidth <= window.innerWidth"), true);
  console.log("PASS: mobile layout has no horizontal overflow at 390px");

  await evaluate(`window.originalFetch = window.fetch; window.fetch = (url, options) => url === '/api/recognize'
    ? Promise.resolve(new Response(JSON.stringify({detail:{request_id:'browser-error-test'}}), {status:429,headers:{'Content-Type':'application/json'}}))
    : window.originalFetch(url, options); document.getElementById('analyze').click();`);
  await until(() => evaluate("!document.getElementById('error').hidden"), "Overload error was not displayed");
  assert.match(await evaluate("document.getElementById('error').textContent"), /déjà en cours/);
  await evaluate("window.fetch = window.originalFetch; document.getElementById('clear-image').click()");
  assert.equal(await evaluate("document.getElementById('analyze').disabled"), true);
  assert.equal(await evaluate("document.getElementById('preview').hidden"), true);
  assert.deepEqual(runtimeErrors, []);
  console.log("PASS: overload message, retry controls and image reset; no browser JavaScript exceptions");
} catch (error) {
  for (const child of children) console.error(child.launchError || child.log || "");
  throw error;
} finally {
  socket?.close();
  for (const child of children.reverse()) {
    const running = () => child.pid && child.exitCode === null && child.signalCode === null;
    if (running()) {
      const exited = new Promise((done) => child.once("exit", done));
      child.kill("SIGTERM");
      await Promise.race([exited, sleep(3000)]);
      if (running()) {
        child.kill("SIGKILL");
        await Promise.race([exited, sleep(3000)]);
      }
    }
  }
  await rm(profile, { recursive: true, force: true });
}
