// app/components/Navbar/Navbar/CampusFuelNav.js
import styles from "./CampusFuelNav.module.css";

export default function CampusFuelNav() {
  return (
    <header className={styles.navbar}>
      <div className={styles.navbarInner}>
        {/* Left: logo */}
        <a href="/" className={styles.brand}>
          <span className={styles.brandMark}>🌿</span>
          <span className={styles.brandText}>CampusFuel</span>
        </a>

        {/* Center: main links */}
        <nav className={styles.navLinks}>
          <a href="/dashboard">Dashboard</a>
          <a href="/ai">AI Coach</a>
          <a href="/survey">Survey</a>
          <a href="#">Nutrition</a>
          <a href="#">Progress</a>
          <a href="#">Meals</a>
        </nav>

        {/* Right: actions */}
        <div className={styles.navActions}>
          <a href="/ai" className={styles.btnAi}>
            🤖 AI Coach
          </a>
          <a href="/login" className={styles.btnPrimary}>
            Sign in
          </a>
        </div>
      </div>
    </header>
  );
}

