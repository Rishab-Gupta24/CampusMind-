export function PageTitle({ children, subtitle }: { children: React.ReactNode; subtitle?: string }) {
  return (
    <div className="mb-6">
      <h1 className="text-[28px] leading-[1.2] font-semibold tracking-tight">{children}</h1>
      {subtitle ? <p className="mt-2 text-[15px] text-text-2">{subtitle}</p> : null}
    </div>
  );
}
