import { createPinia } from "pinia";
import { createApp } from "vue";
import App from "./App.vue";
import { makeRouter } from "./router.js";
import "./styles.scss";

const pinia = createPinia();
createApp(App).use(pinia).use(makeRouter(pinia)).mount("#app");
