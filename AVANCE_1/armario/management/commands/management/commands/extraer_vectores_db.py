import os
from django.core.management.base import BaseCommand
from armario.models import FotoArmario
from PIL import Image
import torch
from transformers import CLIPProcessor, CLIPModel

class Command(BaseCommand):
    help = 'Extrae y guarda los vectores de características (embeddings) usando Fashion-CLIP para las prendas del armario.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Cargando el modelo Fashion-CLIP..."))
        
        model_id = "patrickjohncyh/fashion-clip"
        model = CLIPModel.from_pretrained(model_id)
        processor = CLIPProcessor.from_pretrained(model_id)
        model.eval()

        # Obtener todas las fotos registradas en la base de datos de Django
        prendas = FotoArmario.objects.all()
        
        if not prendas.exists():
            self.stdout.write(self.style.WARNING("No hay prendas registradas en la base de datos para procesar."))
            return

        self.stdout.write(f"Se encontraron {prendas.count()} prendas. Iniciando extracción...")

        procesadas = 0
        for prenda in prendas:
            try:
                # Obtener la ruta absoluta del archivo de imagen en el servidor
                image_path = prenda.imagen.path
                
                if not os.path.exists(image_path):
                    self.stdout.write(self.style.ERROR(f"[ERROR] El archivo físico no existe para la prenda ID {prenda.id}"))
                    continue

                image = Image.open(image_path).convert("RGB")
                inputs = processor(images=image, return_tensors="pt")
                
                with torch.no_grad():
                    outputs = model.get_image_features(pixel_values=inputs["pixel_values"])
                    image_features = outputs.pooler_output if hasattr(outputs, "pooler_output") else outputs
                
                # Normalizar el vector
                image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
                vector_np = image_features.cpu().numpy().flatten().tolist()
                
                # Guardar el vector como texto/JSON en el modelo de Django
                prenda.vector_caracteristicas = str(vector_np)
                prenda.save()
                
                procesadas += 1
                self.stdout.write(self.style.SUCCESS(f"[ÉXITO] Vector extraído y guardado para la prenda ID {prenda.id}"))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[ERROR] Falló el procesamiento de la prenda ID {prenda.id}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"\n¡Proceso finalizado! Total de prendas procesadas con éxito: {procesadas}/{prendas.count()}"))
