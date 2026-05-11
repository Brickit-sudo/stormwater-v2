type EmptyStateProps = {
  title: string;
  description?: string;
};

export default function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="flex min-h-44 flex-col items-center justify-center rounded-md border border-dashed border-[#cfd8cc] bg-white px-6 py-8 text-center">
      <p className="text-sm font-semibold text-[#172017]">{title}</p>
      {description ? (
        <p className="mt-2 max-w-md text-sm leading-6 text-[#667466]">
          {description}
        </p>
      ) : null}
    </div>
  );
}
