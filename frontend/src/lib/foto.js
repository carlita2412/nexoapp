export const FOTO_OBJETIVO_BYTES = 100 * 1024;
export const FOTO_MAX_ENTRADA_BYTES = 12 * 1024 * 1024;
export const FOTO_TIPOS_PERMITIDOS = new Set(['image/jpeg', 'image/png', 'image/webp']);

function cargarImagen(file) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error('No se pudo leer la imagen seleccionada.'));
    img.src = URL.createObjectURL(file);
  });
}

function blobDesdeCanvas(canvas, calidad) {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error('No se pudo comprimir la foto.'))),
      'image/jpeg',
      calidad,
    );
  });
}

function validarFoto(file) {
  if (!file) return;
  if (!FOTO_TIPOS_PERMITIDOS.has(file.type)) {
    throw new Error('Tipo de foto inválido. Usa JPG, PNG o WebP.');
  }
  if (file.size > FOTO_MAX_ENTRADA_BYTES) {
    throw new Error('La foto es demasiado grande para procesarla en este teléfono. Toma otra foto o reduce la resolución.');
  }
}

export function kb(bytes) {
  return Math.round((bytes || 0) / 1024);
}

export async function comprimirFoto(file, maxBytes = FOTO_OBJETIVO_BYTES) {
  if (!file) return null;
  validarFoto(file);

  const img = await cargarImagen(file);
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d', { alpha: false });
  const maxLados = [1280, 1024, 900, 768, 640, 520];
  const calidades = [0.78, 0.68, 0.58, 0.5, 0.42, 0.35, 0.3];

  let mejorBlob = null;

  try {
    for (const maxLado of maxLados) {
      const escala = Math.min(1, maxLado / Math.max(img.width, img.height));
      canvas.width = Math.max(1, Math.round(img.width * escala));
      canvas.height = Math.max(1, Math.round(img.height * escala));
      ctx.fillStyle = '#fff';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

      for (const calidad of calidades) {
        const blob = await blobDesdeCanvas(canvas, calidad);
        mejorBlob = !mejorBlob || blob.size < mejorBlob.size ? blob : mejorBlob;
        if (blob.size <= maxBytes) {
          return new File([blob], 'entrega.jpg', { type: 'image/jpeg', lastModified: Date.now() });
        }
      }
    }
  } finally {
    URL.revokeObjectURL(img.src);
  }

  if (mejorBlob && mejorBlob.size <= Math.round(maxBytes * 1.15)) {
    return new File([mejorBlob], 'entrega.jpg', { type: 'image/jpeg', lastModified: Date.now() });
  }

  throw new Error(`Foto muy grande: comprimida queda en ${kb(mejorBlob?.size)} KB. El objetivo es 100 KB.`);
}
