"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function Login() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/");
  }, [router]);

  return (
    <main style={{ maxWidth: 440, margin: "100px auto", padding: 24, textAlign: "center" }}>
      <p style={{ opacity: 0.7 }}>Redirecting to Studio Dashboard...</p>
    </main>
  );
}
