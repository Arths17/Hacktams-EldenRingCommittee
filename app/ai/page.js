"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import CampusFuelNav from "../components/Navbar/CampusFuelNav";
import styles from "./ai.module.css";

export default function AIPage() {
  const router = useRouter();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [profileReady, setProfileReady] = useState(false);
  const [profileName, setProfileName] = useState("");
  const [checkingProfile, setCheckingProfile] = useState(true);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  // Check for profile on mount
  useEffect(() => {
    const saved = localStorage.getItem("campusfuel_profile");
    if (saved) {
      try {
        const p = JSON.parse(saved);
        setProfileName(p.name || "");
        setProfileReady(true);
      } catch {
        setProfileReady(false);
      }
    } else {
      setProfileReady(false);
    }
    setCheckingProfile(false);
  }, []);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function sendMessage() {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    // Placeholder for streaming AI response
    const aiMsgIndex = messages.length + 1;
    setMessages((prev) => [...prev, { role: "ai", content: "" }]);

    try {
      const token = localStorage.getItem("token");
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ message: text }),
      });

      if (!res.ok) throw new Error(`Server error: ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let aiText = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        aiText += decoder.decode(value, { stream: true });
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = { role: "ai", content: aiText };
          return updated;
        });
      }
    } catch (err) {
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "ai",
          content: `⚠️ Could not reach the AI server. Make sure the backend is running on port 8000.\n\n\`${err.message}\``,
          error: true,
        };
        return updated;
      });
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  const SUGGESTED = [
    "Give me a meal plan for today",
    "What should I eat before a 3-hour study session?",
    "I'm on a tight budget — what's a high-protein cheap meal?",
    "I only slept 4 hours, what should I eat?",
    "Help me reduce stress with nutrition",
  ];

  if (checkingProfile) return null;

  // No profile → prompt survey
  if (!profileReady) {
    return (
      <div className={styles.layout}>
        <CampusFuelNav />
        <div className={styles.main}>
          <div className={styles.gateWrap}>
            <div className={styles.gateCard}>
              <div className={styles.gateEmoji}>🤖</div>
              <h2 className={styles.gateTitle}>Meet Your AI Health Coach</h2>
              <p className={styles.gateSub}>
                Before we start, CampusFuel needs to learn about you — your goals,
                schedule, diet, and lifestyle — so it can give truly personalized advice.
              </p>
              <p className={styles.gateNote}>
                ⏱ Takes about <strong>2 minutes</strong>. You only do this once.
              </p>
              <button
                className={styles.gateBtn}
                onClick={() => router.push("/survey")}
              >
                Start My Health Profile →
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.layout}>
      <CampusFuelNav />
      <div className={styles.main}>
        {/* Header */}
        <div className={styles.header}>
          <div className={styles.headerLeft}>
            <span className={styles.aiAvatar}>🤖</span>
            <div>
              <h1 className={styles.headerTitle}>AI Health Coach</h1>
              <span className={styles.headerSub}>
                Personalized nutrition & wellness for {profileName || "you"}
              </span>
            </div>
          </div>
          <button
            className={styles.retakeBtn}
            onClick={() => router.push("/survey")}
            title="Update your health profile"
          >
            ✏️ Update Profile
          </button>
        </div>

        {/* Chat area */}
        <div className={styles.chatArea}>
          {messages.length === 0 && (
            <div className={styles.empty}>
              <div className={styles.emptyEmoji}>💬</div>
              <p className={styles.emptyText}>
                Ask anything about nutrition, energy, sleep, stress, or meal planning.
              </p>
              <div className={styles.suggestions}>
                {SUGGESTED.map((s) => (
                  <button
                    key={s}
                    className={styles.suggestion}
                    onClick={() => { setInput(s); inputRef.current?.focus(); }}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              className={`${styles.msgRow} ${msg.role === "user" ? styles.userRow : styles.aiRow}`}
            >
              {msg.role === "ai" && (
                <div className={styles.aiAvatarSmall}>🤖</div>
              )}
              <div
                className={`${styles.bubble} ${msg.role === "user" ? styles.userBubble : styles.aiBubble} ${msg.error ? styles.errorBubble : ""}`}
              >
                {msg.content
                  ? msg.content.split("\n").map((line, j) => (
                      <span key={j}>
                        {line}
                        {j < msg.content.split("\n").length - 1 && <br />}
                      </span>
                    ))
                  : <span className={styles.typing}>●●●</span>}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        {/* Input area */}
        <div className={styles.inputArea}>
          <textarea
            ref={inputRef}
            className={styles.chatInput}
            placeholder="Ask your AI health coach anything..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={2}
            disabled={loading}
          />
          <button
            className={styles.sendBtn}
            onClick={sendMessage}
            disabled={loading || !input.trim()}
          >
            {loading ? "..." : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}
