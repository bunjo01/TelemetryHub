<script setup>
import { useRoute, useRouter } from "vue-router";
import BaseButton from "./components/BaseButton.vue";
import ToastHost from "./components/ToastHost.vue";
import { useAuthStore } from "./stores/auth.js";

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();
function focusMain() {
  const main = document.getElementById("main");
  main?.setAttribute("tabindex", "-1");
  main?.focus();
}
function signOut() {
  auth.logout();
  if (route.name !== "register") router.replace({ name: "login" });
}
</script>

<template>
  <div class="app-layout">
    <a class="skip-link" href="#main" @click.prevent="focusMain"
      >Skip to content</a
    >
    <header class="site-header">
      <RouterLink
        class="brand"
        :to="auth.isAuthenticated ? '/profile' : '/'"
        aria-label="TelemetryHub home"
      >
        <span class="brand__symbol" aria-hidden="true">✧</span>
        Telemetry<span class="brand__suffix">Hub</span>
      </RouterLink>
      <BaseButton
        v-if="auth.isAuthenticated"
        variant="secondary"
        type="button"
        compact
        @click="signOut"
      >
        Sign out <span aria-hidden="true">↗</span>
      </BaseButton>
      <span v-else class="site-header__tagline">YOUR WORLD. CONNECTED.</span>
    </header>
    <RouterView />
    <ToastHost />
    <footer class="site-footer">
      <span>TelemetryHub</span><span>A little closer to everything.</span
      ><span class="site-footer__coordinate" aria-hidden="true"
        >◌ &nbsp; CONNECTED POSSIBILITIES</span
      >
    </footer>
  </div>
</template>

<style scoped lang="scss">
.app-layout {
  min-height: 100svh;
  display: flex;
  flex-direction: column;
  position: relative;
  isolation: isolate;
  overflow: hidden;
}

.app-layout::before {
  content: "";
  position: absolute;
  inset: 0;
  z-index: -1;
  pointer-events: none;
  opacity: 0.55;
  background-image:
    radial-gradient(1px 1px at 22px 37px, #b4ccd5 70%, transparent 100%),
    radial-gradient(1px 1px at 125px 173px, #8099bb 70%, transparent 100%);
  background-size: 197px 211px, 283px 307px;
  mask-image: linear-gradient(#000, #0005);
}

.skip-link {
  position: absolute;
  top: -5rem;
  left: 1rem;
  z-index: 5;
  background: var(--panel);
  padding: 1rem;
  color: var(--text);
}

.skip-link:focus {
  top: 1rem;
}

.site-header,
.site-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1.5rem;
  padding: clamp(0.75rem, 2svh, 1.8rem) 5%;
}

.site-header {
  border-bottom: 1px solid var(--line);
}

.site-header__tagline,
.site-footer__coordinate {
  font-size: 0.65rem;
  letter-spacing: 0.18em;
  color: var(--muted);
}

.brand {
  display: flex;
  align-items: center;
  text-decoration: none;
  color: var(--text);
  font-size: 1.25rem;
  font-weight: 650;
  letter-spacing: -0.04em;
  gap: 0.12rem;
}

.brand__symbol {
  font-size: 2rem;
  color: var(--accent);
  margin-right: 0.6rem;
}

.brand__suffix {
  font-weight: 350;
  color: var(--muted);
}

.site-footer {
  padding-block: 0.75rem;
  margin-top: auto;
  color: var(--muted);
  font-size: 0.75rem;
  border-top: 1px solid var(--line);
}

@media (max-width: 600px) {
  .site-header__tagline,
  .site-footer__coordinate {
    display: none;
  }

  .site-header,
  .site-footer {
    padding: 1.2rem 6%;
  }
}
</style>
