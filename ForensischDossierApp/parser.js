const fs = require('fs');
const pdf = require('pdf-parse');
const Tesseract = require('tesseract.js');
const imageType = require('image-type');

let sharedWorkerPromise = null;

// Lazy initialize the Tesseract worker to avoid blocking and reuse the instance.
async function getWorker() {
  if (!sharedWorkerPromise) {
    sharedWorkerPromise = Tesseract.createWorker('nld');
  }
  return sharedWorkerPromise;
}

async function parsePDF(file) {
  const buffer = fs.readFileSync(file);
  const type = imageType(buffer);

  if (type && (type.ext === 'png' || type.ext === 'jpg' || type.ext === 'jpeg')) {
    // It's an image, use OCR
    const worker = await getWorker();
    const result = await worker.recognize(buffer);
    return result.data.text;
  } else {
    // Assume it's a PDF
    const data = await pdf(buffer);
    if (data.text.trim().length > 50) {
      return data.text;
    } else {
      // OCR fallback for scanned PDF (or PDF with no text)
      const worker = await getWorker();
      const result = await worker.recognize(buffer);
      return result.data.text;
    }
  }
}

module.exports = parsePDF;
