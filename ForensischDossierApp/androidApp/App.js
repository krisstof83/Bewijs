import React, { useState } from 'react'
import { SafeAreaView, Button, Text, ScrollView } from 'react-native'
import RNFS from 'react-native-fs'
import DocumentPicker from 'react-native-document-picker'

export default function App() {
  const [files, setFiles] = useState([])

  async function scan() {
    const docs = await RNFS.readDir(RNFS.DownloadDirectoryPath)
    const pdfs = docs.filter(f => f.name.endsWith('.pdf'))
    setFiles(pdfs)
  }

  return (
    <SafeAreaView>
      <Button title="Scan PDF's" onPress={scan} />
      <ScrollView>
        {files.map(f => <Text key={f.path}>{f.name}</Text>)}
      </ScrollView>
    </SafeAreaView>
  )
}