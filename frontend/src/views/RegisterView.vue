<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { acceptInvitation, previewInvitation } from "../api/invitations.api.js";
import { useAuthStore } from "../stores/auth.js";

const auth = useAuthStore();
const route = useRoute();
const router = useRouter();
const invitation = ref(null);
const password = ref("");
const confirmation = ref("");
const error = ref("");
const isLoading = ref(false);
const isSaving = ref(false);
const canRetry = ref(false);
const isUnusable = ref(false);
let activeRequest;
let isDisposed = false;
const invitationToken = computed(() => {
  const params = new URLSearchParams(route.hash.slice(1));
  const tokens = params.getAll("token");
  return tokens.length === 1 && /^[A-Za-z0-9_-]{43}$/.test(tokens[0])
    ? tokens[0]
    : "";
});

function clearPasswords() {
  password.value = "";
  confirmation.value = "";
}
async function loadInvitation() {
  activeRequest?.abort();
  invitation.value = null;
  clearPasswords();
  error.value = "";
  canRetry.value = false;
  isUnusable.value = false;
  isSaving.value = false;
  isLoading.value = false;
  if (auth.isAuthenticated) return;
  if (!invitationToken.value) {
    error.value =
      "This invitation link is missing or invalid. Open the full link you received.";
    return;
  }
  const controller = new AbortController();
  activeRequest = controller;
  isLoading.value = true;
  try {
    const result = await previewInvitation(
      invitationToken.value,
      controller.signal,
    );
    if (!controller.signal.aborted && !isDisposed) invitation.value = result;
  } catch (failure) {
    if (!controller.signal.aborted && !isDisposed) {
      error.value = failure.message;
      canRetry.value = failure.status !== 400 && failure.status !== 422;
    }
  } finally {
    if (activeRequest === controller) isLoading.value = false;
  }
}
watch([() => route.hash, () => auth.isAuthenticated], loadInvitation, {
  immediate: true,
});
onBeforeUnmount(() => {
  isDisposed = true;
  activeRequest?.abort();
  clearPasswords();
});
async function submit() {
  if (
    isSaving.value ||
    !invitation.value ||
    isUnusable.value ||
    auth.isAuthenticated
  )
    return;
  error.value = "";
  if (password.value !== confirmation.value) {
    error.value = "Passwords do not match.";
    return;
  }
  // Match Python's character count, including characters outside the BMP.
  const length = Array.from(password.value).length;
  if (length < 15 || length > 128) {
    error.value = "Use between 15 and 128 characters for your password.";
    return;
  }
  const controller = new AbortController();
  activeRequest = controller;
  isSaving.value = true;
  try {
    await acceptInvitation(
      invitationToken.value,
      password.value,
      controller.signal,
    );
    if (controller.signal.aborted || isDisposed) return;
    clearPasswords();
    await router.replace({ name: "login", query: { registered: "1" } });
  } catch (failure) {
    if (!controller.signal.aborted && !isDisposed) {
      error.value = failure.message;
      isUnusable.value = [400, 409].includes(failure.status);
    }
  } finally {
    if (activeRequest === controller) {
      clearPasswords();
      isSaving.value = false;
    }
  }
}
</script>

<template>
  <main id="main" class="registration-layout">
    <section
      class="panel registration-panel"
      aria-labelledby="registration-title"
    >
      <p class="eyebrow">YOUR INVITATION TO CONNECT</p>
      <h1 id="registration-title" tabindex="-1">Join your space.</h1>
      <p class="muted">Create your TelemetryHub account.</p>
      <template v-if="auth.isAuthenticated">
        <p class="message">
          You are signed in as {{ auth.user.email }}. Sign out to create the
          invited account.
        </p>
        <button class="button primary" type="button" @click="auth.logout">
          Sign out to register
        </button>
      </template>
      <template v-else>
        <p v-if="isLoading" role="status">Checking your invitation…</p>
        <p
          v-if="error"
          id="registration-error"
          class="message error"
          role="alert"
        >
          {{ error }}
        </p>
        <button
          v-if="canRetry"
          class="button secondary"
          type="button"
          @click="loadInvitation"
        >
          Retry
        </button>
        <form v-if="invitation" @submit.prevent="submit" :aria-busy="isSaving">
          <label for="registration-email">Email address</label>
          <input
            id="registration-email"
            :value="invitation.email"
            type="email"
            autocomplete="username"
            readonly
          >
          <label for="registration-password">Password</label>
          <input
            id="registration-password"
            v-model="password"
            type="password"
            autocomplete="new-password"
            required
            :readonly="isSaving || isUnusable"
            :aria-describedby="error ? 'password-help registration-error' : 'password-help'"
          >
          <p id="password-help" class="muted password-help">
            Use 15–128 characters.
          </p>
          <label for="registration-confirmation">Confirm password</label>
          <input
            id="registration-confirmation"
            v-model="confirmation"
            type="password"
            autocomplete="new-password"
            required
            :readonly="isSaving || isUnusable"
            :aria-describedby="error ? 'registration-error' : undefined"
          >
          <button
            class="button primary"
            type="submit"
            :disabled="isSaving || isUnusable"
          >
            {{ isSaving ? "Creating account…" : "Create account"
            }}<span aria-hidden="true">→</span>
          </button>
        </form>
      </template>
      <RouterLink class="sign-in-link" :to="{ name: 'login' }"
        >Back to sign in</RouterLink
      >
    </section>
  </main>
</template>

<style scoped lang="scss">
.registration-layout { width: min(480px, 90%); margin: auto; padding: 1.5rem 0; }
.registration-panel { padding: 1.75rem 2rem; }
h1 { font-size: 1.8rem; letter-spacing: -.04em; margin: .75rem 0; }
form { display: grid; margin-top: 1.25rem; }
input { margin: .4rem 0 1rem; }
input[readonly] { opacity: .8; }
.password-help { font-size: .8rem; margin: -.5rem 0 1rem; }
.primary { justify-content: space-between; }
.sign-in-link { display: inline-block; color: var(--accent); margin-top: 1.25rem; }
@media (max-width: 480px) { .registration-panel { padding: 1.5rem; } }
@media (min-width: 681px) and (max-height: 740px) {
  .registration-layout { padding-block: .75rem; }
  .registration-panel { padding: 1rem 1.5rem; }
  form { margin-top: .75rem; }
  input { margin-bottom: .75rem; }
}
</style>
