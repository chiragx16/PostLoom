document.getElementById("loginForm").addEventListener("submit", async function (e) {
    e.preventDefault();

    const form = new FormData(this);
    const payload = {
        email: form.get("email"),
        password: form.get("password")
    };

    const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        credentials: "include",  // 👈 important for sending/storing cookies
        body: JSON.stringify(payload)
    });

    const result = await response.json();
    if (response.ok) {
        alert("Login success!");
        // proceed to another page or load protected data
    } else {
        alert(result.msg || "Login failed.");
    }
});