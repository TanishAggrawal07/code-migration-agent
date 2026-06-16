"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ChevronLeft,
  ChevronRight,
  Clock,
  Cpu,
  LayoutDashboard,
  Settings,
  Workflow,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

interface NavItem {
  href: string;
  label: string;
  icon: React.ElementType;
  badge?: string;
}

const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard",  label: "Dashboard",    icon: LayoutDashboard },
  { href: "/migrations", label: "Migrations",   icon: Workflow,        badge: "0" },
  { href: "/history",    label: "History",      icon: Clock },
  { href: "/about",      label: "Architecture", icon: Cpu },
];

const BOTTOM_ITEMS: NavItem[] = [
  { href: "/settings", label: "Settings", icon: Settings },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const pathname = usePathname();

  return (
    // delay={0} is the correct prop for this shadcn/base-ui Tooltip
    <TooltipProvider delay={0}>
      <aside
        aria-label="Main navigation"
        className={cn(
          "sidebar-transition relative flex flex-col h-full border-r border-border/60 bg-sidebar",
          collapsed ? "w-14" : "w-56",
        )}
      >
        {/* Collapse toggle */}
        <button
          type="button"
          onClick={onToggle}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="absolute -right-3 top-6 z-10 flex h-6 w-6 items-center justify-center rounded-full border border-border bg-background text-muted-foreground shadow-sm hover:text-foreground hover:bg-accent transition-colors"
        >
          {collapsed ? (
            <ChevronRight className="h-3 w-3" />
          ) : (
            <ChevronLeft className="h-3 w-3" />
          )}
        </button>

        {/* Primary nav */}
        <nav
          className="flex flex-col gap-1 p-2 pt-4 flex-1"
          aria-label="Primary navigation"
        >
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.href}
              item={item}
              active={
                pathname === item.href ||
                pathname.startsWith(item.href + "/")
              }
              collapsed={collapsed}
            />
          ))}
        </nav>

        {/* Bottom nav */}
        <div className="p-2 pb-4">
          <Separator className="mb-2" />
          {BOTTOM_ITEMS.map((item) => (
            <NavLink
              key={item.href}
              item={item}
              active={pathname === item.href}
              collapsed={collapsed}
            />
          ))}
        </div>
      </aside>
    </TooltipProvider>
  );
}

/* ── NavLink ─────────────────────────────────────────────────────────────── */

function NavLink({
  item,
  active,
  collapsed,
}: {
  item: NavItem;
  active: boolean;
  collapsed: boolean;
}) {
  const Icon = item.icon;

  const linkContent = (
    <Link
      href={item.href}
      aria-current={active ? "page" : undefined}
      className={cn(
        "group flex items-center gap-3 rounded-lg px-2.5 py-2 text-sm font-medium transition-all",
        "hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
        active
          ? "bg-sidebar-accent text-sidebar-primary font-semibold"
          : "text-sidebar-foreground/70",
        collapsed && "justify-center px-0",
      )}
    >
      <Icon
        className={cn(
          "h-4 w-4 shrink-0 transition-colors",
          active
            ? "text-sidebar-primary"
            : "text-muted-foreground group-hover:text-foreground",
        )}
      />

      {!collapsed && (
        <>
          <span className="flex-1 truncate">{item.label}</span>
          {item.badge !== undefined && (
            <Badge
              variant="secondary"
              className="h-5 min-w-5 px-1.5 text-xs tabular-nums bg-muted"
            >
              {item.badge}
            </Badge>
          )}
        </>
      )}
    </Link>
  );

  if (!collapsed) return linkContent;

  // Wrap in tooltip when collapsed — TooltipTrigger wraps a <span> to avoid
  // nesting interactive elements (base-ui doesn't support asChild here)
  return (
    <Tooltip>
      <TooltipTrigger>
        <span className="block">{linkContent}</span>
      </TooltipTrigger>
      <TooltipContent side="right">
        <span className="flex items-center gap-2">
          {item.label}
          {item.badge !== undefined && (
            <Badge variant="secondary" className="h-4 px-1 text-xs">
              {item.badge}
            </Badge>
          )}
        </span>
      </TooltipContent>
    </Tooltip>
  );
}
