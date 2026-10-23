# AutoTest DPRH — Frontend

SPA construida con **React 19**, **TypeScript**, **Vite** y
**Tailwind CSS v4**.

## Estructura

```
src/
├── pages/       # Pantallas completas (se renderizan desde routes/)
├── layouts/     # Estructuras compartidas (sidebar + header, etc.) — Fase 4+
├── routes/      # Definicion de rutas (React Router) — Fase 3+
├── features/    # Un modulo por dominio: auth, evaluados, empresas,
│                  evaluaciones, aplicaciones, resultados, reportes,
│                  usuarios, configuracion (se llenan progresivamente)
├── services/    # Clientes HTTP (Axios)
├── hooks/       # Hooks reutilizables
├── contexts/    # Estado global (auth, tema, etc.)
├── types/       # Tipos TypeScript compartidos
└── utils/       # Utilidades puras
```

## Requisitos

- Node.js 20+

## Instalacion

```bash
npm install
```

## Ejecutar en desarrollo

```bash
npm run dev
```

Disponible en `http://localhost:5173`. Las peticiones a `/api` se
redirigen automaticamente al backend FastAPI en `http://localhost:8000`
(configurado en `vite.config.ts`).

## Verificar tipos

```bash
npx tsc --noEmit
```

## Compilar para produccion

```bash
npm run build
```

## Fase 1

La pantalla inicial (`src/pages/ConnectionCheckPage.tsx`) solo
verifica la conexion con el backend a traves de `GET /api/health`.
Sera reemplazada por el flujo de autenticacion en la Fase 3.

## Convenciones

- No colocar logica de negocio en componentes de UI: debe vivir en
  `features/<modulo>/` o `services/`.
- Cada modulo de `features/` es responsable de sus propios
  componentes, hooks y llamadas a la API relacionadas con ese
  dominio.
