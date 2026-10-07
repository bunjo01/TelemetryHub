import { nextTick } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "./stores/auth.js";
import LoginView from "./views/LoginView.vue";
import ProfileView from "./views/ProfileView.vue";

export function makeRouter(pinia, history = createWebHistory()) {
  const router = createRouter({
    history,
    routes: [
      { path: "/", name: "login", component: LoginView },
      { path: "/profile", name: "profile", component: ProfileView },
      { path: "/:pathMatch(.*)*", redirect: "/" },
    ],
  });
  router.beforeEach((to) => {
    const auth = useAuthStore(pinia);
    if (to.name === "profile" && !auth.isAuthenticated)
      return { name: "login" };
    if (to.name === "login" && auth.isAuthenticated) return { name: "profile" };
  });
  router.afterEach(async (to) => {
    document.title = `${to.name === "profile" ? "Your profile" : "Sign in"} · TelemetryHub`;
    await nextTick();
    document.querySelector("h1")?.focus();
  });
  return router;
}
