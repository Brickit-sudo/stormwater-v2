export default function Topbar() {
  return (
    <header className="border-b border-[#dbe1d8] bg-white">
      <div className="flex min-h-16 items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <div>
          <p className="text-sm font-semibold text-[#172017]">CRM Workspace</p>
          <p className="text-xs text-[#667466]">Clients, sites, and jobs</p>
        </div>
        <div className="rounded-md border border-[#dbe1d8] px-3 py-1.5 text-xs font-medium text-[#516151]">
          V2 bootstrap
        </div>
      </div>
    </header>
  );
}
