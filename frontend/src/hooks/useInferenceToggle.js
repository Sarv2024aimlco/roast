import { useState, useEffect } from 'react'

export function useInferenceToggle() {
  const [showInference, setShowInference] = useState(() => {
    return localStorage.getItem('roast_inference_toggle') !== 'off'
  })

  useEffect(() => {
    localStorage.setItem('roast_inference_toggle', showInference ? 'on' : 'off')
  }, [showInference])

  return [showInference, setShowInference]
}
