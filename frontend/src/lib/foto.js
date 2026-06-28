const MAX_BYTES = 100 * 1024;

function cargarImagen(file) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = URL.createObjectURL(file);
  });
}

export async function comprimirFoto(file, maxBytes = MAX_BYTES) {
  if (!file) return null;

  const img = await cargarImagen(file);
  const canvas = document.createElement('canvas');
  const maxLado = 1280;
  const escala = Math.min(1, maxLado / Math.max(img.width, img.height));
  canvas.width = Math.max(1, Math.round(img.width * escala));
  canvas.height = Math.max(1, Math.round(img.height * escala));

  const ctx = canvas.getContext('2d', { alpha: false });
  ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

  let calidad = 0.78;
  let blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', calidad));

  while (blob && blob.size > maxBytes && calidad > 0.35) {
    calidad -= 0.08;
    blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', calidad));
  }

  URL.revokeObjectURL(img.src);
  return blob;
}
