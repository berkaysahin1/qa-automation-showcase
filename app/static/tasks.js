const token = localStorage.getItem("taskflow.token");
if (!token) window.location.replace("/login");

const list = document.querySelector('[data-testid="task-list"]');
const empty = document.querySelector('[data-testid="empty-state"]');
const openCount = document.querySelector('[data-testid="open-count"]');
const error = document.querySelector('[data-testid="task-error"]');
const form = document.querySelector('[data-testid="new-task-form"]');

const api = (path, options = {}) =>
  fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(options.headers || {}),
    },
  });

function signOut() {
  localStorage.removeItem("taskflow.token");
  window.location.replace("/login");
}

function render(tasks) {
  list.replaceChildren();
  empty.hidden = tasks.length > 0;
  openCount.textContent = String(tasks.filter((t) => !t.done).length);

  for (const task of tasks) {
    const li = document.createElement("li");
    li.dataset.testid = "task-item";
    li.dataset.taskId = task.id;
    li.dataset.done = String(task.done);

    const toggle = document.createElement("input");
    toggle.type = "checkbox";
    toggle.checked = task.done;
    toggle.dataset.testid = "toggle-task";
    toggle.addEventListener("change", async () => {
      await api(`/api/tasks/${task.id}`, {
        method: "PATCH",
        body: JSON.stringify({ done: toggle.checked }),
      });
      await refresh();
    });

    const title = document.createElement("span");
    title.className = "task-title";
    title.dataset.testid = "task-title";
    title.textContent = task.title;

    const badge = document.createElement("span");
    badge.className = "badge";
    badge.dataset.testid = "task-priority";
    badge.textContent = task.priority;

    const remove = document.createElement("button");
    remove.type = "button";
    remove.dataset.testid = "delete-task";
    remove.textContent = "Delete";
    remove.addEventListener("click", async () => {
      await api(`/api/tasks/${task.id}`, { method: "DELETE" });
      await refresh();
    });

    li.append(toggle, title, badge, remove);
    list.append(li);
  }
}

async function refresh() {
  const response = await api("/api/tasks?limit=100");
  if (response.status === 401) return signOut();
  const page = await response.json();
  render(page.items);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  error.hidden = true;

  const title = form.title.value.trim();
  if (!title) {
    error.textContent = "Title is required.";
    error.hidden = false;
    return;
  }

  const response = await api("/api/tasks", {
    method: "POST",
    body: JSON.stringify({ title, priority: form.priority.value }),
  });

  if (!response.ok) {
    error.textContent = "Could not save the task.";
    error.hidden = false;
    return;
  }

  form.reset();
  await refresh();
});

document.querySelector('[data-testid="logout"]').addEventListener("click", signOut);

api("/api/me")
  .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
  .then((user) => {
    document.querySelector('[data-testid="current-user"]').textContent = user.email;
    return refresh();
  })
  .catch(signOut);
