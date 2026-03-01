import { Inter } from "next/font/google";
import { SpeedInsights } from "@vercel/speed-insights/next";
import ThemeProvider from "./components/ThemeProvider";
import { AppProvider } from "./context/AppContext";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata = {
  title: "CampusFuel",
  description: "Your campus nutrition tracker",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        {/* Prevent flash of wrong theme on first paint */}
        <script dangerouslySetInnerHTML={{ __html: `
          try {
            var t = localStorage.getItem('cf-theme');
            if (t === 'dark') {
              document.documentElement.setAttribute('data-theme', 'dark');
            }
          } catch(e) {}
        `}} />
      </head>
      <body className={inter.className}>
        <ThemeProvider>
          <AppProvider>
            {children}
          </AppProvider>
        </ThemeProvider>
        <SpeedInsights />
      </body>
    </html>
  );
}
