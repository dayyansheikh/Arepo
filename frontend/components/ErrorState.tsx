export function ErrorState({
  message,
  title = "Couldn't load this data",
}: {
  message: string;
  title?: string;
}) {
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
