export default function Carregando() {
  return (
    <div className="flex items-center justify-center py-32" role="status">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-borda border-t-marca" />
      <span className="sr-only">Carregando</span>
    </div>
  );
}
