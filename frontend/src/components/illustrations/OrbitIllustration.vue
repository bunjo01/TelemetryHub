<template>
  <svg class="orbit" viewBox="0 0 600 400" fill="none" aria-hidden="true">
    <defs>
      <radialGradient id="planet">
        <stop stop-color="#254d60" />
        <stop offset=".7" stop-color="#102738" />
        <stop offset="1" stop-color="#091320" />
      </radialGradient>
      <linearGradient
        id="rim"
        x1="200"
        y1="120"
        x2="350"
        y2="290"
        gradientUnits="userSpaceOnUse"
      >
        <stop stop-color="#8be6dc" />
        <stop offset="1" stop-color="#183044" />
      </linearGradient>
    </defs>
    <ellipse
      cx="300"
      cy="215"
      rx="255"
      ry="111"
      transform="rotate(-20 300 215)"
      stroke="#537388"
      stroke-opacity=".22"
    />
    <ellipse
      cx="300"
      cy="215"
      rx="210"
      ry="74"
      transform="rotate(-20 300 215)"
      stroke="#81c9ce"
      stroke-opacity=".3"
      stroke-dasharray="3 9"
    />
    <circle cx="300" cy="215" r="93" fill="url(#planet)" stroke="url(#rim)" />
    <ellipse
      cx="300"
      cy="215"
      rx="40"
      ry="93"
      stroke="#4f8190"
      stroke-opacity=".3"
      transform="rotate(-25 300 215)"
    />
    <ellipse
      cx="300"
      cy="215"
      rx="93"
      ry="32"
      stroke="#4f8190"
      stroke-opacity=".3"
      transform="rotate(-25 300 215)"
    />
    <path
      d="M109 276 261 188 466 126M261 188l75 53 87 64"
      stroke="#74dacf"
      stroke-opacity=".35"
      stroke-dasharray="4 5"
    />
    <g fill="#97efe0">
      <circle cx="261" cy="188" r="5" />
      <circle cx="336" cy="241" r="4" />
      <circle cx="423" cy="305" r="4" />
    </g>
    <g stroke="#8de5d7">
      <rect x="90" y="257" width="38" height="38" rx="11" fill="#112932" />
      <path d="M102 270h14v12h-14zM105 266v4m7-4v4m-7 12v4m7-4v4" />
      <rect x="447" y="107" width="38" height="38" rx="11" fill="#112932" />
      <path d="M460 133v-6m6 6v-12m6 12v-18" />
    </g>
    <circle cx="300" cy="215" r="108" stroke="#548696" stroke-opacity=".1" />
    <g fill="#748c9e" font-family="monospace" font-size="9" letter-spacing="2">
      <text x="61" y="322">EDGE / 01</text>
      <text x="441" y="90">NODE / 02</text>
      <text x="250" y="367">ONE CONNECTED WORLD</text>
    </g>
  </svg>
</template>

<style scoped lang="scss">
.orbit {
  width: 100%;
  max-width: 37.5rem;
  display: block;
}
</style>
