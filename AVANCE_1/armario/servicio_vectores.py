"""Guarda embeddings visuales en el campo ya existente de FotoArmario."""
import json
from .motor_similitud import extraer_vector_imagen


def vectorizar_prenda(prenda):
    """Calcula el embedding con FashionCLIP y lo guarda como JSON."""
    # storage.open funciona con disco local y otros almacenamientos Django.
    with prenda.imagen.storage.open(prenda.imagen.name, "rb") as archivo:
        vector = extraer_vector_imagen(archivo)
    prenda.vector_caracteristicas = json.dumps(vector.tolist(), separators=(",", ":"))
    prenda.save(update_fields=["vector_caracteristicas"])
    return vector
