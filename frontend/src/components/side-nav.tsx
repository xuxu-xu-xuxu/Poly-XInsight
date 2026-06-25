"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, Download, Library, MessageCircle, Microscope, Network } from "lucide-react";

const navItems = [
  { href: "/", label: "聊天", icon: MessageCircle },
  { href: "/library", label: "文献库", icon: Library },
  { href: "/downloads", label: "下载", icon: Download },
  { href: "/entities", label: "实体", icon: Microscope },
  { href: "/graph", label: "图谱", icon: Network },
  { href: "/analytics", label: "分析", icon: BarChart3 },
];

export function SideNav() {
  const pathname = usePathname();

  return (
    <nav
      className="flex flex-col items-center gap-2 py-5 w-[72px] shrink-0"
      style={{ backgroundColor: "#1a2744" }}
    >
      {navItems.map((item) => {
        const isActive = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
        const Icon = item.icon;

        return (
          <Link
            key={item.href}
            href={item.href}
            className={`flex flex-col items-center gap-1 px-2 py-2 w-[56px] rounded-lg transition-colors ${
              isActive
                ? "bg-white/20 text-white"
                : "text-[#8fa4c0] opacity-50 hover:opacity-80"
            }`}
          >
            <Icon className="w-5 h-5" />
            <span className="text-[9px] font-medium font-heading">{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
