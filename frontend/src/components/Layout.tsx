import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom'
import { PhoneIcon, ChartBarIcon, ClockIcon, ArrowRightOnRectangleIcon } from '@heroicons/react/24/outline'

export default function Layout() {
  const location = useLocation()
  const navigate = useNavigate()

  const handleLogout = () => {
    localStorage.removeItem('token')
    navigate('/login')
  }

  const navigation = [
    { name: 'Оператор', href: '/operator', icon: PhoneIcon },
    { name: 'Админ панель', href: '/admin', icon: ChartBarIcon },
    { name: 'История', href: '/history', icon: ClockIcon },
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Навигация */}
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <span className="text-2xl font-bold text-blue-600">🤖 AI Call Center</span>
              </div>
              <div className="hidden sm:ml-8 sm:flex sm:space-x-8">
                {navigation.map((item) => {
                  const isActive = location.pathname === item.href
                  const Icon = item.icon
                  return (
                    <Link
                      key={item.name}
                      to={item.href}
                      className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                        isActive
                          ? 'border-blue-500 text-gray-900'
                          : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                      }`}
                    >
                      <Icon className="h-5 w-5 mr-2" />
                      {item.name}
                    </Link>
                  )
                })}
              </div>
            </div>
            <div className="flex items-center">
              <button
                onClick={handleLogout}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
              >
                <ArrowRightOnRectangleIcon className="h-5 w-5 mr-2" />
                Выйти
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Контент */}
      <main>
        <Outlet />
      </main>
    </div>
  )
}

