const fs = require('fs')
const { google } = require('googleapis')
const SCOPES = ['https://www.googleapis.com/auth/drive.file']

async function authorize(credentials) {
  const { client_secret, client_id, redirect_uris } = credentials.installed
  const oAuth2Client = new google.auth.OAuth2(client_id, client_secret, redirect_uris[0])
  return oAuth2Client
}

async function listPDFs(auth) {
  const drive = google.drive({ version: 'v3', auth })
  const res = await drive.files.list({ q: "mimeType='application/pdf'" })
  return res.data.files
}

module.exports = { authorize, listPDFs }