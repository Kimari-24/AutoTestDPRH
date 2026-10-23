interface StatCardProps {
  label: string
  value: number
  accent?: 'guinda' | 'azul' | 'dorado'
}

const ACCENTS: Record<NonNullable<StatCardProps['accent']>, string> = {
  guinda: 'text-dprh-guinda',
  azul: 'text-dprh-azul',
  dorado: 'text-dprh-dorado',
}

export default function StatCard({ label, value, accent = 'azul' }: StatCardProps) {
  return (
    <div className="rounded-xl border border-dprh-gray bg-white p-5 shadow-sm">
      <div className="text-sm text-gray-500">{label}</div>
      <div className={`mt-1 text-3xl font-semibold ${ACCENTS[accent]}`}>{value}</div>
    </div>
  )
}
