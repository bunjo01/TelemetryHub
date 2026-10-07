<script setup>
import { useRouter } from "vue-router";
import { useAuthStore } from "./stores/auth.js";

const auth = useAuthStore();
const router = useRouter();
function signOut() {
  auth.logout();
  router.replace({ name: "login" });
}
</script>

<template>
  <div class="universe">
    <a class="skip-link" href="#main">Skip to content</a>
    <header class="site-header">
      <RouterLink
        class="brand"
        :to="auth.isAuthenticated ? '/profile' : '/'"
        aria-label="TelemetryHub home"
      >
        <span class="brand-symbol" aria-hidden="true">✧</span>
        Telemetry<span>Hub</span>
      </RouterLink>
      <button
        v-if="auth.isAuthenticated"
        class="button secondary compact"
        type="button"
        @click="signOut"
      >
        Sign out <span aria-hidden="true">↗</span>
      </button>
      <span v-else class="header-label">YOUR WORLD. CONNECTED.</span>
    </header>
    <RouterView />
    <footer class="site-footer">
      <span>TelemetryHub</span><span>A little closer to everything.</span
      ><span class="footer-coordinate" aria-hidden="true"
        >◌ &nbsp; CONNECTED POSSIBILITIES</span
      >
    </footer>
  </div>
</template>

<style scoped lang="scss">
.universe { min-height: 100svh; display: flex; flex-direction: column; position: relative; isolation: isolate; overflow: hidden; }
.universe::before { content: ""; position: absolute; inset: 0; z-index: -1; pointer-events: none; opacity: .55; background-image: radial-gradient(1px 1px at 22px 37px, #b4ccd5 70%, transparent 100%), radial-gradient(1px 1px at 125px 173px, #8099bb 70%, transparent 100%); background-size: 197px 211px, 283px 307px; mask-image: linear-gradient(#000, #0005); }
.site-header, .site-footer { display: flex; justify-content: space-between; align-items: center; gap: 1.5rem; padding: clamp(.75rem, 2svh, 1.8rem) 5%; }
.site-header { border-bottom: 1px solid var(--line); }
.brand { display: flex; align-items: center; text-decoration: none; color: var(--text); font-size: 1.25rem; font-weight: 650; letter-spacing: -.04em; gap: .12rem; }
.brand > span:last-child { font-weight: 350; color: var(--muted); }
.brand-symbol { font-size: 2rem; color: var(--accent); margin-right: .6rem; }
.header-label, .footer-coordinate { font-size: .65rem; letter-spacing: .18em; color: var(--muted); }
.site-footer { padding-block: .75rem; margin-top: auto; color: var(--muted); font-size: .75rem; border-top: 1px solid var(--line); }
.skip-link { position: absolute; top: -5rem; left: 1rem; z-index: 5; background: var(--panel); padding: 1rem; color: var(--text); }
.skip-link:focus { top: 1rem; }
@media (max-width: 600px) { .header-label, .footer-coordinate { display: none; } .site-header, .site-footer { padding: 1.2rem 6%; } }
</style>
