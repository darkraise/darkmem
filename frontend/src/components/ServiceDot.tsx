export function ServiceDot({ ok }: { ok: boolean }) {
  return (
    <span className={`inline-block w-2 h-2 rounded-full ${ok ? "bg-green-500" : "bg-destructive"}`} />
  );
}
