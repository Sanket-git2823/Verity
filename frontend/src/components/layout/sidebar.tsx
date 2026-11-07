"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Search,
  FileText,
  Microscope,
  BarChart3,
  Activity,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { getSystemHealth } from "@/lib/api";

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
}

const navItems: NavItem[] = [
  { label: "Research", href: "/research", icon: Search },
  { label: "Documents", href: "/documents", icon: FileText },
  { label: "Inspector", href: "/inspector", icon: Microscope },
  { label: "Evaluation", href: "/evaluation", icon: BarChart3 },
  { label: "System", href: "/system", icon: Activity },
];

export function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [healthStatus, setHealthStatus] = useState<
    "healthy" | "degraded" | "unhealthy" | "unknown"
  >("unknown");

  useEffect(() => {
    let mounted = true;
    const checkHealth = async () => {
      try {
        const health = await getSystemHealth();
        if (mounted) setHealthStatus(health.status);
      } catch {
        if (mounted) setHealthStatus("unknown");
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const healthColor = {
    healthy: "bg-emerald-500",
    degraded: "bg-amber-500",
    unhealthy: "bg-red-500",
    unknown: "bg-zinc-600",
  }[healthStatus];

  return (
    <aside
      className={cn(
        "fixed left-0 top-0 h-screen bg-zinc-900 border-r border-zinc-800 flex flex-col z-40 transition-all duration-200",
        collapsed ? "w-14" : "w-48"
      )}
    >
      {/* Logo */}
      <div className="h-12 flex items-center px-4 border-b border-zinc-800">
        <span className="font-mono text-sm font-semibold tracking-[0.25em] text-zinc-100 uppercase">
          {collapsed ? "V" : "Verity"}
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-2">
        {navItems.map((item) => {
          const isActive =
            pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-4 h-9 text-sm transition-colors relative",
                isActive
                  ? "text-zinc-100 bg-zinc-800/50"
                  : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/30"
              )}
            >
              {isActive && (
                <div className="absolute left-0 top-1 bottom-1 w-0.5 bg-zinc-100" />
              )}
              <item.icon className="h-4 w-4 flex-shrink-0" />
              {!collapsed && (
                <span className="truncate">{item.label}</span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Bottom section */}
      <div className="border-t border-zinc-800 p-3">
        <div className="flex items-center gap-2">
          <div className={cn("h-1.5 w-1.5 rounded-full", healthColor)} />
          {!collapsed && (
            <span className="text-[10px] text-zinc-500 uppercase tracking-wider">
              {healthStatus}
            </span>
          )}
        </div>
      </div>

      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="h-8 flex items-center justify-center border-t border-zinc-800 text-zinc-600 hover:text-zinc-400 transition-colors"
      >
        {collapsed ? (
          <ChevronRight className="h-3.5 w-3.5" />
        ) : (
          <ChevronLeft className="h-3.5 w-3.5" />
        )}
      </button>
    </aside>
  );
}
