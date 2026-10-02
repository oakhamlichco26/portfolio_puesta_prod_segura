// 1) Actividades del menú lateral
const activities = {
  todo:       { name: "Todo",           desc: "Todos los ejercicios, del más reciente al más antiguo." },
  frontend:   { name: "Frontend",       desc: "HTML, CSS y JavaScript." },
  backend:    { name: "Backend",        desc: "APIs, bases de datos y servidores." },
  algoritmos: { name: "Algoritmos",     desc: "Estructuras de datos y resolución de problemas." },
  cloud:      { name: "Cloud / DevOps", desc: "Despliegue, CI/CD e infraestructura." }
};

// 2) Entradas del timeline: añade las tuyas aquí
const entries = [
  { date: "-", activity: "-", title: "-",
    text: "Proximamente",
    demo: "",
    repo: "" },
];

const menu = document.getElementById("menu");
const timeline = document.getElementById("timeline");

Object.entries(activities).forEach(([key, a]) => {
  const link = document.createElement("a");
  link.href = "#" + key;
  link.textContent = a.name;
  link.dataset.key = key;
  menu.appendChild(link);
});

const esc = s => Object.assign(document.createElement("div"), { textContent: s }).innerHTML;
const fmt = d => new Date(d + "T00:00:00").toLocaleDateString("es-ES", { day: "numeric", month: "long" });

function render() {
  const hash = location.hash.slice(1);
  const current = activities[hash] ? hash : "todo";
  document.title = activities[current].name + " · Tu Nombre";
  document.getElementById("title").textContent = activities[current].name;
  document.getElementById("desc").textContent = activities[current].desc;
  menu.querySelectorAll("a").forEach(a => a.classList.toggle("active", a.dataset.key === current));

  const list = entries
    .filter(e => current === "todo" || e.activity === current)
    .sort((a, b) => b.date.localeCompare(a.date));

  const byYear = {};
  list.forEach(e => (byYear[e.date.slice(0, 4)] ||= []).push(e));

  timeline.innerHTML = Object.keys(byYear).sort((a, b) => b - a).map(year => `
    <section class="year-group">
      <div class="year">${year}</div>
      <div class="entries">
        ${byYear[year].map(e => `
          <article class="entry">
            <time datetime="${esc(e.date)}">${fmt(e.date)}</time>
            <h3>${esc(e.title)}</h3>
            <p>${esc(e.text)}</p>
            <div class="links">
              ${e.demo ? `<a href="${esc(e.demo)}">Ver demo →</a>` : ""}
              ${e.repo ? `<a href="${esc(e.repo)}" target="_blank" rel="noopener">Código ↗</a>` : ""}
            </div>
          </article>`).join("")}
      </div>
    </section>`).join("") || `<p class="empty">Aún no hay entradas en esta actividad.</p>`;
}

window.addEventListener("hashchange", render);
render();