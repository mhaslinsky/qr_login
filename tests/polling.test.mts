import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

test("start flows hand secrets to guarded polling without clobbering saved tokens", async () => {
  const html = readFileSync(new URL("../custom_components/qr_login/www/qr_login_start.html", import.meta.url), "utf8");
  const script = new vm.Script(html.split("<script>")[1].split("</script>")[0]);
  let poll;
  let finish;
  let calls = 0;
  let pollSignal;
  let expire;
  const saved = new Map([["hassTokens", "saved"]]);
  const errors = [];
  const starts = [];
  const context = vm.createContext({
    window: { location: { origin: "https://ha.test" }, QRLoginI18n: { t: value => value } },
    document: { addEventListener() {}, getElementById: () => ({ value: "mike", style: {}, replaceChildren() {} }), createElement: () => ({}) },
    localStorage: { setItem: (key, value) => saved.set(key, value) },
    setInterval: callback => { poll = callback; return 1; }, clearInterval() {},
    setTimeout() {}, clearTimeout() {}, console, errors,
    AbortSignal: { timeout: () => {
      const controller = new AbortController();
      pollSignal = controller.signal;
      expire = () => controller.abort();
      return pollSignal;
    } },
    fetch: (url, options) => {
      if (url.endsWith("/start")) {
        const body = JSON.parse(options.body);
        assert.equal(body.client_id, "https://ha.test/");
        starts.push(body.channel);
        return Promise.resolve({ json: async () => ({ session_id: body.channel + "-session", poll_secret: body.channel + "-secret" }) });
      }
      assert.equal(url, "/api/qr_login/status?session_id=" + starts.at(-1) + "-session");
      assert.equal(options.headers.Authorization, "QRLogin " + starts.at(-1) + "-secret");
      assert.equal(options.signal, pollSignal);
      calls++;
      return new Promise((resolve, reject) => {
        finish = resolve;
        options.signal.addEventListener("abort", () => reject(new Error("timeout")));
      });
    },
  });
  script.runInContext(context);
  vm.runInContext("showError = message => errors.push(message); resetChannelUI = () => {}; generateQR = () => {}", context);
  await vm.runInContext("startSession()", context);
  const pending = poll();
  const duplicate = poll();
  assert.equal(calls, 1);
  await duplicate;
  vm.runInContext("stopPolling()", context);
  finish({ ok: true, json: async () => ({ status: "approved", access_token: "late", refresh_token: "late" }) });
  await pending;
  assert.equal(saved.get("hassTokens"), "saved");
  assert.equal(errors.length, 0);
  vm.runInContext("startPolling()", context);
  const tokenless = poll();
  finish({ ok: true, json: async () => ({ status: "approved" }) });
  await tokenless;
  assert.equal(saved.get("hassTokens"), "saved");
  assert.deepEqual(errors, ["start.session_lost"]);
  await vm.runInContext("currentChannel = 'notify'; requestAccess()", context);
  const valid = poll();
  finish({ ok: true, json: async () => ({ status: "approved", access_token: "access", refresh_token: "refresh" }) });
  await valid;
  assert.equal(JSON.parse(saved.get("hassTokens")).refresh_token, "refresh");
  assert.deepEqual(starts, ["qr", "notify"]);
  vm.runInContext("startPolling()", context);
  let reading;
  const bodyStarted = new Promise(resolve => { reading = resolve; });
  const stalledBody = poll();
  finish({ ok: true, json: () => {
    reading();
    return new Promise((resolve, reject) => pollSignal.addEventListener("abort", () => reject(new Error("timeout"))));
  } });
  await bodyStarted;
  expire();
  await stalledBody;
  assert.deepEqual(errors, ["start.session_lost", "start.session_lost"]);
  const completedCalls = calls;
  const afterTimeout = poll();
  assert.equal(calls, completedCalls);
  await afterTimeout;
});
