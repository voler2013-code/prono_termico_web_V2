import "./skewt.js";

// Solo reemplaza la representación del sondeo. El formulario y el worker siguen iguales.
export function renderSondeos(output, blocks) {
  output.replaceChildren();
  if (!Array.isArray(blocks) || !blocks.length) {
    output.textContent = "Sin salida.";
    return;
  }
  const allPoints = blocks.flatMap(b => b.profile?.puntos || []);
  for (const block of blocks) {
    const section = document.createElement("section");
    section.className = "sondeo-block";
    const table = document.createElement("pre");
    table.className = "sondeo-table";
    table.textContent = block.text || "No se recibieron datos para esta hora.";
    section.append(table);
    const profile = block.profile;
    if (profile?.puntos?.length) {
      const header = document.createElement("div");
      header.className = "skewt-toolbar";
      const title = document.createElement("strong");
      title.textContent = `Skew-T · ${String(profile.hora).padStart(2, "0")}:00`;
      header.append(title);
      const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      svg.classList.add("skewt-chart");
      const readout = document.createElement("p");
      readout.className = "skewt-readout";
      readout.textContent = "Tocá un nivel para leer T, Td y altura. Arrastrá para desplazar; dos dedos o +/− para ampliar.";
      const chart = new window.SkewT(svg, readout);
      chart.fitPoints = allPoints;
      const button = (label, fn, ariaLabel) => {
        const el = document.createElement("button");
        el.type = "button"; el.className = "text-btn"; el.textContent = label;
        if (ariaLabel) el.setAttribute("aria-label", ariaLabel);
        el.addEventListener("click", fn); header.append(el);
      };
      button("−", () => {chart.tr.zoom(.8);chart.draw();}, "Alejar gráfico");
      button("+", () => {chart.tr.zoom(1.25);chart.draw();}, "Ampliar gráfico");
      button("Ajustar", () => chart.fit());
      const legend = document.createElement("p");
      legend.className = "skewt-legend";
      legend.innerHTML = '<span class="skewt-t">━ Temperatura</span> <span class="skewt-td">━ Punto de rocío</span>';
      const layers = document.createElement("div");
      layers.className = "skewt-layers";
      for (const [key, labelText] of [["dry", "Adiabáticas secas"], ["moist", "Saturadas"], ["mix", "Mezcla"], ["altitude", "Altitud ISA"]]) {
        const label = document.createElement("label"), input = document.createElement("input");
        input.type = "checkbox"; input.checked = chart.layers[key];
        input.addEventListener("change", () => {chart.layers[key] = input.checked;chart.draw();});
        label.append(input, document.createTextNode(labelText)); layers.append(label);
      }
      const info = document.createElement("p");
      info.className = "skewt-info";
      const count = profile.modelos?.length || 0;
      info.textContent = `${count}/7 respuestas de modelos · ${profile.puntos.length} puntos visibles · 1000–250 hPa solicitados. ` +
        "Medianas; círculos blancos: incluye interpolación local. Alturas de la tabla: referencias aproximadas. Alturas del modelo: al tocar el gráfico.";
      const coverage = document.createElement("details");
      coverage.className = "skewt-coverage";
      const summary = document.createElement("summary"); summary.textContent = "Niveles recibidos por modelo";
      const list = document.createElement("ul");
      const models = ["icon_seamless", "gfs_seamless", "meteofrance_seamless", "ecmwf_ifs", "ukmo_seamless", "gem_seamless", "cma_grapes_global"];
      for (const model of models) {
        const li = document.createElement("li");
        const n = profile.cobertura?.[model];
        li.textContent = `${model}: ${n == null ? "sin respuesta válida" : `${n}/31 niveles con T y HR`}`;
        list.append(li);
      }
      coverage.append(summary, list);
      section.append(header, legend, svg, layers, readout, info, coverage);
      chart.setData(profile.puntos);
    }
    output.append(section);
  }
}

let resizeFrame;
window.addEventListener("resize", () => {
  cancelAnimationFrame(resizeFrame);
  resizeFrame = requestAnimationFrame(() => {
    document.querySelectorAll(".skewt-chart").forEach(svg => svg._skewt?.draw());
  });
});
