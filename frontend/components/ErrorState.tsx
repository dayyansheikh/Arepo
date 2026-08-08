export function ErrorState({
  message,
  title = "Couldn't load this data",
}: {
  message: string;
  title?: string;
}) {
  // A cold-start message (the API waking up on a free host) is not an error: show a restrained,
  // non-alarming "connecting" state with an aria status role instead of alert (spec §13).
  const isColdStart = message.startsWith("Connecting to Arepo data");
  if (isColdStart) {
    return (
      <div className="panel p-6 text-center space-y-1" role="status" aria-live="polite">
        <p className="font-medium">Connecting to Arepo data…</p>
        <p className="text-sm text-muted-fg">
          The server may be waking up. This usually takes a few seconds.
        </p>
      </div>
    );
  }
  return (
    <div className="panel p-6 text-center space-y-1" role="alert">
      <p className="font-medium">{title}</p>
      <p className="text-sm text-muted-fg">{message}</p>
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="panel p-6 text-center text-sm text-muted-fg">{message}</div>
  );
}
