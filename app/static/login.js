const form = document.querySelector('[data-testid="login-form"]');
const error = document.querySelector('[data-testid="login-error"]');

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  error.hidden = true;

  const body = {
    email: form.email.value.trim(),
    password: form.password.value,
  };

  const response = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    error.textContent = "Invalid email or password.";
    error.hidden = false;
    return;
  }

  const { access_token } = await response.json();
  localStorage.setItem("taskflow.token", access_token);
  window.location.assign("/tasks");
});
