import { defineStore } from "pinia";
import { computed, ref } from "vue";
import { getProfile, login } from "../api/auth.api.js";
import { useNotificationStore } from "./notifications.js";

export const useAuthStore = defineStore("auth", () => {
  const token = ref("");
  const user = ref(null);
  const isAuthenticated = computed(() => Boolean(token.value && user.value));
  let activeRequest;

  function logout() {
    useNotificationStore().clear();
    activeRequest?.abort();
    activeRequest = undefined;
    token.value = "";
    user.value = null;
  }

  async function signIn(email, password) {
    logout();
    const controller = new AbortController();
    activeRequest = controller;
    try {
      const nextToken = await login(
        email.trim().toLowerCase(),
        password,
        controller.signal,
      );
      const profile = await getProfile(nextToken, controller.signal);
      if (controller.signal.aborted) return false;
      token.value = nextToken;
      user.value = profile;
      return true;
    } finally {
      if (activeRequest === controller) activeRequest = undefined;
    }
  }

  return { token, user, isAuthenticated, signIn, logout };
});
