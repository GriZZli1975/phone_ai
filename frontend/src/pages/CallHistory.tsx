import { useState, useEffect } from 'react'
import { format } from 'date-fns'
import { ru } from 'date-fns/locale'

export default function CallHistory() {
  const [calls, setCalls] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadCalls()
  }, [])

  const loadCalls = async () => {
    try {
      const response = await fetch('/api/calls')
      const data = await response.json()
      setCalls(data.calls)
    } catch (error) {
      console.error('Error loading calls:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="p-8 text-center">Загрузка...</div>
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        
        <h1 className="text-3xl font-bold text-gray-900 mb-8">
          📋 История звонков
        </h1>

        <div className="bg-white rounded-lg shadow">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Время</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Номер</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Направление</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Длительность</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">AI Обработка</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Маршрут</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Статус</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Действия</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {calls.map((call: any) => (
                  <tr key={call.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {call.start_time ? format(new Date(call.start_time), 'dd MMM HH:mm', { locale: ru }) : '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {call.caller_number}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        call.direction === 'inbound' 
                          ? 'bg-blue-100 text-blue-800' 
                          : 'bg-green-100 text-green-800'
                      }`}>
                        {call.direction === 'inbound' ? '📥 Входящий' : '📤 Исходящий'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {call.duration ? `${Math.floor(call.duration / 60)}:${(call.duration % 60).toString().padStart(2, '0')}` : '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {call.ai_handled ? (
                        <span className="text-green-600">✓ Да</span>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {call.ai_routed_to ? (
                        <span className="px-2 py-1 bg-purple-100 text-purple-800 rounded text-xs">
                          {call.ai_routed_to}
                        </span>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        call.status === 'completed' 
                          ? 'bg-green-100 text-green-800' 
                          : call.status === 'active'
                          ? 'bg-yellow-100 text-yellow-800'
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {call.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <button className="text-blue-600 hover:text-blue-900 mr-3">
                        Детали
                      </button>
                      <button className="text-blue-600 hover:text-blue-900">
                        Запись
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          
          {calls.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              Звонков пока нет
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

