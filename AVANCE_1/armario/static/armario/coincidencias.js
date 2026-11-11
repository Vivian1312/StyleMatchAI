// StyleMatch AI 1.3.3 - interfaz sin inferencia ni guardado de prendas externas.
(() => {
  const $ = (id) => document.getElementById(id);
  const tabSubir = $("pestana-subir");
  const tabEnlace = $("pestana-enlace");
  const panelSubir = $("panel-subir");
  const panelEnlace = $("panel-enlace");
  const archivoInput = $("archivo-consulta");
  const zonaCarga = $("zona-carga");
  const cargaVacia = $("carga-vacia");
  const cargaSeleccionada = $("carga-seleccionada");
  const vistaArchivo = $("vista-archivo");
  const nombreArchivo = $("nombre-archivo");
  const urlConsulta = $("url-consulta");
  const previaEnlace = $("previa-enlace");
  const vistaEnlace = $("vista-enlace");
  const vistaEnlaceGenerica = $("vista-enlace-generica");
  const textoEnlace = $("texto-enlace");
  const errorConsulta = $("error-consulta");
  const fotoConsultada = $("foto-consultada");
  const nombreConsultada = $("nombre-consultada");
  const estado = $("resultado-estado");
  const estadoTitulo = $("estado-titulo");
  const estadoDescripcion = $("estado-descripcion");
  const tarjetasDemo = $("tarjetas-demo");
  const avisos = $("avisos-resultados");
  const cantidadResultados = $("cantidad-resultados");
  const totalArmario = Number(document.body.dataset.totalPrendas || "0");

  let modo = "archivo";
  let urlTemporal = null;
  let archivoElegido = null;

  function error(texto) {
    errorConsulta.textContent = texto;
    errorConsulta.classList.remove("oculto");
  }
  function limpiarError() {
    errorConsulta.classList.add("oculto");
    errorConsulta.textContent = "";
  }
  function activarTab(nuevoModo) {
    modo = nuevoModo;
    const subir = modo === "archivo";
    tabSubir.classList.toggle("activa", subir);
    tabEnlace.classList.toggle("activa", !subir);
    tabSubir.setAttribute("aria-selected", String(subir));
    tabEnlace.setAttribute("aria-selected", String(!subir));
    panelSubir.classList.toggle("oculto", !subir);
    panelEnlace.classList.toggle("oculto", subir);
    limpiarError();
  }
  tabSubir.addEventListener("click", () => activarTab("archivo"));
  tabEnlace.addEventListener("click", () => activarTab("enlace"));

  function mostrarConsultada(src, nombre) {
    fotoConsultada.replaceChildren();
    if (src) {
      const img = document.createElement("img");
      img.src = src;
      img.alt = "Fotograf\u00eda de la prenda consultada";
      img.addEventListener("error", () => {
        fotoConsultada.textContent = "Imagen no disponible";
      }, { once: true });
      fotoConsultada.append(img);
    } else {
      fotoConsultada.textContent = "URL";
    }
    nombreConsultada.textContent = nombre;
  }

  function cargarArchivo(archivo) {
    limpiarError();
    if (!archivo) return;
    const valido = ["image/jpeg", "image/png"].includes(archivo.type)
      && /\.(jpe?g|png)$/i.test(archivo.name)
      && archivo.size <= 10 * 1024 * 1024;
    if (!valido) {
      error("Selecciona una imagen JPG o PNG de hasta 10 MB.");
      archivoInput.value = "";
      archivoElegido = null;
      return;
    }
    archivoElegido = archivo;
    if (urlTemporal) URL.revokeObjectURL(urlTemporal);
    urlTemporal = URL.createObjectURL(archivo);
    vistaArchivo.src = urlTemporal;
    nombreArchivo.textContent = archivo.name;
    cargaVacia.classList.add("oculto");
    cargaSeleccionada.classList.remove("oculto");
    mostrarConsultada(urlTemporal, archivo.name);
    restaurarResultados();
  }
  archivoInput.addEventListener("change", () => cargarArchivo(archivoInput.files[0]));
  ["dragenter", "dragover"].forEach((tipo) => zonaCarga.addEventListener(tipo, (e) => {
    e.preventDefault();
    zonaCarga.classList.add("arrastrando");
  }));
  ["dragleave", "drop"].forEach((tipo) => zonaCarga.addEventListener(tipo, (e) => {
    e.preventDefault();
    zonaCarga.classList.remove("arrastrando");
  }));
  zonaCarga.addEventListener("drop", (e) => {
    const archivo = e.dataTransfer.files[0];
    if (!archivo) return;
    const transfer = new DataTransfer();
    transfer.items.add(archivo);
    archivoInput.files = transfer.files;
    cargarArchivo(archivo);
  });
  window.addEventListener("pagehide", () => { if (urlTemporal) URL.revokeObjectURL(urlTemporal); });

  function urlValida() {
    try {
      const u = new URL(urlConsulta.value.trim());
      return ["https:", "http:"].includes(u.protocol) ? u : null;
    } catch (_) { return null; }
  }
  function prepararEnlace() {
    const u = urlValida();
    if (!u) return null;
    const esImagen = /\.(jpg|jpeg|png)$/i.test(u.pathname);
    previaEnlace.classList.remove("oculto");
    textoEnlace.textContent = u.hostname;
    vistaEnlace.classList.toggle("oculto", !esImagen);
    vistaEnlaceGenerica.classList.toggle("oculto", esImagen);
    if (esImagen) {
      vistaEnlace.src = u.href;
      vistaEnlace.onerror = () => {
        vistaEnlace.classList.add("oculto");
        vistaEnlaceGenerica.classList.remove("oculto");
      };
    } else {
      vistaEnlace.removeAttribute("src");
    }
    mostrarConsultada(esImagen ? u.href : null, u.hostname);
    return u;
  }
  urlConsulta.addEventListener("change", () => {
    limpiarError();
    if (urlConsulta.value.trim()) prepararEnlace();
    restaurarResultados();
  });

  function mostrarEstado(titulo, descripcion) {
    estado.classList.remove("oculto");
    tarjetasDemo.classList.add("oculto");
    avisos.classList.add("oculto");
    estadoTitulo.textContent = titulo;
    estadoDescripcion.textContent = descripcion;
    cantidadResultados.textContent = "Coincidencias en tu armario";
  }
  function restaurarResultados() {
    mostrarEstado("A\u00fan no hay una b\u00fasqueda realizada", "Selecciona una prenda externa para comenzar.");
    document.querySelectorAll(".demo-btn").forEach((b) => b.classList.remove("activo"));
  }

  $("boton-buscar").addEventListener("click", () => {
    limpiarError();
    if (modo === "archivo" && !archivoElegido) {
      error("Primero debes seleccionar una imagen de la prenda externa.");
      return;
    }
    let urlExterna = null;
    if (modo === "enlace") {
      urlExterna = prepararEnlace();
      if (!urlExterna) {
        error("Introduce un enlace completo que comience por https:// o http://.");
        return;
      }
    }
    if (modo === "enlace" && !/\.(jpe?g|png)$/i.test(urlExterna.pathname)) {
      mostrarEstado("Enlace de tienda registrado", "La tienda est\u00e1 enlazada como referencia. A\u00fan no extraemos la foto de una p\u00e1gina de producto; puedes subir una imagen de esa prenda para preparar la comparaci\u00f3n.");
    } else if (totalArmario === 0) {
      mostrarEstado("Tu armario est\u00e1 vac\u00edo", "Agrega prendas en Mi armario antes de buscar alternativas a una compra.");
    } else {
      mostrarEstado("Consulta preparada", "La imagen o enlace est\u00e1 listo. Falta conectar el modelo de similitud visual para calcular resultados reales.");
    }
  });

  const ejemplos = [
    { nombre:"Su\u00e9ter similar de ejemplo", porcentaje:92, css:"" },
    { nombre:"Prenda alternativa de ejemplo", porcentaje:87, css:"medio" },
    { nombre:"Prenda con similitud baja", porcentaje:64, css:"bajo" },
  ];
  const dibujo = '<svg class="icono" viewBox="0 0 24 24" aria-hidden="true"><path d="m16 4 3 2 4 1-2 6-4-2v9H7v-9l-4 2-2-6 4-1 3-2a4 4 0 0 0 8 0Z"/></svg>';
  function renderDemo(cantidad) {
    estado.classList.add("oculto");
    tarjetasDemo.classList.toggle("oculto", cantidad === 0);
    avisos.classList.remove("oculto");
    avisos.textContent = "DEMOSTRACI\u00d3N: las puntuaciones y prendas son ficticias. No se ha ejecutado un modelo de IA.";
    cantidadResultados.textContent = `Coincidencias en tu armario (${cantidad}) - ejemplo`;
    tarjetasDemo.replaceChildren();
    if (cantidad === 0) {
      mostrarEstado("No se encontraron coincidencias", "Ejemplo visual del estado sin resultados. Un modelo real deber\u00e1 determinar cu\u00e1ndo mostrarlo.");
      avisos.classList.remove("oculto");
      cantidadResultados.textContent = "Coincidencias en tu armario (0) - ejemplo";
      return;
    }
    ejemplos.slice(0, cantidad).forEach((dato, index) => {
      const card = document.createElement("article");
      card.className = "coincidencia-card";
      card.innerHTML = `<div class="coincidencia-foto">${dibujo}</div>`;
      const name = document.createElement("h4");
      name.textContent = `Coincidencia ${index + 1}`;
      const pct = document.createElement("span");
      pct.className = `porcentaje ${dato.css}`;
      pct.textContent = `${dato.porcentaje}% simulado`;
      const desc = document.createElement("p");
      desc.textContent = dato.nombre;
      const cat = document.createElement("span");
      cat.className = "etiqueta";
      cat.textContent = "Ejemplo visual";
      const link = document.createElement("a");
      link.className = "boton-ver";
      link.href = document.body.dataset.armarioUrl;
      link.textContent = "Ver mi armario";
      card.append(name,pct,desc,cat,link);
      tarjetasDemo.append(card);
    });
  }
  document.querySelectorAll(".demo-btn").forEach((boton) => {
    boton.addEventListener("click", () => {
      document.querySelectorAll(".demo-btn").forEach((b) => b.classList.remove("activo"));
      if (boton.dataset.demo === "reset") { restaurarResultados(); return; }
      boton.classList.add("activo");
      renderDemo(Number(boton.dataset.demo));
    });
  });
})();
