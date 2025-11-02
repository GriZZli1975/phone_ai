import { useState, useEffect } from 'react'
import { ChartBarIcon, UsersIcon, PhoneIcon, Cog6ToothIcon } from '@heroicons/react/24/outline'

export default function AdminPanel() {
  const [stats, setStats] = useState({
    total_calls: 0,
    ai_handled: 0,
    ai_handled_percent: 0,
    active_calls: 0,
    avg_duration: 0
  })
  
  const [operators, setOperators] = useState([])
  const [routingRules, setRoutingRules] = useState([])

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      // Загрузка статистики
      const statsRes = await fetch('/api/admin/stats')
      const statsData = await statsRes.json()
      setStats(statsData)
      
      // Загрузка операторов
      const opsRes = await fetch('/api/admin/operators')
      const opsData = await opsRes.json()
      setOperators(opsData.operators)
      
      // Загрузка правил
      const rulesRes = await fetch('/api/admin/routing-rules')
      const rulesData = await rulesRes.json()
      setRoutingRules(rulesData.rules)
    } catch (error) {
      console.error('Error loading data:', error)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        
        {/* Заголовок */}
        <h1 className="text-3xl font-bold text-gray-900 mb-8">
          🎛️ Админ Панель
        </h1>

        {/* Статистика */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <PhoneIcon className="h-10 w-10 text-blue-500" />
              <div className="ml-4">
                <p className="text-sm text-gray-500">Всего звонков</p>
                <p className="text-2xl font-bold text-gray-900">{stats.total_calls}</p>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <ChartBarIcon className="h-10 w-10 text-green-500" />
              <div className="ml-4">
                <p className="text-sm text-gray-500">AI обработано</p>
                <p className="text-2xl font-bold text-gray-900">
                  {stats.ai_handled_percent.toFixed(1)}%
                </p>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <UsersIcon className="h-10 w-10 text-purple-500" />
              <div className="ml-4">
                <p className="text-sm text-gray-500">Активных звонков</p>
                <p className="text-2xl font-bold text-gray-900">{stats.active_calls}</p>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <Cog6ToothIcon className="h-10 w-10 text-orange-500" />
              <div className="ml-4">
                <p className="text-sm text-gray-500">Средняя длительность</p>
                <p className="text-2xl font-bold text-gray-900">
                  {Math.floor(stats.avg_duration / 60)}:{(stats.avg_duration % 60).toString().padStart(2, '0')}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Операторы */}
        <div className="bg-white rounded-lg shadow mb-8">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">👥 Операторы</h2>
          </div>
          <div className="p-6">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead>
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Имя</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Отдел</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Статус</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Звонок</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {operators.map((op: any) => (
                    <tr key={op.id}>
                      <td className="px-6 py-4 whitespace-nowrap">{op.name}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{op.email}</td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">
                          {op.department}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                          op.is_available ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                        }`}>
                          {op.is_available ? 'Доступен' : 'Занят'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        {op.current_call_uuid ? (
                          <span className="text-red-600">На линии</span>
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Правила маршрутизации */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">🔀 Правила маршрутизации AI</h2>
          </div>
          <div className="p-6">
            <div className="space-y-4">
              {routingRules.map((rule: any) => (
                <div key={rule.id} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-lg font-medium text-gray-900">{rule.name}</h3>
                    <span className="px-3 py-1 text-sm font-medium rounded-full bg-purple-100 text-purple-800">
                      → {rule.route_to}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {rule.keywords.map((keyword: string, idx: number) => (
                      <span key={idx} className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded">
                        {keyword}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

