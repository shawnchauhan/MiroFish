<template>
  <div class="not-found">
    <div class="not-found-content">
      <h1>404</h1>
      <p>Page not found</p>
      <router-link to="/" class="home-link">Back to Home</router-link>
    </div>
  </div>
</template>

<script setup>
</script>

<style scoped>
.not-found {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: #fafafa;
  font-family: 'JetBrains Mono', monospace;
}

.not-found-content {
  text-align: center;
}

.not-found-content h1 {
  font-size: 6rem;
  font-weight: 700;
  margin: 0;
  color: #1a1a1a;
}

.not-found-content p {
  font-size: 1.2rem;
  color: #666;
  margin: 0.5rem 0 2rem;
}

.home-link {
  display: inline-block;
  padding: 0.75rem 2rem;
  background: #1a1a1a;
  color: #fff;
  text-decoration: none;
  font-size: 0.9rem;
  transition: background 0.2s;
}

.home-link:hover {
  background: #333;
}
</style>
