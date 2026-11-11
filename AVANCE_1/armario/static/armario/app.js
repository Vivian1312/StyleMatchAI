// StyleMatch AI - carga de prendas, vista previa y edicion.
// La busqueda, filtros y paginacion usan Django para consultar toda la BD.
const archivoInput = document.getElementById("id_imagen");
const imagenPreview = document.getElementById("imagen-preview");
const cargaVacia = document.getElementById("carga-vacia");
const cargaSeleccionada = document.getElementById("carga-seleccionada");
const nombreArchivo = document.getElementById("nombre-archivo");
const botonGuardar = document.getElementById("boton-guardar");
const errorCliente = document.getElementById("error-cliente");
const zonaCarga = document.getElementById("zona-carga");

let urlTemporal = null;

function restaurarCarga() {
  if (urlTemporal) {
    URL.revokeObjectURL(urlTemporal);
    urlTemporal = null;
  }
  imagenPreview.removeAttribute("src");
  cargaVacia.classList.remove("oculto");
  cargaSeleccionada.classList.add("oculto");
  botonGuardar.disabled = true;
}

function mostrarImagenSeleccionada() {
  const archivo = archivoInput.files[0];
  if (!archivo) {
    restaurarCarga();
    return;
  }

  const permitido = ["image/jpeg", "image/png"].includes(archivo.type);
  const tamanoValido = archivo.size <= 10 * 1024 * 1024;
  const extensionValida = /\.(jpe?g|png)$/i.test(archivo.name);

  if (!permitido || !tamanoValido || !extensionValida) {
    errorCliente.textContent =
      "Selecciona un archivo JPG, JPEG o PNG de m\u00e1ximo 10 MB.";
    errorCliente.classList.remove("oculto");
    archivoInput.value = "";
    restaurarCarga();
    return;
  }

  errorCliente.classList.add("oculto");
  if (urlTemporal) URL.revokeObjectURL(urlTemporal);
  urlTemporal = URL.createObjectURL(archivo);
  imagenPreview.src = urlTemporal;
  nombreArchivo.textContent = archivo.name;
  cargaVacia.classList.add("oculto");
  cargaSeleccionada.classList.remove("oculto");
  botonGuardar.disabled = false;
}

if (archivoInput && zonaCarga) {
  archivoInput.addEventListener("change", mostrarImagenSeleccionada);

  ["dragenter", "dragover"].forEach((evento) => {
    zonaCarga.addEventListener(evento, (e) => {
      e.preventDefault();
      zonaCarga.classList.add("arrastrando");
    });
  });

  ["dragleave", "drop"].forEach((evento) => {
    zonaCarga.addEventListener(evento, (e) => {
      e.preventDefault();
      zonaCarga.classList.remove("arrastrando");
    });
  });

  zonaCarga.addEventListener("drop", (e) => {
    const archivo = e.dataTransfer.files[0];
    if (!archivo) return;
    const transferencia = new DataTransfer();
    transferencia.items.add(archivo);
    archivoInput.files = transferencia.files;
    mostrarImagenSeleccionada();
  });
}

window.addEventListener("pagehide", () => {
  if (urlTemporal) URL.revokeObjectURL(urlTemporal);
});

const dialogEditar = document.getElementById("dialog-editar");
const formEditar = document.getElementById("form-editar");
const editarNombre = document.getElementById("editar-nombre");
const editarCategoria = document.getElementById("editar-categoria");

if (dialogEditar && formEditar) {
  document.querySelectorAll("[data-editar-prenda]").forEach((boton) => {
    boton.addEventListener("click", () => {
      formEditar.action = boton.dataset.url;
      editarNombre.value = boton.dataset.nombre || "";
      editarCategoria.value = boton.dataset.categoria || "";
      dialogEditar.showModal();
      editarNombre.focus();
    });
  });

  document.getElementById("cerrar-edicion").addEventListener("click", () => {
    dialogEditar.close();
  });
  document.getElementById("cancelar-edicion").addEventListener("click", () => {
    dialogEditar.close();
  });
}

document.querySelectorAll(".form-eliminar-prenda").forEach((formulario) => {
  formulario.addEventListener("submit", (e) => {
    if (!confirm("\u00bfEliminar esta prenda de tu armario?")) {
      e.preventDefault();
    }
  });
});
