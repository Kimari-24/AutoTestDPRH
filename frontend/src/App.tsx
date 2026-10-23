import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import { PortalAuthProvider } from './contexts/PortalAuthContext'
import LoginPage from './features/auth/LoginPage'
import DashboardPage from './features/dashboard/DashboardPage'
import EmpresasPage from './features/empresas/EmpresasPage'
import EvaluacionDetallePage from './features/evaluaciones/EvaluacionDetallePage'
import EvaluacionesPage from './features/evaluaciones/EvaluacionesPage'
import EvaluadosPage from './features/evaluados/EvaluadosPage'
import ExpedienteEvaluadoPage from './features/evaluados/ExpedienteEvaluadoPage'
import AplicarEvaluacionPage from './features/portal/AplicarEvaluacionPage'
import MisEvaluacionesPage from './features/portal/MisEvaluacionesPage'
import PortalLoginPage from './features/portal/PortalLoginPage'
import AdminLayout from './layouts/AdminLayout'
import PortalLayout from './layouts/PortalLayout'
import RequireAuth from './routes/RequireAuth'

/**
 * Raiz de la aplicacion (Fase 7).
 *
 * Dos superficies completamente separadas, cada una con su propio
 * contexto de sesion:
 *  - Panel administrativo (/, /evaluados, /empresas, /evaluaciones...)
 *  - Portal del evaluado (/portal/...), con acceso temporal
 */
function App() {
  return (
    <AuthProvider>
      <PortalAuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />

            <Route
              path="/"
              element={
                <RequireAuth>
                  <AdminLayout />
                </RequireAuth>
              }
            >
              <Route index element={<DashboardPage />} />
              <Route path="evaluados" element={<EvaluadosPage />} />
              <Route path="evaluados/:id" element={<ExpedienteEvaluadoPage />} />
              <Route path="empresas" element={<EmpresasPage />} />
              <Route path="evaluaciones" element={<EvaluacionesPage />} />
              <Route path="evaluaciones/:id" element={<EvaluacionDetallePage />} />
            </Route>

            <Route path="/portal/login" element={<PortalLoginPage />} />
            <Route path="/portal" element={<PortalLayout />}>
              <Route index element={<MisEvaluacionesPage />} />
              <Route path="evaluaciones/:asignacionId" element={<AplicarEvaluacionPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </PortalAuthProvider>
    </AuthProvider>
  )
}

export default App
