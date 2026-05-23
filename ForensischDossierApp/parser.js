const fs = require('fs');
const pdf = require('pdf-parse');
const Tesseract = require('tesseract.js');
const imageType = require('image-type');

async function parsePDF(file) {
  const buffer = fs.readFileSync(file);
  // Support both ES module default export and CommonJS export of image-type
  const typeFn = typeof imageType === 'function' ? imageType : imageType.default;
  const type = await typeFn(buffer);

  if (type && (type.ext === 'png' || type.ext === 'jpg' || type.ext === 'jpeg')) {
    // It's an image, use OCR
    const result = await Tesseract.recognize(buffer, 'nld');
    return result.data.text;
  } else {
    // Assume it's a PDF
    try {
      const data = await pdf(buffer);
      if (data.text.trim().length > 50) {
        return data.text;
      }
    } catch (e) {
      // Ignore PDF parse errors and fall back to OCR
    }

    // OCR fallback for scanned PDF (or PDF with no text)
    const result = await Tesseract.recognize(buffer, 'nld');
    return result.data.text;
  }
}

module.exports = parsePDF;
