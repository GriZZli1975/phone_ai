import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import LoginPage from './pages/LoginPage'
import OperatorDashboard from './pages/OperatorDashboard'
import AdminPanel from './pages/AdminPanel'
import CallHistory from './pages/CallHistory'
import Layout from './components/Layout'

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Проверка токена
    const token = localStorage.getItem('token')
    if (token) {
      // TODO: валидация токена
      setIsAuthenticated(true)
    }
    setLoading(false)
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <div className="text-xl text-gray-600">Загрузка...</div>
      </div>
    )
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={
          isAuthenticated ? <Navigate to="/operator" /> : <LoginPage onLogin={() => setIsAuthenticated(true)} />
        } />
        
        <Route element={<Layout />}>
          <Route path="/operator" element={
            isAuthenticated ? <OperatorDashboard /> : <Navigate to="/login" />
          } />
          
          <Route path="/admin" element={
            isAuthenticated ? <AdminPanel /> : <Navigate to="/login" />
          } />
          
          <Route path="/history" element={
            isAuthenticated ? <CallHistory /> : <Navigate to="/login" />
          } />
        </Route>
        
        <Route path="/" element={<Navigate to="/operator" />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App

