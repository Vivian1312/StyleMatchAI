import ast
import io
import json
import time
import urllib.request
import numpy as np
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor
from .models import FotoArmario

_MODELO_CLIP = None
_PROCESADOR_CLIP = None
MODEL_ID = "patrickjohncyh/fashion-clip"

# Cache en memoria de vectores para evitar parsear texto en cada consulta
_CACHE_VECTORES = {
    "firma": None,
    "matriz": None,
    "metadatos": [],
}


def _obtener_modelo():
    global _MODELO_CLIP, _PROCESADOR_CLIP
    if _MODELO_CLIP is None or _PROCESADOR_CLIP is None:
        _MODELO_CLIP = CLIPModel.from_pretrained(MODEL_ID)
        _PROCESADOR_CLIP = CLIPProcessor.from_pretrained(MODEL_ID)
        _MODELO_CLIP.eval()
    return _MODELO_CLIP, _PROCESADOR_CLIP


def _parsear_vector(texto_vector):
    try:
        return np.array(json.loads(texto_vector), dtype=np.float32)
    except Exception:
        return np.array(ast.literal_eval(texto_vector), dtype=np.float32)


def _obtener_indice_vectores():
    """Construye o reutiliza en RAM la matriz (N, 512) de prendas vectorizadas."""
    qs = (
        FotoArmario.objects.exclude(vector_caracteristicas__isnull=True)
        .exclude(vector_caracteristicas="")
        .only("id", "nombre", "categoria", "imagen", "propietario_id", "vector_caracteristicas")
    )
    firma_actual = (qs.count(), qs.order_by("-id").values_list("id", flat=True).first())

    if _CACHE_VECTORES["firma"] == firma_actual and _CACHE_VECTORES["matriz"] is not None:
        return _CACHE_VECTORES["matriz"], _CACHE_VECTORES["metadatos"]

    vectores = []
    metadatos = []
    vistos = set()

    for prenda in qs:
        if prenda.vector_caracteristicas in vistos:
            continue
        try:
            vec = _parsear_vector(prenda.vector_caracteristicas)
            if vec.ndim != 1 or vec.size == 0:
                continue
            vistos.add(prenda.vector_caracteristicas)
            vectores.append(vec)
            metadatos.append(
                {
                    "id": prenda.id,
                    "nombre": prenda.nombre or f"Prenda #{prenda.id}",
                    "categoria_codigo": prenda.categoria or "",
                    "categoria": prenda.get_categoria_display() if prenda.categoria else "Sin categoría",
                    "imagen_url": f"/prenda/{prenda.id}/imagen/" if prenda.propietario_id else prenda.imagen.url,
                    "propietario_id": prenda.propietario_id,
                }
            )
        except Exception:
            continue

    matriz = np.vstack(vectores) if vectores else np.empty((0, 512), dtype=np.float32)
    _CACHE_VECTORES["firma"] = firma_actual
    _CACHE_VECTORES["matriz"] = matriz
    _CACHE_VECTORES["metadatos"] = metadatos
    return matriz, metadatos


def cargar_imagen_segura(fuente_imagen):
    """Abre y valida una imagen desde archivo subido o URL directa."""
    if isinstance(fuente_imagen, str) and fuente_imagen.startswith(("http://", "https://")):
        req = urllib.request.Request(
            fuente_imagen,
            headers={"User-Agent": "Mozilla/5.0 StyleMatchAI/1.0"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            contenido = resp.read(10 * 1024 * 1024 + 1)
            if len(contenido) > 10 * 1024 * 1024:
                raise ValueError("La imagen enlazada supera el limite de 10 MB.")
            buffer = io.BytesIO(contenido)
            imagen = Image.open(buffer).convert("RGB")
            return imagen

    imagen = Image.open(fuente_imagen).convert("RGB")
    return imagen


def extraer_vector_imagen(fuente_imagen):
    modelo, procesador = _obtener_modelo()
    imagen = cargar_imagen_segura(fuente_imagen)
    inputs = procesador(images=imagen, return_tensors="pt")
    with torch.no_grad():
        outputs = modelo.get_image_features(pixel_values=inputs["pixel_values"])
        features = outputs.pooler_output if hasattr(outputs, "pooler_output") else outputs
    features = features / features.norm(p=2, dim=-1, keepdim=True)
    return features.cpu().numpy().flatten().astype(np.float32)


def buscar_top_3_similares(fuente_imagen, usuario=None, categoria="", orden="desc", devolver_metricas=False):
    inicio = time.perf_counter()
    vec_consulta = extraer_vector_imagen(fuente_imagen)
    matriz, metadatos = _obtener_indice_vectores()

    if matriz.shape[0] == 0:
        tiempo_ms = round((time.perf_counter() - inicio) * 1000, 1)
        return ([], tiempo_ms) if devolver_metricas else []

    # Una sola multiplicacion matricial vectorizada (mucho mas rapida que bucle for)
    similitudes = matriz @ vec_consulta

    categorias_validas = {codigo for codigo, _ in FotoArmario.CATEGORIAS}
    resultados = []

    for idx, meta in enumerate(metadatos):
        # Evitar mostrar prendas privadas de otros usuarios distintos al actual
        if meta["propietario_id"] and (not usuario or meta["propietario_id"] != usuario.id):
            continue

        if categoria in categorias_validas and meta["categoria_codigo"] != categoria:
            continue
        if categoria == "sin_categoria" and meta["categoria_codigo"] != "":
            continue

        porcentaje = max(0.0, min(100.0, round(float(similitudes[idx]) * 100, 1)))
        resultados.append(
            {
                "id": meta["id"],
                "nombre": meta["nombre"],
                "categoria": meta["categoria"],
                "imagen_url": meta["imagen_url"],
                "porcentaje": porcentaje,
            }
        )

    # Extraer siempre las 3 mejores coincidencias primero y luego ordenarlas
    resultados.sort(key=lambda x: x["porcentaje"], reverse=True)
    top_3 = resultados[:3]

    if orden == "asc":
        top_3.sort(key=lambda x: x["porcentaje"], reverse=False)

    tiempo_ms = round((time.perf_counter() - inicio) * 1000, 1)
    return (top_3, tiempo_ms) if devolver_metricas else top_3
