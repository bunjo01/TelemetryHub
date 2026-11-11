import { nextTick } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "./stores/auth.js";
import { useNotificationStore } from "./stores/notifications.js";
import DeviceListView from "./views/DeviceListView.vue";
import LoginView from "./views/LoginView.vue";
import ProfileView from "./views/ProfileView.vue";
import RegisterView from "./views/RegisterView.vue";

export function makeRouter(pinia, history = createWebHistory()) {
  const router = createRouter({
    history,
    routes: [
      { path: "/", name: "login", component: LoginView },
      { path: "/register", name: "register", component: RegisterView },
      {
        path: "/profile",
        name: "profile",
        component: ProfileView,
        meta: { requiresAuth: true },
      },
      {
        path: "/devices",
        name: "devices",
        component: DeviceListView,
        meta: {
          requiresAuth: true,
          roles: ["company_owner", "member"],
        },
      },
      { path: "/:pathMatch(.*)*", redirect: "/" },
    ],
  });
  router.beforeEach((to) => {
    const auth = useAuthStore(pinia);
    if (to.meta.requiresAuth && !auth.isAuthenticated) {
      return { name: "login" };
    }

    if (to.meta.roles && !to.meta.roles.includes(auth.user?.role)) {
      return { name: "profile" };
    }

    if (to.name === "login" && auth.isAuthenticated) {
      return { name: "profile" };
    }
  });
  router.afterEach(async (to, from, failure) => {
    if (failure) return;

    const titles = {
      profile: "Your profile",
      register: "Create account",
      login: "Sign in",
      devices: "Devices",
    };

    document.title = `${titles[to.name] ?? "TelemetryHub"} · TelemetryHub`;

    if (to.path === from.path) return;

    useNotificationStore(pinia).clear();

    await nextTick();

    if (router.currentRoute.value.fullPath !== to.fullPath) return;

    document.querySelector("h1")?.focus();
  });
  return router;
}
