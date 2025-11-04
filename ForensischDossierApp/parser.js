const fs = require('fs');
const pdf = require('pdf-parse');
const Tesseract = require('tesseract.js');
const imageType = require('image-type');

async function parsePDF(file) {
  const buffer = fs.readFileSync(file);
  const type = imageType(buffer);

  if (type && (type.ext === 'png' || type.ext === 'jpg' || type.ext === 'jpeg')) {
    // It's an image, use OCR
    const result = await Tesseract.recognize(buffer, 'nld');
    return result.data.text;
  } else {
    // Assume it's a PDF
    const data = await pdf(buffer);
    if (data.text.trim().length > 50) {
      return data.text;
    } else {
      // OCR fallback for scanned PDF (or PDF with no text)
      const result = await Tesseract.recognize(buffer, 'nld');
      return result.data.text;
    }
  }
}

module.exports = parsePDF;
