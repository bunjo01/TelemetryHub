<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { acceptInvitation, previewInvitation } from "../api/invitations.api.js";
import BaseButton from "../components/BaseButton.vue";
import BaseInput from "../components/BaseInput.vue";
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
      <h1
        id="registration-title"
        class="registration-panel__title"
        tabindex="-1"
      >
        Join your space.
      </h1>
      <p class="supporting-text">Create your TelemetryHub account.</p>
      <template v-if="auth.isAuthenticated">
        <p class="message">
          You are signed in as {{ auth.user.email }}. Sign out to create the
          invited account.
        </p>
        <BaseButton variant="primary" type="button" spread @click="auth.logout">
          Sign out to register
        </BaseButton>
      </template>
      <template v-else>
        <p v-if="isLoading" role="status">Checking your invitation…</p>
        <p
          v-if="error"
          id="registration-error"
          class="message message--error"
          role="alert"
        >
          {{ error }}
        </p>
        <BaseButton
          v-if="canRetry"
          variant="secondary"
          type="button"
          @click="loadInvitation"
        >
          Retry
        </BaseButton>
        <form
          v-if="invitation"
          class="registration-panel__form"
          @submit.prevent="submit"
          :aria-busy="isSaving"
        >
          <label class="registration-panel__label" for="registration-email"
            >Email address</label
          >
          <BaseInput
            id="registration-email"
            class="registration-panel__input"
            :model-value="invitation.email"
            type="email"
            autocomplete="username"
            readonly
          />
          <label class="registration-panel__label" for="registration-password"
            >Password</label
          >
          <BaseInput
            id="registration-password"
            class="registration-panel__input"
            v-model="password"
            type="password"
            autocomplete="new-password"
            required
            :readonly="isSaving || isUnusable"
            :aria-describedby="error ? 'password-help registration-error' : 'password-help'"
          />
          <p
            id="password-help"
            class="supporting-text registration-panel__password-help"
          >
            Use 15–128 characters.
          </p>
          <label
            class="registration-panel__label"
            for="registration-confirmation"
            >Confirm password</label
          >
          <BaseInput
            id="registration-confirmation"
            class="registration-panel__input"
            v-model="confirmation"
            type="password"
            autocomplete="new-password"
            required
            :readonly="isSaving || isUnusable"
            :aria-describedby="error ? 'registration-error' : undefined"
          />
          <BaseButton
            variant="primary"
            type="submit"
            :disabled="isSaving || isUnusable"
            spread
          >
            {{ isSaving ? "Creating account…" : "Create account" }}
            <span aria-hidden="true">→</span>
          </BaseButton>
        </form>
      </template>
      <RouterLink
        class="registration-panel__sign-in-link"
        :to="{ name: 'login' }"
        >Back to sign in</RouterLink
      >
    </section>
  </main>
</template>

<style scoped lang="scss">
.registration-layout {
  width: min(480px, 90%);
  margin: auto;
  padding: 1.5rem 0;
}

.registration-panel {
  padding: 1.75rem 2rem;
}

.registration-panel__title {
  font-size: 1.8rem;
  letter-spacing: -0.04em;
  margin: 0.75rem 0;
}

.registration-panel__form {
  display: grid;
  margin-top: 1.25rem;
}

.registration-panel__label {
  font-size: 0.8rem;
  font-weight: 500;
}

.registration-panel__input {
  margin: 0.4rem 0 1rem;
}

.registration-panel__input[readonly] {
  opacity: 0.8;
}

.registration-panel__password-help {
  --supporting-text-font-size: 0.8rem;
  margin: -0.5rem 0 1rem;
}

.registration-panel__sign-in-link {
  display: inline-block;
  color: var(--accent);
  margin-top: 1.25rem;
}

@media (max-width: 480px) {
  .registration-panel {
    padding: 1.5rem;
  }
}

@media (min-width: 681px) and (max-height: 740px) {
  .registration-layout {
    padding-block: 0.75rem;
  }

  .registration-panel {
    padding: 1rem 1.5rem;
  }

  .registration-panel__form {
    margin-top: 0.75rem;
  }

  .registration-panel__input {
    margin-bottom: 0.75rem;
  }
}
</style>
