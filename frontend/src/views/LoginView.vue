<script setup>
import { onBeforeUnmount, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import BaseButton from "../components/BaseButton.vue";
import BaseInput from "../components/BaseInput.vue";
import OrbitIllustration from "../components/OrbitIllustration.vue";
import { useAuthStore } from "../stores/auth.js";
import { useNotificationStore } from "../stores/notifications.js";

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();
const email = ref("");
const password = ref("");
const isLoading = ref(false);
const notifications = useNotificationStore();
watch(
  () => route.fullPath,
  () => {
    if (route.query.expired)
      notifications.show({
        key: "login",
        variant: "error",
        message: "Your session has expired. Please sign in again.",
      });
    else if (route.query.registered === "1")
      notifications.show({
        key: "registration",
        variant: "success",
        message: "Account created. Sign in with your new password.",
      });
  },
  { immediate: true, flush: "post" },
);
let isDisposed = false;
onBeforeUnmount(() => {
  isDisposed = true;
  if (isLoading.value) auth.logout();
  password.value = "";
});
async function submit() {
  if (isLoading.value) return;
  const origin = document.activeElement;
  isLoading.value = true;
  notifications.remove("login");
  try {
    const signedIn = await auth.signIn(email.value, password.value);
    password.value = "";
    isLoading.value = false;
    if (signedIn && !isDisposed) await router.replace({ name: "profile" });
  } catch (failure) {
    if (!isDisposed)
      notifications.show({
        key: "login",
        variant: "error",
        message: failure.message,
        origin,
      });
  } finally {
    password.value = "";
    isLoading.value = false;
  }
}
</script>

<template>
  <main id="main" class="login-layout">
    <section class="login-intro" aria-label="Welcome to TelemetryHub">
      <p class="eyebrow">
        <span aria-hidden="true">✦</span>
        A NETWORK OF POSSIBILITIES
      </p>
      <h2 class="login-intro__title">
        Your devices.<br>One
        <span class="login-intro__highlight">universe.</span>
      </h2>
      <p class="login-intro__copy">
        A home for your connected world.<br>Bring your people and devices into
        orbit.
      </p>
      <OrbitIllustration class="login-intro__illustration" />
    </section>
    <section class="panel login-panel" aria-labelledby="login-title">
      <div class="login-panel__marker" aria-hidden="true">↗</div>
      <p class="eyebrow">WELCOME ABOARD</p>
      <h1 id="login-title" class="login-panel__title" tabindex="-1">
        Sign in to your space.
      </h1>
      <p class="supporting-text">Enter your details to access TelemetryHub.</p>
      <form
        class="login-panel__form"
        @submit.prevent="submit"
        :aria-busy="isLoading"
      >
        <label class="login-panel__label" for="email">Email address</label>
        <BaseInput
          id="email"
          class="login-panel__input"
          v-model="email"
          type="email"
          autocomplete="username"
          placeholder="you@company.com"
          required
          maxlength="254"
          :readonly="isLoading"
        />
        <label class="login-panel__label" for="password">Password</label>
        <BaseInput
          id="password"
          class="login-panel__input"
          v-model="password"
          type="password"
          autocomplete="current-password"
          placeholder="Enter your password"
          required
          maxlength="128"
          :readonly="isLoading"
        />
        <BaseButton
          class="login-panel__submit"
          variant="primary"
          type="submit"
          :disabled="isLoading"
          spread
        >
          {{ isLoading ? "Signing in…" : "Sign in" }}
          <span aria-hidden="true">→</span>
        </BaseButton>
      </form>
      <p class="login-panel__access-note">
        New to this space? Your administrator or company owner can invite you.
      </p>
      <div class="login-panel__footer">
        <span aria-hidden="true">◇</span>
        YOUR CONNECTION STARTS HERE
      </div>
    </section>
  </main>
</template>

<style scoped lang="scss">
.login-layout {
  width: min(1160px, 90%);
  margin: auto;
  padding: clamp(1rem, 3svh, 3rem) 0;
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  align-items: center;
  gap: 5rem;
}

.login-intro__title {
  font-size: clamp(2.7rem, 5vw, 4.6rem);
  font-weight: 450;
  line-height: 1.08;
  letter-spacing: -0.055em;
  margin: 1.5rem 0;
}

.login-intro__highlight {
  color: var(--accent);
}

.login-intro__copy {
  color: var(--muted);
  font-size: 1rem;
  line-height: 1.8;
}

.login-intro__illustration {
  margin: -1rem 0 -2.5rem -1.5rem;
}

.login-panel {
  padding: 2.5rem;
}

.login-panel__marker {
  display: grid;
  place-items: center;
  width: 2.8rem;
  height: 2.8rem;
  border: 1px solid var(--line);
  border-radius: 0.8rem;
  color: var(--accent);
  font-size: 1.5rem;
  margin-bottom: 2rem;
  background: #96e9db09;
}

.login-panel__title {
  font-size: 1.8rem;
  letter-spacing: -0.04em;
  margin: 0.75rem 0;
}

.login-panel__form {
  margin-top: 2rem;
  display: grid;
}

.login-panel__label {
  font-size: 0.8rem;
  font-weight: 500;
}

.login-panel__input {
  margin: 0.6rem 0 1.4rem;
}

.login-panel__submit {
  margin-top: 0.4rem;
}

.login-panel__access-note {
  margin: 1.5rem 0 2rem;
  color: var(--muted);
  font-size: 0.8rem;
  line-height: 1.7;
}

.login-panel__footer {
  border-top: 1px solid var(--line);
  padding-top: 1.5rem;
  color: var(--muted);
  font-size: 0.6rem;
  letter-spacing: 0.13em;
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

@media (max-width: 850px) {
  .login-layout {
    gap: 2rem;
  }

  .login-panel {
    padding: 1.75rem;
  }
}

@media (max-width: 680px) {
  .login-layout {
    grid-template-columns: 1fr;
    max-width: 440px;
    padding: 2.5rem 0;
  }

  .login-intro {
    display: none;
  }
}

@media (min-width: 681px) and (max-height: 900px) {
  .login-panel {
    padding: 1.5rem 2rem;
  }

  .login-panel__marker {
    margin-bottom: 1rem;
    width: 2.4rem;
    height: 2.4rem;
  }

  .login-panel__form {
    margin-top: 1.25rem;
  }

  .login-panel__input {
    margin: 0.4rem 0 1rem;
  }

  .login-panel__access-note {
    margin: 1rem 0;
  }

  .login-panel__footer {
    padding-top: 1rem;
  }

  .login-intro__title {
    font-size: clamp(2.7rem, 4vw, 3.6rem);
    margin-block: 1rem;
  }

  .login-intro__illustration {
    max-height: 28svh;
    margin-top: 0;
  }
}

@media (min-width: 681px) and (max-height: 740px) {
  .login-panel__marker,
  .login-panel__footer {
    display: none;
  }
}
</style>
