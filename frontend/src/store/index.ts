// Grand Contract v1.0 — M12 Global state (Zustand)
import { create } from "zustand";
import type { User } from "../types";

interface AuthState {
  user: User | null;
  setUser: (user: User | null) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  setUser: (user) => set({ user }),
}));
