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


def buscar_top_3_similares(archivo_imagen, usuario=None):
    vec_consulta = extraer_vector_imagen(archivo_imagen)

    # Busca prendas con vector del usuario actual; si no tiene, usa el dataset vectorizado
    candidatas = FotoArmario.objects.exclude(
        vector_caracteristicas__isnull=True
    ).exclude(vector_caracteristicas="")

    if usuario and usuario.is_authenticated:
        propias = candidatas.filter(propietario=usuario)
        if propias.exists():
            candidatas = propias

    resultados = []
    for prenda in candidatas:
        try:
            vec_prenda = np.array(
                ast.literal_eval(prenda.vector_caracteristicas),
                dtype=np.float32,
            )
            if vec_prenda.shape != vec_consulta.shape:
                continue
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

    resultados.sort(key=lambda x: x["porcentaje"], reverse=True)
    return resultados[:3]
