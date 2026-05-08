import { useState, useRef } from 'react'
import { motion } from 'framer-motion'
import { Upload, FileText, X } from 'lucide-react'

export function DropZone({ onFile }) {
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef()

  const handleFile = (f) => {
    if (!f || f.type !== 'application/pdf') return
    if (f.size > 5 * 1024 * 1024) {
      alert('File too large. Max 5MB.')
      return
    }
    setFile(f)
    onFile(f)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    handleFile(e.dataTransfer.files[0])
  }

  const clear = (e) => {
    e.stopPropagation()
    setFile(null)
    onFile(null)
    inputRef.current.value = ''
  }

  return (
    <motion.div
      animate={file ? {} : {
        borderColor: ['#333', '#f97316', '#333'],
      }}
      transition={{ duration: 2, repeat: Infinity }}
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => !file && inputRef.current.click()}
      className={`
        border-2 rounded-lg p-8 text-center cursor-pointer transition-colors
        ${dragging ? 'border-orange-500 bg-orange-500/5' : 'border-[#333]'}
        ${file ? 'cursor-default' : 'hover:border-orange-500/50'}
      `}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf"
        className="hidden"
        onChange={(e) => handleFile(e.target.files[0])}
      />

      {file ? (
        <div className="flex items-center justify-center gap-3">
          <FileText size={20} className="text-orange-500" />
          <span className="text-sm text-gray-300">{file.name}</span>
          <button onClick={clear} className="text-gray-500 hover:text-gray-300">
            <X size={16} />
          </button>
        </div>
      ) : (
        <div className="space-y-2">
          <Upload size={24} className="mx-auto text-gray-500" />
          <p className="text-sm text-gray-400">Drop your resume PDF here or click to browse</p>
          <p className="text-xs text-gray-600">PDF only · Max 5MB</p>
        </div>
      )}
    </motion.div>
  )
}
