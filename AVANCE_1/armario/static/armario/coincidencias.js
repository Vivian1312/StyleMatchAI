// StyleMatch AI — 1.3.5: clasificacion automatica y outfits dentro de Coincidencias.
// La prenda externa se conserva solo en la pagina; nunca se anade a Mi armario.
(() => {
  const $ = (id) => document.getElementById(id);
  const tabSubir = $('pestana-subir');
  const tabEnlace = $('pestana-enlace');
  const panelSubir = $('panel-subir');
  const panelEnlace = $('panel-enlace');
  const archivoInput = $('archivo-consulta');
  const zonaCarga = $('zona-carga');
  const cargaVacia = $('carga-vacia');
  const cargaSeleccionada = $('carga-seleccionada');
  const vistaArchivo = $('vista-archivo');
  const nombreArchivo = $('nombre-archivo');
  const urlConsulta = $('url-consulta');
  const previaEnlace = $('previa-enlace');
  const vistaEnlace = $('vista-enlace');
  const vistaEnlaceGenerica = $('vista-enlace-generica');
  const textoEnlace = $('texto-enlace');
  const filtroCategoria = $('filtro-categoria');
  const ordenSimilitud = $('orden-similitud');
  const errorConsulta = $('error-consulta');
  const fotoConsultada = $('foto-consultada');
  const nombreConsultada = $('nombre-consultada');
  const estado = $('resultado-estado');
  const estadoTitulo = $('estado-titulo');
  const estadoDescripcion = $('estado-descripcion');
  const tarjetasDemo = $('tarjetas-demo');
  const avisos = $('avisos-resultados');
  const cantidadResultados = $('cantidad-resultados');
  const botonBuscar = $('boton-buscar');
  const categoriaDetectada = $('categoria-detectada');
  const compraPanel = $('decision-compra');
  const simularExterna = $('simular-externa');
  const resultadosOutfits = $('outfits-coincidencias');

  if (!botonBuscar || !archivoInput || !compraPanel) return;

  const categorias = {
    tops: 'Tops', pantalones: 'Pantalones', chaquetas: 'Chaquetas',
    vestidos: 'Vestidos', faldas: 'Faldas', calzado: 'Calzado',
    accesorios: 'Accesorios',
  };
  let modo = 'archivo';
  let urlTemporal = null;
  let archivoElegido = null;
  let ultimaCategoria = null;
  let busquedaValida = false;
  let consultaEnCurso = 0;

  function obtenerCSRF() {
    const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
    return cookie ? decodeURIComponent(cookie.split('=')[1]) : '';
  }

  function mostrarError(texto) {
    errorConsulta.textContent = texto;
    errorConsulta.classList.remove('oculto');
  }
  function limpiarError() {
    errorConsulta.classList.add('oculto');
    errorConsulta.textContent = '';
  }
  function mostrarEstado(titulo, descripcion) {
    estado.classList.remove('oculto');
    tarjetasDemo.classList.add('oculto');
    avisos.classList.add('oculto');
    estadoTitulo.textContent = titulo;
    estadoDescripcion.textContent = descripcion;
    cantidadResultados.textContent = 'Coincidencias en tu armario';
  }
  function limpiarOutfits() {
    resultadosOutfits.replaceChildren();
    resultadosOutfits.classList.add('oculto');
    compraPanel.classList.add('oculto');
    ultimaCategoria = null;
    busquedaValida = false;
  }
  function restaurarResultados() {
    consultaEnCurso += 1;
    botonBuscar.disabled = false;
    limpiarOutfits();
    mostrarEstado('Imagen lista para analizar', 'Selecciona filtros si lo deseas y pulsa «Buscar coincidencias».');
    categoriaDetectada.textContent = 'La categoria se detectara automaticamente. Puedes corregirla en el selector.';
  }
  function mostrarConsultada(src, nombre) {
    fotoConsultada.replaceChildren();
    if (src) {
      const img = document.createElement('img');
      img.src = src;
      img.alt = 'Prenda externa consultada';
      img.onerror = () => { fotoConsultada.textContent = 'URL'; };
      fotoConsultada.append(img);
    } else {
      fotoConsultada.textContent = 'URL';
    }
    nombreConsultada.textContent = nombre;
  }
  function activarTab(nuevoModo) {
    modo = nuevoModo;
    const subir = modo === 'archivo';
    tabSubir.classList.toggle('activa', subir);
    tabEnlace.classList.toggle('activa', !subir);
    tabSubir.setAttribute('aria-selected', String(subir));
    tabEnlace.setAttribute('aria-selected', String(!subir));
    panelSubir.classList.toggle('oculto', !subir);
    panelEnlace.classList.toggle('oculto', subir);
    limpiarError();
    restaurarResultados();
    if (subir && urlTemporal) mostrarConsultada(urlTemporal, archivoElegido?.name || 'Archivo');
    else if (!subir && urlConsulta?.value.trim()) {
      try { mostrarConsultada(new URL(urlConsulta.value.trim()).href, new URL(urlConsulta.value.trim()).hostname); }
      catch (_) { mostrarConsultada('', 'Enlace externo'); }
    }
  }
  tabSubir?.addEventListener('click', () => activarTab('archivo'));
  tabEnlace?.addEventListener('click', () => activarTab('enlace'));

  function cargarArchivo(archivo) {
    limpiarError();
    if (!archivo) return;
    const valido = /\.(jpe?g|png)$/i.test(archivo.name) &&
      ['image/jpeg', 'image/png', ''].includes(archivo.type) &&
      archivo.size <= 10 * 1024 * 1024;
    if (!valido) {
      mostrarError('Selecciona una imagen JPG o PNG de hasta 10 MB.');
      archivoInput.value = '';
      archivoElegido = null;
      restaurarResultados();
      return;
    }
    archivoElegido = archivo;
    if (urlTemporal) URL.revokeObjectURL(urlTemporal);
    urlTemporal = URL.createObjectURL(archivo);
    vistaArchivo.src = urlTemporal;
    nombreArchivo.textContent = archivo.name;
    cargaVacia.classList.add('oculto');
    cargaSeleccionada.classList.remove('oculto');
    mostrarConsultada(urlTemporal, archivo.name);
    restaurarResultados();
  }
  archivoInput.addEventListener('change', e => cargarArchivo(e.target.files?.[0]));
  urlConsulta?.addEventListener('input', () => {
    limpiarError();
    restaurarResultados();
    const valor = urlConsulta.value.trim();
    if (!valor) { previaEnlace.classList.add('oculto'); return; }
    try {
      const u = new URL(valor);
      previaEnlace.classList.remove('oculto');
      textoEnlace.textContent = u.hostname;
      vistaEnlace.src = u.href;
      vistaEnlace.classList.remove('oculto');
      vistaEnlaceGenerica.classList.add('oculto');
      vistaEnlace.onerror = () => {
        vistaEnlace.classList.add('oculto');
        vistaEnlaceGenerica.classList.remove('oculto');
      };
      mostrarConsultada(u.href, u.hostname);
    } catch (_) { previaEnlace.classList.add('oculto'); }
  });
  ['dragenter', 'dragover'].forEach(tipo => zonaCarga.addEventListener(tipo, e => {
    e.preventDefault(); zonaCarga.classList.add('arrastrando');
  }));
  ['dragleave', 'drop'].forEach(tipo => zonaCarga.addEventListener(tipo, e => {
    e.preventDefault(); zonaCarga.classList.remove('arrastrando');
  }));
  zonaCarga.addEventListener('drop', e => {
    const archivo = e.dataTransfer.files?.[0];
    if (archivo) cargarArchivo(archivo);
  });

  async function peticionAccion(campos) {
    const formData = new FormData();
    Object.entries(campos).forEach(([clave, valor]) => formData.append(clave, valor));
    const respuesta = await fetch('/coincidencias/buscar/', {
      method: 'POST', headers: {'X-CSRFToken': obtenerCSRF()}, body: formData,
    });
    const contenido = await respuesta.json();
    if (!respuesta.ok) throw new Error(contenido.error || 'No se pudo procesar la consulta.');
    return contenido;
  }

  function fuenteExternaActual() {
    if (modo === 'archivo') return urlTemporal;
    return urlConsulta?.value.trim() || '';
  }
  function categoriaParaOutfits() {
    const seleccion = filtroCategoria.value;
    return categorias[seleccion] ? seleccion : ultimaCategoria;
  }

  function presentarOutfits(outfits, faltantes, descripcion) {
    resultadosOutfits.replaceChildren();
    resultadosOutfits.classList.remove('oculto');
    const titulo = document.createElement('h3');
    titulo.className = 'compra-outfits-titulo';
    titulo.textContent = `${descripcion} (${outfits.length})`;
    resultadosOutfits.append(titulo);
    if (!outfits.length) {
      const aviso = document.createElement('p');
      aviso.className = 'compra-aviso';
      aviso.textContent = faltantes?.length
        ? `No hay combinaciones completas. Faltan estas categorias en tu armario: ${faltantes.join(', ')}.`
        : 'No hay outfits completos con las prendas disponibles. Puedes agregar prendas a tu armario.';
      resultadosOutfits.append(aviso);
      return;
    }
    outfits.forEach(outfit => {
      const tarjeta = document.createElement('article');
      tarjeta.className = 'compra-outfit';
      const cabecera = document.createElement('h4');
      cabecera.textContent = outfit.titulo;
      const desc = document.createElement('p');
      desc.textContent = `${outfit.descripcion} · ${outfit.etiquetas.join(' + ')}`;
      const fotos = document.createElement('div');
      fotos.className = 'compra-fotos';
      outfit.prendas.forEach(prenda => {
        const bloque = document.createElement('div');
        bloque.className = `compra-foto${prenda.externa ? ' compra-foto--externa' : ''}`;
        const img = document.createElement('img');
        img.loading = 'lazy';
        img.src = prenda.externa ? fuenteExternaActual() : prenda.imagen_url;
        img.alt = prenda.nombre;
        img.onerror = () => { img.alt = 'Imagen no disponible'; };
        const nombre = document.createElement('span');
        nombre.textContent = `${prenda.nombre} (${prenda.categoria})`;
        bloque.append(img, nombre);
        fotos.append(bloque);
      });
      tarjeta.append(cabecera, desc, fotos);
      resultadosOutfits.append(tarjeta);
    });
  }

  async function consultarOutfits(accion, prendaId, boton) {
    if (!busquedaValida) return;
    boton.disabled = true;
    resultadosOutfits.replaceChildren();
    resultadosOutfits.classList.remove('oculto');
    const aviso = document.createElement('p');
    aviso.className = 'compra-aviso';
    aviso.textContent = 'Creando looks con las prendas de tu armario...';
    resultadosOutfits.append(aviso);
    try {
      const campos = {accion};
      if (accion === 'outfits_existente') campos.prenda_id = prendaId;
      else {
        campos.categoria = categoriaParaOutfits();
        if (!categorias[campos.categoria]) {
          throw new Error('Selecciona una categoria valida para simular outfits con la prenda externa.');
        }
      }
      const data = await peticionAccion(campos);
      presentarOutfits(data.outfits || [], data.faltantes || [],
        accion === 'outfits_externa' ? 'Looks con la prenda que quieres comprar' : 'Looks con la prenda que ya tienes');
      resultadosOutfits.scrollIntoView({behavior: 'smooth', block: 'nearest'});
    } catch (err) {
      resultadosOutfits.replaceChildren();
      const mensaje = document.createElement('p');
      mensaje.className = 'compra-aviso';
      mensaje.textContent = err.message || 'No se pudieron generar outfits.';
      resultadosOutfits.append(mensaje);
    } finally { boton.disabled = false; }
  }
  simularExterna.addEventListener('click', () => consultarOutfits('outfits_externa', null, simularExterna));

  function renderResultadosReales(data) {
    const resultados = data.resultados || [];
    const detectada = data.categoria_detectada;
    ultimaCategoria = detectada;
    busquedaValida = true;
    categoriaDetectada.textContent = detectada && categorias[detectada]
      ? `Categoria sugerida por FashionCLIP: ${categorias[detectada]} (orientativa). Puedes corregirla en el selector.`
      : 'El modelo no pudo sugerir una categoria. Seleccionala manualmente.';

    tarjetasDemo.replaceChildren();
    compraPanel.classList.remove('oculto');
    const avisoExistentes = compraPanel.querySelector('.compra-acciones p');
    if (avisoExistentes) {
      avisoExistentes.textContent = resultados.length
        ? '1. Aprovecha tu armario: pulsa «Crear outfits» en una coincidencia para usar una prenda que ya tienes.'
        : '1. No hay prendas comparables en la categoria consultada. Puedes explorar looks con la prenda externa.';
    }
    resultadosOutfits.replaceChildren();
    resultadosOutfits.classList.add('oculto');
    if (!resultados.length) {
      mostrarEstado('No hay prendas en esta categoria',
        'No encontramos prendas disponibles para comparar. Puedes simular un outfit con la prenda externa si tienes otras categorias.');
      return;
    }
    estado.classList.add('oculto');
    tarjetasDemo.classList.remove('oculto');
    avisos.classList.remove('oculto');
    const categoriaTexto = filtroCategoria.value === 'auto'
      ? `${categorias[data.categoria_aplicada] || 'categoria sugerida'} (automatica)`
      : filtroCategoria.options[filtroCategoria.selectedIndex].text;
    const ordenTexto = ordenSimilitud.value === 'asc' ? 'menor a mayor' : 'mayor a menor';
    const metrica = typeof data.tiempo_ms === 'number' ? ` · Tiempo: ${data.tiempo_ms} ms` : '';
    avisos.textContent = `Categoria: ${categoriaTexto} · Orden: ${ordenTexto}${metrica}`;
    cantidadResultados.textContent = `Top ${resultados.length} coincidencias (${categoriaTexto})`;

    resultados.forEach((prenda, indice) => {
      const tarjeta = document.createElement('article');
      tarjeta.className = 'coincidencia-card';
      const foto = document.createElement('div');
      foto.className = 'coincidencia-foto';
      const img = document.createElement('img');
      img.src = prenda.imagen_url;
      img.alt = prenda.nombre;
      img.style.width = '100%'; img.style.height = '100%'; img.style.objectFit = 'contain';
      img.onerror = () => { foto.textContent = 'Vista previa no disponible'; };
      foto.append(img);
      const nombre = document.createElement('h4');
      nombre.textContent = `#${indice + 1} · ${prenda.nombre}`;
      const porcentaje = document.createElement('span');
      const clase = prenda.porcentaje >= 85 ? '' : prenda.porcentaje >= 70 ? 'medio' : 'bajo';
      porcentaje.className = `porcentaje ${clase}`;
      porcentaje.textContent = `${prenda.porcentaje}% de similitud`;
      const cat = document.createElement('span');
      cat.className = 'etiqueta'; cat.textContent = prenda.categoria;
      const enlace = document.createElement('a');
      enlace.className = 'boton-ver';
      enlace.href = document.body.dataset.armarioUrl;
      enlace.textContent = 'Ver en mi armario';
      const accion = document.createElement('button');
      accion.type = 'button';
      accion.className = 'boton-outfit';
      accion.textContent = 'Crear outfits con esta prenda';
      accion.addEventListener('click', () => consultarOutfits('outfits_existente', prenda.id, accion));
      tarjeta.append(foto, nombre, porcentaje, cat, accion, enlace);
      tarjetasDemo.append(tarjeta);
    });
  }

  async function ejecutarBusqueda() {
    limpiarError();
    const formData = new FormData();
    if (modo === 'archivo') {
      if (!archivoElegido) { mostrarError('Selecciona una imagen en Subir imagen.'); return; }
      formData.append('imagen', archivoElegido);
    } else {
      const url = urlConsulta?.value.trim() || '';
      if (!url) { mostrarError('Pega la URL directa de una imagen.'); return; }
      formData.append('url_imagen', url);
    }
    formData.append('accion', 'buscar');
    formData.append('categoria', filtroCategoria.value);
    formData.append('orden', ordenSimilitud.value);
    const turno = ++consultaEnCurso;
    botonBuscar.disabled = true;
    limpiarOutfits();
    mostrarEstado('Analizando consulta...', 'Calculando categoria y similitud visual con FashionCLIP.');
    try {
      const respuesta = await fetch('/coincidencias/buscar/', {
        method:'POST', headers:{'X-CSRFToken':obtenerCSRF()}, body:formData,
      });
      const data = await respuesta.json();
      if (turno !== consultaEnCurso) return;
      if (!respuesta.ok) {
        mostrarError(data.error || 'Error al procesar la consulta.');
        mostrarEstado('No se pudo analizar la imagen', 'Prueba otra imagen o una URL directa.');
      } else renderResultadosReales(data);
    } catch (_) {
      if (turno === consultaEnCurso) {
        mostrarError('Error de conexion con el servidor Django.');
        mostrarEstado('Error de conexion', 'Verifica que el servidor este activo.');
      }
    } finally {
      if (turno === consultaEnCurso) botonBuscar.disabled = false;
    }
  }

  botonBuscar.addEventListener('click', ejecutarBusqueda);
  [filtroCategoria, ordenSimilitud].forEach(control => control.addEventListener('change', () => {
    if ((modo === 'archivo' && archivoElegido) || (modo === 'enlace' && urlConsulta?.value.trim())) {
      ejecutarBusqueda();
    }
  }));
})();
