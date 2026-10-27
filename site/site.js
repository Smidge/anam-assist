const examples = {
  read: {
    request: "“What’s the temperature in the living room?”",
    cloud: "The conversation requests an available state-reading tool.",
    home: "Checks the session and reads Assist-exposed state.",
    reply: "“It’s 21 degrees in the living room.”",
  },
  light: {
    request: "“Turn on the reading lamp.”",
    cloud:
      "The conversation requests a light-control tool, if enabled for this session.",
    home: "Checks the session, allowed tool and exposed target, then sends the light command.",
    reply: "“The reading lamp is on.” Only after a successful tool result.",
  },
};
for (const button of document.querySelectorAll("[data-example]")) {
  button.addEventListener("click", () => {
    const example = examples[button.dataset.example];
    for (const control of document.querySelectorAll("[data-example]")) {
      control.setAttribute("aria-pressed", String(control === button));
    }
    document.querySelector("#request").textContent = example.request;
    document.querySelector("#cloud-detail").textContent = example.cloud;
    document.querySelector("#ha-detail").textContent = example.home;
    document.querySelector("#reply").textContent = example.reply;
  });
}

document.querySelector(".example-controls").hidden = false;
