import "./globals.css";

export const metadata = {
  title: "CampusFuel",
  description: "Your campus nutrition tracker",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
