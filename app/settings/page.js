"use client";

import { useEffect, useState } from "react";
import CampusFuelNav from "../components/Navbar/CampusFuelNav";
import Header from "../components/Header/Header";
import { useApp } from "../context/AppContext";
import styles from "./settings.module.css";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function SettingsPage() {
  const { user, userProfile, refreshUser } = useApp();
  const [form, setForm] = useState({ name: "", goal: "", diet_type: "" });
  const [passwordForm, setPasswordForm] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });
  const [saving, setSaving] = useState(false);
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [passwordMessage, setPasswordMessage] = useState("");

  useEffect(() => {
    setForm({
      name: userProfile?.name || "",
      goal: userProfile?.goal || "",
      diet_type: userProfile?.diet_type || "",
    });
  }, [userProfile]);

  const handleSave = async () => {
    setSaving(true);
    setMessage("");
    try {
      const token = localStorage.getItem("token") || sessionStorage.getItem("token");
      const response = await fetch(`${API_BASE_URL}/api/profile`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
          "ngrok-skip-browser-warning": "true",
        },
        body: JSON.stringify(form),
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok || data?.success === false) {
        setMessage(data?.error || "Failed to update profile.");
        setSaving(false);
        return;
      }

      await refreshUser(token);
      setMessage("Profile updated.");
    } catch {
      setMessage("Failed to update profile.");
    } finally {
      setSaving(false);
    }
  };

  const handlePasswordChange = async () => {
    if (!passwordForm.current_password || !passwordForm.new_password) {
      setPasswordMessage("Current and new password are required.");
      return;
    }
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setPasswordMessage("New passwords do not match.");
      return;
    }

    setPasswordSaving(true);
    setPasswordMessage("");
    try {
      const token = localStorage.getItem("token") || sessionStorage.getItem("token");
      const response = await fetch(`${API_BASE_URL}/api/change-password`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
          "ngrok-skip-browser-warning": "true",
        },
        body: JSON.stringify(passwordForm),
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok || data?.success === false) {
        setPasswordMessage(data?.error || "Failed to change password.");
        return;
      }

      setPasswordMessage("Password changed successfully.");
      setPasswordForm({ current_password: "", new_password: "", confirm_password: "" });
    } catch {
      setPasswordMessage("Failed to change password.");
    } finally {
      setPasswordSaving(false);
    }
  };

  return (
    <div className={styles.layout}>
      <CampusFuelNav />
      <div className={styles.main}>
        <Header title="Settings" username={user?.username || ""} />
        <div className={styles.content}>
          <div className={styles.card}>
            <h2 className={styles.title}>Profile Settings</h2>
            <label className={styles.label}>Name</label>
            <input className={styles.input} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />

            <label className={styles.label}>Goal</label>
            <select className={styles.input} value={form.goal} onChange={(e) => setForm({ ...form, goal: e.target.value })}>
              <option value="">Select goal</option>
              <option value="fat loss">Fat loss</option>
              <option value="muscle gain">Muscle gain</option>
              <option value="maintenance">Maintenance</option>
              <option value="general health">General health</option>
            </select>

            <label className={styles.label}>Diet type</label>
            <select className={styles.input} value={form.diet_type} onChange={(e) => setForm({ ...form, diet_type: e.target.value })}>
              <option value="">Select diet</option>
              <option value="omnivore">Omnivore</option>
              <option value="vegetarian">Vegetarian</option>
              <option value="vegan">Vegan</option>
              <option value="halal">Halal</option>
              <option value="kosher">Kosher</option>
            </select>

            <button className={styles.btn} type="button" onClick={handleSave} disabled={saving}>
              {saving ? "Saving..." : "Save Changes"}
            </button>

            {message && <p className={styles.message}>{message}</p>}

            <div className={styles.passwordCard}>
              <h3 className={styles.subtitle}>Change Password</h3>
              <label className={styles.label}>Current password</label>
              <input
                type="password"
                className={styles.input}
                value={passwordForm.current_password}
                onChange={(e) => setPasswordForm({ ...passwordForm, current_password: e.target.value })}
              />

              <label className={styles.label}>New password</label>
              <input
                type="password"
                className={styles.input}
                value={passwordForm.new_password}
                onChange={(e) => setPasswordForm({ ...passwordForm, new_password: e.target.value })}
              />

              <label className={styles.label}>Confirm new password</label>
              <input
                type="password"
                className={styles.input}
                value={passwordForm.confirm_password}
                onChange={(e) => setPasswordForm({ ...passwordForm, confirm_password: e.target.value })}
              />

              <button className={styles.btn} type="button" onClick={handlePasswordChange} disabled={passwordSaving}>
                {passwordSaving ? "Updating..." : "Update Password"}
              </button>
              {passwordMessage && <p className={styles.note}>{passwordMessage}</p>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
