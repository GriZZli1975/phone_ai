import { useState, useEffect, useRef } from 'react'
import { PhoneIcon, MicrophoneIcon, SpeakerWaveIcon } from '@heroicons/react/24/solid'

interface Suggestion {
  type: 'suggestion' | 'transcript' | 'alert'
  mode?: 'text' | 'audio' | 'hybrid'
  priority?: 'normal' | 'critical'
  text?: string
  audio_url?: string
  speaker?: string
  timestamp: string
}

export default function OperatorDashboard() {
  const [activeCall, setActiveCall] = useState<any>(null)
  const [supervisorMode, setSupervisorMode] = useState<'text' | 'audio' | 'hybrid'>('hybrid')
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [transcript, setTranscript] = useState<any[]>([])
  const [audioEnabled, setAudioEnabled] = useState(true)
  
  const wsRef = useRef<WebSocket | null>(null)
  const audioRef = useRef<HTMLAudioElement>(null)

  useEffect(() => {
    // Подключение к WebSocket когда есть активный звонок
    if (activeCall) {
      connectWebSocket(activeCall.uuid)
    }
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [activeCall])

  const connectWebSocket = (callId: string) => {
    const wsUrl = `${import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'}/supervisor/${callId}`
    wsRef.current = new WebSocket(wsUrl)
    
    wsRef.current.onopen = () => {
      console.log('WebSocket connected')
      // Отправляем текущий режим
      wsRef.current?.send(JSON.stringify({
        action: 'change_mode',
        mode: supervisorMode
      }))
    }
    
    wsRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data)
      handleWebSocketMessage(data)
    }
    
    wsRef.current.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
    
    wsRef.current.onclose = () => {
      console.log('WebSocket closed')
    }
  }

  const handleWebSocketMessage = (data: Suggestion) => {
    console.log('Received:', data)
    
    switch (data.type) {
      case 'suggestion':
        // Добавляем подсказку
        setSuggestions(prev => [...prev, data])
        
        // Если есть аудио и включен звук
        if (data.audio_url && audioEnabled && (data.mode === 'audio' || data.mode === 'hybrid')) {
          playAudioSuggestion(data.audio_url)
        }
        
        // Показываем уведомление для критичных
        if (data.priority === 'critical') {
          showNotification(data.text || 'Критичная подсказка!')
        }
        break
        
      case 'transcript':
        // Обновляем транскрипцию
        setTranscript(prev => [...prev, {
          speaker: data.speaker,
          text: data.text,
          timestamp: data.timestamp
        }])
        break
        
      case 'alert':
        // Показываем алерт
        showNotification(data.text || 'Внимание!')
        break
    }
  }

  const playAudioSuggestion = (audioUrl: string) => {
    if (audioRef.current) {
      audioRef.current.src = audioUrl
      audioRef.current.play().catch(err => {
        console.error('Audio play error:', err)
      })
    }
  }

  const showNotification = (message: string) => {
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification('AI Суфлер', { body: message })
    }
  }

  const changeSupervisorMode = (mode: 'text' | 'audio' | 'hybrid') => {
    setSupervisorMode(mode)
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        action: 'change_mode',
        mode: mode
      }))
    }
  }

  // Демо данные для активного звонка
  useEffect(() => {
    // Симуляция активного звонка
    setActiveCall({
      uuid: 'demo-call-123',
      caller_number: '+7 926 123-45-67',
      duration: 145
    })
  }, [])

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Скрытый audio элемент для проигрывания подсказок */}
      <audio ref={audioRef} className="hidden" />
      
      {/* Хедер */}
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-900">
              🎧 AI Суфлер - Dashboard Оператора
            </h1>
            
            {activeCall && (
              <div className="flex items-center space-x-4">
                <span className="flex items-center">
                  <PhoneIcon className="h-5 w-5 text-green-500 mr-2 animate-pulse" />
                  <span className="text-sm text-gray-600">Звонок активен</span>
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Левая колонка - Информация о звонке */}
          <div className="lg:col-span-1 space-y-6">
            
            {/* Информация о клиенте */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                📞 Активный звонок
              </h2>
              
              {activeCall ? (
                <div className="space-y-3">
                  <div>
                    <span className="text-sm text-gray-500">Номер:</span>
                    <p className="text-lg font-medium">{activeCall.caller_number}</p>
                  </div>
                  <div>
                    <span className="text-sm text-gray-500">Длительность:</span>
                    <p className="text-lg font-medium">
                      {Math.floor(activeCall.duration / 60)}:{(activeCall.duration % 60).toString().padStart(2, '0')}
                    </p>
                  </div>
                  <div>
                    <span className="text-sm text-gray-500">История клиента:</span>
                    <p className="text-sm">Предыдущих звонков: 3</p>
                    <p className="text-sm">Категория: VIP</p>
                  </div>
                </div>
              ) : (
                <p className="text-gray-500">Нет активных звонков</p>
              )}
            </div>

            {/* Настройки суфлера */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                ⚙️ Режим суфлера
              </h2>
              
              <div className="space-y-2">
                <button
                  onClick={() => changeSupervisorMode('text')}
                  className={`w-full flex items-center justify-between px-4 py-3 rounded-lg border-2 transition ${
                    supervisorMode === 'text'
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <span className="font-medium">📝 Только текст</span>
                  {supervisorMode === 'text' && <span className="text-blue-500">✓</span>}
                </button>
                
                <button
                  onClick={() => changeSupervisorMode('audio')}
                  className={`w-full flex items-center justify-between px-4 py-3 rounded-lg border-2 transition ${
                    supervisorMode === 'audio'
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <span className="font-medium">🎧 Только аудио</span>
                  {supervisorMode === 'audio' && <span className="text-blue-500">✓</span>}
                </button>
                
                <button
                  onClick={() => changeSupervisorMode('hybrid')}
                  className={`w-full flex items-center justify-between px-4 py-3 rounded-lg border-2 transition ${
                    supervisorMode === 'hybrid'
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <span className="font-medium">🔀 Гибрид (текст + аудио)</span>
                  {supervisorMode === 'hybrid' && <span className="text-blue-500">✓</span>}
                </button>
              </div>
              
              <div className="mt-4 pt-4 border-t">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={audioEnabled}
                    onChange={(e) => setAudioEnabled(e.target.checked)}
                    className="rounded"
                  />
                  <span className="ml-2 text-sm">Включить аудио подсказки</span>
                </label>
              </div>
            </div>
          </div>

          {/* Центральная колонка - Транскрипция и подсказки */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* Транскрипция разговора */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                💬 Разговор в реальном времени
              </h2>
              
              <div className="space-y-3 max-h-64 overflow-y-auto">
                {transcript.length > 0 ? (
                  transcript.map((msg, idx) => (
                    <div key={idx} className={`flex ${msg.speaker === 'client' ? 'justify-start' : 'justify-end'}`}>
                      <div className={`max-w-xs px-4 py-2 rounded-lg ${
                        msg.speaker === 'client'
                          ? 'bg-gray-100 text-gray-900'
                          : 'bg-blue-500 text-white'
                      }`}>
                        <p className="text-sm font-medium mb-1">
                          {msg.speaker === 'client' ? '👤 Клиент' : '👨‍💼 Вы'}
                        </p>
                        <p>{msg.text}</p>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-center text-gray-500 py-8">
                    Ожидание разговора...
                  </p>
                )}
              </div>
            </div>

            {/* AI Подсказки */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                🤖 AI Подсказки
              </h2>
              
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {suggestions.length > 0 ? (
                  suggestions.map((suggestion, idx) => (
                    <div
                      key={idx}
                      className={`p-4 rounded-lg border-l-4 ${
                        suggestion.priority === 'critical'
                          ? 'bg-red-50 border-red-500'
                          : 'bg-blue-50 border-blue-500'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          {suggestion.priority === 'critical' && (
                            <span className="inline-block px-2 py-1 text-xs font-semibold text-red-700 bg-red-200 rounded mb-2">
                              ⚠️ ВАЖНО
                            </span>
                          )}
                          <p className="text-gray-900">{suggestion.text}</p>
                          {suggestion.audio_url && (
                            <div className="mt-2 flex items-center text-sm text-gray-600">
                              <SpeakerWaveIcon className="h-4 w-4 mr-1" />
                              <span>Аудио подсказка</span>
                            </div>
                          )}
                        </div>
                        <span className="text-xs text-gray-500 ml-4">
                          {new Date(suggestion.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-center text-gray-500 py-8">
                    Подсказки появятся во время разговора
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

