"""Comparacion visual y clasificacion orientativa de categorias con FashionCLIP.

El indice es privado por usuario. La clasificacion es zero-shot: no ha sido
calibrada y se puede corregir desde la interfaz.
"""
import ast
import io
import ipaddress
import json
import socket
import time
import urllib.request
from urllib.parse import urlsplit

import numpy as np
import torch
from PIL import Image, UnidentifiedImageError
from transformers import CLIPModel, CLIPProcessor

from .models import FotoArmario

_MODELO_CLIP = None
_PROCESADOR_CLIP = None
_VECTORES_TEXTO = None
MODEL_ID = "patrickjohncyh/fashion-clip"

# Las cache no se comparten entre usuarios. La vigencia corta permite reflejar
# guardados/ediciones sin campos updated_at ni migraciones de base de datos.
_CACHE_VECTORES = {}
_CACHE_SEGUNDOS = 8

# Descripciones en ingles porque FashionCLIP fue entrenado para moda en ingles.
# Dos o mas ejemplos por categoria ayudan a reducir ambiguedades de una sola frase.
_PROMPTS = {
    "tops": ["a product photo of a t-shirt", "a product photo of a blouse", "a product photo of a sweater", "a photo of a tank top"],
    "pantalones": ["a product photo of jeans", "a product photo of pants", "a product photo of trousers", "a product photo of shorts"],
    "chaquetas": ["a product photo of a jacket", "a product photo of a coat", "a product photo of a blazer"],
    "vestidos": ["a product photo of a dress", "a product photo of a long dress"],
    "faldas": ["a product photo of a skirt", "a product photo of a mini skirt"],
    "calzado": ["a product photo of sneakers", "a product photo of shoes", "a product photo of boots", "a product photo of sandals"],
    "accesorios": ["a product photo of a handbag", "a product photo of a hat", "a product photo of fashion accessories"],
}


def _obtener_modelo():
    global _MODELO_CLIP, _PROCESADOR_CLIP
    if _MODELO_CLIP is None or _PROCESADOR_CLIP is None:
        _MODELO_CLIP = CLIPModel.from_pretrained(MODEL_ID)
        _PROCESADOR_CLIP = CLIPProcessor.from_pretrained(MODEL_ID)
        _MODELO_CLIP.eval()
    return _MODELO_CLIP, _PROCESADOR_CLIP


def _a_tensor_salida(salida):
    return salida.pooler_output if hasattr(salida, "pooler_output") else salida


def _parsear_vector(texto_vector):
    try:
        return np.array(json.loads(texto_vector), dtype=np.float32)
    except (ValueError, TypeError):
        return np.array(ast.literal_eval(texto_vector), dtype=np.float32)


def _obtener_indice_vectores(usuario):
    """Matriz de prendas del usuario autenticado; nunca consulta armarios ajenos."""
    if usuario is None or not getattr(usuario, "is_authenticated", False):
        raise ValueError("Debes iniciar sesion para consultar tu armario.")

    ahora = time.monotonic()
    cache = _CACHE_VECTORES.get(usuario.pk)
    if cache is not None and ahora < cache["vence"]:
        return cache["matriz"], cache["metadatos"]

    qs = (
        FotoArmario.objects.filter(propietario=usuario)
        .exclude(vector_caracteristicas__isnull=True)
        .exclude(vector_caracteristicas="")
        .only("id", "nombre", "categoria", "propietario_id", "vector_caracteristicas")
    )
    vectores, metadatos = [], []
    vistos = set()
    for prenda in qs:
        try:
            vec = _parsear_vector(prenda.vector_caracteristicas)
            if vec.ndim != 1 or vec.size != 512 or not np.all(np.isfinite(vec)):
                continue
            # El mismo archivo importado dos veces puede tener el mismo embedding.
            marca = prenda.vector_caracteristicas
            if marca in vistos:
                continue
            vistos.add(marca)
            norma = np.linalg.norm(vec)
            if norma <= 0:
                continue
            vectores.append(vec / norma)
            metadatos.append({
                "id": prenda.pk,
                "nombre": prenda.nombre or f"Prenda #{prenda.pk}",
                "categoria_codigo": prenda.categoria or "",
                "categoria": prenda.get_categoria_display() if prenda.categoria else "Otro",
                "imagen_url": f"/prenda/{prenda.pk}/imagen/",
            })
        except (ValueError, SyntaxError, TypeError, OverflowError):
            continue

    matriz = np.vstack(vectores) if vectores else np.empty((0, 512), dtype=np.float32)
    _CACHE_VECTORES[usuario.pk] = {
        "vence": ahora + _CACHE_SEGUNDOS,
        "matriz": matriz,
        "metadatos": metadatos,
    }
    return matriz, metadatos


def invalidar_cache_vectores(usuario_id=None):
    """Opcional para llamar tras guardar/borrar una prenda vectorizada."""
    if usuario_id is None:
        _CACHE_VECTORES.clear()
    else:
        _CACHE_VECTORES.pop(usuario_id, None)


def _validar_url_publica(url):
    """Bloqueo basico de direcciones locales para evitar SSRF accidental.

    En produccion se recomienda sustituir urllib por un proxy de imagenes
    con lista de destinos permitidos y validacion en la conexion final.
    """
    partes = urlsplit(url)
    if partes.scheme not in ("https", "http") or not partes.hostname:
        raise ValueError("Usa un enlace directo http/https de una imagen.")
    if partes.username or partes.password:
        raise ValueError("El enlace no debe incluir credenciales.")
    try:
        direcciones = socket.getaddrinfo(partes.hostname, partes.port or (443 if partes.scheme == "https" else 80), type=socket.SOCK_STREAM)
        if not direcciones:
            raise ValueError("No se pudo resolver el dominio del enlace.")
        for info in direcciones:
            ip = ipaddress.ip_address(info[4][0])
            if not ip.is_global:
                raise ValueError("No se permiten enlaces a direcciones privadas o locales.")
    except (socket.gaierror, OSError) as exc:
        raise ValueError("No se pudo resolver el dominio del enlace.") from exc


class _RedireccionPublica(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validar_url_publica(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def cargar_imagen_segura(fuente_imagen):
    """Abre imagen recibida o URL directa; no guarda la imagen externa."""
    maximo = 10 * 1024 * 1024
    if isinstance(fuente_imagen, str):
        _validar_url_publica(fuente_imagen)
        peticion = urllib.request.Request(
            fuente_imagen,
            headers={"User-Agent": "Mozilla/5.0 StyleMatchAI/1.0"},
        )
        with urllib.request.build_opener(_RedireccionPublica()).open(peticion, timeout=8) as respuesta:
            longitud = respuesta.headers.get("Content-Length")
            if longitud and longitud.isdigit() and int(longitud) > maximo:
                raise ValueError("La imagen supera el limite de 10 MB.")
            contenido = respuesta.read(maximo + 1)
            if len(contenido) > maximo:
                raise ValueError("La imagen supera el limite de 10 MB.")
            fuente_imagen = io.BytesIO(contenido)
    try:
        with Image.open(fuente_imagen) as imagen:
            imagen.verify()
        if hasattr(fuente_imagen, "seek"):
            fuente_imagen.seek(0)
        with Image.open(fuente_imagen) as imagen:
            if imagen.width * imagen.height > 28_000_000:
                raise ValueError("La imagen tiene una resolucion demasiado grande.")
            return imagen.convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("La URL debe apuntar directamente a una imagen JPG o PNG valida.") from exc


def extraer_vector_imagen(fuente_imagen):
    modelo, procesador = _obtener_modelo()
    imagen = cargar_imagen_segura(fuente_imagen)
    entradas = procesador(images=imagen, return_tensors="pt")
    with torch.no_grad():
        salida = _a_tensor_salida(modelo.get_image_features(pixel_values=entradas["pixel_values"]))
        salida = salida / salida.norm(p=2, dim=-1, keepdim=True)
    return salida.cpu().numpy().flatten().astype(np.float32)


def clasificar_categoria_vector(vector):
    """Clasificacion zero-shot orientativa para las siete categorias de la web."""
    global _VECTORES_TEXTO
    modelo, procesador = _obtener_modelo()
    codigos = list(_PROMPTS)
    if _VECTORES_TEXTO is None:
        # Una sola inferencia de texto en lote, mas rapida que siete llamadas.
        frases = [frase for codigo in codigos for frase in _PROMPTS[codigo]]
        entradas = procesador(text=frases, padding=True, truncation=True, return_tensors="pt")
        with torch.no_grad():
            caracteristicas = _a_tensor_salida(modelo.get_text_features(**entradas))
            caracteristicas = caracteristicas / caracteristicas.norm(p=2, dim=-1, keepdim=True)
            representantes = []
            inicio = 0
            for codigo in codigos:
                fin = inicio + len(_PROMPTS[codigo])
                centro = caracteristicas[inicio:fin].mean(dim=0)
                centro = centro / centro.norm(p=2)
                representantes.append(centro)
                inicio = fin
        _VECTORES_TEXTO = torch.stack(representantes).cpu().numpy().astype(np.float32)
    puntuaciones = _VECTORES_TEXTO @ vector
    codigo = codigos[int(np.argmax(puntuaciones))]
    return codigo


def buscar_top_3_similares(
    fuente_imagen, usuario=None, categoria="auto", orden="desc",
    devolver_metricas=False, incluir_categoria=False,
):
    """Devuelve hasta tres resultados del usuario y categoria detectada opcional.

    categoria='auto': CLIP determina una categoria para filtrar resultados.
    categoria='': busqueda en todas las categorias (modo manual).
    """
    inicio = time.perf_counter()
    vector = extraer_vector_imagen(fuente_imagen)
    categoria_detectada = clasificar_categoria_vector(vector) if (categoria == "auto" or incluir_categoria) else None
    filtro = categoria_detectada if categoria == "auto" else categoria
    matriz, metadatos = _obtener_indice_vectores(usuario)

    resultados = []
    if matriz.shape[0]:
        similitudes = matriz @ vector
        validas = {codigo for codigo, _ in FotoArmario.CATEGORIAS}
        for idx, meta in enumerate(metadatos):
            if filtro in validas and meta["categoria_codigo"] != filtro:
                continue
            if filtro == "sin_categoria" and meta["categoria_codigo"]:
                continue
            puntuacion = max(0.0, min(100.0, round(float(similitudes[idx]) * 100, 1)))
            resultados.append({**meta, "porcentaje": puntuacion})

    resultados.sort(key=lambda item: item["porcentaje"], reverse=True)
    top_3 = resultados[:3]
    if orden == "asc":
        top_3.reverse()

    tiempo = round((time.perf_counter() - inicio) * 1000, 1)
    if devolver_metricas and incluir_categoria:
        return top_3, tiempo, categoria_detectada
    if devolver_metricas:
        return top_3, tiempo
    if incluir_categoria:
        return top_3, categoria_detectada
    return top_3
