// StyleMatch AI - Busqueda real de Top 3 coincidencias con Fashion-CLIP
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
  const errorConsulta = $("error-consulta");
  const fotoConsultada = $("foto-consultada");
  const nombreConsultada = $("nombre-consultada");
  const estado = $("resultado-estado");
  const estadoTitulo = $("estado-titulo");
  const estadoDescripcion = $("estado-descripcion");
  const tarjetasDemo = $("tarjetas-demo");
  const avisos = $("avisos-resultados");
  const cantidadResultados = $("cantidad-resultados");
  const botonBuscar = $("boton-buscar");

  let modo = "archivo";
  let urlTemporal = null;
  let archivoElegido = null;

  function obtenerCSRF() {
    const cookie = document.cookie.split("; ").find((row) => row.startsWith("csrftoken="));
    return cookie ? decodeURIComponent(cookie.split("=")[1]) : "";
  }

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

  if (tabSubir) tabSubir.addEventListener("click", () => activarTab("archivo"));
  if (tabEnlace) tabEnlace.addEventListener("click", () => activarTab("enlace"));

  function mostrarConsultada(src, nombre) {
    fotoConsultada.replaceChildren();
    if (src) {
      const img = document.createElement("img");
      img.src = src;
      img.alt = "Fotografia de la prenda consultada";
      fotoConsultada.append(img);
    } else {
      fotoConsultada.textContent = "URL";
    }
    nombreConsultada.textContent = nombre;
  }

  function cargarArchivo(archivo) {
    limpiarError();
    if (!archivo) return;

    const extensionValida = /\.(jpe?g|png|webp)$/i.test(archivo.name);
    const tamanoValido = archivo.size <= 10 * 1024 * 1024;

    if (!extensionValida || !tamanoValido) {
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

  archivoInput.addEventListener("change", (e) => {
    const file = e.target.files && e.target.files[0];
    cargarArchivo(file);
  });

  ["dragenter", "dragover"].forEach((tipo) => zonaCarga.addEventListener(tipo, (e) => {
    e.preventDefault();
    zonaCarga.classList.add("arrastrando");
  }));

  ["dragleave", "drop"].forEach((tipo) => zonaCarga.addEventListener(tipo, (e) => {
    e.preventDefault();
    zonaCarga.classList.remove("arrastrando");
  }));

  zonaCarga.addEventListener("drop", (e) => {
    const archivo = e.dataTransfer.files && e.dataTransfer.files[0];
    if (!archivo) return;
    cargarArchivo(archivo);
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
    mostrarEstado("Imagen lista para analizar", "Haz clic en 'Buscar coincidencias' para calcular el Top 3.");
  }

  function renderResultadosReales(resultados) {
    estado.classList.add("oculto");
    tarjetasDemo.replaceChildren();
    if (!resultados || resultados.length === 0) {
      mostrarEstado("No se encontraron coincidencias", "No hay prendas vectorizadas disponibles para comparar.");
      return;
    }
    tarjetasDemo.classList.remove("oculto");
    avisos.classList.remove("oculto");
    avisos.textContent = "Resultados reales calculados con Fashion-CLIP y Similitud del Coseno (Top 3).";
    cantidadResultados.textContent = `Top ${resultados.length} coincidencias mas similares`;

    resultados.forEach((dato, index) => {
      const claseColor = dato.porcentaje >= 85 ? "" : dato.porcentaje >= 70 ? "medio" : "bajo";
      const card = document.createElement("article");
      card.className = "coincidencia-card";

      const fotoDiv = document.createElement("div");
      fotoDiv.className = "coincidencia-foto";
      const img = document.createElement("img");
      img.src = dato.imagen_url;
      img.alt = dato.nombre;
      img.style.width = "100%";
      img.style.height = "100%";
      img.style.objectFit = "cover";
      fotoDiv.append(img);

      const title = document.createElement("h4");
      title.textContent = `#${index + 1} · ${dato.nombre}`;

      const pct = document.createElement("span");
      pct.className = `porcentaje ${claseColor}`;
      pct.textContent = `${dato.porcentaje}% de similitud`;

      const cat = document.createElement("span");
      cat.className = "etiqueta";
      cat.textContent = dato.categoria;

      const link = document.createElement("a");
      link.className = "boton-ver";
      link.href = document.body.dataset.armarioUrl;
      link.textContent = "Ver en mi armario";

      card.append(fotoDiv, title, pct, cat, link);
      tarjetasDemo.append(card);
    });
  }

  botonBuscar.addEventListener("click", async () => {
    limpiarError();
    if (modo !== "archivo" || !archivoElegido) {
      error("Selecciona una imagen JPG o PNG en la pestana 'Subir imagen' para calcular el Top 3.");
      return;
    }

    botonBuscar.disabled = true;
    mostrarEstado("Analizando prenda con Fashion-CLIP...", "Extrayendo vector y calculando similitud del coseno contra la base de datos.");

    try {
      const formData = new FormData();
      formData.append("imagen", archivoElegido);

      const resp = await fetch("/coincidencias/buscar/", {
        method: "POST",
        headers: { "X-CSRFToken": obtenerCSRF() },
        body: formData,
      });
      const data = await resp.json();

      if (!resp.ok) {
        error(data.error || "Error al calcular similitud.");
        restaurarResultados();
      } else {
        renderResultadosReales(data.resultados);
      }
    } catch (err) {
      error("Error de conexion con el servidor Django.");
      restaurarResultados();
    } finally {
      botonBuscar.disabled = false;
    }
  });
})();
