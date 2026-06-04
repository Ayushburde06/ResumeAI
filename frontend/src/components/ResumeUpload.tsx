import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { UploadCloud, FileText, X } from 'lucide-react'

interface Props {
  file: File | null
  onChange: (file: File | null) => void
}

export default function ResumeUpload({ file, onChange }: Props) {
  const onDrop = useCallback(
    (accepted: File[]) => { if (accepted[0]) onChange(accepted[0]) },
    [onChange]
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    },
    maxSize: 10 * 1024 * 1024,
    multiple: false,
  })

  if (file) {
    return (
      <div className="flex items-center gap-3 p-4 bg-brand-50 border border-brand-200 rounded-xl">
        <div className="flex-shrink-0 w-10 h-10 bg-brand-100 rounded-lg flex items-center justify-center">
          <FileText className="w-5 h-5 text-brand-600" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-medium text-gray-900 truncate">{file.name}</p>
          <p className="text-sm text-gray-500">{(file.size / 1024).toFixed(0)} KB</p>
        </div>
        <button
          onClick={() => onChange(null)}
          className="flex-shrink-0 p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
          aria-label="Remove file"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    )
  }

  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-150
        ${isDragActive
          ? 'border-brand-500 bg-brand-50 scale-[1.01]'
          : 'border-gray-200 hover:border-brand-400 hover:bg-brand-50/40'
        }`}
    >
      <input {...getInputProps()} />
      <UploadCloud className={`w-10 h-10 mx-auto mb-3 transition-colors ${isDragActive ? 'text-brand-500' : 'text-gray-300'}`} />
      {isDragActive ? (
        <p className="font-medium text-brand-600">Drop your resume here</p>
      ) : (
        <>
          <p className="font-medium text-gray-700">
            Drag & drop your resume, or{' '}
            <span className="text-brand-600 underline underline-offset-2">browse</span>
          </p>
          <p className="text-sm text-gray-400 mt-1">PDF or DOCX · max 10 MB</p>
        </>
      )}
    </div>
  )
}
