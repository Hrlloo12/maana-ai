import type { Metadata } from "next";
import "./globals.css";
import Footer from "@/components/Footer";
import Nav from "@/components/Nav";

export const metadata: Metadata = {
  title: "مَعنى | هل وصل المعنى كما قصدته؟",
  icons: { icon: "/icon.svg" },
  description: "مَعنى يساعد صنّاع المحتوى الإسلامي على معرفة ما إذا كان المعنى الذي قصدوه قد وصل إلى جمهورهم، وعلى شرحه بطريقة أوضح.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ar" dir="rtl">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&family=IBM+Plex+Sans+Arabic:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <Nav />
        <main className="mx-auto w-full max-w-6xl px-4 pb-24 pt-10 sm:px-6">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
