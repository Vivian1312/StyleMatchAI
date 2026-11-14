import ast
import numpy as np
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor
from .models import FotoArmario

_MODELO_CLIP = None
_PROCESADOR_CLIP = None
MODEL_ID = "patrickjohncyh/fashion-clip"


def _obtener_modelo():
    global _MODELO_CLIP, _PROCESADOR_CLIP
    if _MODELO_CLIP is None or _PROCESADOR_CLIP is None:
        _MODELO_CLIP = CLIPModel.from_pretrained(MODEL_ID)
        _PROCESADOR_CLIP = CLIPProcessor.from_pretrained(MODEL_ID)
        _MODELO_CLIP.eval()
    return _MODELO_CLIP, _PROCESADOR_CLIP


def extraer_vector_imagen(archivo_imagen):
    modelo, procesador = _obtener_modelo()
    imagen = Image.open(archivo_imagen).convert("RGB")
    inputs = procesador(images=imagen, return_tensors="pt")
    with torch.no_grad():
        outputs = modelo.get_image_features(pixel_values=inputs["pixel_values"])
        features = outputs.pooler_output if hasattr(outputs, "pooler_output") else outputs
    features = features / features.norm(p=2, dim=-1, keepdim=True)
    return features.cpu().numpy().flatten().astype(np.float32)


def buscar_top_3_similares(archivo_imagen, usuario=None, categoria="", orden="desc"):
    vec_consulta = extraer_vector_imagen(archivo_imagen)

    candidatas = FotoArmario.objects.exclude(
        vector_caracteristicas__isnull=True
    ).exclude(vector_caracteristicas="")

    if usuario and usuario.is_authenticated:
        propias = candidatas.filter(propietario=usuario)
        if propias.exists():
            candidatas = propias

    # 1. Filtrar primero por categoria
    categorias_validas = {codigo for codigo, _ in FotoArmario.CATEGORIAS}
    if categoria in categorias_validas:
        candidatas = candidatas.filter(categoria=categoria)
    elif categoria == "sin_categoria":
        candidatas = candidatas.filter(categoria="")

    # 2. Calcular similitud del coseno descartando vectores identicos duplicados
    resultados = []
    vectores_vistos = set()

    for prenda in candidatas:
        if prenda.vector_caracteristicas in vectores_vistos:
            continue
        try:
            vec_prenda = np.array(
                ast.literal_eval(prenda.vector_caracteristicas),
                dtype=np.float32,
            )
            if vec_prenda.shape != vec_consulta.shape:
                continue
            vectores_vistos.add(prenda.vector_caracteristicas)
            similitud = float(np.dot(vec_consulta, vec_prenda))
            porcentaje = max(0, min(100, round(similitud * 100, 1)))
            resultados.append(
                {
                    "id": prenda.id,
                    "nombre": prenda.nombre or f"Prenda #{prenda.id}",
                    "categoria": prenda.get_categoria_display() if prenda.categoria else "Sin categoría",
                    "imagen_url": f"/prenda/{prenda.id}/imagen/" if prenda.propietario else prenda.imagen.url,
                    "porcentaje": porcentaje,
                }
            )
        except Exception:
            continue

    # 3. Obtener siempre el Top 3 de mayor similitud primero
    resultados.sort(key=lambda x: x["porcentaje"], reverse=True)
    top_3 = resultados[:3]

    # 4. Ordenar ese Top 3 segun la preferencia del usuario (desc o asc)
    if orden == "asc":
        top_3.sort(key=lambda x: x["porcentaje"], reverse=False)

    return top_3
