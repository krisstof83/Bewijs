const fs = require('fs')
const { PDFDocument } = require('pdf-lib')

async function merge(files) {
  const merged = await PDFDocument.create()
  for (const file of files) {
    // Read files as needed. To optimize, avoid unnecessary operations in a tight loop.
    // However, the real bottleneck usually comes from loading the whole PDF byte array into memory if they are large.
    const pdfBytes = fs.readFileSync(file);
    const pdf = await PDFDocument.load(pdfBytes, { ignoreEncryption: true });
    const pageIndices = pdf.getPageIndices();
    if (pageIndices.length > 0) {
      const copiedPages = await merged.copyPages(pdf, pageIndices);
      copiedPages.forEach(p => merged.addPage(p));
    }
  }
  const out = await merged.save()
  fs.writeFileSync('MasterDossier.pdf', out)
  console.log('✅ MasterDossier.pdf aangemaakt')
}

module.exports = merge