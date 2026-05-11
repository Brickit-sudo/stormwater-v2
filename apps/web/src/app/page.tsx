import Link from "next/link";

const links = [
  {
    href: "/crm/clients",
    title: "Clients",
    description: "Start with accounts and their primary contact details.",
  },
  {
    href: "/crm/sites",
    title: "Sites",
    description: "Manage locations tied to client records.",
  },
  {
    href: "/crm/jobs",
    title: "Jobs",
    description: "Track scheduled work for client and site combinations.",
  },
];

export default function Home() {
  return (
    <main className="min-h-screen bg-[#f4f6f3] px-6 py-12 text-[#172017]">
      <section className="mx-auto flex min-h-[calc(100vh-6rem)] max-w-5xl flex-col justify-center">
        <div className="max-w-2xl">
          <h1 className="text-4xl font-semibold tracking-normal text-[#172017]">
            Stormwater CRM
          </h1>
          <p className="mt-4 text-base leading-7 text-[#5f6d5f]">
            Use the CRM workspace to manage clients, sites, and jobs against the
            new V2 API.
          </p>
        </div>

        <div className="mt-8 grid gap-3 sm:grid-cols-3">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="rounded-md border border-[#dbe1d8] bg-white p-5 transition hover:border-[#b9c9b6] hover:bg-[#fbfcfa]"
            >
              <span className="text-lg font-semibold text-[#172017]">
                {link.title}
              </span>
              <span className="mt-2 block text-sm leading-6 text-[#667466]">
                {link.description}
              </span>
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
