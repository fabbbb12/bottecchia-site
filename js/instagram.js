(function () {
  "use strict";

  var grid = document.getElementById("instaGrid");
  if (!grid) return;

  var posts = (window.INSTAGRAM_POSTS || []).filter(Boolean);

  function loadEmbedScript(callback) {
    if (window.instgrm) { callback(); return; }
    var script = document.createElement("script");
    script.src = "https://www.instagram.com/embed.js";
    script.async = true;
    script.onload = callback;
    script.onerror = renderFallback;
    document.body.appendChild(script);
  }

  function renderRealPosts() {
    grid.innerHTML = "";
    posts.forEach(function (url) {
      var wrap = document.createElement("div");
      wrap.className = "insta-embed-wrap";
      var blockquote = document.createElement("blockquote");
      blockquote.className = "instagram-media";
      blockquote.setAttribute("data-instgrm-permalink", url);
      blockquote.setAttribute("data-instgrm-version", "14");
      blockquote.style.margin = "0";
      wrap.appendChild(blockquote);
      grid.appendChild(wrap);
    });

    loadEmbedScript(function () {
      if (window.instgrm && window.instgrm.Embeds) {
        window.instgrm.Embeds.process();
      }
    });
  }

  function renderFallback() {
    var icon = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.2" cy="6.8" r="1"/></svg>';
    grid.innerHTML = "";
    for (var i = 0; i < 3; i++) {
      var a = document.createElement("a");
      a.className = "insta-placeholder";
      a.href = "https://www.instagram.com/bottecchiaadvogados/";
      a.target = "_blank";
      a.rel = "noopener";
      a.innerHTML = icon;
      grid.appendChild(a);
    }
    var empty = document.createElement("div");
    empty.className = "insta-empty";
    empty.innerHTML =
      "<p>Novas publicações em breve por aqui. Enquanto isso, acompanhe tudo em tempo real no nosso perfil oficial.</p>" +
      '<a class="btn btn-outline" href="https://www.instagram.com/bottecchiaadvogados/" target="_blank" rel="noopener" style="margin-top:14px;"><span>Ver perfil no Instagram</span></a>';
    grid.appendChild(empty);
  }

  if (posts.length) {
    renderRealPosts();
  } else {
    renderFallback();
  }
})();
