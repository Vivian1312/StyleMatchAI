// StyleMatch AI - Selector de prendas y filtro local por categoria.
// La generacion real de outfits se realiza en Django, no en JavaScript.
document.addEventListener('DOMContentLoaded', () => {
  const formulario = document.getElementById('reco-formulario');
  if (!formulario) return;

  const campoPrenda = document.getElementById('reco-prenda-id');
  const filtro = document.getElementById('reco-filtro');
  const mensajeVacio = document.getElementById('reco-filtro-vacio');
  const botonGenerar = document.getElementById('reco-generar');
  const botones = Array.from(formulario.querySelectorAll('[data-prenda-id]'));

  function seleccionar(boton) {
    campoPrenda.value = boton.dataset.prendaId;
    botones.forEach(item => {
      const activo = item === boton;
      item.classList.toggle('reco-prenda--activa', activo);
      item.setAttribute('aria-pressed', String(activo));
    });
    botonGenerar.disabled = false;
  }

  botones.forEach(boton => {
    boton.addEventListener('click', () => seleccionar(boton));
  });

  filtro.addEventListener('change', () => {
    let visibles = 0;
    botones.forEach(boton => {
      const aparece = !filtro.value || boton.dataset.categoria === filtro.value;
      boton.hidden = !aparece;
      if (aparece) visibles += 1;
    });
    mensajeVacio.hidden = visibles !== 0;
    // Si la prenda elegida queda oculta, seleccionar la primera visible.
    const actual = botones.find(item => item.dataset.prendaId === campoPrenda.value);
    if (!actual || actual.hidden) {
      const primera = botones.find(item => !item.hidden);
      if (primera) {
        seleccionar(primera);
      } else {
        campoPrenda.value = '';
        botonGenerar.disabled = true;
      }
    }
  });

  botonGenerar.disabled = !campoPrenda.value;
});
