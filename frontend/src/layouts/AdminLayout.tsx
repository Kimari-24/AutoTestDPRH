import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

interface NavItem {
  to: string
  label: string
  icon: string
}

const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: '⬛' },
  { to: '/evaluados', label: 'Evaluados', icon: '☰' },
  { to: '/empresas', label: 'Empresas', icon: '⌂' },
  { to: '/evaluaciones', label: 'Evaluaciones', icon: '◈' },
]

/**
 * Estructura visual del panel administrativo (sección 14 de los
 * requisitos): sidebar + header + contenido. Las pantallas de cada
 * módulo se renderizan dentro vía <Outlet /> (React Router).
 */
export default function AdminLayout() {
  const { usuario, logout } = useAuth()

  return (
    <div className="min-h-screen flex bg-dprh-bg">
      <aside className="w-64 shrink-0 bg-dprh-guinda text-white flex flex-col">
        <div className="px-6 py-5 border-b border-white/10">
          <div className="text-lg font-semibold leading-tight">AutoTest</div>
          <div className="text-sm text-white/70">DPRH</div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive ? 'bg-white/15 text-white' : 'text-white/80 hover:bg-white/10'
                }`
              }
            >
              <span aria-hidden>{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="px-3 py-4 border-t border-white/10 text-xs text-white/50">
          Fase 4 · Panel administrador
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 shrink-0 bg-white border-b border-dprh-gray flex items-center justify-end gap-4 px-6">
          {usuario && (
            <>
              <div className="text-right leading-tight">
                <div className="text-sm font-medium text-gray-800">
                  {usuario.nombre} {usuario.apellidos}
                </div>
                <div className="text-xs text-gray-500">{usuario.roles.join(', ')}</div>
              </div>
              <div className="h-9 w-9 rounded-full bg-dprh-azul text-white flex items-center justify-center text-sm font-semibold">
                {usuario.nombre.charAt(0).toUpperCase()}
              </div>
              <button
                onClick={logout}
                className="text-sm font-medium text-dprh-guinda hover:underline"
              >
                Cerrar sesión
              </button>
            </>
          )}
        </header>

        <main className="flex-1 p-6 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
