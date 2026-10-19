<script setup>
import { onBeforeUnmount, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import BaseButton from "../components/BaseButton.vue";
import BaseInput from "../components/BaseInput.vue";
import OrbitIllustration from "../components/OrbitIllustration.vue";
import { useAuthStore } from "../stores/auth.js";

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();
const email = ref("");
const password = ref("");
const isLoading = ref(false);
const error = ref(
  route.query.expired ? "Your session has expired. Please sign in again." : "",
);
let isDisposed = false;
onBeforeUnmount(() => {
  isDisposed = true;
  if (isLoading.value) auth.logout();
  password.value = "";
});
async function submit() {
  if (isLoading.value) return;
  isLoading.value = true;
  error.value = "";
  try {
    const signedIn = await auth.signIn(email.value, password.value);
    password.value = "";
    isLoading.value = false;
    if (signedIn && !isDisposed) await router.replace({ name: "profile" });
  } catch (failure) {
    if (!isDisposed) error.value = failure.message;
  } finally {
    password.value = "";
    isLoading.value = false;
  }
}
</script>

<template>
  <main id="main" class="login-layout">
    <section class="intro" aria-label="Welcome to TelemetryHub">
      <p class="eyebrow">
        <span aria-hidden="true">✦</span>
        A NETWORK OF POSSIBILITIES
      </p>
      <h2>Your devices.<br>One <span>universe.</span></h2>
      <p class="intro-copy">
        A home for your connected world.<br>Bring your people and devices into
        orbit.
      </p>
      <OrbitIllustration />
    </section>
    <section class="panel login-panel" aria-labelledby="login-title">
      <div class="panel-marker" aria-hidden="true">↗</div>
      <p class="eyebrow">WELCOME ABOARD</p>
      <h1 id="login-title" tabindex="-1">Sign in to your space.</h1>
      <p class="muted">Enter your details to access TelemetryHub.</p>
      <p
        v-if="route.query.registered === '1'"
        class="message success"
        role="status"
      >
        Account created. Sign in with your new password.
      </p>
      <form @submit.prevent="submit" :aria-busy="isLoading">
        <label for="email">Email address</label>
        <BaseInput
          id="email"
          v-model="email"
          type="email"
          autocomplete="username"
          placeholder="you@company.com"
          required
          maxlength="254"
          :readonly="isLoading"
          :aria-describedby="error ? 'login-error' : undefined"
        />
        <label for="password">Password</label>
        <BaseInput
          id="password"
          v-model="password"
          type="password"
          autocomplete="current-password"
          placeholder="Enter your password"
          required
          maxlength="128"
          :readonly="isLoading"
          :aria-describedby="error ? 'login-error' : undefined"
        />
        <p v-if="error" id="login-error" class="message error" role="alert">
          {{ error }}
        </p>
        <BaseButton
          class="primary"
          variant="primary"
          type="submit"
          :disabled="isLoading"
        >
          {{ isLoading ? "Signing in…" : "Sign in"
          }}<span aria-hidden="true">→</span>
        </BaseButton>
      </form>
      <p class="access-note">
        New to this space? Your administrator or company owner can invite you.
      </p>
      <div class="panel-bottom">
        <span aria-hidden="true">◇</span>
        YOUR CONNECTION STARTS HERE
      </div>
    </section>
  </main>
</template>

<style scoped lang="scss">
.login-layout { width: min(1160px, 90%); margin: auto; padding: clamp(1rem, 3svh, 3rem) 0; display: grid; grid-template-columns: 1.2fr 1fr; align-items: center; gap: 5rem; }
.intro h2 { font-size: clamp(2.7rem, 5vw, 4.6rem); font-weight: 450; line-height: 1.08; letter-spacing: -.055em; margin: 1.5rem 0; }
.intro h2 span { color: var(--accent); }
.intro-copy { color: var(--muted); font-size: 1rem; line-height: 1.8; }
.intro :deep(.orbit) { margin: -1rem 0 -2.5rem -1.5rem; }
.login-panel { padding: 2.5rem; }
.panel-marker { display: grid; place-items: center; width: 2.8rem; height: 2.8rem; border: 1px solid var(--line); border-radius: .8rem; color: var(--accent); font-size: 1.5rem; margin-bottom: 2rem; background: #96e9db09; }
h1 { font-size: 1.8rem; letter-spacing: -.04em; margin: .75rem 0; }
form { margin-top: 2rem; display: grid; }
input { margin: .6rem 0 1.4rem; }
.primary { margin-top: .4rem; justify-content: space-between; }
.access-note { margin: 1.5rem 0 2rem; color: var(--muted); font-size: .8rem; line-height: 1.7; }
.panel-bottom { border-top: 1px solid var(--line); padding-top: 1.5rem; color: var(--muted); font-size: .6rem; letter-spacing: .13em; display: flex; align-items: center; gap: .6rem; }
@media (max-width: 850px) { .login-layout { gap: 2rem; } .login-panel { padding: 1.75rem; } }
@media (max-width: 680px) { .login-layout { grid-template-columns: 1fr; max-width: 440px; padding: 2.5rem 0; } .intro { display: none; } }
@media (min-width: 681px) and (max-height: 900px) {
  .login-panel { padding: 1.5rem 2rem; }
  .panel-marker { margin-bottom: 1rem; width: 2.4rem; height: 2.4rem; }
  form { margin-top: 1.25rem; }
  input { margin: .4rem 0 1rem; }
  .access-note { margin: 1rem 0; }
  .panel-bottom { padding-top: 1rem; }
  .intro h2 { font-size: clamp(2.7rem, 4vw, 3.6rem); margin-block: 1rem; }
  .intro :deep(.orbit) { max-height: 28svh; margin-top: 0; }
}
@media (min-width: 681px) and (max-height: 740px) {
  .panel-marker, .panel-bottom { display: none; }
}
</style>
