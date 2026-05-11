type EmptyStateProps = {
  title: string;
  description?: string;
};

export default function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="flex min-h-44 flex-col items-center justify-center rounded-lg border border-dashed border-border-strong bg-panel/60 px-6 py-10 text-center">
      <p className="text-sm font-semibold text-text">{title}</p>
      {description ? (
        <p className="mt-2 max-w-md text-sm leading-6 text-text-muted">
          {description}
        </p>
      ) : null}
    </div>
  );
}
