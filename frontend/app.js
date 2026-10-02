/**
 * Ask the server whether the database is reachable and show the result.
 * Fills the status box with the counts, or turns it red with the reason.
 */
async function loadHealth() {
  const box = document.getElementById("status");
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    if (data.status === "ok") {
      const c = data.counts;
      box.textContent = `Returns: ${c.returns} · "Other": ${c.other} · Classified: ${c.classified}`;
    } else {
      box.classList.add("error");
      box.textContent = `Database problem: ${data.detail}`;
    }
  } catch (err) {
    box.classList.add("error");
    box.textContent = "Can't reach the server. Is uvicorn running?";
  }
}

loadHealth();
