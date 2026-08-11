import { getOriginKey } from "./origin.js";
import {
  AUTO_CAPTURE_KEY,
  autoCaptureRequest,
  readAutoCaptureState,
} from "./autocapture.js";

const FIELDS = {
  base: "darkmem.base_url",
  token: "darkmem.token",
  project: "darkmem.project",
};

const stored = await chrome.storage.local.get(Object.values(FIELDS));
for (const [id, key] of Object.entries(FIELDS)) {
  document.getElementById(id).value = stored[key] ?? "";
}
document.getElementById("origin").textContent = await getOriginKey(
  chrome.storage.local,
);

document.getElementById("save").addEventListener("click", async () => {
  const update = {};
  for (const [id, key] of Object.entries(FIELDS)) {
    update[key] = document.getElementById(id).value.trim();
  }
  await chrome.storage.local.set(update);
  document.getElementById("status").textContent = "saved";
});


// ── auto-capture opt-in (T4.07) ──
//
// The checkbox writes the stored flag *and* asks Chrome for the host
// permission, and it reflects the result rather than the click: a human who
// dismisses the browser's permission prompt has not opted in, and a switch
// that stayed on would be telling them they did.

const autoBox = document.getElementById("autocapture");
const autoStatus = document.getElementById("autocapture-status");

async function renderAutoCapture() {
  const state = await readAutoCaptureState(chrome.storage.local, (request) =>
    chrome.permissions.contains(request),
  );
  autoBox.checked = state.active;
  autoStatus.textContent = state.active
    ? "on — every new turn on those three sites is sent to darkmem"
    : state.enabled && !state.granted
      ? "off — the browser permission was not granted, so nothing is being read"
      : "off";
}

autoBox.addEventListener("change", async () => {
  if (autoBox.checked) {
    const granted = await chrome.permissions.request(autoCaptureRequest());
    // Stored only on a real grant. Writing the flag first and letting the
    // permission fail would leave an install that believes it opted in.
    await chrome.storage.local.set({ [AUTO_CAPTURE_KEY]: granted });
  } else {
    await chrome.storage.local.set({ [AUTO_CAPTURE_KEY]: false });
    // Handing the permission back rather than merely ignoring it: an
    // extension that keeps read access to three chat sites after the human
    // switched the feature off has not honoured the switch.
    await chrome.permissions.remove(autoCaptureRequest());
  }
  await renderAutoCapture();
});

await renderAutoCapture();
