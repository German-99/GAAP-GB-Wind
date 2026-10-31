export default function Status({ loading, error, className = "" }) {
  if (error) return <p className={`status error ${className}`}>{error.message}</p>;
  if (loading) return <p className={`status ${className}`}>Loading…</p>;
  return null;
}