"use client";
import { usePathname } from "next/navigation";
import { SideNav } from "@/components/side-nav";
import { AuthGuard } from "@/components/auth-guard";

const PUBLIC_PATHS = ["/login", "/register"];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isPublic = PUBLIC_PATHS.includes(pathname);

  if (isPublic) {
    return <>{children}</>;
  }

  return (
    <>
      <SideNav />
      <main className="flex-1 min-w-0 overflow-hidden">
        <AuthGuard>{children}</AuthGuard>
      </main>
    </>
  );
}
