(function () {
  "use strict";

  /* ---------- Header scroll state ---------- */
  var header = document.getElementById("siteHeader");
  var backToTop = document.getElementById("backToTop");

  function onScroll() {
    var scrolled = window.scrollY > 40;
    header.classList.toggle("is-scrolled", scrolled);
    backToTop.classList.toggle("is-visible", window.scrollY > 500);
  }
  document.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  backToTop.addEventListener("click", function () {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  /* ---------- Mobile nav toggle ---------- */
  var navToggle = document.getElementById("navToggle");
  var mainNav = document.getElementById("mainNav");

  function closeNav() {
    navToggle.classList.remove("is-open");
    mainNav.classList.remove("is-open");
    navToggle.setAttribute("aria-expanded", "false");
    document.body.style.overflow = "";
  }

  navToggle.addEventListener("click", function () {
    var isOpen = mainNav.classList.toggle("is-open");
    navToggle.classList.toggle("is-open", isOpen);
    navToggle.setAttribute("aria-expanded", String(isOpen));
    document.body.style.overflow = isOpen ? "hidden" : "";
  });

  mainNav.querySelectorAll("a").forEach(function (link) {
    link.addEventListener("click", closeNav);
  });

  /* ---------- Scroll-spy active nav link ---------- */
  var navLinks = Array.prototype.slice.call(mainNav.querySelectorAll("a"));
  var sections = navLinks
    .map(function (link) {
      var id = link.getAttribute("href");
      return id && id.charAt(0) === "#" ? document.querySelector(id) : null;
    })
    .filter(Boolean);

  if ("IntersectionObserver" in window && sections.length) {
    var spy = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            var id = "#" + entry.target.id;
            navLinks.forEach(function (link) {
              link.classList.toggle("active", link.getAttribute("href") === id);
            });
          }
        });
      },
      { rootMargin: "-45% 0px -50% 0px" }
    );
    sections.forEach(function (section) { spy.observe(section); });
  }

  /* ---------- Reveal on scroll ---------- */
  var revealEls = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window) {
    var revealer = new IntersectionObserver(
      function (entries, obs) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("in-view");
            obs.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15 }
    );
    revealEls.forEach(function (el) { revealer.observe(el); });
  } else {
    revealEls.forEach(function (el) { el.classList.add("in-view"); });
  }

  /* ---------- Hero rotating headline ---------- */
  var headlines = document.querySelectorAll("#heroHeadline h1");
  if (headlines.length > 1) {
    var current = 0;
    setInterval(function () {
      headlines[current].classList.remove("is-active");
      current = (current + 1) % headlines.length;
      headlines[current].classList.add("is-active");
    }, 4500);
  }

  /* ---------- Especialidades: expand/collapse long text ---------- */
  document.querySelectorAll(".spec-card").forEach(function (card) {
    var text = card.querySelector("p.is-clamped");
    if (!text) return;
    requestAnimationFrame(function () {
      if (text.scrollHeight - 4 > text.clientHeight) {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "spec-more";
        btn.innerHTML = '<span>Ler mais</span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg>';
        btn.addEventListener("click", function () {
          var expanded = card.classList.toggle("is-expanded");
          btn.querySelector("span").textContent = expanded ? "Ler menos" : "Ler mais";
        });
        card.appendChild(btn);
      }
    });
  });

  /* ---------- Contact form (progressive enhancement) ---------- */
  var contactForm = document.getElementById("contactForm");
  var formStatus = document.getElementById("formStatus");
  var submitBtn = document.getElementById("submitBtn");

  function showStatus(kind, message) {
    formStatus.textContent = message;
    formStatus.className = "form-status is-visible " + kind;
  }

  if (contactForm) {
    contactForm.addEventListener("submit", function (event) {
      event.preventDefault();

      if (!contactForm.checkValidity()) {
        contactForm.reportValidity();
        return;
      }

      submitBtn.setAttribute("disabled", "true");
      submitBtn.querySelector("span").textContent = "Enviando...";

      var data = new FormData(contactForm);

      fetch(contactForm.action, { method: "POST", body: data })
        .then(function (res) {
          if (!res.ok) throw new Error("network");
          showStatus("success", "Mensagem enviada com sucesso! Em breve retornaremos o seu contato.");
          contactForm.reset();
        })
        .catch(function () {
          // Backend indisponível neste ambiente (ex.: sem PHP) — oferece envio alternativo por e-mail.
          var subject = encodeURIComponent(data.get("assunto") || "Contato pelo site");
          var body = encodeURIComponent(
            "Nome: " + data.get("nome") + "\nTelefone: " + data.get("telefone") + "\nE-mail: " + data.get("email") + "\n\n" + data.get("mensagem")
          );
          showStatus("error", "Não foi possível enviar automaticamente. Abrindo seu e-mail para concluir o envio...");
          window.location.href = "mailto:contato@bottecchia.adv.br?subject=" + subject + "&body=" + body;
        })
        .finally(function () {
          submitBtn.removeAttribute("disabled");
          submitBtn.querySelector("span").textContent = "Enviar mensagem";
        });
    });
  }

  /* ---------- Newsletter (front-end only placeholder) ---------- */
  var newsletterForm = document.getElementById("newsletterForm");
  if (newsletterForm) {
    newsletterForm.addEventListener("submit", function (event) {
      event.preventDefault();
      var email = newsletterForm.querySelector("input[type=email]").value;
      newsletterForm.innerHTML = '<p style="margin:0; color: var(--navy-800); font-weight:600;">Obrigado! Em breve você receberá novidades em ' + email + ".</p>";
    });
  }

  /* ---------- Footer year ---------- */
  var yearEl = document.getElementById("year");
  if (yearEl) yearEl.textContent = new Date().getFullYear();
})();
