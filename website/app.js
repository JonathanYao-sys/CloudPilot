// CloudPilot Local Static Product Launch Website Interactive Gallery (Zero external dependencies)
document.addEventListener("DOMContentLoaded", () => {
  const buttons = document.querySelectorAll(".tab-btn");
  const images = document.querySelectorAll(".shot-img");

  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetId = btn.getAttribute("data-target");
      buttons.forEach((b) => b.classList.remove("active"));
      images.forEach((img) => img.classList.remove("active"));

      btn.classList.add("active");
      const targetImg = document.getElementById(targetId);
      if (targetImg) {
        targetImg.classList.add("active");
      }
    });
  });
});
