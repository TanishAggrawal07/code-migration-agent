"use client";

import * as React from "react";
import { Navbar } from "@/components/navbar";
import { Sidebar } from "@/components/sidebar";

export default function ShellLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [collapsed, setCollapsed] = React.useState(false);

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      <Navbar />
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar — hidden on mobile, visible md+ */}
        <div className="hidden md:flex shrink-0">
          <Sidebar
            collapsed={collapsed}
            onToggle={() => setCollapsed((c) => !c)}
          />
        </div>
        {/* Main content */}
        <main
          className="flex-1 overflow-y-auto bg-background"
          id="main-content"
        >
          <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
