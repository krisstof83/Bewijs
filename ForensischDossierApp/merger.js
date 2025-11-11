const fs = require('fs')
const { PDFDocument } = require('pdf-lib')

async function merge(files) {
  const merged = await PDFDocument.create()
  for (const file of files) {
    const pdf = await PDFDocument.load(fs.readFileSync(file))
    const copiedPages = await merged.copyPages(pdf, pdf.getPageIndices())
    copiedPages.forEach(p => merged.addPage(p))
  }
  const out = await merged.save()
  fs.writeFileSync('MasterDossier.pdf', out)
  console.log('✅ MasterDossier.pdf aangemaakt')
}

module.exports = merge