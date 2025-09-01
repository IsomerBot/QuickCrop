import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Photo Cropping Tool - Isomer',
  description: 'Professional photo cropping and resizing tool for consistent team photos',
  icons: {
    icon: '/favicon.ico',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-gray-900">
        {children}
      </body>
    </html>
  );
}