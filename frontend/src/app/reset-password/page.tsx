"use client";

import { useState, FormEvent, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { authResetPassword } from "@/lib/api";
import { PasswordInput } from "@/components/password-input";

type Status = "idle" | "success" | "error";

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<Status>("idle");
  const [message, setMessage] = useState("");

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setStatus("idle");
    setMessage("");

    if (!token) {
      setStatus("error");
      setMessage("Token reset tidak ditemukan di URL.");
      return;
    }
    if (password.length < 6) {
      setStatus("error");
      setMessage("Password minimal 6 karakter.");
      return;
    }
    if (password !== confirm) {
      setStatus("error");
      setMessage("Konfirmasi password tidak cocok.");
      return;
    }

    setLoading(true);
    try {
      const res = await authResetPassword(token, password);
      setStatus("success");
      setMessage(res.detail || "Password berhasil direset.");
      setTimeout(() => router.push("/login"), 2000);
    } catch (err) {
      setStatus("error");
      setMessage(
        err instanceof Error && err.message
          ? err.message
          : "Gagal mereset password. Coba lagi nanti."
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
          Reset Password
        </h1>
        <p className="text-sm text-zinc-400 text-center mb-6">
          Buat password baru untuk akun Anda.
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
          <PasswordInput
            placeholder="Password baru"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <PasswordInput
            placeholder="Konfirmasi password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            required
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full mt-6 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white rounded-xl font-medium transition-colors"
        >
          {loading ? "Memproses..." : "Reset Password"}
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

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={null}>
      <ResetPasswordForm />
    </Suspense>
  );
}
