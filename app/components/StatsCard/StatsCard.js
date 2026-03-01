import styles from "./StatsCard.module.css";

export default function StatsCard({ label, value, unit, icon, progress, color = "green", goalText }) {
  return (
    <div className={`${styles.card} ${styles[color]}`}>
      <div className={styles.top}>
        <div className={styles.iconWrap}>{icon}</div>
        <div className={styles.info}>
          <span className={styles.label}>{label}</span>
          <span className={styles.value}>
            {value}
            <span className={styles.unit}>{unit}</span>
            {goalText && <span className={styles.goalText}>{goalText}</span>}
          </span>
        </div>
      </div>
      {progress !== undefined && (
        <div className={styles.progressTrack}>
          <div
            className={styles.progressBar}
            style={{ width: `${Math.min(progress, 100)}%` }}
          />
        </div>
      )}
      {progress !== undefined && (
        <span className={styles.progressLabel}>{progress}% of daily goal</span>
      )}
    </div>
  );
}
