import { getOriginKey } from "./origin.js";

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
