<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { searchCompanies } from "../api/companies.api.js";
import { inviteOwner } from "../api/invitations.api.js";
import { useAuthStore } from "../stores/auth.js";

const emit = defineEmits(["close"]);
const auth = useAuthStore();
const router = useRouter();
const dialog = ref(null);
const emailInput = ref(null);
const dropdown = ref(null);
const searchInput = ref(null);
const email = ref("");
const query = ref("");
const selected = ref(null);
const companies = ref([]);
const offset = ref(0);
const hasMore = ref(false);
const isLoading = ref(false);
const isSaving = ref(false);
const searchError = ref("");
const error = ref("");
const invitation = ref(null);
let searchRequest;
let invitationRequest;
let debounce;
let isDisposed = false;

onMounted(() => {
  dialog.value.showModal();
  emailInput.value.focus();
  loadCompanies(0);
});
onBeforeUnmount(() => {
  isDisposed = true;
  clearTimeout(debounce);
  searchRequest?.abort();
  invitationRequest?.abort();
});
watch(query, () => {
  clearTimeout(debounce);
  searchRequest?.abort();
  companies.value = [];
  hasMore.value = false;
  searchError.value = "";
  isLoading.value = true;
  debounce = setTimeout(() => loadCompanies(0), 250);
});
async function handleFailure(failure, destination) {
  if (failure.status === 401) {
    auth.logout();
    await router.replace({ name: "login", query: { expired: "1" } });
  } else destination.value = failure.message;
}
async function loadCompanies(nextOffset) {
  clearTimeout(debounce);
  searchRequest?.abort();
  const controller = new AbortController();
  searchRequest = controller;
  isLoading.value = true;
  searchError.value = "";
  try {
    const result = await searchCompanies(
      query.value,
      nextOffset,
      auth.token,
      controller.signal,
    );
    if (controller.signal.aborted || isDisposed) return;
    companies.value = result.items;
    hasMore.value = result.hasMore;
    offset.value = nextOffset;
  } catch (failure) {
    if (!controller.signal.aborted && !isDisposed) {
      companies.value = [];
      hasMore.value = false;
      await handleFailure(failure, searchError);
    }
  } finally {
    if (searchRequest === controller) isLoading.value = false;
  }
}
function close() {
  if (isSaving.value) return;
  dialog.value.close();
  emit("close");
}
async function onDropdownToggle() {
  if (dropdown.value?.open) {
    await nextTick();
    searchInput.value?.focus();
  }
}
function selectCompany(company) {
  selected.value = company;
  dropdown.value.open = false;
  dropdown.value.querySelector("summary").focus();
  error.value = "";
}
function escapeDropdown(event) {
  if (dropdown.value?.open) {
    event.preventDefault();
    event.stopPropagation();
    dropdown.value.open = false;
    dropdown.value.querySelector("summary").focus();
  }
}
async function submit() {
  if (isSaving.value) return;
  error.value = "";
  if (!selected.value) {
    error.value = "Choose a company from the dropdown.";
    dropdown.value.open = true;
    return;
  }
  isSaving.value = true;
  dropdown.value.open = false;
  searchRequest?.abort();
  clearTimeout(debounce);
  const controller = new AbortController();
  invitationRequest = controller;
  try {
    invitation.value = await inviteOwner(
      selected.value.id,
      email.value,
      auth.token,
      controller.signal,
    );
    if (isDisposed) return;
    await nextTick();
    dialog.value.querySelector(".invitation-result")?.focus();
  } catch (failure) {
    if (!controller.signal.aborted && !isDisposed)
      await handleFailure(failure, error);
  } finally {
    isSaving.value = false;
    isLoading.value = false;
  }
}
</script>

<template>
  <dialog
    ref="dialog"
    class="panel owner-dialog"
    aria-labelledby="owner-title"
    @cancel.prevent="close"
  >
    <div class="dialog-heading">
      <h2 id="owner-title">Invite company owner</h2>
      <button
        class="close-button"
        type="button"
        aria-label="Close invite owner"
        :disabled="isSaving"
        @click="close"
      >
        ×
      </button>
    </div>
    <section
      v-if="invitation"
      class="invitation-result"
      tabindex="-1"
      aria-label="Invitation created"
    >
      <p class="message success" role="status">
        Invitation created for {{ invitation.email }} at {{ selected.name }}.
      </p>
      <p class="muted">
        No email was sent. Share this invitation token with the owner. It is
        only available here until you close this popup.
      </p>
      <label for="owner-token">Invitation token</label>
      <textarea
        id="owner-token"
        :value="invitation.token"
        readonly
        rows="3"
        spellcheck="false"
      />
      <p class="muted">
        Expires {{ new Date(invitation.expiresAt).toLocaleString() }}.
      </p>
    </section>
    <form v-else @submit.prevent="submit" :aria-busy="isSaving">
      <label for="owner-email">Owner email address</label>
      <input
        id="owner-email"
        ref="emailInput"
        v-model="email"
        type="email"
        required
        maxlength="254"
        autocomplete="email"
        placeholder="owner@company.com"
        :readonly="isSaving"
        :aria-describedby="error ? 'owner-error' : undefined"
      >
      <span id="company-picker-label" class="field-label">Company</span>
      <details
        ref="dropdown"
        class="company-picker"
        @toggle="onDropdownToggle"
        @keydown.esc="escapeDropdown"
      >
        <summary
          aria-labelledby="company-picker-label company-selection"
          :inert="isSaving"
        >
          <span id="company-selection">{{
            selected?.name ?? "Select a company"
          }}</span><span aria-hidden="true">⌄</span>
        </summary>
        <div class="company-options" :inert="isSaving">
          <label class="field-label" for="company-search"
            >Search companies</label
          >
          <input
            id="company-search"
            ref="searchInput"
            v-model="query"
            type="search"
            maxlength="200"
            autocomplete="off"
            placeholder="Type a company name"
            @keydown.enter.prevent
          >
          <p v-if="isLoading" class="muted" role="status">
            Searching companies…
          </p>
          <div v-else-if="searchError">
            <p class="message error" role="alert">{{ searchError }}</p>
            <button
              type="button"
              class="button secondary"
              @click="loadCompanies(0)"
            >
              Retry search
            </button>
          </div>
          <template v-else>
            <p v-if="!companies.length" class="muted" role="status">
              No companies found. Try a different name or create a company
              first.
            </p>
            <ul v-else class="company-results" aria-label="Matching companies">
              <li v-for="company in companies" :key="company.id">
                <button
                  type="button"
                  class="company-option"
                  :aria-pressed="selected?.id === company.id"
                  :title="company.name"
                  @click="selectCompany(company)"
                >
                  <span class="company-node" aria-hidden="true">{{
                    selected?.id === company.id ? "✓" : "◇"
                  }}</span>
                  <span class="company-name">{{ company.name }}</span>
                </button>
              </li>
            </ul>
            <div class="pagination">
              <button
                v-if="offset > 0"
                type="button"
                class="button secondary"
                @click="loadCompanies(offset - 20)"
              >
                Previous
              </button>
              <button
                v-if="hasMore && offset < 10000"
                type="button"
                class="button secondary"
                @click="loadCompanies(offset + 20)"
              >
                Next
              </button>
              <p v-if="hasMore && offset >= 10000" class="muted">
                Narrow your search to find more companies.
              </p>
            </div>
          </template>
        </div>
      </details>
      <p v-if="error" id="owner-error" class="message error" role="alert">
        {{ error }}
      </p>
      <button class="button primary" type="submit" :disabled="isSaving">
        {{ isSaving ? "Creating invitation…" : "Invite owner" }}
      </button>
    </form>
  </dialog>
</template>

<style scoped lang="scss">
.owner-dialog { width: min(480px, calc(100% - 2rem)); max-height: calc(100svh - 2rem); padding: 1.75rem; color: var(--text); overflow: visible; }
.owner-dialog::backdrop { background: #030810b8; backdrop-filter: blur(5px); }
.dialog-heading { display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: 1.75rem; }
h2 { font-size: 1.4rem; font-weight: 500; margin: 0; }
.close-button { display: grid; place-items: center; width: 2.75rem; height: 2.75rem; flex-shrink: 0; padding: 0; border: 1px solid var(--line); border-radius: .5rem; background: transparent; color: var(--muted); font-size: 1.5rem; }
form { display: grid; gap: .75rem; }
form > .primary { margin-top: .75rem; }
.field-label { font-size: .8rem; font-weight: 500; }
.company-picker { position: relative; border: 1px solid #8aa5c02b; border-radius: .5rem; background: #09121e; }
summary { display: flex; justify-content: space-between; align-items: center; gap: .75rem; padding: .8rem 1rem; cursor: pointer; overflow-wrap: anywhere; }
summary::-webkit-details-marker { display: none; }
.company-options {
  position: absolute;
  z-index: 2;
  top: calc(100% + .35rem);
  left: -1px;
  right: -1px;
  display: flex;
  flex-direction: column;
  max-height: min(28rem, calc(50svh - 6rem));
  overflow: hidden;
  border: 1px solid #8aa5c040;
  border-radius: .65rem;
  padding: 1rem;
  background: #101b28;
  box-shadow: 0 16px 40px #0008;
}
.company-options > :not(.company-results) { flex-shrink: 0; }
.company-options input { display: block; width: 100%; margin-top: .5rem; }
.company-results {
  --row-height: 3rem;
  --row-gap: .375rem;
  display: flex;
  flex-direction: column;
  gap: var(--row-gap);
  list-style: none;
  padding: 0 .35rem 0 0;
  margin: .75rem 0;
  min-height: 0;
  // Four complete rows at most; smaller screens can show fewer.
  max-height: calc(4 * var(--row-height) + 3 * var(--row-gap));
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-width: thin;
  scrollbar-color: #507d82 #09121e;
}
.company-results::-webkit-scrollbar { width: 6px; }
.company-results::-webkit-scrollbar-track { background: #09121e; border-radius: 1rem; }
.company-results::-webkit-scrollbar-thumb { background: #507d82; border-radius: 1rem; }
.company-results::-webkit-scrollbar-thumb:hover { background: var(--accent); }
.company-results li { flex: 0 0 var(--row-height); min-height: 0; }
.company-option {
  display: flex;
  align-items: center;
  gap: .65rem;
  width: 100%;
  height: 100%;
  padding: .5rem .7rem;
  text-align: left;
  background: linear-gradient(110deg, #1b3442, #132332);
  color: var(--text);
  border: 1px solid #74b9b52b;
  border-radius: .4rem;
  box-shadow: inset 2px 0 #76c6bc55;
  transition: background .15s, border-color .15s, box-shadow .15s;
}
.company-option:hover, .company-option[aria-pressed="true"] {
  background: linear-gradient(110deg, #244d51, #182d3f);
  border-color: #9be5d580;
  box-shadow: inset 3px 0 var(--accent), inset 0 0 18px #9be5d50c;
}
.company-option:focus-visible { outline-offset: -3px; }
.company-node { color: var(--accent); flex-shrink: 0; text-shadow: 0 0 10px #9be5d566; }
.company-name { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: .875rem; }
.pagination { display: flex; justify-content: space-between; gap: .5rem; }
textarea { display: block; width: 100%; margin-top: .5rem; background: #09121e; color: var(--text); border: 1px solid var(--line); border-radius: .5rem; padding: .75rem; resize: vertical; font: inherit; }
.invitation-result { overflow-wrap: anywhere; }
</style>
