"use client";

import { useState, FormEvent } from "react";
import Link from "next/link";
import { authForgotPassword } from "@/lib/api";

type Status = "idle" | "success" | "error";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<Status>("idle");
  const [message, setMessage] = useState("");

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setStatus("idle");
    setMessage("");
    setLoading(true);
    try {
      const res = await authForgotPassword(email);
      setStatus("success");
      setMessage(res.detail || "Tautan reset password telah dikirim ke email Anda.");
    } catch (err) {
      setStatus("error");
      setMessage(
        err instanceof Error && err.message
          ? err.message
          : "Gagal mengirim permintaan. Coba lagi nanti."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex items-center justify-center min-h-screen px-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm p-6 bg-zinc-900 border border-zinc-800 rounded-2xl"
      >
        <h1 className="text-2xl font-bold text-zinc-100 mb-2 text-center">
          Lupa Password
        </h1>
        <p className="text-sm text-zinc-400 text-center mb-6">
          Masukkan email akun Anda untuk menerima tautan reset password.
        </p>

        {status === "success" && (
          <div className="mb-4 p-3 bg-green-950/30 border border-green-900/50 rounded-xl text-green-400 text-sm">
            {message}
          </div>
        )}
        {status === "error" && (
          <div className="mb-4 p-3 bg-red-950/30 border border-red-900/50 rounded-xl text-red-400 text-sm">
            {message}
          </div>
        )}

        <div className="space-y-4">
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-xl text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full mt-6 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white rounded-xl font-medium transition-colors"
        >
          {loading ? "Memproses..." : "Kirim Tautan Reset"}
        </button>

        <p className="mt-4 text-center text-sm text-zinc-500">
          Ingat password?{" "}
          <Link href="/login" className="text-blue-400 hover:text-blue-300">
            Login
          </Link>
        </p>
      </form>
    </main>
  );
}
