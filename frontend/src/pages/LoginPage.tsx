// Grand Contract v1.0 — M1 Login page
import React from "react";
import { redirectToLogin } from "../api/auth";

export const LoginPage: React.FC = () => (
  <div className="flex items-center justify-center h-screen bg-gray-950">
    <div className="bg-gray-900 p-10 rounded-xl flex flex-col gap-6 w-96">
      <h1 className="text-2xl font-bold text-white text-center">TrafficCount</h1>
      <button
        onClick={() => redirectToLogin("google")}
        className="bg-white text-gray-900 rounded-lg py-3 font-semibold hover:bg-gray-100"
      >
        Sign in with Google
      </button>
      <button
        onClick={() => redirectToLogin("yandex")}
        className="bg-yellow-400 text-gray-900 rounded-lg py-3 font-semibold hover:bg-yellow-300"
      >
        Sign in with Yandex
      </button>
    </div>
  </div>
);
