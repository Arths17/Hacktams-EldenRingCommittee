"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import styles from "./Sidebar.module.css";

const navItems = [
  { label: "Dashboard", href: "/dashboard", icon: "⊞" },
  { label: "Meals", href: "/meals", icon: "🍽" },
  { label: "Nutrition", href: "/nutrition", icon: "📊" },
  { label: "Progress", href: "/progress", icon: "📈" },
  { label: "AI Coach", href: "/ai", icon: "🤖" },
  { label: "Profile", href: "/profile", icon: "👤" },
  { label: "Settings", href: "/settings", icon: "⚙" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside className={`${styles.sidebar} ${collapsed ? styles.collapsed : ""}`}>
      <div className={styles.brand}>
        <span className={styles.logo}>🌿</span>
        {!collapsed && <span className={styles.brandName}>CampusFuel</span>}
      </div>

      <button
        className={styles.collapseBtn}
        onClick={() => setCollapsed((c) => !c)}
        aria-label="Toggle sidebar"
      >
        {collapsed ? "›" : "‹"}
      </button>

      <nav className={styles.nav}>
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`${styles.navItem} ${pathname === item.href ? styles.active : ""}`}
          >
            <span className={styles.icon}>{item.icon}</span>
            {!collapsed && <span className={styles.label}>{item.label}</span>}
          </Link>
        ))}
      </nav>

      <div className={styles.footer}>
        {!collapsed && <span className={styles.footerText}>© 2026 CampusFuel</span>}
      </div>
    </aside>
  );
}
