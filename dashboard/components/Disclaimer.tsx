// Required by the spec: every view must carry the not-financial-advice notice.
export function Disclaimer() {
  return (
    <p className="text-xs text-muted border border-border rounded-md px-3 py-2 bg-panel/50">
      This is experimental research tooling. Not financial advice.
    </p>
  );
}
