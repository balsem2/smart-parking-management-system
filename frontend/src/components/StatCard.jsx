export default function StatCard({ label, value, note, tone = '' }) {
  return <article className={tone}><p>{label}</p><strong>{value}</strong><span>{note}</span></article>
}
