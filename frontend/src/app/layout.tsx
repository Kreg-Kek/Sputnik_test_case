import React from "react";
import type { Metadata } from "next";
import "bootstrap/dist/css/bootstrap.min.css";
import { Container } from "react-bootstrap";

export async function generateMetadata(): Promise<Metadata> {
  return {
    title: "Тестовое задание Fullstack",
    description: "Тестовое задание Fullstack",
  };
}

type RootLayoutProps = Readonly<{
  children: React.ReactNode;
}>;

export default async function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="ru">
      <head>
        <link rel="icon" href="/favicon.ico" sizes="any" />
      </head>
      <body>
        <Container fluid className="p-0">{children}</Container>
      </body>
    </html>
  );
}