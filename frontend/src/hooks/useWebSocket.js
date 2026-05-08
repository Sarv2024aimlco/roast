import { useEffect, useRef, useState, useCallback } from 'react'
import { createWebSocket, getSessionState } from '../lib/api'

export function useWebSocket(sessionId) {
  const [sections, setSections] = useState({})
  const [status, setStatus] = useState('connecting') // connecting | streaming | complete | error
  const [error, setError] = useState(null)
  const wsRef = useRef(null)
  const pollRef = useRef(null)
  const missedPings = useRef(0)

  const addSection = useCallback((section, result) => {
    setSections(prev => ({ ...prev, [section]: result }))
  }, [])

  const startPolling = useCallback(() => {
    if (pollRef.current) return
    pollRef.current = setInterval(async () => {
      try {
        const state = await getSessionState(sessionId)
        // Restore completed sections
        Object.entries(state.results || {}).forEach(([section, result]) => {
          addSection(section, result)
        })
        if (state.status === 'completed') {
          setStatus('complete')
          clearInterval(pollRef.current)
          pollRef.current = null
        }
      } catch (e) {
        // ignore polling errors
      }
    }, 5000)
  }, [sessionId, addSection])

  useEffect(() => {
    if (!sessionId) return

    const connect = () => {
      const ws = createWebSocket(sessionId)
      wsRef.current = ws

      ws.onopen = () => {
        setStatus('streaming')
        missedPings.current = 0
        if (pollRef.current) {
          clearInterval(pollRef.current)
          pollRef.current = null
        }
      }

      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data)

          if (msg.event === 'ping') {
            ws.send('pong')
            missedPings.current = 0
            return
          }

          if (msg.event === 'section_complete') {
            addSection(msg.data.section, msg.data.result)
          }

          if (msg.event === 'complete') {
            setStatus('complete')
          }

          if (msg.event === 'error') {
            setError(msg.data.message)
            setStatus('error')
          }
        } catch (e) {
          // ignore parse errors
        }
      }

      ws.onclose = () => {
        // Start polling on disconnect
        startPolling()
      }

      ws.onerror = () => {
        startPolling()
      }
    }

    connect()

    // Heartbeat monitor — if 3 pings missed, switch to polling
    // Only start monitoring after connection is established
    const heartbeatCheck = setInterval(() => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        missedPings.current += 1
        if (missedPings.current >= 3) {
          startPolling()
        }
      }
    }, 15000) // check every 15s, not 10s

    return () => {
      clearInterval(heartbeatCheck)
      if (pollRef.current) clearInterval(pollRef.current)
      if (wsRef.current) wsRef.current.close()
    }
  }, [sessionId, addSection, startPolling])

  return { sections, status, error }
}
